"""
Internal data structures.
"""
from collections.abc import Collection
from enum import Enum
from typing import Any, ClassVar, Generic, List, MutableMapping, Type, TypeVar

import attrs

from ._compat import Final, Protocol


SECRET_REPR: Final[str] = "*******"


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


class SecretStr(str):
    """
    A subclass of :class:`str` that masks the output of :func:`repr()`.

    It is less secure than :class:`Secret` but is a drop-in replacement for
    normal strings.

    The main use case is avoiding accidental secrets leakage via tracebacks.
    It also helps to enforce secret usage via Typing.

    It does **not help** when you:

    - :func:`print()` it
    - :class:`str` it
    - Log it
    - Use it in an f-string (``f"{val}"``)

    .. versionadded:: 2.0.0
    """

    def __repr__(self) -> str:
        return f"'{SECRET_REPR}'" if self else "''"


class Secret(Generic[T]):
    """
    A secret wrapper around any value.

    It makes it very hard to accidentally leak the secret, even when printing
    or logging it.

    You need to explicitly call :meth:`get_secret_value()` to get the wrapped
    value.  Thus, it is no drop-in replacement for the wrapped data.

    See :class:`SecretStr` if you need a drop-in replacement for strings,
    even if it is not quite as safe.

    You can use :class:`bool` to get the boolean value of the wrapped secret.
    Other protocol methods (e.g., for length or comparison operators) are not
    implemented.

    .. versionadded:: 2.0.0
    """

    def __init__(self, secret_value: T) -> None:
        self._is_collection = isinstance(secret_value, Collection)
        self._secret_value = secret_value

    def __bool__(self) -> bool:
        return bool(self._secret_value)

    def __repr__(self) -> str:
        r = repr(
            self._secret_value
            if not self._secret_value and self._is_collection
            else SECRET_REPR
        )
        return f"{self.__class__.__name__}({r})"

    def __str__(self) -> str:
        return str(
            self._secret_value
            if not self._secret_value and self._is_collection
            else SECRET_REPR
        )

    def get_secret_value(self) -> T:
        """
        Return the wrapped secret value.
        """
        return self._secret_value
