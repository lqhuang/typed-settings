"""
Typed settings
"""
from typing import Any, List

from ._core import default_loaders, load, load_settings
from ._file_utils import find
from .attrs import evolve, option, secret, settings
from .converters import default_converter, register_strlist_hook
from .loaders import EnvLoader, FileLoader, TomlFormat


__all__ = [
    "EnvLoader",
    "FileLoader",
    "TomlFormat",
    "click_options",
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


def __getattr__(name: str) -> Any:
    if name == "click_options":
        from .click_utils import click_options

        return click_options
    if name == "pass_settings":
        from .click_utils import pass_settings

        return pass_settings

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> List[str]:
    return __all__
