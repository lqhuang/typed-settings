"""
Framework agnostic utilities for generating CLI options from Typed Settings
options.
"""
from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)
from typing import Protocol, get_args, get_origin

from ._compat import PY_310


if PY_310:
    from types import UnionType
else:
    from typing import Union as UnionType  # type: ignore

from typing import Any, Collection, Dict, List, Optional, Tuple, Union

from . import converters, types


__all__ = [
    "NO_DEFAULT",
    "NoDefaultType",
    "TypeHandlerFunc",
    "TypeHandler",
    "TypeArgsMaker",
    "get_default",
    "check_if_optional",
]


class NoDefaultType:
    """
    Sentinel class to indicate the lack of a default value for an option when ``None``
    is ambiguous.

    ``NoDefaultType`` is a singleton. There is only ever one of it.
    """

    _singleton = None

    def __new__(cls) -> "NoDefaultType":
        if NoDefaultType._singleton is None:
            NoDefaultType._singleton = super().__new__(cls)
        return NoDefaultType._singleton

    def __repr__(self) -> str:
        return "NO_DEFAULT"


NO_DEFAULT = NoDefaultType()
"""
Sentinel that indicates the lack of a default value for an option.
"""

DEFAULT_SENTINEL = object()
DEFAULT_SENTINEL_NAME = "DEFAULT_SENTINEL"


Default = Union[Any, None, NoDefaultType]
NoneType = type(None)
StrDict = Dict[str, Any]


class TypeHandlerFunc(Protocol):
    """
    **Protocol:** A function that returns keyword arguments for a CLI option
    for a specific type.
    """

    def __call__(self, type: type, default: Default, is_optional: bool) -> StrDict:
        """
        Return keyword arguments for creating an option for *type*.

        Args:
            type: The type to create the option for.
            default: The default value for the option.  May be ``None`` or
                :data:`NO_DEFAULT`.
            is_optional: Whether the original type was an
                :class:`~typing.Optional`.
        """
        ...


