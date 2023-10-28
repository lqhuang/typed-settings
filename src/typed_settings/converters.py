"""
Converters and structure hooks for various data types.
"""
import dataclasses
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from ._compat import PY_310


if PY_310:
    from types import UnionType
else:
    from typing import Union as UnionType  # type: ignore

from .types import ET, T


if TYPE_CHECKING:
    import cattrs
#
#
# __all__ = [
#     "Converter",
#     "TSConverter",
#     "default_converter",
#     "get_default_structure_hooks",
#     "register_attrs_hook_factory",
#     "register_strlist_hook",
#     "to_dt",
#     "to_bool",
#     "to_enum",
#     "to_path",
#     "to_resolved_path",
# ]


class Converter(Protocol):
    """
    **Protocol** that converters must implement.

    Only a :meth:`structure()` method similar to the one from :program:`cattrs` is
    required.

    .. versionadded:: 23.1.0
    """

    def structure(self, value: Any, cls: Type[T]) -> T:
        """
        Convert *value* to an instance of *cls* and return it.

        Args:
            value: The data to be converted.
            cls: The type to convert *value* to.

        Return:
            An instance of *cls* for *value*.
        """
        ...


class TSConverter:
    """
    A simple converter that can replace :program:`cattrs` if you want to use
    Typed Settings without dependencies.

    It supports the same types as the default :program:`cattrs` converter.
    """

    def __init__(
        self,
        resolve_paths: bool = True,
        strlist_sep: Union[str, Callable[[str], list], None] = ":",
    ) -> None:
        if strlist_sep is None:
            self.strlist_hook: Optional[Callable[[str], list]] = None
        elif isinstance(strlist_sep, str):
            self.strlist_hook = lambda v: v.split(strlist_sep)  # type: ignore
        else:
            self.strlist_hook = strlist_sep

        self.scalar_converters: Dict[Any, Callable[[Any, type], Any]] = {
            Any: to_any,
            bool: to_bool,
            int: to_type,
            float: to_type,
            str: to_type,
            datetime: to_dt,
            Enum: to_enum,
            Path: to_resolved_path if resolve_paths else to_path,
        }
        self.composite_hook_factories: List[HookFactory] = [
            ListHookFactory,
            TupleHookFactory,
            DictHookFactory,
            MappingProxyTypeHookFactory,
            SetHookFactory,
            FrozenSetHookFactory,
            UnionHookFactory,
            AttrsHookFactory,
            DataclassesHookFactory,
            PydanticHookFactory,
        ]

    def structure(self, value: Any, cls: Type[T]) -> T:
        """
        Convert *value* to an instance of *cls* and return it.

        Args:
            value: The data to be converted.
            cls: The type to convert *value* to.

        Return:
            An instance of *cls* for *value*.
        """
        for ctype, convert in self.scalar_converters.items():
            if cls is ctype or (
                ctype is not Any and isinstance(cls, type) and issubclass(cls, ctype)
            ):
                return convert(value, cls)

        origin = get_origin(cls)
        args = get_args(cls)
        for hook in self.composite_hook_factories:
            if hook.match(cls, origin, args):
                convert = hook.get_structure_hook(self, cls, origin, args)
                return convert(value, cls)

        raise TypeError(f"Cannot create converter for generic type: {cls}")

    def maybe_apply_strlist_hook(self, value: T) -> Union[list, T]:
        """
        Apply the string list hook to *value* if one is defined and if *value* is a
        string.
        """
        if self.strlist_hook and isinstance(value, str):
            return self.strlist_hook(value)
        return value


