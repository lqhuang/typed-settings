import logging
import os
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

import pytest
from attr import field, frozen

from typed_settings import _core
from typed_settings._dict_utils import _deep_fields
from typed_settings.attrs import option, settings


# Test with frozen settings.  If it works this way, it will also work with
# mutable settings but not necessarily the other way around.
@settings(frozen=True)
class Host:
    name: str
    port: int = option(converter=int)


@settings(frozen=True)
class Settings:
    host: Host
    url: str
    default: int = 3


class TestAuto:
    """Tests for the AUTO sentinel."""

    def test_is_singleton(self):
        assert _core.AUTO is _core._Auto()

    def test_str(self):
        assert str(_core.AUTO) == "AUTO"


class TestLoadSettings:
    """Tests for load_settings()."""

    config = """[example]
        url = "https://example.com"
        [example.host]
        name = "example.com"
        port = 443
    """

    def test_load_settings(self, tmp_path, monkeypatch):
        """Test basic functionality."""
        monkeypatch.setenv("EXAMPLE_HOST_PORT", "42")

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(self.config)

        settings = _core.load_settings(
            cls=Settings,
            appname="example",
            config_files=[config_file],
        )
        assert settings == Settings(
            url="https://example.com",
            default=3,
            host=Host(
                name="example.com",
                port=42,
            ),
        )

    def test__load_settings(self, tmp_path, monkeypatch):
        """
        The _load_settings() can be easier reused.  It takes the fields lists
        and returns the settings as dict that can still be updated.
        """
        monkeypatch.setenv("EXAMPLE_HOST_PORT", "42")

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(self.config)

        settings = _core._load_settings(
            fields=_deep_fields(Settings),
            appname="example",
            config_files=[config_file],
            config_file_section=_core.AUTO,
            config_files_var=_core.AUTO,
            env_prefix=_core.AUTO,
        )
        assert settings == {
            "url": "https://example.com",
            "default": 3,  # This is from the cls
            "host": {
                "name": "example.com",
                "port": "42",  # Value not yet converted
            },
        }

    def test_load_nested_settings_by_default(self):
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

        s = _core.load_settings(Settings, "test")
        assert s == Settings(Nested())

    def test_default_factories(self):
        """
        The default value "attr.Factory" is handle as if "attr.NOTHING" was
        set.

        See: https://gitlab.com/sscherfke/typed-settings/-/issues/6
        """

        @settings
        class S:
            opt: List[int] = option(factory=list)

        result = _core.load_settings(S, "t")
        assert result == S()


