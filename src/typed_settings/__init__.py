"""
Core functions for loading and working with settings.
"""
from typing import Any, List

from ._core import default_loaders, load, load_settings
from ._file_utils import find
from .argparse_utils import cli
from .attrs import combine, evolve, option, secret, settings
from .converters import default_converter, register_strlist_hook
from .loaders import EnvLoader, FileLoader, TomlFormat


__all__ = [
    # Core
    "default_loaders",
    "load",
    "load_settings",
    # File utils
    "find",
    # Loaders
    "EnvLoader",
    "FileLoader",
    "TomlFormat",
    # Attrs helpers
    "combine",
    "evolve",
    "option",
    "secret",
    "settings",
    # Cattrs converters/helpers
    "default_converter",
    "register_strlist_hook",
    # Argparse utils
    "cli",
    # Click utils
    "click_options",
    "pass_settings",
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