def default_converter(*, resolve_paths: bool = True) -> Converter:
    """
    Get a default instances of a converter which will be used to convert/structured
    the loaded settings.

    Args:
        resolve_paths: Whether or not to resolve relative paths.

    Return:
        If :program:`cattrs` is installed, a :class:`cattrs.Converter`.  Else, a
        :class:`TSConverter`.  The converters are configured to handle the following
        types:

        - :class:`bool` (see :func:`to_bool()` for supported inputs)
        - :class:`int`
        - :class:`float`
        - :class:`str`
        - :class:`datetime.datetime` (see :func:`to_dt()`)
        - :class:`enum.Enum` using (see :func:`to_enum()`)
        - :class:`pathlib.Path` (see :func:`to_path()` and :func:`to_resolved_path()`)
        - :class:`list`
        - :class:`tuple`
        - :class:`dict`
        - :class:`types.MappingProxyType` ("read-only" dicts)
        - :class:`set`
        - :class:`frozenset`
        - :data:`typing.Optional`
        - :data:`typing.Union` (depending on the converter, only to a certain degree,
          but this should not be relevant for settings with clearly defined types)
        - :mod:`attrs` classes (from instances and dicts)

        :class:`list`, :class:`tuple`, :class:`set`, and :class:`frozenset` set can also
        be converted from strings.  By default, strings are split by ``:``.  See
        :class:`TSConverter` or :func:`register_strlist_hook()` for details.

    This converter can also be used as a base for converters with custom
    structure hooks.

    .. versionchanged:: 23.1.0
       Return a :program:`cattrs` converter if it is installed or else a Typed Settings
       converter.
    """
    try:
        import cattrs  # noqa: F401
    except ImportError:
        return get_default_ts_converter(resolve_paths=resolve_paths)
    else:
        return get_default_cattrs_converter(resolve_paths=resolve_paths)


def get_default_ts_converter(resolve_paths: bool = True) -> "TSConverter":
    """
    Return a :class:`TSConverter` with default settings
    (see :func:`default_converter()` for argument and return value description).

    Args:
        resolve_paths: Whether or not to resolve relative paths.

    Return:
        A :class:`TSConverter` instance with default configuration.
    """
    return TSConverter(resolve_paths=resolve_paths)


def get_default_cattrs_converter(resolve_paths: bool = True) -> "cattrs.Converter":
    """
    Return a :class:`cattrs.Converter` with default settings
    (see :func:`default_converter()` for argument and return value description).

    Args:
        resolve_paths: Whether or not to resolve relative paths.

    Return:
        A :class:`cattrs.Converter` instance with default configuration.

    Raises:
        ModuleNotFoundError: if :program:`cattrs` is not installed.
    """
    try:
        import cattrs
    except ImportError as e:
        raise ModuleNotFoundError(
            "Module 'cattrs' not installed.  Please run "
            "'python -m pip install -U typed-settings[cattrs]'"
        ) from e

    converter = cattrs.Converter()
    register_mappingproxy_hook(converter)
    register_attrs_hook_factory(converter)
    register_dataclasses_hook_factory(converter)
    register_pydantic_hook_factory(converter)
    register_strlist_hook(converter, ":")
    for t, h in get_default_structure_hooks(resolve_paths=resolve_paths):
        converter.register_structure_hook(t, h)  # type: ignore
    return converter


def get_default_structure_hooks(
    *,
    resolve_paths: bool = True,
) -> List[Tuple[type, Callable[[Any, type], Any]]]:
    """
    Return a list of default structure hooks for cattrs.

    Args:
        resolve_paths: Whether or not to resolve relative paths.

    Return:
        A list of tuples that can be used as args for
        :meth:`cattrs.BaseConverter.register_structure_hook()`.
    """
    path_hook = to_resolved_path if resolve_paths else to_path
    return [
        (bool, to_bool),
        (datetime, to_dt),
        (Enum, to_enum),
        (Path, path_hook),
    ]


def register_attrs_hook_factory(converter: "cattrs.Converter") -> None:
    """
    Register a hook factory that allows using instances of :program:`attrs` classes
    where :program:`cattrs` would normally expect a dictionary.

    These instances are then returned as-is and without further processing.

    Args:
        converter: The :class:`cattrs.Converter` to register the hook at.
    """

    def allow_attrs_instances(typ):  # type: ignore[no-untyped-def]
        def structure_attrs(val, _):  # type: ignore[no-untyped-def]
            if isinstance(val, typ):
                return val
            return converter.structure_attrs_fromdict(val, typ)

        return structure_attrs

    import attrs

    converter.register_structure_hook_factory(attrs.has, allow_attrs_instances)


def register_dataclasses_hook_factory(converter: "cattrs.Converter") -> None:
    """
    Register a hook factory that allows using instances of :mod:`dataclasses` classes
    where :program:`cattrs` would normally expect a dictionary.

    These instances are then returned as-is and without further processing.

    Args:
        converter: The :class:`cattrs.Converter` to register the hook at.
    """

    def allow_dataclasses_instances(typ):  # type: ignore[no-untyped-def]
        def structure_dataclasses(val, _):  # type: ignore[no-untyped-def]
            if isinstance(val, typ):
                return val
            return converter.structure_attrs_fromdict(val, typ)

        return structure_dataclasses

    converter.register_structure_hook_factory(
        dataclasses.is_dataclass, allow_dataclasses_instances
    )


