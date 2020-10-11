"""
Typed settings
"""
from functools import partial
from typing import Any, List

import attr

from ._core import load_settings, update_settings


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
        from ._click import click_options

        return click_options
    if name == "pass_settings":
        from ._click import pass_settings

        return pass_settings

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> List[str]:
    return __all__


settings = attr.frozen
# settings = partial(attr.frozen, field_transformer=attr.auto_convert)
option = attr.field
secret = partial(attr.field, repr=lambda v: "***")