class TestFromToml:
    """Tests for _from_toml()"""

    @pytest.fixture
    def fnames(self, tmp_path: Path) -> List[Path]:
        p0 = tmp_path.joinpath("0.toml")
        p1 = tmp_path.joinpath("1.toml")
        p2 = tmp_path.joinpath("2")
        p3 = tmp_path.joinpath("3")
        p0.touch()
        p2.touch()
        return [p0, p1, p2, p3]

    @pytest.mark.parametrize(
        "cfn, env, expected",
        [
            ([], None, []),
            ([0], None, [0]),
            ([1], None, []),
            ([2], None, [2]),
            ([3], None, []),
            ([], [0], [0]),
            ([0, 1], [2, 3], [0, 2]),
            ([2, 1, 0], [2], [2, 0, 2]),
        ],
    )
    def test_get_config_filenames(
        self, cfn, env, expected, fnames, monkeypatch
    ):
        """
        Config files names (cnf) can be specified explicitly or via an env var.
        It's no problem if a files does not exist (or is it?).
        """
        if env is not None:
            monkeypatch.setenv("CF", ":".join(str(fnames[i]) for i in env))
            env = "CF"

        paths = _core._get_config_filenames([fnames[i] for i in cfn], env)
        assert paths == [fnames[i] for i in expected]

    def test_load_toml(self, tmp_path):
        """We can load settings from toml."""

        @frozen
        class Sub:
            b: str

        @frozen
        class Settings:
            a: str
            sub: Sub

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[example]
            a = "spam"
            [example.sub]
            b = "eggs"
        """
        )
        results = _core._load_toml(
            _deep_fields(Settings), config_file, "example"
        )
        assert results == {
            "a": "spam",
            "sub": {"b": "eggs"},
        }

    def test_load_from_nested(self, tmp_path):
        """
        We can load settings from a nested section (e.g., "tool.example").
        """

        @frozen
        class Sub:
            b: str

        @frozen
        class Settings:
            a: str
            sub: Sub

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[tool.example]
            a = "spam"
            [tool.example.sub]
            b = "eggs"
        """
        )
        results = _core._load_toml(
            _deep_fields(Settings), config_file, "tool.example"
        )
        assert results == {
            "a": "spam",
            "sub": {"b": "eggs"},
        }

    def test_section_not_found(self, tmp_path):
        """
        An empty tick is returned when the config file does not contain the
        desired section.
        """

        @frozen
        class Settings:
            pass

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[tool]
            a = "spam"
        """
        )
        assert _core._load_toml(Settings, config_file, "tool.example") == {}

    def test_load_convert_dashes(self, tmp_path):
        """
        Dashes in settings and section names are replaced with underscores.
        """

        @frozen
        class Sub:
            b_1: str

        @frozen
        class Settings:
            a_1: str
            a_2: str
            sub_section: Sub

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[example]
            a-1 = "spam"
            a_2 = "eggs"
            [example.sub-section]
            b-1 = "bacon"
        """
        )
        results = _core._load_toml(
            _deep_fields(Settings), config_file, "example"
        )
        assert results == {
            "a_1": "spam",
            "a_2": "eggs",
            "sub_section": {"b_1": "bacon"},
        }

    def test_invalid_settings(self):
        """
        Settings for which there is no attribute are errors
        """
        settings = {
            "url": "abc",
            "host": {"port": 23, "eggs": 42},
            "spam": 23,
        }
        with pytest.raises(ValueError) as exc_info:
            _core._clean_settings(_deep_fields(Settings), settings, Path("p"))
        assert str(exc_info.value) == (
            "Invalid settings found in p: host.eggs, spam"
        )

    def test_clean_settings_unresolved_type(self):
        """
        Cleaning must also work if an options type is an unresolved string.
        """

        @frozen
        class Host:
            port: int = field(converter=int)

        @frozen
        class Settings:
            host: "Host"

        settings = {"host": {"port": 23, "eggs": 42}}
        with pytest.raises(ValueError) as exc_info:
            _core._clean_settings(_deep_fields(Settings), settings, Path("p"))
        assert str(exc_info.value) == "Invalid settings found in p: host.eggs"

    def test_clean_settings_dict_values(self):
        """
        Some dicts may be actuall values (not nested) classes.  Don't try to
        check theses as option paths.
        """

        @frozen
        class Settings:
            option: Dict[str, Any]

        settings = {"option": {"a": 1, "b": 2}}
        _core._clean_settings(_deep_fields(Settings), settings, Path("p"))

    def test_no_replace_dash_in_dict_keys(self, tmp_path):
        """
        "-" in TOML keys are replaced with "_" for sections and options, but
        "-" in actuall dict keys are left alone.

        See: https://gitlab.com/sscherfke/typed-settings/-/issues/3
        """

        @frozen
        class Settings:
            option_1: Dict[str, Any]
            option_2: Dict[str, Any]

        cf = tmp_path.joinpath("settings.toml")
        cf.write_text(
            "[my-config]\n"
            'option-1 = {my-key = "val1"}\n'
            "[my-config.option-2]\n"
            "another-key = 23\n"
        )

        settings = _core._load_toml(_deep_fields(Settings), cf, "my-config")
        assert settings == {
            "option_1": {"my-key": "val1"},
            "option_2": {"another-key": 23},
        }

    def test_load_settings_explicit_config(self, tmp_path, monkeypatch):
        """
        The automatically derived config section name and settings files var
        name can be overriden.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[le-section]
            spam = "eggs"
        """
        )

        monkeypatch.setenv("LE_SETTINGS", str(config_file))

        @frozen
        class Settings:
            spam: str = ""

        settings = _core._from_toml(
            _deep_fields(Settings),
            appname="example",
            files=[],
            section="le-section",
            var_name="LE_SETTINGS",
        )
        assert settings == {"spam": "eggs"}

    @pytest.mark.parametrize(
        "is_mandatory, is_path, in_env, exists",
        product([True, False], repeat=4),
    )
    def test_mandatory_files(
        self,
        is_mandatory,
        is_path,
        in_env,
        exists,
        tmp_path,
        monkeypatch,
    ):
        """
        Paths with a "!" are mandatory and an error is raised if they don't
        exist.
        """
        p = tmp_path.joinpath("s.toml")
        if exists:
            p.touch()
        p = f"!{p}" if is_mandatory else str(p)
        if is_path:
            p = Path(p)
        files = []
        if in_env:
            monkeypatch.setenv("TEST_SETTINGS", str(p))
        else:
            files = [p]

        args = ([], "test", files, _core.AUTO, _core.AUTO)
        if is_mandatory and not exists:
            pytest.raises(FileNotFoundError, _core._from_toml, *args)
        else:
            _core._from_toml(*args)

    def test_env_var_dash_underscore(self, monkeypatch, tmp_path):
        """
        Dashes in the appname get replaced with underscores for the settings
        fiels var name.
        """

        @frozen
        class Settings:
            option: bool = True

        sf = tmp_path.joinpath("settings.py")
        sf.write_text("[a-b]\noption = false\n")
        monkeypatch.setenv("A_B_SETTINGS", str(sf))

        result = _core.load_settings(Settings, appname="a-b")
        assert result == Settings(option=False)


class TestFromEnv:
    """Tests for _from_env()"""

    @pytest.mark.parametrize("prefix", ["T_", _core.AUTO])
    def test_from_env(self, prefix, monkeypatch):
        """Ignore env vars for which no settings attrib exis_core."""
        fields = _deep_fields(Settings)
        monkeypatch.setattr(
            os,
            "environ",
            {
                "T_URL": "foo",
                "T_HOST": "spam",  # Haha! Just a deceit!
                "T_HOST_PORT": "25",
            },
        )
        settings = _core._from_env(fields, "t", prefix)
        assert settings == {
            "url": "foo",
            "host": {
                "port": "25",
            },
        }

    def test_no_env_prefix(self, monkeypatch):
        """
        The prefix for env vars can be disabled w/o disabling loading env. vars
        themselves.
        """
        monkeypatch.setenv("CONFIG_VAL", "42")

        @frozen
        class Settings:
            config_val: str

        settings = _core._from_env(_deep_fields(Settings), "example", "")
        assert settings == {"config_val": "42"}

    def test_disable_environ(self):
        """Setting env_prefix=None diables loading env vars."""

        @frozen
        class Settings:
            x: str = "spam"

        settings = _core._from_env(_deep_fields(Settings), "example", None)
        assert settings == {}


class TestLogging:
    """
    Test emitted log messages.
    """

    def test_successfull_loading(self, caplog, tmp_path, monkeypatch):
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

        _core.load_settings(S, "test", [sf1])

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

    def test_optional_files_not_found(self, caplog, tmp_path, monkeypatch):
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

        _core.load_settings(S, "test", [sf1])

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

    def test_mandatory_files_not_found(self, caplog, tmp_path, monkeypatch):
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
            _core.load_settings(S, "test")

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
