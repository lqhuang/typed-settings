"""
Helpers for and additions to attrs.
"""
from functools import partial

import attr

from .hooks import auto_convert


class _SecretRepr:
    def __call__(self, _v):
        return "***"

    def __repr__(self):
        return "***"


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
