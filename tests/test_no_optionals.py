"""
Test behavior when no optional dependencies are installed.
"""
import sys

import pytest

import typed_settings
import typed_settings.loaders

from . import conftest


try:
    import attrs, click  # noqa: E401, F401, I001

    pytestmark = pytest.mark.skip(reason="Optional dependencies are installed")
except ImportError:
    pass


@pytest.mark.parametrize(
    "dep, name",
    [
        ("attrs", "combine"),
        ("attrs", "evolve"),
        ("attrs", "option"),
        ("attrs", "secret"),
        ("attrs", "settings"),
        ("click", "click_options"),
        ("click", "pass_settings"),
    ],
)
def test_import_error(dep: str, name: str) -> None:
    """
    An ImportError is raised when trying to get an attrib from "typed_settings" that
    requires an optional import.
    """
    with pytest.raises(ImportError) as exc_info:
        getattr(typed_settings, name)
    assert dep in str(exc_info.value)


def test_attribute_not_found() -> None:
    """
    Names not provided by typed settings lead to an attribute error as expected.
    """
    with pytest.raises(AttributeError):
        _ = typed_settings.spam


def test_load(
    settings_clss: conftest.SettingsClasses, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    "load()" works with dataclasses when no optional dependencies are installed.
    """
    monkeypatch.setenv("TEST_HOST_NAME", "n")
    monkeypatch.setenv("TEST_HOST_PORT", "1")
    monkeypatch.setenv("TEST_URL", "u")
    monkeypatch.setenv("TEST_DEFAULT", "2")
    result: conftest.Settings = typed_settings.load(settings_clss[0], "test")
    assert result == conftest.Settings(conftest.Host("n", 1), "u", 2)


def test_load_settings(settings_clss: conftest.SettingsClasses) -> None:
    """
    "load_settings()" and "default_converter()" work with dataclasses when no optional
    dependencies are installed.
    """
    default = conftest.Settings(conftest.Host("n", 1), "u", 2)
    result: conftest.Settings = typed_settings.load_settings(
        settings_clss[0],
        loaders=[typed_settings.loaders.InstanceLoader(default)],
        converter=typed_settings.default_converter(),
    )
    assert result == default


def test_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic test "cli()" - simple CLI for a simple settings class.
    """
    monkeypatch.setattr(
        sys, "argv", ["cli", "--host-name=n", "--host-port=1", "--url=u", "--default=2"]
    )

    @typed_settings.cli(conftest.Settings, "test")
    def cli(settings: conftest.Settings) -> None:
        assert settings == conftest.Settings(conftest.Host("n", 1), "u", 2)

    cli()
