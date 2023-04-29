"""
Converters and helpers for :mod:`cattrs`.
"""
import os
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generator, List, Optional, Set, Type, Union

import attrs
from cattrs import BaseConverter, Converter
from cattrs._compat import is_frozenset, is_mutable_set, is_sequence, is_tuple

from . import dict_utils
from .exceptions import InvalidSettingsError
from .types import ET, LoaderMeta, MergedSettings, OptionList, SettingsDict, T


__all__ = [
    "BaseConverter",
    "Converter",
    "default_converter",
    "register_attrs_hook_factory",
    "register_strlist_hook",
    "from_slist",
    "to_dt",
    "to_bool",
    "to_enum",
    "to_path",
    "DEFAULT_STRUCTURE_HOOKS",
]


def default_converter() -> BaseConverter:
    """
    Get an instanceof the default converter used by Typed Settings.

    Return:
        A :class:`cattrs.BaseConverter` configured with addional hooks for
        loading the follwing types:

        - :class:`bool` using :func:`.to_bool()`
        - :class:`datetime.datetime` using :func:`.to_dt()`
        - :class:`enum.Enum` using :func:`.to_enum()`
        - :class:`pathlib.Path`

        The converter can also structure attrs instances from existing attrs
        instances (normaly, it would only work with dicts).  This allows using
        instances of nested class es of default values for options.  See
        :meth:`cattrs.converters.BaseConverter.register_structure_hook_factory()`.

    This converter can also be used as a base for converters with custom
    structure hooks.
    """
    converter = Converter()
    register_attrs_hook_factory(converter)
    register_strlist_hook(converter, ":")
    for t, h in DEFAULT_STRUCTURE_HOOKS:
        converter.register_structure_hook(t, h)  # type: ignore
    return converter


def register_attrs_hook_factory(converter: BaseConverter) -> None:
    """
    Register a hook factory that allows using instances of attrs classes where
    cattrs would normally expect a dictionary.

    These instances are then returned as-is and without further processing.
    """

    def allow_attrs_instances(typ):  # type: ignore[no-untyped-def]
        def structure_attrs(val, _):  # type: ignore[no-untyped-def]
            if isinstance(val, typ):
                return val
            return converter.structure_attrs_fromdict(val, typ)

        return structure_attrs

    converter.register_structure_hook_factory(attrs.has, allow_attrs_instances)


def register_strlist_hook(
    converter: BaseConverter,
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


def _generate_hook_factory(structure_func, fn):  # type: ignore[no-untyped-def]
    def gen_func(typ):  # type: ignore[no-untyped-def]
        def str2collection(val, _):  # type: ignore[no-untyped-def]
            if isinstance(val, str):
                val = fn(val)
            return structure_func(val, typ)

        return str2collection

    return gen_func


@contextmanager
def set_context(meta: LoaderMeta) -> Generator[None, None, None]:
    """
    Set the context for converting option values from a given loader.

    Currently only chagnes the cwd to :attr:`.LoaderMeta.cwd`.

    Args:
        meta: A loaders meta data

    Return:
        A context manager (that yields ``None``)
    """
    old_cwd = os.getcwd()
    os.chdir(meta.cwd)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def convert(
    merged_settings: MergedSettings,
    cls: Type[T],
    option_infos: OptionList,
    converter: BaseConverter,
) -> T:
    """
    Create an instance of *cls* from the settings in *merged_settings* using the given
    *converter*.

    Args:
        merged_settings: The list of settings values to convert.
        cls: The class to convert to.
        option_infos: The list of all available settings for *cls*.
        converter: The converter to use.

    Return:
        An instance of *cls*.

    Raise:
        InvalidSettingsError: If an instance of *cls* cannot be created for the given
            settings.
    """
    settings_dict: SettingsDict = {}
    errors: List[str] = []
    loaded_settings_paths: Set[str] = set()
    for option_info, meta, value in merged_settings.values():
        field = option_info.field
        if field.type:
            with set_context(meta):
                try:
                    if field.converter:
                        converted_value = field.converter(value)
                    else:
                        converted_value = converter.structure(value, field.type)
                except Exception as e:
                    errors.append(
                        f"Could not convert value {value!r} for option "
                        f"{field.path!r} from loader {meta.name}: {e!r}"
                    )
        else:
            converted_value = value
        dict_utils.set_path(settings_dict, option_info.path, converted_value)
        loaded_settings_paths.add(option_info.path)

    for option_info in option_infos:
        if option_info.path in loaded_settings_paths:
            continue
        if option_info.field.default is not attrs.NOTHING:
            continue
        errors.append(f"No value set for required option {option_info.path!r}")

    try:
        settings = converter.structure(settings_dict, cls)
    except Exception as e:
        errors.append(f"Could not convert loaded settings: {e!r}")

    if errors:
        errs = "".join(f"\n- {e}" for e in errors)
        raise InvalidSettingsError(
            f"{len(errors)} errors occured while converting the loaded option values "
            f"to an instance of {cls.__name__!r}:{errs}"
        )

    return settings


def to_dt(value: Union[datetime, str], _type: type = datetime) -> datetime:
    """
    Convert an ISO formatted string to :class:`datetime.datetime`.  Leave the
    input untouched if it is already a datetime.

    See: :meth:`datetime.datetime.fromisoformat()`

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
            f"Invalid type {type(value).__name__!r}; expected 'datetime' or " f"'str'."
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
    Return a converter that creates an instance of the :class:`~enum.Enum`
    *cls*.

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
