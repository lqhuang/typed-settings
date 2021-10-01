"""
Internal data structures.
"""
from enum import Enum
from typing import Any, List, MutableMapping, TypeVar

import attr


T = TypeVar("T")
ET = TypeVar("ET", bound=Enum)
SettingsDict = MutableMapping[str, Any]


class _Auto:
    """
    Sentinel class to indicate the lack of a value when ``None`` is ambiguous.

    ``_Auto`` is a singleton. There is only ever one of it.
    """

    _singleton = None

    def __new__(cls):
        if _Auto._singleton is None:
            _Auto._singleton = super(_Auto, cls).__new__(cls)
        return _Auto._singleton

    def __repr__(self):
        return "AUTO"


AUTO = _Auto()
"""
Sentinel to indicate the lack of a value when ``None`` is ambiguous.
"""


@attr.frozen
class OptionInfo:
    """
    Information about (possibly nested) option attributes.

    Each instance represents a single attribute of an apps's settings class.
    """

    path: str
    """
    Dotted path to the option name relative to the root settings class.
    """

    field: attr.Attribute
    """
    :class:`attr.Attribute` instance for the option.
    """

    cls: type
    """
    The option's settings class.  This is either the root settings class or a
    nested one.
    """


OptionList = List[OptionInfo]
