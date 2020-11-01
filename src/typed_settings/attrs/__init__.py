"""
Helpers for and additions to attrs.
"""
from datetime import datetime
from functools import partial

import attr

from .converters import to_bool, to_dt
from .hooks import make_auto_converter


class _SecretRepr:
    def __call__(self, _v):
        return "***"

    def __repr__(self):
        return "***"


auto_convert = make_auto_converter({bool: to_bool, datetime: to_dt})
"""Auto-convert supported types."""

settings = partial(attr.frozen, field_transformer=auto_convert)
"""An alias to :func:`attr.frozen()`"""

# settings = partial(attr.frozen, field_transformer=attr.auto_convert)
option = partial(attr.field)
"""An alias to :func:`attr.field()`"""

secret = partial(attr.field, repr=_SecretRepr())
"""
An alias to :func:`attr.field()`.

When printing a settings instances, secret settings will represented with `***`
istead of their actual value.

Example:

  .. code-block:: python

     >>> from typed_settings import settings, secret
     >>>
     >>> @settings
     ... class Settings:
     ...     password: str = secret()
     ...
     >>> Settings(password="1234")
     Settings(password=***)
"""
