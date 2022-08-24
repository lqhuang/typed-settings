"""
Internal data structures.
"""
from enum import Enum
from typing import Any, ClassVar, List, MutableMapping, Type, TypeVar

import attrs

from ._compat import Protocol


# A protocol to be able to statically accept an attrs class.
# Copied from attrs b/c they only have this in their *.pyi file.
class AttrsInstance(Protocol):
    __attrs_attrs__: ClassVar[Any]


T = TypeVar("T")
ET = TypeVar("ET", bound=Enum)  # Enum type
ST = TypeVar("ST", bound=AttrsInstance)  # SettingsInstance
SettingsClass = Type[AttrsInstance]
SettingsInstance = AttrsInstance
SettingsDict = MutableMapping[str, Any]


class _Auto:
    """
    Sentinel class to indicate the lack of a value when ``None`` is ambiguous.

    ``_Auto`` is a singleton. There is only ever one of it.
    """

    _singleton = None

    def __new__(cls) -> "_Auto":
        if _Auto._singleton is None:
            _Auto._singleton = super(_Auto, cls).__new__(cls)
        return _Auto._singleton

    def __repr__(self) -> str:
        return "AUTO"


AUTO = _Auto()
"""
Sentinel to indicate the lack of a value when ``None`` is ambiguous.
"""


@attrs.frozen
class OptionInfo:
    """
    Information about (possibly nested) option attributes.

    Each instance represents a single attribute of an apps's settings class.
    """

    path: str
    """
    Dotted path to the option name relative to the root settings class.
    """

    field: attrs.Attribute
    """
    :class:`attrs.Attribute` instance for the option.
    """

    cls: type
    """
    The option's settings class.  This is either the root settings class or a
    nested one.
    """


OptionList = List[OptionInfo]
