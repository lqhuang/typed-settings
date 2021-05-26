"""
Utilities for generating Click options
"""
from collections.abc import MutableSequence, MutableSet, Sequence
from datetime import datetime
from enum import Enum
from functools import update_wrapper
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, Union

import attr
import click

from ._core import AUTO, T, _Auto, _load_settings
from ._dict_utils import _deep_fields, _get_path, _merge_dicts, _set_path
from .attrs import METADATA_KEY, _SecretRepr
from .attrs._compat import get_args, get_origin


AnyFunc = Callable[..., Any]
Decorator = Callable[[AnyFunc], AnyFunc]
StrDict = Dict[str, Any]


def click_options(
    cls: Type[T],
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    config_file_section: Union[_Auto, str] = AUTO,
    config_files_var: Union[None, _Auto, str] = AUTO,
    env_prefix: Union[None, _Auto, str] = AUTO,
    type_handler: "Optional[TypeHandler]" = None,
) -> Callable[[Callable], Callable]:
    """
    Generates :mod:`click` options for a CLI which override settins loaded via
    :func:`.load_settings()`.

    A single *cls* instance is passed to the decorated function

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

    See :func:`.load_settings()` for argument descriptions.
    """
    cls = attr.resolve_types(cls)
    fields = _deep_fields(cls)
    settings = _load_settings(
        fields=fields,
        appname=appname,
        config_files=config_files,
        config_file_section=config_file_section,
        config_files_var=config_files_var,
        env_prefix=env_prefix,
    )
    type_handler = type_handler or TypeHandler()

    def pass_settings(f: AnyFunc) -> Decorator:
        """
        Creates a *cls* instances from the settings dict stored in
        :attr:`click.Context.obj` and passes it to the decorated function *f*.
        """

        def new_func(*args, **kwargs):
            ctx = click.get_current_context()
            _merge_dicts(settings, ctx.obj.get("settings"))
            ctx.obj["settings"] = cls(**settings)
            return f(ctx.obj["settings"], *args, **kwargs)

        return update_wrapper(new_func, f)

    def wrap(f):
        """
        The wrapper that actually decorates a function with all options.
        """
        for path, field, _cls in reversed(fields):
            default = _get_default(field, path, settings)
            option = _mk_option(
                click.option, path, field, default, type_handler
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


class EnumChoice(click.Choice):
    """*Click* parameter type for representing enums."""

    def __init__(self, enum_type: Type[Enum]):
        self.__enum = enum_type
        super().__init__(list(enum_type.__members__))

    # def __call__(
    #     self,
    #     value,
    #     param,
    #     ctx,
    # ):
    #     breakpoint()
    #     return value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__enum})"

    def convert(
        self,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Enum:
        return self.__enum[super().convert(value, param, ctx)]


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


def _get_default(field: attr.Attribute, path: str, settings: StrDict) -> Any:
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
