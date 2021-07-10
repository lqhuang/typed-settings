import logging
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

import pytest
from attr import field, frozen

from typed_settings import _core
from typed_settings._dict_utils import _deep_options
from typed_settings.attrs import option, settings


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
    @pytest.fixture
    def config_file(self, tmp_path: Path) -> Path:
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(self.config)
        return config_file

    @pytest.fixture
    def loaders(self, config_file: Path) -> List[Loader]:
        loaders=[
            FileLoader(
                files=[config_file],
                formats={"*.toml": TomlFormat()},
            ),
            EnvLoader(prefix=env_prefix),
        ],

    def test_load_settings(self, tmp_path, monkeypatch):
        """Test basic functionality."""
        monkeypatch.setenv("EXAMPLE_HOST_PORT", "42")

        settings = _core.load(
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
        The _load_settings() can be easier reused.  It takes the options lists
        and returns the settings as dict that can still be updated.
        """
        monkeypatch.setenv("EXAMPLE_HOST_PORT", "42")

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(self.config)

        settings = _core._load_settings(
            options=_deep_options(Settings),
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

        s = _core.load(Settings, "test")
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

        result = _core.load(S, "t")
        assert result == S()


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
