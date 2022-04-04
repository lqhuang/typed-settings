"""
Helpers for and additions to :mod:`attrs`.
"""
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    overload,
)

import attrs


if TYPE_CHECKING:
    try:
        from attr import (  # type: ignore
            _T,
            _ConverterType,
            _OnSetAttrArgType,
            _ReprArgType,
            _ValidatorArgType,
        )
    except ImportError:
        # Just in case the symbols are moved from "attr" to "attrs"
        from attrs import (  # type: ignore
            _T,
            _ConverterType,
            _OnSetAttrArgType,
            _ReprArgType,
            _ValidatorArgType,
        )

from .hooks import auto_convert


__all__ = [
    "METADATA_KEY",
    "SECRET",
    "auto_convert",
    "evolve",
    "option",
    "secret",
    "settings",
]


METADATA_KEY = "typed_settings"


class _SecretRepr:
    def __call__(self, _v) -> str:
        return "***"

    def __repr__(self) -> str:
        return "***"


SECRET = _SecretRepr()


settings = attrs.define
"""An alias to :func:`attrs.define()`"""


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
    default=attrs.NOTHING,
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
    """An alias to :func:`attrs.field()`"""
    if help is not None:
        if metadata is None:
            metadata = {}
        metadata.setdefault(METADATA_KEY, {})["help"] = help

    return attrs.field(
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
    default=attrs.NOTHING,
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
        - :func:`attrs.field()`

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

    return attrs.field(
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


def evolve(inst, **changes):
    """
    Create a new instance, based on *inst* with *changes* applied.

    If the old value of an attribute is an ``attrs`` class and the new value
    is a dict, the old value is updated recursively.

    .. warning::

       This function is very similar to :func:`attrs.evolve()`, but the
       ``attrs`` version is not updating values recursively.  Instead, it will
       just replace ``attrs`` instances with a dict.

    :param inst: Instance of a class with ``attrs`` attributes.
    :param changes: Keyword changes in the new copy.

    :return: A copy of inst with *changes* incorporated.

    :raise TypeError: If *attr_name* couldn't be found in the class
        ``__init__``.
    :raise attr.exceptions.NotAnAttrsClassError: If *cls* is not an ``attrs``
        class.

    ..  versionadded:: 1.0.0
    """
    cls = inst.__class__
    attribs = attrs.fields(cls)
    for a in attribs:
        if not a.init:
            continue
        attr_name = a.name  # To deal with private attributes.
        init_name = attr_name if attr_name[0] != "_" else attr_name[1:]
        old_value = getattr(inst, attr_name)
        if init_name not in changes:
            # Add original value to changes
            changes[init_name] = old_value
        elif attrs.has(old_value) and isinstance(changes[init_name], Mapping):
            # Evolve nested attrs classes
            changes[init_name] = evolve(old_value, **changes[init_name])

    return cls(**changes)
