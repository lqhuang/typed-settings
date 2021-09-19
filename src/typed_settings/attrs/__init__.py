"""
Helpers for and additions to attrs.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, overload

import attr
import attr._make
import cattr
from cattr._compat import is_sequence


if TYPE_CHECKING:
    from attr import (
        _T,
        _ConverterType,
        _OnSetAttrArgType,
        _ReprArgType,
        _ValidatorArgType,
    )

from ..exceptions import InvalidValueError
from ..types import SettingsDict, T
from .converters import to_bool, to_dt, to_enum
from .hooks import make_auto_converter


METADATA_KEY = "typed_settings"

DEFAULT_STRUCTURE_HOOKS = [
    (bool, lambda v, t: to_bool(v)),
    (datetime, lambda v, t: to_dt(v)),
    (Enum, lambda v, t: to_enum(t)(v)),
    (Path, lambda v, t: Path(v)),
]


class _SecretRepr:
    def __call__(self, _v) -> str:
        return "***"

    def __repr__(self) -> str:
        return "***"


SECRET = _SecretRepr()


auto_convert = make_auto_converter({bool: to_bool, datetime: to_dt})


def default_converter() -> cattr.GenConverter:
    """
    Get an instanceof the default converter used by Typed Settings.

    Return:
        A :class:`cattr.GenConverter` configured with addional hooks for
        loading the follwing types:

        - :class:`bool` using :func:`.to_bool()`
        - :class:`datetime.datetime` using :func:`.to_dt()`
        - :class:`enum.Enum` using :func:`.to_enum()`
        - :class:`pathlib.Path`

    This converter can also be used as a base for converters with custom
    structure hooks.
    """
    converter = cattr.GenConverter()
    for t, h in DEFAULT_STRUCTURE_HOOKS:
        converter.register_structure_hook(t, h)
    return converter


def register_strlist_hook(
    converter: cattr.Converter,
    sep: Optional[str] = None,
    fn: Optional[Callable[[str], list]] = None,
) -> None:
    """
    Register a hook factory with *converter* that allows structuring lists
    from strings (which may, e.g., come from environment variables).

    Args:
        converter: The converter to register the hooks with.
        sep: A separator used for splitting strings (see :meth:`str.split()`).
            Cannot be used together with *fn*.
        fn: A function that takes a string and returns a list, e.g.,
            :func:`json.loads()`.  Cannot be used together with *spe*.

    Example:

        .. code-block:: python

            >>> from typing import List
            >>>
            >>> converter = default_converter()
            >>> register_strlist_hook(converter, sep=":")
            >>> converter.structure("1:2:3", List[int])
            [1, 2, 3]
            >>>
            >>> import json
            >>>
            >>> converter = default_converter()
            >>> register_strlist_hook(converter, fn=json.loads)
            >>> converter.structure("[1,2,3]", List[int])
            [1, 2, 3]


    """
    if (sep is None and fn is None) or (sep is not None and fn is not None):
        raise ValueError('You may either pass "sep" *or* "fn"')
    if sep is not None:
        fn = lambda v: v.split(sep)  # noqa

    def gen_str2list(typ):
        def str2list(val, _):
            if isinstance(val, str):
                val = fn(val)
            # "_structure_list()" is private but it seems more appropriate
            # than this comprehension:
            # return [c.structure(e, typ.__args__[0]) for e in val]
            return converter._structure_list(val, typ)

        return str2list

    converter.register_structure_hook_factory(is_sequence, gen_str2list)


def from_dict(
    settings: SettingsDict, cls: Type[T], converter: cattr.Converter
) -> T:
    """
    Convert a settings dict to an attrs class instance using a cattrs
    converter.

    Args:
        settings: Dictionary with settings
        cls: Attrs class to which the settings are converted to
        converter: Cattrs convert to use for the conversion

    Return:
        An instance of *cls*.

    Raise:
        InvalidValueError: If a value cannot be converted to the correct type.
    """
    try:
        return converter.structure_attrs_fromdict(settings, cls)
    except (AttributeError, ValueError, TypeError) as e:
        raise InvalidValueError(str(e)) from e


settings = attr.define
"""An alias to :func:`attr.define()`"""


@overload
def option(
    *,
    default: None = ...,
    validator: None = ...,
    repr: "_ReprArgType" = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: None = ...,
    factory: None = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: Optional["_OnSetAttrArgType"] = ...,
    help: Optional[str] = ...,
) -> Any:
    ...


# This form catches an explicit None or no default and infers the type from the
# other arguments.
@overload
def option(
    *,
    default: None = ...,
    validator: "Optional[_ValidatorArgType[_T]]" = ...,
    repr: "_ReprArgType" = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: Optional["_ConverterType"] = ...,
    factory: "Optional[Callable[[], _T]]" = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> "_T":
    ...


# This form catches an explicit default argument.
@overload
def option(
    *,
    default: "_T",
    validator: "Optional[_ValidatorArgType[_T]]" = ...,
    repr: "_ReprArgType" = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: "Optional[_ConverterType]" = ...,
    factory: "Optional[Callable[[], _T]]" = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> "_T":
    ...


# This form covers type=non-Type: e.g. forward references (str), Any
@overload
def option(
    *,
    default: Optional["_T"] = ...,
    validator: "Optional[_ValidatorArgType[_T]]" = ...,
    repr: "_ReprArgType" = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: "Optional[_ConverterType]" = ...,
    factory: "Optional[Callable[[], _T]]" = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> Any:
    ...


def option(
    *,
    default=attr.NOTHING,
    validator=None,
    repr=True,
    hash=None,
    init=True,
    metadata=None,
    converter=None,
    factory=None,
    kw_only=False,
    eq=None,
    order=None,
    on_setattr=None,
    help=None,
):
    """An alias to :func:`attr.field()`"""
    if help is not None:
        if metadata is None:
            metadata = {}
        metadata.setdefault(METADATA_KEY, {})["help"] = help

    return attr.field(
        default=default,
        validator=validator,
        repr=repr,
        hash=hash,
        init=init,
        metadata=metadata,
        converter=converter,
        factory=factory,
        kw_only=kw_only,
        eq=eq,
        order=order,
        on_setattr=on_setattr,
    )


@overload
def secret(
    *,
    default: None = ...,
    validator: None = ...,
    repr: _SecretRepr = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: None = ...,
    factory: None = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> Any:
    ...


# This form catches an explicit None or no default and infers the type from the
# other arguments.
@overload
def secret(
    *,
    default: None = ...,
    validator: "Optional[_ValidatorArgType[_T]]" = ...,
    repr: _SecretRepr = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: "Optional[_ConverterType]" = ...,
    factory: "Optional[Callable[[], _T]]" = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> "_T":
    ...


# This form catches an explicit default argument.
@overload
def secret(
    *,
    default: "_T",
    validator: "Optional[_ValidatorArgType[_T]]" = ...,
    repr: _SecretRepr = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: "Optional[_ConverterType]" = ...,
    factory: "Optional[Callable[[], _T]]" = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> "_T":
    ...


# This form covers type=non-Type: e.g. forward references (str), Any
@overload
def secret(
    *,
    default: "Optional[_T]" = ...,
    validator: "Optional[_ValidatorArgType[_T]]" = ...,
    repr: _SecretRepr = ...,
    hash: Optional[bool] = ...,
    init: bool = ...,
    metadata: Optional[Dict[Any, Any]] = ...,
    converter: "Optional[_ConverterType]" = ...,
    factory: "Optional[Callable[[], _T]]" = ...,
    kw_only: bool = ...,
    eq: Optional[bool] = ...,
    order: Optional[bool] = ...,
    on_setattr: "Optional[_OnSetAttrArgType]" = ...,
    help: Optional[str] = ...,
) -> Any:
    ...


def secret(
    *,
    default=attr.NOTHING,
    validator=None,
    repr=SECRET,
    hash=None,
    init=True,
    metadata=None,
    converter=None,
    factory=None,
    kw_only=False,
    eq=None,
    order=None,
    on_setattr=None,
    help=None,
):
    """
    An alias to :func:`option()` but with a default repr that hides screts.

    When printing a settings instances, secret settings will represented with
    `***` istead of their actual value.

    See also:

        All arguments are describted here:

        - :func:`option()`
        - :func:`attr.field()`

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
    if help is not None:
        if metadata is None:
            metadata = {}
        metadata.setdefault(METADATA_KEY, {})["help"] = help

    return attr.field(
        default=default,
        validator=validator,
        repr=repr,
        hash=hash,
        init=init,
        metadata=metadata,
        converter=converter,
        factory=factory,
        kw_only=kw_only,
        eq=eq,
        order=order,
        on_setattr=on_setattr,
    )
