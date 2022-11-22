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

from ._compat import PY_310


if PY_310:
    from types import UnionType
else:
    from typing import Union as UnionType  # type: ignore

from typing import Any, Collection, Dict, List, Optional, Tuple, Union

import attrs
import cattrs
from attr._make import _Nothing as NothingType

from ._compat import Protocol, get_args, get_origin
from ._dict_utils import _get_path
from .converters import BaseConverter
from .types import SettingsDict


__all__ = [
    "TypeHandlerFunc",
    "TypeHandler",
    "TypeArgsMaker",
    "get_default",
    "check_if_optional",
]


NoneType = type(None)
StrDict = Dict[str, Any]
Default = Union[Any, None, NothingType]


class TypeHandlerFunc(Protocol):
    """
    **Protocol:** A function that returns keyword arguments for a CLI option
    for a specific type.
    """

    def __call__(
        self, type: type, default: Default, is_optional: bool
    ) -> StrDict:
        """
        Return keyword arguments for creating an option for *type*.

        Args:
            type: The type to create the option for.
            default: The default value for the option.  May be ``None`` or
                :data:`attrs.NOTHING`.
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
                if default not in (None, attrs.NOTHING):
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
                :data:`attrs.NOTHING`.
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
        args: Tuple[Any, ...],
        default: Optional[Tuple],
        is_optional: bool,
    ) -> StrDict:
        """
        Handle options for structured tuples (i.e., not list-like tuples).

        Args:
            type_args_maker: The :class:`TypeArgsMaker` that called this
                function.
            args: The types of all tuple items.
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
        args: Tuple[Any, ...],
        default: Optional[List[Any]],
        is_optional: bool,
    ) -> StrDict:
        """
        Handle collections, add options to allow multiple values and to
        collect them in a list/collection.

        Args:
            type_args_maker: The :class:`TypeArgsMaker` that called this
                function.
            args: The types of the list items.
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
        args: Tuple[Any, ...],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        """
        Handle dictionaries.

        Args:
            type_args_maker: The :class:`TypeArgsMaker` that called this
                function.
            args: The types of keys and values.
            default: Either a mapping of default values, ``None`` or
                :data:`attrs.NOTHING`.
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
    for CLI options from an Attrs field's type.

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
                untyped attrs class.
            default: The default value for the option.  It can be anything,
                but the values ``None`` (possible default for optional types)
                and :data:`attrs.NOTHING` (no default set) should be handled
                explicitly.

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
                return self._handle_collection(
                    otype, args, default, is_optional
                )
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

        if isinstance(default, tuple):
            if not len(default) == len(args):
                raise TypeError(
                    f"Default value must be of len {len(args)}: {len(default)}"
                )
            default = tuple(
                self.get_kwargs(a, d)["default"] for a, d in zip(args, default)
            )
        else:
            default = None

        kwargs = self.type_handler.handle_tuple(
            self, args, default, is_optional
        )
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

        kwargs = self.type_handler.handle_collection(
            self, args, default, is_optional
        )
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
        kwargs = self.type_handler.handle_mapping(
            self, args, default, is_optional
        )
        return kwargs


def get_default(
    field: attrs.Attribute,
    path: str,
    settings: SettingsDict,
    converter: BaseConverter,
) -> Default:
    """
    Return the proper default value for an attribute.

    If possible, the default is taken from loaded settings.  Else, use the
    field's default value.

    Args:
        field: The attrs field description for the attribute.
        path: The dotted path the the option in the settings dict.
        settings: A (nested) dict with the loaded settings.
        converter: The cattrs converter to be used.

    Return:
        The default value to be used for the option.  This can also be ``None``
        or :data:`attrs.NOTHING`.
    """
    try:
        # Use loaded settings value
        default = _get_path(settings, path)
    except KeyError:
        # Use field's default
        default = field.default
    else:
        # If the default was found (no KeyError), convert the input value to
        # the proper type.
        # See: https://gitlab.com/sscherfke/typed-settings/-/issues/11
        if field.type:
            try:
                default = converter.structure(default, field.type)
            except cattrs.BaseValidationError as e:
                raise ValueError(
                    f"Invalid default for type {field.type}: {default}"
                ) from e

    if isinstance(default, attrs.Factory):  # type: ignore
        if default.takes_self:
            # There is no instance yet.  Passing ``None`` migh be more correct
            # than passing a fake instance, because it raises an error instead
            # of silently creating a false value. :-?
            default = default.factory(None)
        else:
            default = default.factory()

    return default


def check_if_optional(
    otype: Optional[type],
    default: Default,
    origin: Any,
    args: Tuple[Any, ...],
) -> Tuple[Optional[type], Any, Any, Tuple[Any, ...], bool]:
    """
    Check if *otype* is optional and return the actual type for it and a flag
    indicating the optionality.

    If it is optional and the default value is :data:`attrs.NOTHING`, use
    ``None`` as new default.

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
    is_optional = (
        origin in (Union, UnionType) and len(args) == 2 and NoneType in args
    )
    if is_optional:
        if default is attrs.NOTHING:
            default = None

        # "idx" is the index of the not-NoneType:
        idx = (args.index(NoneType) + 1) % 2
        otype = args[idx]
        origin = get_origin(otype)
        args = get_args(otype)

    return otype, default, origin, args, is_optional