def register_pydantic_hook_factory(converter: "cattrs.Converter") -> None:
    """
    Register a hook factory that allows using instances of :mod:`dataclasses` classes
    where :program:`cattrs` would normally expect a dictionary.

    These instances are then returned as-is and without further processing.

    Args:
        converter: The :class:`cattrs.Converter` to register the hook at.
    """
    try:
        import pydantic
    except ImportError:  # pragma: no cover
        return

    def check(typ: type) -> bool:
        return issubclass(typ, pydantic.BaseModel)

    def to_pydantic(typ):  # type: ignore[no-untyped-def]
        def structure_dataclasses(val, _):  # type: ignore[no-untyped-def]
            if isinstance(val, typ):
                return val
            return typ(**val)

        return structure_dataclasses

    converter.register_structure_hook_factory(check, to_pydantic)


def register_mappingproxy_hook(converter: "cattrs.Converter") -> None:
    """
    Register a hook factory for converting data to :class:`types.MappingProxyType`
    instances.

    Args:
        converter: The :class:`cattrs.Converter` to register the hook at.
    """

    def check(cls: type) -> bool:
        return cls is MappingProxyType or get_origin(cls) is MappingProxyType

    def convert(val: Mapping, cls: Type[T]) -> T:
        args = get_args(cls)
        t = Dict[args[0], args[1]] if args else Dict  # type: ignore
        return MappingProxyType(converter.structure(val, t))  # type: ignore

    converter.register_structure_hook_func(check, convert)


def register_strlist_hook(
    converter: "cattrs.Converter",
    sep: Optional[str] = None,
    fn: Optional[Callable[[str], list]] = None,
) -> None:
    """
    Register a hook factory with *converter* that allows structuring lists,
    (frozen) sets and tuples from strings (which may, e.g., come from
    environment variables).

    Args:
        converter: The :class:`cattrs.Converter` to register the hook at.
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

    from cattrs._compat import is_frozenset, is_mutable_set, is_sequence, is_tuple

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


def to_any(value: Any, _cls: type) -> Any:
    """
    Return *value* as-is.
    """
    return value


def to_bool(value: Any, _cls: type = bool) -> bool:
    """
    Convert "boolean" strings (e.g., from env. vars.) to real booleans.

    Values mapping to :code:`True`:

    - :code:`True`
    - :code:`"true"` / :code:`"t"` (case insensitive)
    - :code:`"yes"` / :code:`"y"` (case insensitive)
    - :code:`"on"` (case insensitive)
    - :code:`"1"`
    - :code:`1`

    Values mapping to :code:`False`:

    - :code:`False`
    - :code:`"false"` / :code:`"f"` (case insensitive)
    - :code:`"no"` / :code:`"n"` (case insensitive)
    - :code:`"off"` (case insensitive)
    - :code:`"0"`
    - :code:`0`

    Args:
        value: The value to parse.
        _cls: (ignored)

    Return:
        A :class:`bool` for the input *value*.

    Raise:
        ValueError: If *value* is any other value than stated above.
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


def to_dt(value: Union[datetime, str], _cls: type = datetime) -> datetime:
    """
    Convert an ISO formatted string to :class:`datetime.datetime`.  Leave the
    input untouched if it is already a datetime.

    See: :meth:`datetime.datetime.fromisoformat()`

    The ``Z`` suffix is also supported and will be replaced with ``+00:00``.

    Args:
        value: The input data
        _cls: (ignored)

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


def to_enum(value: Any, cls: Type[ET]) -> ET:
    """
    Return an instance of the enum *cls* for *value*.

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


def to_path(value: Union[Path, str], _cls: type) -> Path:
    """
    Convert *value* to :class:`~pathlib.Path`.

    Args:
        value: The input data
        _cls: (ignored)

    Return:
        An instance of :class:`~pathlib.Path`

    Raise:
        TypeError: If *value* cannot be converted to a path.
    """
    return Path(value)


def to_resolved_path(value: Union[Path, str], _cls: type) -> Path:
    """
    Convert *value* to :class:`~pathlib.Path` and resolve it.

    Args:
        value: The input data
        _cls: (ignored)

    Return:
        A resolved instance of :class:`~pathlib.Path`

    Raise:
        TypeError: If *value* cannot be converted to a path.
    """
    return Path(value).resolve()


