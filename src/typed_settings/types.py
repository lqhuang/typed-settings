"""
Internal data structures.
"""
from collections.abc import Collection
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import (
    Any,
    Dict,
    Final,
    Generic,
    NamedTuple,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import attrs

from ._compat import PY_39


__all__ = [
    "AUTO",
    "SECRET_REPR",
    "T",
    "ET",
    "ST",
    "SettingsClass",
    "SettingsInstance",
    "SettingsDict",
    "OptionName",
    "OptionPath",
    "OptionInfo",
    "OptionList",
    "OptionDict",
    "LoaderMeta",
    "LoadedValue",
    "LoadedSettings",
    "MergedSettings",
    "Secret",
    "SecretStr",
    "SECRETS_TYPES",
]


SECRET_REPR: Final[str] = "*******"


T = TypeVar("T")
ET = TypeVar("ET", bound=Enum)  # Enum type
ST = TypeVar("ST", bound=attrs.AttrsInstance)  # SettingsInstance
SettingsClass = Type[attrs.AttrsInstance]
SettingsInstance = attrs.AttrsInstance
OptionName = str
OptionPath = str
SettingsDict = Dict[OptionName, Union[Any, "SettingsDict"]]


class _Auto:
    """
    Sentinel class to indicate the lack of a value when ``None`` is ambiguous.

    ``_Auto`` is a singleton. There is only ever one of it.
    """

    _singleton = None

    def __new__(cls) -> "_Auto":
        if _Auto._singleton is None:
            _Auto._singleton = super().__new__(cls)
        return _Auto._singleton

    def __repr__(self) -> str:
        return "AUTO"


AUTO = _Auto()
"""
Sentinel to indicate the lack of a value when ``None`` is ambiguous.
"""


def _type2name(value: Union[str, Any]) -> str:
    """
    Return either *value* if it is a str or else its type name.
    """
    if isinstance(value, str):
        return value
    return type(value).__name__


@attrs.frozen
class OptionInfo:
    """
    Information about (possibly nested) option attributes.

    Each instance represents a single attribute of an apps's settings class.
    """

    path: OptionPath
    """
    Dotted path to the option name relative to the root settings class.
    """

    field: attrs.Attribute
    """
    :class:`attrs.Attribute` instance for the option.
    """

    cls: type
    """
    The option's settings class.  This is either the root settings class or a nested
    one.
    """


OptionList = Tuple[OptionInfo, ...]
"""
A flat list of all available options, including those from nested settings.
"""

if PY_39:
    OptionDict = MappingProxyType[OptionPath, OptionInfo]
else:
    from typing import Mapping

    OptionDict = Mapping[OptionPath, OptionInfo]  # type: ignore
"""
A dict version of :class:`OptionList`.
"""


@attrs.frozen
class LoaderMeta:
    """
    Meta data about the loader that loaded a set of option values.

    That data is used to improve error reporting and for converting loaded values to the
    target type.
    """

    name: str = attrs.field(converter=_type2name)
    """
    The loader's name.  Can be a string or the loader class itself (it's class name is
    will then be used).
    """

    base_dir: Path = attrs.field(factory=Path.cwd)
    """
    The loader's base directory.

    It is used to resolve relative paths in loaded option values in the proper context.

    For most loaders, this should be the *cwd* (which is also the default).  For file
    loaders, the parent directory of a loaded file might be a better alternative.
    """


class LoadedValue(NamedTuple):
    """
    A container for a loaded option value and the meta data of the originating loader.
    """

    value: Any
    """
    The loaded option value.
    """

    loader_meta: LoaderMeta
    """
    Meta data of the loader that loaded the corresponding value.
    """


@attrs.frozen
class LoadedSettings:
    """
    A container for the settings loaded by a single loader, and the meta data of that
    loader.
    """

    settings: SettingsDict
    """
    The loaded settings values.
    """

    meta: LoaderMeta
    """
    Meta data of the loader that loaded the settings.
    """


MergedSettings = Dict[OptionPath, LoadedValue]
"""
A dict that maps a dotted option path to a loaded option value.

The values may come from different loaders, so each option values stores the meta data
of it's loader.
"""


class SecretStr(str):
    """
    A subclass of :class:`str` that masks the output of :func:`repr()`.

    It is less secure than :class:`Secret` but is a drop-in replacement for normal
    strings.

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
        return f"{SECRET_REPR!r}" if self else "''"


class Secret(Generic[T]):
    """
    A secret wrapper around any value.

    It makes it very hard to accidentally leak the secret, even when printing or logging
    it.

    You need to explicitly call :meth:`get_secret_value()` to get the wrapped value.
    Thus, it is no drop-in replacement for the wrapped data.

    See :class:`SecretStr` if you need a drop-in replacement for strings, even if it is
    not quite as safe.

    You can use :class:`bool` to get the boolean value of the wrapped secret.  Other
    protocol methods (e.g., for length or comparison operators) are not implemented.

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


SECRETS_TYPES = (Secret, SecretStr)
"""
Types that mask the repr of their values.
"""
