"""
Test that all public functions are properly exposed.
"""
from pathlib import Path
from typing import Type

import pytest

import typed_settings as ts


@ts.settings
class Settings:
    """
    A simple test class with the TS aliases for attrs.
    """

    u: str = ts.option()
    p: str = ts.secret()


@ts.settings(frozen=True)
class FrozenSettings:
    """
    A frozen test class with the TS aliases for attrs.
    """

    u: str = ts.option()
    p: str = ts.secret()


classes = [Settings, FrozenSettings]


@pytest.mark.parametrize("cls", classes)
def test_load(cls: Type[Settings], tmp_path: Path) -> None:
    """
    We can load settings with a class decorated with our decorator.
    """
    f = tmp_path.joinpath("cfg.toml")
    f.write_text('[test]\nu = "spam"\np = "eggs"\n')
    settings = ts.load(cls, "test", [f])
    assert settings == cls("spam", "eggs")


@pytest.mark.parametrize("cls", classes)
def test_load_settings(cls: Type[Settings], tmp_path: Path) -> None:
    """
    We can load settings with a class decorated with our decorator.
    """
    f = tmp_path.joinpath("cfg.toml")
    f.write_text('[test]\nu = "spam"\np = "eggs"\n')
    settings = ts.load(cls, "test", [f])
    assert settings == cls("spam", "eggs")


def test_dir() -> None:
    """
    dir(typed_settings) returns the expected list of names, including the
    ones requiring optional dependencies.
    """
    names = dir(ts)
    assert names == [
        "EnvLoader",
        "FileLoader",
        "Secret",
        "SecretStr",
        "SettingsState",
        "TomlFormat",
        "cli",
        "click_options",
        "combine",
        "convert",
        "default_converter",
        "default_loaders",
        "evolve",
        "find",
        "load",
        "load_settings",
        "option",
        "pass_settings",
        "register_strlist_hook",
        "secret",
        "settings",
    ]
