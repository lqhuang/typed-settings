"""
Utilities for generating Click options
"""
from collections.abc import MutableSequence, MutableSet, Sequence
from datetime import datetime
from enum import Enum
from functools import update_wrapper
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import attr
import cattr
import click

from ._compat import get_args, get_origin
from ._core import T, _load_settings, default_loaders
from ._dict_utils import _deep_options, _get_path, _merge_dicts, _set_path
from .attrs import METADATA_KEY, _SecretRepr
from .converters import default_converter, from_dict
from .loaders import Loader


AnyFunc = Callable[..., Any]
Decorator = Callable[[AnyFunc], AnyFunc]
StrDict = Dict[str, Any]


def click_options(
    cls: Type[T],
    loaders: Union[str, List[Loader]],
    converter: Optional[cattr.Converter] = None,
    type_handler: "Optional[TypeHandler]" = None,
) -> Callable[[Callable], Callable]:
    """
    Generate :mod:`click` options for a CLI which override settins loaded via
    :func:`.load_settings()`.

    A single *cls* instance is passed to the decorated function

    Args:
        cls: Attrs class with options (and default values).
        loaders: Either a string with your app name or a list of settings
            :class:`Loader`'s.  If it is a string, use it with
            :func:`~typed_settings.default_loaders()` to get the defalt
            loaders.
        converter: An optional :class:`cattr.Converter` used for converting
            option values to the required type.

            By default, :data:`typed_settings.attrs.converter` is used.
        type_handler: Helps creating proper click options for option types that
            are not natively supported by click.

    Return:
        A decorator for a click command.

    Example:

      .. code-block:: python

         >>> import click
         >>> import typed_settings as ts
         >>>
         >>> @ts.settings
         ... class Settings: ...
         ...
         >>> @click.command()
         ... @ts.click_options(Settings, "example")
         ... def cli(settings):
         ...     print(settings)

    .. versionchanged:: 1.0.0
       Instead of a list of loaders, you can also just pass an application
       name.
    """
    cls = attr.resolve_types(cls)
    options = _deep_options(cls)

    if isinstance(loaders, str):
        loaders = default_loaders(loaders)

    settings_dict = _load_settings(cls, options, loaders)

    converter = converter or default_converter()
    type_handler = type_handler or TypeHandler()

    def pass_settings(f: AnyFunc) -> Decorator:
        """
        Creates a *cls* instances from the settings dict stored in
        :attr:`click.Context.obj` and passes it to the decorated function *f*.
        """

        def new_func(*args, **kwargs):
            ctx = click.get_current_context()
            _merge_dicts(settings_dict, ctx.obj.get("settings"))
            ctx.obj["settings"] = from_dict(settings_dict, cls, converter)
            return f(ctx.obj["settings"], *args, **kwargs)

        return update_wrapper(new_func, f)

    def wrap(f):
        """
        The wrapper that actually decorates a function with all options.
        """
        for oinfo in reversed(options):
            default = _get_default(
                oinfo.field, oinfo.path, settings_dict, converter
            )
            option = _mk_option(
                click.option, oinfo.path, oinfo.field, default, type_handler
            )
            f = option(f)
        f = pass_settings(f)
        return f

    return wrap


def pass_settings(f: AnyFunc) -> AnyFunc:
    """
    Marks a callback as wanting to receive the innermost settings instance as
    first argument.
    """

    def new_func(*args, **kwargs):
        ctx = click.get_current_context()
        node = ctx
        settings = None
        while node is not None:
            if isinstance(node.obj, dict) and "settings" in node.obj:
                settings = node.obj["settings"]
                break
            node = node.parent
        return ctx.invoke(f, settings, *args, **kwargs)

    return update_wrapper(new_func, f)


def handle_datetime(type: type, default: Any) -> StrDict:
    """
    Use :class:`click.DateTime` as option type and convert the default value
    to an ISO string.
    """
    type_info = {
        "type": click.DateTime(
            ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"]
        ),
    }
    if default is not attr.NOTHING:
        type_info["default"] = default.isoformat()
    return type_info


def handle_enum(type: Type[Enum], default: Any) -> StrDict:
    """
    Use :class:`EnumChoice` as option type and use the enum value's name as
    default.
    """
    type_info = {"type": click.Choice(list(type.__members__))}
    if default is not attr.NOTHING:
        # Convert Enum instance to string
        type_info["default"] = default.name

    return type_info


