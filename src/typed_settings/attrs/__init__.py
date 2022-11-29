"""
Helpers for and additions to :mod:`attrs`.
"""
from collections.abc import Collection
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Type,
    overload,
)

import attr  # The old namespaces is needed in "combine()"
import attrs

from ..types import SECRET_REPR, AttrsInstance
from .hooks import auto_convert


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
CLICK_KEY = "click"
ARGPARSE_KEY = "argparse"

AttrsClass = Type[AttrsInstance]


class _SecretRepr:
    def __call__(self, v: Any) -> str:
        return repr(v if not v and isinstance(v, Collection) else SECRET_REPR)

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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
) -> Any:
    ...


def option(  # type: ignore[no-untyped-def]
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
    click=None,
    argparse=None,
):
    """An alias to :func:`attrs.field()`"""
    metadata = _get_metadata(metadata, help, click, argparse)

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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
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
    click: Optional[Dict[str, Any]] = ...,
    argparse: Optional[Dict[str, Any]] = ...,
) -> Any:
    ...


def secret(  # type: ignore[no-untyped-def]
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
    click=None,
    argparse=None,
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
        Settings(password='*******')
    """
    metadata = _get_metadata(metadata, help, click, argparse)

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


def _get_metadata(
    metadata: Optional[Dict[str, Any]],
    help: str,
    click: Dict[str, Any],
    argparse: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    click_config = {"help": help}
    if click:
        click_config.update(click)
    argparse_config = {"help": help}
    if argparse:
        argparse_config.update(argparse)
    if metadata is None:
        metadata = {}
    ts_meta = metadata.setdefault(METADATA_KEY, {})
    ts_meta["help"] = help
    ts_meta[CLICK_KEY] = click_config
    ts_meta[ARGPARSE_KEY] = argparse_config
    return metadata


def evolve(inst: "AttrsInstance", **changes: Any) -> "AttrsInstance":
    """
    Create a new instance, based on *inst* with *changes* applied.

    If the old value of an attribute is an ``attrs`` class and the new value
    is a dict, the old value is updated recursively.

    .. warning::

       This function is very similar to :func:`attrs.evolve()`, but the
       ``attrs`` version is not updating values recursively.  Instead, it will
       just replace ``attrs`` instances with a dict.

    Args:
        inst: Instance of a class with ``attrs`` attributes.
        changes: Keyword changes in the new copy.

    Return:
        A copy of *inst* with *changes* incorporated.

    Raise:
        TypeError: If *attr_name* couldn't be found in the class ``__init__``.
        attrs.exceptions.NotAnAttrsClassError: If *cls* is not an ``attrs``
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


def combine(
    name: str, base_cls: "AttrsClass", nested: Dict[str, "AttrsInstance"]
) -> "AttrsClass":
    """
    Create a new class called *name* based on *base_class* with additional
    attributes for *nested* classes.

    The same effect can be achieved by manually composing settings classes.
    A use case for this method is to combine settings classes from dynamically
    loaded plugins with the base settings of the main program.

    Args:
        name: The name for the new class.
        base_cls: The base class from which to copy all attributes.
        nested: A mapping of attribute names to (settings) class instances
            for which to generated additional attributes.  The attribute's
            type is the instance's type and its default value is the instance
            itself.  Keys in this dict must not overlap with the attributes
            of *base_cls*.

    Return:
        The created class *name*.

    Raise:
        ValueError: If *nested* contains a key for which *base_cls* already
            defines an attribute.

    Example:

        .. code-block:: python

           >>> import typed_settings as ts
           >>>
           >>> @ts.settings
           ... class Nested1:
           ...     a: str = ""
           >>>
           >>> @ts.settings
           ... class Nested2:
           ...     a: str = ""
           >>>
           >>> # Static composition
           >>> @ts.settings
           ... class Composed1:
           ...     a: str = ""
           ...     n1: Nested1 = Nested1()
           ...     n2: Nested2 = Nested2()
           ...
           >>> Composed1()
           Composed1(a='', n1=Nested1(a=''), n2=Nested2(a=''))
           >>>
           >>> # Dynamic composition
           >>> @ts.settings
           ... class BaseSettings:
           ...     a: str = ""
           >>>
           >>> Composed2 = ts.combine(
           ...     "Composed2",
           ...     BaseSettings,
           ...     {"n1": Nested1(), "n2": Nested2()},
           ... )
           >>> Composed2()
           Composed2(a='', n1=Nested1(a=''), n2=Nested2(a=''))


    .. versionadded:: 1.1.0
    """

    attribs = {
        a.name: attr.attrib(  # type: ignore[misc]
            default=a.default,
            validator=a.validator,  # type: ignore[arg-type]
            repr=a.repr,
            hash=a.hash,
            init=a.init,
            metadata=a.metadata,
            type=a.type,  # type: ignore[arg-type]
            converter=a.converter,  # type: ignore[arg-type]
            kw_only=a.kw_only,
            eq=a.eq,
            order=a.order,
            on_setattr=a.on_setattr,  # type: ignore[arg-type]
        )
        for a in attr.fields(base_cls)
    }
    for aname, default in nested.items():
        if aname in attribs:
            raise ValueError(f"Duplicate attribute for nested class: {aname}")
        attribs[aname] = attr.attrib(default=default, type=default.__class__)

    cls = attr.make_class(name, attribs)
    cls.__doc__ = base_cls.__doc__
    return cls
