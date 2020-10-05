import os
from itertools import product
from pathlib import Path
from typing import List

import pytest
from attr import field, frozen

from typed_settings import _core
from typed_settings._dict_utils import _deep_fields


@frozen
class Host:
    name: str
    port: int = field(converter=int)


@frozen(kw_only=True)
class Settings:
    url: str
    default: int = 3
    host: Host = field(
        converter=lambda d: Host(**d) if isinstance(d, dict) else d  # type: ignore  # noqa
    )


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

        @frozen
        class Nested:
            a: int = 3
            b: str = "spam"

        @frozen
        class Settings:
            nested: Nested = field(
                converter=lambda d: Nested(**d) if isinstance(d, dict) else d
            )

        settings = _core.load_settings(Settings, "test")
        assert settings == Settings(Nested())


class TestUpdateSettings:
    """Tests for update_settings()."""

    settings = Settings(url="a", host=Host("h", 3))

    def test_update_top_level(self):
        """Top level attributes can be updated."""
        updated = _core.update_settings(self.settings, "default", 4)
        assert updated.default == 4
        assert updated.host == self.settings.host

    def test_update_nested_scalar(self):
        """Nested scalar attributes can be updated."""
        updated = _core.update_settings(self.settings, "host.name", "x")
        assert updated.host.name == "x"

    def test_update_nested_settings(self):
        """Nested scalar attributes can be updated."""
        updated = _core.update_settings(
            self.settings, "host", Host("spam", 23)
        )
        assert updated.host.name == "spam"
        assert updated.host.port == 23

    def test_copied(self):
        """
        Top level and nested settings classes are copied, even if unchanged.
        """
        updated = _core.update_settings(self.settings, "url", "x")
        assert updated is not self.settings
        assert updated.host is not self.settings.host

    @pytest.mark.parametrize("path", ["x", "host.x", "host.name.x"])
    def test_invalid_path(self, path):
        """
        Raise AttributeError if path points to non existing attribute.
        Improve default error message.
        """
        with pytest.raises(
            AttributeError,
            match=(f"'Settings' object has no setting '{path}'"),
        ):
            _core.update_settings(self.settings, path, "x")


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

    def test_clean_settings(self):
        """
        Settings for which there is no attribute must be recursively removed.
        """
        settings = {
            "url": "abc",
            "host": {"port": 23, "eggs": 42},
            "spam": 23,
        }
        result = _core._clean_settings(_deep_fields(Settings), settings)
        assert result == {
            "url": "abc",
            "host": {"port": 23},
        }

    def test_clean_settings_unresolved_type(self):
        """
        Cleaning must also work if an options type is an unresolved string.
        """

        @frozen
        class Host:
            port: int = field(converter=int)

        @frozen(kw_only=True)
        class Settings:
            host: "Host" = field(
                converter=lambda d: Host(**d) if isinstance(d, dict) else d
            )

        settings = {"host": {"port": 23, "eggs": 42}}
        result = _core._clean_settings(_deep_fields(Settings), settings)
        assert result == {"host": {"port": 23}}

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
