"""
Deprecated alias for :mod:`typed_settings.cli_utils`.
"""
import warnings

from .cls_attrs import *  # noqa


warnings.warn(
    "This module has been renamed to 'typed_settings.cls_attrs'.",
    DeprecationWarning,
    stacklevel=2,
)