def to_type(value: Any, cls: Type[T]) -> T:
    """
    Convert *value* to *cls*.

    Args:
        value: The input data
        cls: A class that takes a single argument, e.g., :class:`int`, :class:`float`,
            or :class:`str`.

    Return:
        An instance of *cls*.

    Raise:
        ValueError: if *value* cannot be converted to *cls*.
    """
    return cls(value)  # type: ignore[call-arg]


class HookFactory(Protocol):
    """
    **Protocol** for :class:`TSConverter` hook factories.

    Hook factories have a :meth:`match` functions that decides whether they can handle
    given type/class.  In addition, they can generate a structure hook for that type.
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        """
        Check whether this class can handle the given type *cls*.

        Args:
            cls: The type/class to check.
            origin: The type's origin as returned by :func:`typing.get_origin()`.
            args: The type's args as retuned by :func:`typing.get_args()`.

        Return:
            ``True`` if this class can convert the given type, or else ``False``.
        """
        ...

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Any, Type[T]], T]:
        """
        Return a structure hook for the given type/class.

        Args:
            converter: The :class:`TSConverter` that the returned hook will be
                registered at.  The structure hook can use the converter to recursively
                convert sub elements of composite types.
            cls: The type/class to convert to.
            origin: The type's origin as returned by :func:`typing.get_origin()`.
            args: The type's args as retuned by :func:`typing.get_args()`.

        Return:
            A structure hook, which is a function
            :samp:`hook({value}: Any, {cls}: Type[T]) -> T`.
        """
        ...


class AttrsHookFactory:
    """
    A :class:`HookFactory` that returns :program:`attrs` classes from dicts.  Instances
    are of the given class are accepted as well and returned as-is (without further
    processing of their attributes).
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        try:
            import attrs
        except ImportError:
            return False

        return attrs.has(cls)

    @staticmethod
    def get_structure_hook(
        converter: Converter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Union[dict, T], Type[T]], T]:
        import attrs

        def convert(value: Union[dict, T], cls: Type[T]) -> T:
            if isinstance(value, cls):
                return value

            if not isinstance(value, dict):
                raise TypeError(
                    f'Invalid type "{type(value).__name__}"; expected '
                    f'"{cls.__name__}" or "dict".'
                )

            fields = attrs.fields_dict(cls)  # type: ignore[arg-type]
            values = {
                n: converter.structure(v, fields[n].type)  # type: ignore[arg-type]
                for n, v in value.items()
            }
            return cls(**values)

        return convert


class DataclassesHookFactory:
    """
    A :class:`HookFactory` that returns :mod:`dataclasses` from dicts.  Instances
    are of the given class are accepted as well and returned as-is (without further
    processing of their attributes).
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return dataclasses.is_dataclass(cls)

    @staticmethod
    def get_structure_hook(
        converter: Converter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Union[dict, T], Type[T]], T]:
        def convert(value: Union[dict, T], cls: Type[T]) -> T:
            if isinstance(value, cls):
                return value

            if not isinstance(value, dict):
                raise TypeError(
                    f'Invalid type "{type(value).__name__}"; expected '
                    f'"{cls.__name__}" or "dict".'
                )

            fields = {
                f.name: f for f in dataclasses.fields(cls)  # type: ignore[arg-type]
            }
            values = {
                n: converter.structure(v, fields[n].type)  # type: ignore[arg-type]
                for n, v in value.items()
            }
            return cls(**values)

        return convert


class PydanticHookFactory:
    """
    A :class:`HookFactory` that returns :mod:`dataclasses` from dicts.  Instances
    are of the given class are accepted as well and returned as-is (without further
    processing of their attributes).
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        try:
            import pydantic
        except ImportError:
            return False
        return issubclass(cls, pydantic.BaseModel)

    @staticmethod
    def get_structure_hook(
        converter: Converter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Union[dict, T], Type[T]], T]:
        def convert(value: Union[dict, T], cls: Type[T]) -> T:
            if isinstance(value, cls):
                return value

            if not isinstance(value, dict):
                raise TypeError(
                    f'Invalid type "{type(value).__name__}"; expected '
                    f'"{cls.__name__}" or "dict".'
                )

            return cls(**value)

        return convert


