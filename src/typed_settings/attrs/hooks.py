"""
Addtional attrs hooks
"""
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar, Union, get_type_hints

from ._compat import get_args, get_origin
from .converters import (
    to_attrs,
    to_dt,
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
    Return a

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


def _get_converter(
    type_,
    converters,
    iterable_types=frozenset({list, set, frozenset}),
    tuple_types=frozenset({tuple}),
    mapping_types=frozenset({dict}),
):
    """
    Recursively resolves concrete and generic types and return a proper
    converter.
    """
    # Detect whether "type_" is a container type.  Currently we need
    # to check, e.g., for "typing.List".  From python 3.9, we also
    # need to check for "list" directly.
    origin = get_origin(type_)
    if origin is None:
        converter = _handle_concrete(type_, converters)
    else:
        converter = _handle_generic(
            type_, converters, iterable_types, tuple_types, mapping_types
        )

    return converter


def _handle_concrete(type_, converters):
    """
    Returns a converter for concrete types.

    These include attrs classes, :code:`Any` andall types in *converters*.
    """
    # Get converter for concrete type
    if type_ is Any:
        converter = _to_any
    elif getattr(type_, "__attrs_attrs__", None) is not None:
        # Attrs classes
        converter = to_attrs(type_)
    else:
        # Check if type is in converters dict
        for convert_type, convert_func in converters.items():
            if issubclass(type_, convert_type):
                converter = convert_func
                break
        else:
            # Fall back to simple types like bool, int, str, Enum, ...
            converter = type_
    return converter


def _handle_generic(
    type_, converters, iterable_types, tuple_types, mapping_types
):
    """
    Returns a converter for generic types like lists, tuples, dicts or Union.
    """
    origin = get_origin(type_)
    args = get_args(type_)
    if origin in iterable_types:
        item_converter = _get_converter(args[0], converters)
        converter = to_iterable(origin, item_converter)
    elif origin in tuple_types:
        if len(args) == 2 and args[1] == ...:
            # "frozen list" variant of tuple
            item_converter = _get_converter(args[0], converters)
            converter = to_iterable(tuple, item_converter)
        else:
            # "struct" variant of tuple
            item_converters = [_get_converter(t, converters) for t in args]
            converter = to_tuple(tuple, item_converters)
    elif origin in mapping_types:
        key_converter = _get_converter(args[0], converters)
        val_converter = _get_converter(args[1], converters)
        converter = to_mapping(dict, key_converter, val_converter)
    elif origin is Union:
        item_converters = [_get_converter(t, converters) for t in args]
        converter = to_union(item_converters)
    else:
        raise TypeError(f"Cannot create converter for generic type: {type_}")
    return converter


A = TypeVar("A")


def _to_any(val: A) -> A:
    return val


# TODO: Also add "to_bool()"?
auto_convert = make_auto_converter({datetime: to_dt})
"""Auto-convert :class:`datetime.datetime` as well as other stuff."""


def auto_serialize(_inst, _attrib, value):
    """Inverse hook to :func:`auto_convert` for use with
    :func:`attrs.asdict()`.
    """
    if isinstance(value, datetime):
        return datetime.isoformat(value)
    if isinstance(value, Enum):
        return value.value
    return value