#: Default handlers for click option types.
DEFAULT_TYPES = {
    datetime: handle_datetime,
    Enum: handle_enum,
}


class TypeHandler:
    """
    This class derives type information for Click options from an Attrs field's
    type.

    The class differentitates between specific and generic types (e.g.,
    :samp:`int` vs. :samp:`List[{T}]`.

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
                if default is not attr.NOTHING:
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

    def __init__(self, types=None):
        self.types = types or DEFAULT_TYPES
        self.list_types = (
            list,
            Sequence,
            MutableSequence,
            set,
            frozenset,
            MutableSet,
        )
        self.tuple_types = frozenset({tuple})

    def get_type(self, otype: type, default: Any) -> StrDict:
        """
        Analyses the option type and returns updated options.
        """
        origin = get_origin(otype)
        args = get_args(otype)

        if origin is None:
            for target_type, get_type_info in self.types.items():
                if issubclass(otype, target_type):
                    return get_type_info(otype, default)

            return self._handle_basic_types(otype, default)

        else:
            if origin in self.list_types:
                return self._handle_list(otype, default, args)
            elif origin in self.tuple_types:
                return self._handle_tuple(otype, default, args)

            raise TypeError(f"Cannot create click type for: {otype}")

    def _handle_basic_types(self, type: type, default: Any):
        if default is attr.NOTHING:
            type_info = {"type": type}
        else:
            type_info = {"type": type, "default": default}
        return type_info

    def _handle_list(
        self, type: type, default: Any, args: Tuple[Any, ...]
    ) -> StrDict:
        # lists and list-like tuple
        type_info = self.get_type(args[0], attr.NOTHING)
        if default is not attr.NOTHING:
            default = [self.get_type(args[0], d)["default"] for d in default]
            type_info["default"] = default
        type_info["multiple"] = True
        return type_info

    def _handle_tuple(
        self, type: type, default: Any, args: Tuple[Any, ...]
    ) -> StrDict:
        if len(args) == 2 and args[1] == ...:
            return self._handle_list(type, default, args)
        else:
            # "struct" variant of tuple
            if default is attr.NOTHING:
                default = [attr.NOTHING] * len(args)
            dicts = [self.get_type(a, d) for a, d in zip(args, default)]
            type_info = {
                "type": tuple(d["type"] for d in dicts),
                "nargs": len(dicts),
            }
            if all("default" in d for d in dicts):
                type_info["default"] = tuple(d["default"] for d in dicts)
            return type_info


def _get_default(
    field: attr.Attribute,
    path: str,
    settings: StrDict,
    converter: cattr.Converter,
) -> Any:
    """
    Returns the proper default value for an attribute.

    If possible, the default is taken from loaded settings.  Else, use the
    field's default value.
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
            default = converter.structure(default, field.type)

    if isinstance(default, attr.Factory):  # type: ignore
        if default.takes_self:
            # There is no instance yet.  Passing ``None`` migh be more correct
            # than passing a fake instance, because it raises an error instead
            # of silently creating a false value. :-?
            default = default.factory(None)
        else:
            default = default.factory()

    return default


def _mk_option(
    option: Callable[..., Decorator],
    path: str,
    field: attr.Attribute,
    default: Any,
    type_handler: TypeHandler,
) -> Decorator:
    """
    Recursively creates click options and returns them as a list.
    """
    opt_name = path.replace(".", "-").replace("_", "-")
    param_decl = f"--{opt_name}"

    def cb(ctx, _param, value):
        if ctx.obj is None:
            ctx.obj = {}
        settings = ctx.obj.setdefault("settings", {})
        _set_path(settings, path, value)
        return value

    metadata = field.metadata.get(METADATA_KEY, {})
    kwargs = {
        "show_default": True,
        "callback": cb,
        "expose_value": False,
        "help": metadata.get("help", ""),
    }

    if isinstance(field.repr, _SecretRepr):
        kwargs["show_default"] = False
        if default is not attr.NOTHING:  # pragma: no cover
            kwargs["help"] = f"{kwargs['help']}  [default: {field.repr('')}]"

    if default is attr.NOTHING:
        kwargs["required"] = True

    if field.type:  # pragma: no cover
        if field.type is bool:
            param_decl = f"{param_decl}/--no-{opt_name}"
        kwargs.update(type_handler.get_type(field.type, default))

    return option(param_decl, **kwargs)
