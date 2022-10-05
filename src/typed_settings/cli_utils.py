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
from typing import Any, Collection, Dict, List, Optional, Tuple, Union

import attrs

from ._compat import Protocol, get_args, get_origin


NoneType = type(None)
StrDict = Dict[str, Any]
# TypeHandlerFunc = Callable[[type, Any, bool], StrDict]


class TypeHandlerFunc(Protocol):
    def __call__(self, type: type, default: Any, is_optional: bool) -> StrDict:
        ...


class TypeHandler(Protocol):
    def get_scalar_handlers(self) -> Dict[type, TypeHandlerFunc]:
        ...

    def handle_scalar(
        self, type: Optional[type], default: Any, is_optional: bool
    ) -> StrDict:
        ...

    def handle_collection(
        self,
        # kwargs: StrDict,
        type_args_maker: "TypeArgsMaker",
        args,
        default: Optional[Collection[Any]],
        is_optional: bool,
    ) -> StrDict:
        """
        Handle collections, add options to allow multiple values and to
        collect them in a list/collection.

        Args:
            kwargs: Kwargs with type info
        """
        ...

    def handle_tuple(
        self,
        args: Tuple[Any, ...],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        ...

    def handle_mapping(
        self,
        type_args_maker: "TypeArgsMaker",
        args: Tuple[Any, ...],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        ...


class TypeArgsMaker:
    """
    This class derives type information for Click options from an Attrs field's
    type.

    The class differentitates between specific and generic types (e.g.,
    :samp:`int` vs. :samp:`list[{T}]`.

    Specific types:
        Handlers for specific types can be extended and modified by passing
        a *types* dict to the class.  By default, :data:`DEFAULT_TYPES` is
        used.

        This dict maps Python types to a handler function.  Handler functions
        take the field type and default value and return a dict that is passed
        as keyword arguments to :func:`click.option()`.  This dict should
        contain a ``type`` key and, optionally, an updated ``default``.

        .. code-block:: python

            def handle_mytype(type: type, default: Any) -> Dict[str, Any]:
                type_info = {
                    "type": ClickType(...)
                }
                if default is not attrs.NOTHING:
                    type_info["default"] = default.stringify()
                return type_info

        You can use :func:`handle_datetime` and :func:`handle_enum` as
        a sample.

        Types without a handler get no special treatment and cause options to
        look like this: :samp:`click.option(..., type=field_type,
        default=field_default)`.

    Generic types:
        Handlers for generic types cannot be changed.  They either create an
        option with :samp:`multiple=True` or :samp:`nargs={x}`.  Nested types
        are recursively resolved.

        Types that cause :samp:`multiple=True`:

        - :class:`typing.List`
        - :class:`typing.Sequence`
        - :class:`typing.MutableSequence`
        - :class:`typing.Set`
        - :class:`typing.FrozenSet`
        - :class:`typing.MutableSet`

        Types that cause :samp:`nargs={x}`:

        - :class:`typing.Tuple`
        - :class:`typing.NamedTuple`

        Dicts are not (yet) supported.
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

    def get_kwargs(self, otype: Optional[type], default: Any) -> StrDict:
        """
        Analyses the option type and returns updated options.
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

            raise TypeError(f"Cannot create click type for: {otype}")

        def get_defaults(
            self, types: Union[type, Sequence[type]], defaults: Sequence[Any]
        ) -> List[Any]:
            if isinstance(types, type):
                types = [types] * len(defaults)
            if len(types) != len(defaults):
                raise ValueError(
                    f'"types" and "defaults" must have the same length: '
                    f"{len(types)} != {len(defaults)}"
                )
            return [
                self.get_kwargs(t, d)["default"]
                for t, d in zip(types, defaults)
            ]

    def _handle_scalar(
        self,
        type: Optional[type],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        type_info = self.type_handler.handle_scalar(type, default, is_optional)
        return type_info

    def _handle_collection(
        self,
        type: type,
        args: Tuple[Any, ...],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        """
        Get kwargs for collections (e.g., lists or list-like tuples) of the
        same type.
        """
        # kwargs = self.get_kwargs(args[0], attrs.NOTHING)
        # if isinstance(default, Collection):
        #     # Call get_kwargs() to get proper default value formatting
        #     default = [self.get_kwargs(args[0], d)["default"] for d in default]
        # else:
        #     default = None
        if isinstance(default, Collection):
            default = self.get_defaults(args[0], default)
        else:
            default = None

        # Kwargs contains all type info.  Now modify it to collect multiple
        # values into a single list:
        kwargs = self.type_handler.handle_collection(
            self, args, default, is_optional
        )
        return kwargs

    def _handle_tuple(
        self,
        type: type,
        args: Tuple[Any, ...],
        default: Any,
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
            default = tuple(self.get_defaults(types, default))
        else:
            default = None

        kwargs = self.type_handler.handle_tuple(
            self, args, default, is_optional
        )
        return kwargs

    def _handle_mapping(
        self,
        type: type,
        args: Tuple[Any, ...],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        """
        Get kwargs for mapping types (e.g, dicts).
        """
        kwargs = self.type_handler.handle_mapping(
            self, args, default, is_optional
        )
        return kwargs


def check_if_optional(
    otype: Optional[type],
    default: Any,
    origin: Any,
    args: Tuple[Any, ...],
) -> Tuple[Optional[type], Any, Any, Tuple[Any, ...], bool]:
    """
    Check if *otype* is optional and return the actual type for it and a flag
    indicating the optionality.

    If it is optional and the default value is *NOTHING*, use ``None`` as new
    default.
    """
    is_optional = origin is Union and len(args) == 2 and NoneType in args
    if is_optional:
        if default is attrs.NOTHING:
            default = None

        # "idx" is the index of the not-NoneType:
        idx = (args.index(NoneType) + 1) % 2
        otype = args[idx]
        origin = get_origin(otype)
        args = get_args(otype)

    return otype, default, origin, args, is_optional