class TypeHandler(Protocol):
    """
    **Protocol:** Callbacks for the :class:`TypeArgsMaker` that provide
    framework specific arguments for various classes of CLI options.

    .. versionadded:: 2.0.0
    """

    def get_scalar_handlers(self) -> Dict[type, TypeHandlerFunc]:
        """
        Return a dict that maps specialized handlers for certain types (e.g.,
        enums or datetimes.

        Such a handler can look like this:

        .. code-block:: python

            def handle_mytype(
                type: type,
                default: Default,
                is_optional: bool,
            ) -> Dict[str, Any]:
                kwargs = {
                    "type": MyCliType(...)
                }
                if default not in (None, NO_DEFAULT):
                    kwargs["default"] = default.stringify()
                elif is_optional:
                    kwargs["default"] = None
                return kwargs

        Return:
            A dict mapping types to the corresponding type handler function.
        """
        ...

    def handle_scalar(
        self, type: Optional[type], default: Default, is_optional: bool
    ) -> StrDict:
        """
        Handle all scalars for which :func:`get_scalar_handlers()` does not
        provide a specific handler.

        Args:
            type: The type to create an option for.  Can be none if the option
                is untyped.
            default: The default value for the option. My be ``None`` or
                :data:`NO_DEFAULT`.
            is_optional: Whether or not the option type was marked as option
                or not.

        Return:
            A dictionary with keyword arguments for creating an option for the
            given type.
        """
        ...

    def handle_tuple(
        self,
        type_args_maker: "TypeArgsMaker",
        types: Tuple[Any, ...],
        default: Optional[Tuple],
        is_optional: bool,
    ) -> StrDict:
        """
        Handle options for structured tuples (i.e., not list-like tuples).

        Args:
            type_args_maker: The :class:`TypeArgsMaker` that called this
                function.
            types: The types of all tuple items.
            default: Either a tuple of default values or ``None``.
            is_optional: Whether or not the option type was marked as option
                or not.

        Return:
            A dictionary with keyword arguments for creating an option for the
            tuple.
        """
        ...

    def handle_collection(
        self,
        type_args_maker: "TypeArgsMaker",
        types: Tuple[Any, ...],
        default: Optional[List[Any]],
        is_optional: bool,
    ) -> StrDict:
        """
        Handle collections, add options to allow multiple values and to
        collect them in a list/collection.

        Args:
            type_args_maker: The :class:`TypeArgsMaker` that called this
                function.
            types: The types of the list items.
            default: Either a collection of default values or ``None``.
            is_optional: Whether or not the option type was marked as option
                or not.

        Return:
            A dictionary with keyword arguments for creating an option for the
            list type.
        """
        ...

    def handle_mapping(
        self,
        type_args_maker: "TypeArgsMaker",
        types: Tuple[Any, ...],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        """
        Handle dictionaries.

        Args:
            type_args_maker: The :class:`TypeArgsMaker` that called this
                function.
            types: The types of keys and values.
            default: Either a mapping of default values, ``None`` or :data:`NO_DEFAULT`.
            is_optional: Whether or not the option type was marked as option
                or not.

        Return:
            A dictionary with keyword arguments for creating an option for the
            tuple.
        """
        ...


class TypeArgsMaker:
    """
    This class derives type information (in the form of keyword arguments)
    for CLI options from attributes of a settings class.

    For example, it could return a dict ``{"type": int, "default": 3}`` for
    an option ``val: int = 3``.

    It is agnostic of the CLI framework being used.  The specifics for each
    framework are implemented in a :class:`TypeHandler` that is passed to this
    class.

    The TypeArgsMaker differentitates between scalar and collection types
    (e.g., :samp:`int` vs. :samp:`list[int]`. It inspects each option (field)
    of a settings class and calls the appropriate method of the
    :class:`TypeHandler`:

    - If a type is in the dict returned by
      :meth:`TypeHandler.get_scalar_handlers()`, call the corresponding
      handler.

    - For other scalar types, call :meth:`TypeHandler.handle_scalar()`.

    - For structured tuples, call :meth:`TypeHandler.handle_tuple()`.

    - For collections (e.g., lists, sets, and list-like tuples), call
      :meth:`TypeHandler.handle_collection()`.

    - For mappings (e.g., dicts), call :meth:`TypeHandler.handle_mapping()`.

    .. versionchanged:: 2.0.0
       Complete refactoring and renamed from *TypeHandler* to *TypeArgsMaker*.
    """

    def __init__(
        self,
        type_handler: TypeHandler,
    ) -> None:
        self.type_handler = type_handler
        self.list_types = (
            list,
            Sequence,
            MutableSequence,
            set,
            frozenset,
            MutableSet,
        )
        self.tuple_types = (tuple,)
        self.mapping_types = (
            dict,
            Mapping,
            MutableMapping,
        )

    def get_kwargs(self, otype: Any, default: Default) -> StrDict:
        """
        Analyse the option type and return keyword arguments for creating a
        CLI option for it.

        Args:
            otype: The option's type.  It can be None if the user uses an
                untyped class.
            default: The default value for the option.  It can be anything, but the
                values ``None`` (possible default for optional types) and
                :data:`NO_DEFAULT` (no default set) should be handled explicitly.

        Return:
            A dictionary with keyword arguments for creating a CLI option in
            for a given framework.

        Raise:
            TypeError: If the *otype* has an unsupported type (e.g., a union
                type).
        """
        origin = get_origin(otype)
        args = get_args(otype)
        otype, default, origin, args, is_optional = check_if_optional(
            otype, default, origin, args
        )

        if otype is None:
            return self._handle_scalar(otype, default, is_optional)

        elif origin is None:
            scalar_handlers = self.type_handler.get_scalar_handlers()
            for target_type, get_kwargs in scalar_handlers.items():
                if issubclass(otype, target_type):
                    return get_kwargs(otype, default, is_optional)

            return self._handle_scalar(otype, default, is_optional)

        else:
            if origin in self.list_types:
                return self._handle_collection(otype, args, default, is_optional)
            elif origin in self.tuple_types:
                return self._handle_tuple(otype, args, default, is_optional)
            elif origin in self.mapping_types:
                return self._handle_mapping(otype, args, default, is_optional)

            raise TypeError(f"Cannot create CLI option for: {otype}")

    def _handle_scalar(
        self,
        type: Optional[type],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        """
        Get kwargs for scalar types.
        """
        return self.type_handler.handle_scalar(type, default, is_optional)

    def _handle_tuple(
        self,
        type: type,
        args: Tuple[Any, ...],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        """
        Get kwargs for tuples.

        Call :meth:`_handle_collection()` for list like tuples.
        """
        if len(args) == 2 and args[1] == ...:
            # "Immutable list" variant of tuple
            return self._handle_collection(type, args, default, is_optional)

        # "struct" variant of tuple

        default_val: Optional[Tuple]
        if isinstance(default, tuple):
            if not len(default) == len(args):
                raise TypeError(
                    f"Default value must be of len {len(args)}: {len(default)}"
                )
            kwargs = {"strict": True} if PY_310 else {}
            default_val = tuple(
                self.get_kwargs(a, d)["default"]
                for a, d in zip(args, default, **kwargs)
            )
        else:
            default_val = None

        kwargs = self.type_handler.handle_tuple(self, args, default_val, is_optional)
        return kwargs

    def _handle_collection(
        self,
        type: type,
        args: Tuple[Any, ...],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        """
        Get kwargs for collections (e.g., lists or list-like tuples) of the
        same type.
        """
        if isinstance(default, Collection):
            # Call get_kwargs() to get proper default value formatting
            default = [self.get_kwargs(args[0], d)["default"] for d in default]
        else:
            default = None

        kwargs = self.type_handler.handle_collection(self, args, default, is_optional)
        return kwargs

    def _handle_mapping(
        self,
        type: type,
        args: Tuple[Any, ...],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        """
        Get kwargs for mapping types (e.g, dicts).
        """
        kwargs = self.type_handler.handle_mapping(self, args, default, is_optional)
        return kwargs


def get_default(
    option_info: types.OptionInfo,
    settings: types.MergedSettings,
    converter: converters.Converter,
) -> Any:
    """
    Return the proper default value for an attribute.

    If possible, the default is taken from loaded settings.  Else, use the
    field's default value.

    Args:
        option_info: The option description for the attribute.
        settings: A (nested) dict with the loaded settings.
        converter: The converter to be used.

    Return:
        The default value to be used for the option.  This can also be ``None``
        or a "nothing" value (e.g., :data:`attrs.NOTHING`).
    """
    if option_info.path in settings:
        # Use loaded settings value
        default = settings[option_info.path].value

        # and convert the input value to the proper type.
        # See: https://gitlab.com/sscherfke/typed-settings/-/issues/11
        if option_info.cls:
            try:
                default = converter.structure(default, option_info.cls)
            except Exception as e:
                raise ValueError(
                    f"Invalid default for type {option_info.cls}: {default}"
                ) from e

    elif option_info.default_is_factory:
        # Use a fake factory function to indicate a dynamic default value, that is only
        # computed when the CLI is invoked (and not when the options are generated).
        def default() -> object:
            return None

        default.__name__ = DEFAULT_SENTINEL_NAME
    elif option_info.has_no_default:
        default = NO_DEFAULT
    else:
        default = option_info.default

    return default


def check_if_optional(
    otype: Optional[type],
    default: Default,
    origin: Any,
    args: Tuple[Any, ...],
) -> Tuple[Optional[type], Any, Any, Tuple[Any, ...], bool]:
    """
    Check if *otype* is an optional (``Optional[...]`` or ``Union[None, ...]``) and
    return the actual type for it and a flag indicating the optionality.

    If it is optional and a default value is not set, use ``None`` as new default.

    Args:
        otype: The Python type of the option.
        default: The option's default value.
        origin: The generic origin as returned by :func:`typing.get_origin()`.
        args: The generic args as returned by :func:`typing.get_args()`.

    Return:
        A tuple *(otype, default, origin, args, is_optional)*:

        *otype:*
            is either the original or the unwrapped optional type.
        *default:*
            is the possibly updated default value.
        *origin:*
            is the possibly updated *origin* for the unwrapped *otype*.
        *args:*
            are the possibly updated *args* for the unwrapped *otype*.
        *is_optional:*
            indicates whether *otype* was an optional or not.
    """
    is_optional = origin in (Union, UnionType) and len(args) == 2 and NoneType in args
    if is_optional:
        if default is NO_DEFAULT:
            default = None

        # "idx" is the index of the not-NoneType:
        idx = (args.index(NoneType) + 1) % 2
        otype = args[idx]
        origin = get_origin(otype)
        args = get_args(otype)

    return otype, default, origin, args, is_optional
