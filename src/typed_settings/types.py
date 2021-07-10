from typing import Any, List, MutableMapping, TypeVar

from attr import Attribute, frozen


T = TypeVar("T")
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


@frozen
class OptionInfo:
    """
    Information about (possibly nested) option attributes.
    """

    path: str
    """
    Dotted path to the option name relative to the root settings class.
    """

    field: Attribute
    """
    ``attrs`` :class:`.Attribute` instance for the option.
    """

    cls: type
    """
    The option's settings class.  This is either the root settings class or a
    nested one.
    """


OptionList = List[OptionInfo]
