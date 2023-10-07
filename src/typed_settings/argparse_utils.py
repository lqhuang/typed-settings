"""
Deprecated alias for :mod:`typed_settings.argparse_utils`.
"""
import warnings

from .cli_argparse import *  # noqa


warnings.warn(
    "This module has been renamed to 'typed_settings.argparse_utils'.",
    DeprecationWarning,
    stacklevel=2,
)