class ListHookFactory:
    """
    A :class:`HookFactory` for :class:`list` and :class:`typing.List`.
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return cls is list or origin is list

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Iterable, Type[T]], T]:
        if not args:
            args = (Any,)
        item_type = args[0]

        def convert(value: Iterable, cls: Type[T]) -> T:
            value = converter.maybe_apply_strlist_hook(value)
            values = [converter.structure(v, item_type) for v in value]
            return list(values)  # type: ignore[return-value]

        return convert


class TupleHookFactory:
    """
    A :class:`HookFactory` for :class:`tuple` and :class:`typing.Tuple`.
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return cls is tuple or origin is tuple

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Union[Callable[[Iterable, Type[T]], T], Callable[[Sequence, Type[T]], T]]:
        if not args:
            args = (Any, ...)

        convert: Union[
            Callable[[Iterable, Type[T]], T],  # For list-like tuples
            Callable[[Sequence, Type[T]], T],  # For struct-like tuples
        ]
        if len(args) == 2 and args[1] == ...:
            item_type = args[0]

            def convert(value: Iterable, cls: Type[T]) -> T:
                value = converter.maybe_apply_strlist_hook(value)
                values = [converter.structure(v, item_type) for v in value]
                return tuple(values)  # type: ignore[return-value]

        else:

            def convert(value: Sequence, cls: Type[T]) -> T:
                value = converter.maybe_apply_strlist_hook(value)
                if len(value) != len(args):
                    raise TypeError(
                        f"Value must have {len(args)} items but has: {len(value)}"
                    )
                values = [converter.structure(v, t) for v, t in zip(value, args)]
                return tuple(values)  # type: ignore[return-value]

        return convert


class DictHookFactory:
    """
    A :class:`HookFactory` for :class:`dict` and :class:`typing.Dict`.
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return cls is dict or origin is dict

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Mapping, Type[T]], T]:
        if not args:
            args = (Any, Any)
        key_type, val_type = args

        def convert(value: Mapping, cls: Type[T]) -> T:
            values = {
                converter.structure(k, key_type): converter.structure(v, val_type)
                for k, v in value.items()
            }
            return values  # type: ignore[return-value]

        return convert


class MappingProxyTypeHookFactory:
    """
    A :class:`HookFactory` for :class:`types.MappingProxyType` (a read-only dict proxy).
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return cls is MappingProxyType or origin is MappingProxyType

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Any, Type[T]], T]:
        if not args:
            args = (Any, Any)
        key_type, val_type = args

        def convert(value: Mapping, cls: Type[T]) -> T:
            values = {
                converter.structure(k, key_type): converter.structure(v, val_type)
                for k, v in value.items()
            }
            return MappingProxyType(values)  # type: ignore[return-value]

        return convert


class SetHookFactory:
    """
    A :class:`HookFactory` for :class:`set` and :class:`typing.Set`.
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return cls is set or origin is set

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Any, Type[T]], T]:
        if not args:
            args = (Any,)
        item_type = args[0]

        def convert(value: Iterable, cls: Type[T]) -> T:
            value = converter.maybe_apply_strlist_hook(value)
            values = [converter.structure(v, item_type) for v in value]
            return set(values)  # type: ignore[return-value]

        return convert


class FrozenSetHookFactory:
    """
    A :class:`HookFactory` for :class:`frozenset` and :class:`typing.FrozenSet`.
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return cls is frozenset or origin is frozenset

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Any, Type[T]], T]:
        if not args:
            args = (Any,)
        item_type = args[0]

        def convert(value: Iterable, cls: Type[T]) -> T:
            value = converter.maybe_apply_strlist_hook(value)
            values = [converter.structure(v, item_type) for v in value]
            return frozenset(values)  # type: ignore[return-value]

        return convert


class UnionHookFactory:
    """
    A :class:`HookFactory` for :data:`typing.Optional` and :data:`typing.Union`.

    If the input data already has one of the uniton types, it will be returned without
    further processing.  Otherwise, converters for all union types will be tried until
    one works (i.e., raises no exception).
    """

    @staticmethod
    def match(cls: type, origin: Optional[Any], args: Tuple[Any, ...]) -> bool:
        return origin in (Union, UnionType)

    @staticmethod
    def get_structure_hook(
        converter: TSConverter, cls: type, origin: Optional[Any], args: Tuple[Any, ...]
    ) -> Callable[[Any, Type[T]], T]:
        def convert(value: Any, cls: Type[T]) -> T:
            if type(value) in args:
                # Preserve val as-is if it already has a matching type.
                # Otherwise float(3.2) would be converted to int
                # if the converters are [int, float].
                return value
            for arg in args:
                try:
                    return converter.structure(value, arg)
                except Exception:  # noqa: S110
                    pass
            raise ValueError(f"Failed to convert value to any Union type: {value}")

        return convert
