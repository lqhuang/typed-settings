"""
Typed settings
"""
from typing import Any, List

from ._core import load_settings, update_settings
from .attrs import option, secret, settings


__all__ = [
    "click_options",
    "load_settings",
    "option",
    "pass_settings",
    "secret",
    "settings",
    "update_settings",
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
