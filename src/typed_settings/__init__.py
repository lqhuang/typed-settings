"""
Typed settings
"""
from functools import partial

import attr

from ._click import click_options
from ._core import load_settings, update_settings


settings = attr.frozen
# settings = partial(attr.frozen, field_transformer=attr.auto_convert)
option = attr.field
secret = partial(attr.field, repr=lambda v: "***")


__all__ = [
    "load_settings",
    "update_settings",
    "click_options",
    "settings",
    "option",
    "secret",
]
