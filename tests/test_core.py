"""
Tests for "typed_settings._core".
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, cast

import attrs
import cattrs
import pytest

from typed_settings import _core, dict_utils, exceptions
from typed_settings._compat import PY_310
from typed_settings.cls_attrs import option, settings
from typed_settings.converters import (
    default_converter,
    get_default_cattrs_converter,
    register_strlist_hook,
)
from typed_settings.loaders import DictLoader, EnvLoader, FileLoader, Loader, TomlFormat
from typed_settings.types import (
    LoadedSettings,
    LoadedValue,
    LoaderMeta,
    OptionList,
    SettingsClass,
    SettingsDict,
)


@settings(frozen=True)
class Host:
    """Host settings."""

    name: str
    port: int


@settings(frozen=True)
class Settings:
    """Main settings."""

    host: "Host"  # Assert that types are resolved
    url: str
    default: int = option(default=3, validator=attrs.validators.gt(0))


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
    def loaders(self, config_files: List[Path], env_vars: None) -> List[Loader]:
        return [
            FileLoader(
                formats={"*.toml": TomlFormat("example")},
                files=config_files,
            ),
            EnvLoader(prefix="EXAMPLE_"),
        ]

    def test__load_settings(self, loaders: List[Loader], tmp_path: Path) -> None:
        """
        "_load_settings()" is the internal core loader and takes a list of
        options instead of a normal settings class.  It returns a dict and
        not a settings instance.
        """
        cwd = Path.cwd()
        state = _core.SettingsState(Settings, loaders, [], default_converter(), cwd)
        settings = _core._load_settings(state)
        assert settings == {
            "host.name": LoadedValue(
                "example.com",
                LoaderMeta(
                    f"FileLoader[{tmp_path.joinpath('settings.toml')}]",
                    base_dir=tmp_path,
                ),
            ),
            "host.port": LoadedValue("42", LoaderMeta("EnvLoader", base_dir=cwd)),
            "url": LoadedValue(
                "https://example.com",
                LoaderMeta(
                    f"FileLoader[{tmp_path.joinpath('settings.toml')}]",
                    base_dir=tmp_path,
                ),
            ),
            "default": LoadedValue(3, LoaderMeta("_DefaultsLoader", base_dir=cwd)),
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

    def test_explicit_env_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
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

            def __eq__(self, other: object) -> bool:
                return self.attr == other.attr  # type: ignore

        @settings
        class Settings:
            opt: Test

        converter = cattrs.Converter()
        converter.register_structure_hook(
            Test, lambda v, t: v if isinstance(v, Test) else Test(int(v))
        )

        result = _core.load_settings(
            Settings, [DictLoader({"opt": "42"})], converter=converter
        )
        assert result == Settings(Test(42))

    def test_custom_option_converter(self) -> None:
        """
        Converters defined for individual options are being used.
        """

        @settings
        class Settings:
            opt: str = option(converter=lambda v: f"converted:{v}")

        result = _core.load_settings(Settings, [DictLoader({"opt": "a"})])
        assert result == Settings("converted:a")

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
        Lists can be loaded from env vars.
        """
        c = get_default_cattrs_converter()
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

        result = _core.load_settings(Settings, loaders, converter=c)
        cwd = Path.cwd().joinpath
        assert result == Settings(x=[3, 4, 42], y=[cwd("spam"), cwd("eggs")], z=[1, 2])

    def test_load_empty_cls(self) -> None:
        """
        Empty classes are no special case.
        """

        @settings
        class Settings:
            pass

        result = _core.load(Settings, "example")
        assert result == Settings()

    def test_processors_applied(self, loaders: List[Loader]) -> None:
        """
        Processors are applied to the loaded settings (including the defaults).
        """

        def p1(
            settings_dict: SettingsDict,
            settings_cls: SettingsClass,
            options: OptionList,
        ) -> SettingsDict:
            assert settings_dict == {
                "url": "https://example.com",
                "default": 3,
                "host": {
                    "name": "example.com",
                    "port": "42",
                },
            }
            settings_dict["url"] = "spam"
            return settings_dict

        def p2(
            settings_dict: SettingsDict,
            settings_cls: SettingsClass,
            options: OptionList,
        ) -> SettingsDict:
            assert settings_dict["url"] == "spam"
            settings_dict["host"]["port"] = "2"
            return settings_dict

        settings = _core.load_settings(
            cls=Settings,
            loaders=loaders,
            processors=[p1, p2],
        )
        assert settings == Settings(
            url="spam",
            default=3,
            host=Host(
                name="example.com",
                port=2,
            ),
        )

    def test_resolve_paths(
        self, loaders: List[Loader], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Field converters are preferred over the cattrs converter.
        They can be used to resolves paths relative to the loader's cwd.

        See: https://gitlab.com/sscherfke/typed-settings/-/issues/30
        """

        @settings
        class S:
            a: Path
            b: Path
            c: Path
            d: Path

        d1 = tmp_path.joinpath("d1")
        d1.mkdir()
        c1 = d1.joinpath("s.toml")
        c1.write_text('[example]\na = "f0"\nb = "f1"\n')
        d2 = tmp_path.joinpath("d2")
        d2.mkdir()
        c2 = d2.joinpath("s.toml")
        c2.write_text('[example]\nc = "f2"\n')
        monkeypatch.setenv("EXAMPLE_D", "f3")
        cast(FileLoader, loaders[0]).files = [c1, c2]

        result = _core.load_settings(cls=S, loaders=loaders)
        assert result == S(
            a=d1.joinpath("f0"),
            b=d1.joinpath("f1"),
            c=d2.joinpath("f2"),
            d=Path.cwd().joinpath("f3"),
        )

    @pytest.mark.skipif(
        not PY_310, reason="Error messages differ a bit on older versions"
    )
    @pytest.mark.parametrize(
        "settings, err",
        [
            (
                {"url": "u"},
                (
                    "3 errors occured while converting the loaded option values to an "
                    "instance of 'Settings':\n"
                    "- No value set for required option 'host.name'\n"
                    "- No value set for required option 'host.port'\n"
                    "- Could not convert loaded settings: "
                    'TypeError("Settings.__init__() missing 1 required positional '
                    "argument: 'host'\")"
                ),
            ),
            (
                {"host": {"name": "h"}, "url": "u"},
                (
                    "2 errors occured while converting the loaded option values to an "
                    "instance of 'Settings':\n"
                    "- No value set for required option 'host.port'\n"
                    '- Could not convert loaded settings: TypeError("Host.__init__() '
                    "missing 1 required positional argument: 'port'\")"
                ),
            ),
            (
                {"host": {"name": "h", "port": "spam"}, "url": "u"},
                (
                    "3 errors occured while converting the loaded option values to an "
                    "instance of 'Settings':\n"
                    "- Could not convert value 'spam' for option 'host.port' from "
                    'loader test: ValueError("invalid literal for int() with base 10: '
                    "'spam'\")\n"
                    "- No value set for required option 'host.port'\n"
                    "- Could not convert loaded settings: "
                    'TypeError("Host.__init__() missing 1 required positional '
                    "argument: 'port'\")"
                ),
            ),
            (
                {"host": {"name": "h", "port": 1}, "url": "u", "default": -1},
                (
                    "1 errors occured while converting the loaded option values to an "
                    "instance of 'Settings':\n"
                    "- Could not convert loaded settings: "
                    "ValueError(\"'default' must be > 0: -1\")"
                ),
            ),
        ],
    )
    def test_convert_errors(self, settings: dict, err: str) -> None:
        state = _core.SettingsState(Settings, [], [], default_converter(), Path())
        meta = LoaderMeta("test")
        merged = dict_utils.merge_settings(
            state.options, [LoadedSettings(settings, meta)]
        )
        # convert() error: Could not convert value
        # No value set for required option
        # Could convert loaded settings to instance
        with pytest.raises(exceptions.InvalidSettingsError, match=re.escape(err)):
            _core.convert(merged, state)

    def test_load_resolve_default_paths(self, tmp_path: Path) -> None:
        """
        Relative paths in default values can be resolved relative to a user specified
        base dir.
        """

        @settings(frozen=True)
        class S:
            p: Path = Path("tests")

        result = _core.load(S, "test")
        assert result == S(Path.cwd().joinpath("tests"))
        result = _core.load(S, "test", base_dir=tmp_path)
        assert result == S(tmp_path.joinpath("tests"))

    def test_load_settings_resolve_default_paths(self, tmp_path: Path) -> None:
        """
        Relative paths in default values can be resolved relative to a user specified
        base dir.
        """

        @settings(frozen=True)
        class S:
            p: Path = Path("tests")

        result = _core.load_settings(S, [])
        assert result == S(Path.cwd().joinpath("tests"))
        result = _core.load_settings(S, [], base_dir=tmp_path)
        assert result == S(tmp_path.joinpath("tests"))


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
