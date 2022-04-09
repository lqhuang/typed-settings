"""
Converters and helpers for :mod:`cattr`.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Type, Union

from attrs import has
from cattrs import Converter, GenConverter


try:
    from cattr._compat import (  # type: ignore
        is_frozenset,
        is_mutable_set,
        is_sequence,
        is_tuple,
    )
except ImportError:
    from cattrs._compat import (  # type: ignore
        is_frozenset,
        is_mutable_set,
        is_sequence,
        is_tuple,
    )

from .exceptions import InvalidValueError
from .types import ET, SettingsDict, T


def default_converter() -> GenConverter:
    """
    Get an instanceof the default converter used by Typed Settings.

    Return:
        A :class:`cattrs.GenConverter` configured with addional hooks for
        loading the follwing types:

        - :class:`bool` using :func:`.to_bool()`
        - :class:`datetime.datetime` using :func:`.to_dt()`
        - :class:`enum.Enum` using :func:`.to_enum()`
        - :class:`pathlib.Path`

        The converter can also structure attrs instances from existing attrs
        instances (normaly, it would only work with dicts).  This allows using
        instances of nested class es of default values for options.  See
        :func:`register_structure_hook_factory()`.

    This converter can also be used as a base for converters with custom
    structure hooks.
    """
    converter = GenConverter()
    register_attrs_hook_factory(converter)
    register_strlist_hook(converter, ":")
    for t, h in DEFAULT_STRUCTURE_HOOKS:
        converter.register_structure_hook(t, h)  # type: ignore
    return converter


def register_attrs_hook_factory(converter: Converter) -> None:
    """
    Register a hook factory that allows using instances of attrs classes where
    cattrs would normally expect a dictionary.

    These instances are then returned as-is and without further processing.
    """

    def allow_attrs_instances(typ):
        def structure_attrs(val, _):
            if isinstance(val, typ):
                return val
            return converter.structure_attrs_fromdict(val, typ)

        return structure_attrs

    converter.register_structure_hook_factory(has, allow_attrs_instances)


def register_strlist_hook(
    converter: Converter,
    sep: Optional[str] = None,
    fn: Optional[Callable[[str], list]] = None,
) -> None:
    """
    Register a hook factory with *converter* that allows structuring lists,
    (frozen) sets and tuples from strings (which may, e.g., come from
    environment variables).

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

    collection_types = [
        # Order is important, tuple must be last!
        (is_sequence, converter._structure_list),
        (is_mutable_set, converter._structure_set),
        (is_frozenset, converter._structure_frozenset),
        (is_tuple, converter._structure_tuple),
    ]

    for check, structure_func in collection_types:
        hook_factory = _generate_hook_factory(structure_func, fn)
        converter.register_structure_hook_factory(check, hook_factory)


def _generate_hook_factory(structure_func, fn):
    def gen_func(typ):
        def str2collection(val, _):
            if isinstance(val, str):
                val = fn(val)
            return structure_func(val, typ)

        return str2collection

    return gen_func


def from_dict(settings: SettingsDict, cls: Type[T], converter: Converter) -> T:
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
    except (AttributeError, KeyError, ValueError, TypeError) as e:
        raise InvalidValueError(str(e)) from e


def to_dt(value: Union[datetime, str], _type: type = datetime) -> datetime:
    """
    Convert an ISO formatted string to :class:`datetime.datetime`.  Leave the
    input untouched if it is already a datetime.

    See: :func:`datetime.datetime.fromisoformat()`

    The ``Z`` suffix is also supported and will be replaced with ``+00:00``.

    Args:
        value: The input data
        _type: The desired output type, will be ignored

    Return:
        The converted datetime instance

    Raise:
        TypeError: If *val* is neither a string nor a datetime
    """
    if not isinstance(value, (datetime, str)):
        raise TypeError(
            f'Invalid type "{type(value).__name__}"; expected "datetime" or '
            f'"str".'
        )
    if isinstance(value, str):
        if value[-1] == "Z":
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    return value


def to_bool(value: Any, _type: type = bool) -> bool:
    """
    Convert "boolean" strings (e.g., from env. vars.) to real booleans.

    Values mapping to :code:`True`:

    - :code:`True`
    - :code:`"true"` / :code:`"t"`
    - :code:`"yes"` / :code:`"y"`
    - :code:`"on"`
    - :code:`"1"`
    - :code:`1`

    Values mapping to :code:`False`:

    - :code:`False`
    - :code:`"false"` / :code:`"f"`
    - :code:`"no"` / :code:`"n"`
    - :code:`"off"`
    - :code:`"0"`
    - :code:`0`

    Raise :exc:`ValueError` for any other value.
    """
    if isinstance(value, str):
        value = value.lower()
    truthy = {True, "true", "t", "yes", "y", "on", "1", 1}
    falsy = {False, "false", "f", "no", "n", "off", "0", 0}
    try:
        if value in truthy:
            return True
        if value in falsy:
            return False
    except TypeError:
        # Raised when "val" is not hashable (e.g., lists)
        pass
    raise ValueError(f"Cannot convert value to bool: {value}")


def to_enum(value: Any, cls: Type[ET]) -> ET:
    """
    Return a converter that creates an instance of the :class:`.Enum` *cls*.

    If the to be converted value is not already an enum, the converter will
    create one by name (``MyEnum[val]``).

    Args:
        value: The input data
        cls: The enum type

    Return:
        An instance of *cls*

    Raise:
        KeyError: If *value* is not a valid member of *cls*

    """
    if isinstance(value, cls):
        return value

    return cls[value]


def to_path(value: Union[Path, str], _type: type) -> Path:
    return Path(value)


DEFAULT_STRUCTURE_HOOKS = [
    (bool, to_bool),
    (datetime, to_dt),
    (Enum, to_enum),
    (Path, to_path),
]
