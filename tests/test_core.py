import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pytest

from typed_settings import _core
from typed_settings._dict_utils import _deep_options
from typed_settings.attrs import option, settings
from typed_settings.converters import (
    BaseConverter,
    default_converter,
    register_strlist_hook,
)
from typed_settings.loaders import EnvLoader, FileLoader, Loader, TomlFormat


@settings(frozen=True)
class Host:
    name: str
    port: int


@settings(frozen=True)
class Settings:
    host: Host
    url: str
    default: int = 3


class TestLoadSettings:
    """Tests for load_settings()."""

    config = """[example]
        url = "https://example.com"
        [example.host]
        name = "example.com"
        port = 443
    """

    @pytest.fixture
    def config_files(self, tmp_path: Path) -> List[Path]:
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(self.config)
        return [config_file]

    @pytest.fixture
    def env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXAMPLE_HOST_PORT", "42")

    @pytest.fixture
    def loaders(
        self, config_files: List[Path], env_vars: None
    ) -> List[Loader]:
        return [
            FileLoader(
                formats={"*.toml": TomlFormat("example")},
                files=config_files,
            ),
            EnvLoader(prefix="EXAMPLE_"),
        ]

    def test__load_settings(self, loaders: List[Loader]) -> None:
        """
        "_load_settings()" is the internal core loader and takes a list of
        options instead of a normal settings class.  It returns a dict and
        not a settings instance.
        """
        settings = _core._load_settings(
            cls=Settings,
            options=_deep_options(Settings),
            loaders=loaders,
        )
        assert settings == {
            "url": "https://example.com",
            "default": 3,  # This is from the cls
            "host": {
                "name": "example.com",
                "port": "42",  # Value not yet converted
            },
        }

    def test_load_settings(self, loaders: List[Loader]) -> None:
        """
        The "load_settings()" works like "_load_settings" but takes a settings
        class and returns an instance of it.
        """
        settings = _core.load_settings(
            cls=Settings,
            loaders=loaders,
        )
        assert settings == Settings(
            url="https://example.com",
            default=3,
            host=Host(
                name="example.com",
                port=42,
            ),
        )

    def test_load(self, config_files: List[Path], env_vars: None) -> None:
        """
        The "load()" shortcut automaticaly defines a file loader and an
        env loader.  Section and env var names are derived from the app name.
        """
        settings = _core.load(
            cls=Settings,
            appname="example",
            config_files=config_files,
        )
        assert settings == Settings(
            url="https://example.com",
            default=3,
            host=Host(
                name="example.com",
                port=42,  # Loaded from env var
            ),
        )

    def test_explicit_section(self, tmp_path: Path) -> None:
        """
        The automatically derived config section name name can be overriden.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[le-section]
            spam = "eggs"
        """
        )

        @settings(frozen=True)
        class Settings:
            spam: str = ""

        result = _core.load(
            cls=Settings,
            appname="example",
            config_files=[config_file],
            config_file_section="le-section",
        )
        assert result == Settings(spam="eggs")

    def test_explicit_files_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        The automatically derived settings files var name can be overriden.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[example]
            spam = "eggs"
        """
        )

        monkeypatch.setenv("LE_SETTINGS", str(config_file))

        @settings(frozen=True)
        class Settings:
            spam: str = ""

        result = _core.load(
            cls=Settings,
            appname="example",
            config_files=[],
            config_files_var="LE_SETTINGS",
        )
        assert result == Settings(spam="eggs")

    def test_no_files_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Setting config files via an env var can be disabled.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[example]
            spam = "eggs"
        """
        )

        monkeypatch.setenv("EXAMPLE_SETTINGS", str(config_file))

        @settings(frozen=True)
        class Settings:
            spam: str = ""

        result = _core.load(
            cls=Settings,
            appname="example",
            config_files=[],
            config_files_var=None,
        )
        assert result == Settings(spam="")

    def test_env_var_dash_underscore(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        Dashes in the appname get replaced with underscores for the settings
        fiels var name.
        """

        @settings(frozen=True)
        class Settings:
            option: bool = True

        sf = tmp_path.joinpath("settings.toml")
        sf.write_text("[a-b]\noption = false\n")
        monkeypatch.setenv("A_B_SETTINGS", str(sf))

        result = _core.load(Settings, appname="a-b")
        assert result == Settings(option=False)

    def test_explicit_env_prefix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("P_SPAM", "spam")

        @settings(frozen=True)
        class Settings:
            spam: str = ""

        result = _core.load(
            cls=Settings, appname="example", config_files=[], env_prefix="P_"
        )
        assert result == Settings(spam="spam")

    def test_disable_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXAMPLE_SPAM", "spam")

        @settings(frozen=True)
        class Settings:
            spam: str = ""

        result = _core.load(
            cls=Settings, appname="example", config_files=[], env_prefix=None
        )
        assert result == Settings(spam="")

    def test_load_nested_settings_by_default(self) -> None:
        """
        Instantiate nested settings with default settings and pass it to the
        parent settings even if no nested settings are defined in a config
        file or env var.

        Otherwise, the parent classed needed to set a default_factory for
        creating a nested settings instance.
        """

        @settings
        class Nested:
            a: int = 3
            b: str = "spam"

        @settings
        class Settings:
            nested: Nested

        s = _core.load(Settings, "test")
        assert s == Settings(Nested())

    def test_default_factories(self) -> None:
        """
        The default value "attr.Factory" is handle as if "attr.NOTHING" was
        set.

        See: https://gitlab.com/sscherfke/typed-settings/-/issues/6
        """

        @settings
        class S:
            opt: List[int] = option(factory=list)

        result = _core.load(S, "t")
        assert result == S()

    def test_custom_converter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        A custom cattr converter can be used in "load_settings()".
        """

        class Test:
            def __init__(self, x: int):
                self.attr = x

            def __eq__(self, other):
                return self.attr == other.attr

        @settings
        class Settings:
            opt: Test

        monkeypatch.setenv("TEST_OPT", "42")

        converter = BaseConverter()
        converter.register_structure_hook(Test, lambda v, t: Test(int(v)))

        result = _core.load_settings(Settings, [EnvLoader("TEST_")], converter)
        assert result == Settings(Test(42))

    @pytest.mark.parametrize(
        "vals, kwargs",
        [
            (["3,4,42", "spam,eggs"], {"sep": ","}),
            (["3:4:42", "spam:eggs"], {"sep": ":"}),
            (['[3,4,"42"]', '["spam","eggs"]'], {"fn": json.loads}),
        ],
    )
    def test_load_list_from_env(
        self,
        vals: List[str],
        kwargs: Dict[str, Any],
        loaders: List[Loader],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Lists can be loaded from env vars
        """
        c = default_converter()
        register_strlist_hook(c, **kwargs)

        @settings
        class Settings:
            x: List[int]
            y: List[Path]
            z: List[int]

        # The str2list hook should not interfere with loading of "normal"
        # lists.
        sf = tmp_path.joinpath("settings.toml")
        sf.write_text("[example]\nz = [1, 2]\n")

        monkeypatch.setenv("EXAMPLE_X", vals[0])
        monkeypatch.setenv("EXAMPLE_Y", vals[1])

        result = _core.load_settings(Settings, loaders, c)
        assert result == Settings(
            x=[3, 4, 42], y=[Path("spam"), Path("eggs")], z=[1, 2]
        )

    def test_load_empty_cls(self) -> None:
        """
        Empty classes are no special case.
        """

        @settings
        class Settings:
            pass

        result = _core.load(Settings, "example")
        assert result == Settings()


class TestLogging:
    """
    Test emitted log messages.
    """

    def test_successfull_loading(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        In case of success, only DEBUG messages are emitted.
        """

        @settings
        class S:
            opt: str

        sf1 = tmp_path.joinpath("sf1.toml")
        sf1.write_text('[test]\nopt = "spam"\n')
        sf2 = tmp_path.joinpath("sf2.toml")
        sf2.write_text('[test]\nopt = "eggs"\n')
        monkeypatch.setenv("TEST_SETTINGS", str(sf2))
        monkeypatch.setenv("TEST_OPT", "bacon")

        caplog.set_level(logging.DEBUG)

        _core.load(S, "test", [sf1])

        assert caplog.record_tuples == [
            (
                "typed_settings",
                logging.DEBUG,
                "Env var for config files: TEST_SETTINGS",
            ),
            ("typed_settings", logging.DEBUG, f"Loading settings from: {sf1}"),
            ("typed_settings", logging.DEBUG, f"Loading settings from: {sf2}"),
            (
                "typed_settings",
                logging.DEBUG,
                "Looking for env vars with prefix: TEST_",
            ),
            ("typed_settings", logging.DEBUG, "Env var found: TEST_OPT"),
        ]

    def test_optional_files_not_found(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Non-existing optional files emit an INFO message if file was specified
        by the app (passed to "load_settings()") an a WARNING message if the
        file was specified via an environment variable.
        """

        @settings
        class S:
            opt: str = ""

        sf1 = tmp_path.joinpath("sf1.toml")
        sf2 = tmp_path.joinpath("sf2.toml")
        monkeypatch.setenv("TEST_SETTINGS", str(sf2))

        caplog.set_level(logging.DEBUG)

        _core.load(S, "test", [sf1])

        assert caplog.record_tuples == [
            (
                "typed_settings",
                logging.DEBUG,
                "Env var for config files: TEST_SETTINGS",
            ),
            ("typed_settings", logging.INFO, f"Config file not found: {sf1}"),
            (
                "typed_settings",
                logging.WARNING,
                f"Config file from TEST_SETTINGS not found: {sf2}",
            ),
            (
                "typed_settings",
                logging.DEBUG,
                "Looking for env vars with prefix: TEST_",
            ),
            ("typed_settings", logging.DEBUG, "Env var not found: TEST_OPT"),
        ]

    def test_mandatory_files_not_found(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        In case of success, only ``debug`` messages are emitted.
        """

        @settings
        class S:
            opt: str = ""

        sf1 = tmp_path.joinpath("sf1.toml")
        monkeypatch.setenv("TEST_SETTINGS", f"!{sf1}")

        caplog.set_level(logging.DEBUG)

        with pytest.raises(FileNotFoundError):
            _core.load(S, "test")

        assert caplog.record_tuples == [
            (
                "typed_settings",
                logging.DEBUG,
                "Env var for config files: TEST_SETTINGS",
            ),
            (
                "typed_settings",
                logging.ERROR,
                f"Mandatory config file not found: {sf1}",
            ),
        ]
