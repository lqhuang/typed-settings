"""
Addtional attrs hooks
"""
from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar, Union, get_type_hints

from ._compat import get_args, get_origin
from .converters import (
    to_attrs,
    to_dt,
    to_enum,
    to_iterable,
    to_mapping,
    to_tuple,
    to_union,
)


__all__ = [
    "auto_convert",
    "auto_serialize",
    "make_auto_converter",
]


def make_auto_converter(converters):
    """
    Creates and returns an auto-converter `field transformer`_.

    .. _field transformer: https://www.attrs.org/en/stable/extending.html
                        #automatic-field-transformation-and-modification

    Args:
        converters (Dict[T, Callable[[Any], T]): A dict mapping types to
          converter functions.

    Returns:
        A function that can be passed as *field_transformer* to
        :func:`attr.s()`/:func:`attr.define()`.

    Example:

        .. code-block:: python

            >>> from datetime import datetime
            >>>
            >>> import attr
            >>> from typed_settings.attrs.converters import to_bool, to_dt
            >>> from typed_settings.attrs.hooks import make_auto_converter
            >>>
            >>>
            >>> auto_convert = make_auto_converter({
            ...     bool: to_bool,
            ...     datetime: to_dt,
            ... })
            >>>
            >>> @attr.frozen(field_transformer=auto_convert)
            ... class C:
            ...     a: bool
            ...     b: datetime
            ...
            >>> C(a="false", b="2020-05-04")
            C(a=False, b=datetime.datetime(2020, 5, 4, 0, 0))

    """

    def auto_convert(cls, attribs):
        """
        A field transformer that tries to convert all attribs of a class to
        their annotated type.
        """
        # We cannot use attrs.resolve_types() here,
        # because "cls" is not yet a finished attrs class:
        type_hints = get_type_hints(cls)
        results = []
        for attrib in attribs:
            # Do not override explicitly defined converters!
            if attrib.converter is None:
                converter = _get_converter(type_hints[attrib.name], converters)
                attrib = attrib.evolve(converter=converter)
            results.append(attrib)

        return results

    return auto_convert


def _get_converter(typ, converters):
    """
    Recursively resolves concrete and generic types and return a proper
    converter.
    """
    origin = get_origin(typ)
    if origin is None:
        converter = _handle_concrete(typ, converters)
    else:
        converter = _handle_generic(typ, converters)

    return converter


def _handle_concrete(typ, converters):
    """
    Returns a converter for concrete types.

    These include attrs classes, :code:`Any` andall types in *converters*.
    """
    # Get converter for concrete type
    if typ is Any:
        converter = _to_any
    elif getattr(typ, "__attrs_attrs__", None) is not None:
        # Attrs classes
        converter = to_attrs(typ)
    elif issubclass(typ, Enum):
        converter = to_enum(typ)
    else:
        # Check if type is in converters dict
        for convert_type, convert_func in converters.items():
            if issubclass(typ, convert_type):
                converter = convert_func
                break
        else:
            # Fall back to simple types like bool, int, str, Enum, ...
            converter = typ
    return converter


def _handle_generic(typ, converters):
    """
    Returns a converter for generic types like lists, tuples, dicts or Union.
    """
    origin = get_origin(typ)
    args = get_args(typ)

    # List-like types
    if origin in {list, Sequence, MutableSequence}:
        item_converter = _get_converter(args[0], converters)
        converter = to_iterable(list, item_converter)
    elif origin in {set, MutableSet}:
        item_converter = _get_converter(args[0], converters)
        converter = to_iterable(set, item_converter)
    elif origin is frozenset:
        item_converter = _get_converter(args[0], converters)
        converter = to_iterable(frozenset, item_converter)

    elif origin is tuple:
        if len(args) == 2 and args[1] == ...:
            # "list" variant of tuple
            item_converter = _get_converter(args[0], converters)
            converter = to_iterable(tuple, item_converter)
        else:
            # "struct" variant of tuple
            item_converters = [_get_converter(t, converters) for t in args]
            converter = to_tuple(tuple, item_converters)

    elif origin in {dict, Mapping, MutableMapping}:
        key_converter = _get_converter(args[0], converters)
        val_converter = _get_converter(args[1], converters)
        converter = to_mapping(dict, key_converter, val_converter)

    elif origin is Union:
        item_converters = [_get_converter(t, converters) for t in args]
        converter = to_union(item_converters)

    else:
        raise TypeError(f"Cannot create converter for generic type: {typ}")

    return converter


A = TypeVar("A")


def _to_any(val: A) -> A:
    return val


# TODO: Also add "to_bool()"?
auto_convert = make_auto_converter({datetime: to_dt})
"""
An Attrs `field transformer`_ that adds converters to attributes based on their
type.

It supports concrete types (like :class:`int`) as well as generic types (like
:class:`typing.List`).  Generic/nested types will be converted recursively.

The following types are supported:

Concrete Types:
    - Attrs classes (see :func:`.to_attrs()`)
    - :class:`datetime.datetime`, (ISO format with support for ``Z`` suffix,
      see :func:`.to_dt()`).
    - All other types use the *type* object itself as converter, this includes
      :class:`bool`, :class:`int`, :class:`float`, :class:`str`, and
      :class:`~enum.Enum`.

Generic Types:
    - ``typing.List[T]``, ``typing.Sequence[T]``, ``typing.MutableSequence[T]``
      (converts to :class:`list`, see :func:`.to_iterable()`)
    - ``typing.Tuple[T, ...]`` (converts to
      :class:`tuple`, see :func:`.to_iterable()`)
    - ``typing.Tuple[X, Y, Z]`` (converts to :class:`tuple`, see
      :func:`.to_tuple()`)
    - ``typing.Dict[K, V]``, ``typing.Mapping[K, V]``,
      ``typing.MutableMapping[K, V]`` (converts to :class:`dict`, see
      :func:`.to_mapping()`)
    - ``typing.Optional[T]``, ``typing.Union[X, Y, Z]`` (converts to first
      matching type, see :func:`.to_union()`)

.. _field transformer: https://www.attrs.org/en/stable/extending.html
                       #automatic-field-transformation-and-modification

"""


def auto_serialize(_inst, _attrib, value):
    """
    Inverse hook to :func:`auto_convert` for use with :func:`attrs.asdict()`.
    """
    if isinstance(value, datetime):
        return datetime.isoformat(value)
    if isinstance(value, Enum):
        return value.value
    return value
