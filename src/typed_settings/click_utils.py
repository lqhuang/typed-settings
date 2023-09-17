"""
Deprecated alias for :mod:`typed_settings.cli_utils`.
"""
import warnings

from .cli_click import *  # noqa


warnings.warn(
    "This module has been renamed to 'typed_settings.cli_click'.",
    DeprecationWarning,
    stacklevel=2,
)
