"""
Typed settings
"""
from functools import partial

import attr

from ._click import click_options
from ._core import load_settings


secret = partial(attr.field, repr=lambda v: "***")


__all__ = [
    "load_settings",
    "click_options",
    "secret",
]
