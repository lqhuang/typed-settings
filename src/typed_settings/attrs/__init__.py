"""
Helpers for and additions to attrs.
"""
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, overload

import attr
import attr._make


if TYPE_CHECKING:
    from attr import (
        _T,
        _ConverterType,
        _OnSetAttrArgType,
        _ReprArgType,
        _ValidatorArgType,
    )

from .converters import to_bool, to_dt
from .hooks import make_auto_converter


METADATA_KEY = "typed_settings"


class _SecretRepr:
    def __call__(self, _v) -> str:
        return "***"

    def __repr__(self) -> str:
        return "***"


SECRET = _SecretRepr()


auto_convert = make_auto_converter({bool: to_bool, datetime: to_dt})

settings = partial(attr.define, field_transformer=auto_convert)
"""An alias to :func:`attr.field()`"""


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
