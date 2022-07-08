"""
Utilities for generating Click options
"""
import itertools
import typing as t
from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)
from datetime import datetime
from enum import Enum
from functools import update_wrapper

import attrs
import cattrs
import click

from ._compat import get_args, get_origin
from ._core import T, _load_settings, default_loaders
from ._dict_utils import _deep_options, _get_path, _merge_dicts, _set_path
from .attrs import CLICK_KEY, METADATA_KEY, _SecretRepr
from .converters import default_converter, from_dict
from .loaders import Loader
from .types import OptionInfo, SettingsDict


try:
    from typing import Protocol
except ImportError:
    # Python 3.7
    from typing import _Protocol as Protocol  # type: ignore


CTX_KEY = "settings"


Callback = t.Callable[[click.Context, click.Option, t.Any], t.Any]
AnyFunc = t.Callable[..., t.Any]
Decorator = t.Callable[[AnyFunc], AnyFunc]
StrDict = t.Dict[str, t.Any]
TypeHandlerFunc = t.Callable[[type, t.Any], StrDict]


def click_options(
    cls: t.Type[T],
    loaders: t.Union[str, t.Sequence[Loader]],
    converter: t.Optional[cattrs.Converter] = None,
    type_handler: "t.Optional[TypeHandler]" = None,
    argname: t.Optional[str] = None,
    decorator_factory: "t.Optional[DecoratorFactory]" = None,
) -> t.Callable[[t.Callable], t.Callable]:
    """
    Generate :mod:`click` options for a CLI which override settins loaded via
    :func:`.load_settings()`.

    A single *cls* instance is passed to the decorated function -- by default
    as positional argument.

    Args:
        cls: Attrs class with options (and default values).

        loaders: Either a string with your app name or a list of settings
            :class:`Loader`'s.  If it is a string, use it with
            :func:`~typed_settings.default_loaders()` to get the defalt
            loaders.

        converter: An optional :class:`cattrs.Converter` used for converting
            option values to the required type.

            By default, :data:`typed_settings.attrs.converter` is used.

        type_handler: Helps creating proper click options for option types that
            are not natively supported by click.

        argname: An optional argument name.  If it is set, the settings
            instances is no longer passed as positional argument but as key
            word argument.

            This allows a function to be decorated with this function multiple
            times.

        decorator_factory: A class that generates Click decorators for options
            and settings classes.  This allows you to, e.g., use
            `option groups`_ via :class:`OptionGroupFactory`.  The default
            generates normal Click options via :class:`ClickOptionFactory`.

            .. _option groups: https://click-option-group.readthedocs.io

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
    .. versionchanged:: 1.1.0
       Add the *argname* parameter.
    .. versionchanged:: 1.1.0
       Add the *decorator_factory* parameter.
    """
    cls = attrs.resolve_types(cls)
    options = _deep_options(cls)
    grouped_options = [
        (g_cls, list(g_opts))
        for g_cls, g_opts in itertools.groupby(options, key=lambda o: o.cls)
    ]

    if isinstance(loaders, str):
        loaders = default_loaders(loaders)

    settings_dict = _load_settings(cls, options, loaders)

    converter = converter or default_converter()
    type_handler = type_handler or TypeHandler()
    decorator_factory = decorator_factory or ClickOptionFactory()

    wrapper = _get_wrapper(
        cls,
        settings_dict,
        options,
        grouped_options,
        converter,
        type_handler,
        argname,
        decorator_factory,
    )
    return wrapper


def _get_wrapper(
    cls: t.Type[T],
    settings_dict: SettingsDict,
    options: t.List[OptionInfo],
    grouped_options: t.List[t.Tuple[type, t.List[OptionInfo]]],
    converter: cattrs.Converter,
    type_handler: "TypeHandler",
    argname: t.Optional[str],
    decorator_factory: "DecoratorFactory",
) -> t.Callable[[t.Callable], t.Callable]:
    def pass_settings(f: AnyFunc) -> Decorator:
        """
        Creates a *cls* instances from the settings dict stored in
        :attr:`click.Context.obj` and passes it to the decorated function *f*.
        """

        def new_func(*args: t.Any, **kwargs: t.Any) -> t.Any:
            ctx = click.get_current_context()
            if ctx.obj is None:
                ctx.obj = {}
            _merge_dicts(options, settings_dict, ctx.obj.get(CTX_KEY, {}))
            settings = from_dict(settings_dict, cls, converter)
            if argname:
                ctx_key = argname
                kwargs = {argname: settings, **kwargs}
            else:
                ctx_key = CTX_KEY
                args = (settings,) + args
            ctx.obj[ctx_key] = settings
            return f(*args, **kwargs)

        return update_wrapper(new_func, f)

    def wrap(f: AnyFunc) -> AnyFunc:
        """
        The wrapper that actually decorates a function with all options.
        """
        option_decorator = decorator_factory.get_option_decorator()
        for g_cls, g_opts in reversed(grouped_options):
            for oinfo in reversed(g_opts):
                default = _get_default(
                    oinfo.field, oinfo.path, settings_dict, converter
                )
                option = _mk_option(
                    option_decorator,
                    oinfo.path,
                    oinfo.field,
                    default,
                    type_handler,
                )
                f = option(f)
            f = decorator_factory.get_group_decorator(g_cls)(f)

        f = pass_settings(f)
        return f

    return wrap


def pass_settings(
    f: t.Optional[AnyFunc] = None, *, argname: t.Optional[str] = None
) -> AnyFunc:
    """
    Marks a callback as wanting to receive the innermost settings instance as
    first argument.

    If you specifiy an *argname* in :func:`click_options()`, you must specify
    the same name here in order to get the correct settings instance.  The
    settings instance is then passed as keyword argument.

    Args:
        argname: An optional argument name.  If it is set, the settings
            instances is no longer passed as positional argument but as key
            word argument.

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
         >>> @click.group()
         ... @click_options(Settings, "example", argname="my_settings")
         ... def cli(my_settings):
         ...     pass
         ...
         >>> @cli.command()
         ... # Use the same "argname" as above!
         ... @pass_settings(argname="my_settings")
         ... def sub_cmd(*, my_settings):
         ...     print(my_settings)

    .. versionchanged:: 1.1.0
       Add the *argname* parameter.
    """
    ctx_key = argname or CTX_KEY

    def decorator(f: AnyFunc) -> AnyFunc:
        def new_func(*args: t.Any, **kwargs: t.Any) -> t.Any:
            ctx = click.get_current_context()
            node: t.Optional[click.Context] = ctx
            settings = None
            while node is not None:
                if isinstance(node.obj, dict) and ctx_key in node.obj:
                    settings = node.obj[ctx_key]
                    break
                node = node.parent

            if argname:
                kwargs = {argname: settings, **kwargs}
            else:
                args = (settings,) + args

            return ctx.invoke(f, *args, **kwargs)

        return update_wrapper(new_func, f)

    if f is None:
        return decorator

    return decorator(f)


class DecoratorFactory(Protocol):
    """
    **Protocol:** Methods that a Click decorator factory must implement.

    The decorators returned by the procol methods are used to construct the
    Click options and possibly option groups.

    .. versionadded:: 1.1.0
    """

    def get_option_decorator(self) -> t.Callable[..., Decorator]:
        """
        Return the decorator that is used for creating Click options.

        It must be compatible with :func:`click.option()`.
        """
        ...

    def get_group_decorator(self, settings_cls: type) -> Decorator:
        """
        Return a decorator for the current settings class.

        This can, e.g., be used to group option by settings class.
        """
        ...


class ClickOptionFactory:
    """
    Factory for default Click decorators.
    """

    def get_option_decorator(self) -> t.Callable[..., Decorator]:
        """
        Return :func:`click.option()`.
        """
        return click.option

    def get_group_decorator(self, settings_cls: type) -> Decorator:
        """
        Return a no-op decorator that leaves the decorated function unchanged.
        """
        return lambda f: f


class OptionGroupFactory:
    """
    Factory got generating Click option groups via
    https://click-option-group.readthedocs.io.
    """

    def __init__(self) -> None:
        try:
            from click_option_group import optgroup
        except ImportError as e:
            raise ModuleNotFoundError(
                "Module 'click_option_group' not installed.  "
                "Please run 'python -m pip install click-option-group'"
            ) from e
        self.optgroup = optgroup

    def get_option_decorator(self) -> t.Callable[..., Decorator]:
        """
        Return :func:`click_option_group.optgroup.option()`.
        """
        return self.optgroup.option

    def get_group_decorator(self, settings_cls: type) -> Decorator:
        """
        Return a :func:`click_option_group.optgroup.group()` instantiated with
        the first line of *settings_cls*'s docstring.
        """
        try:
            name = settings_cls.__doc__.strip().splitlines()[0]  # type: ignore
        except (AttributeError, IndexError):
            name = f"{settings_cls.__name__} options"
        return self.optgroup.group(name)


def handle_datetime(type: type, default: t.Any) -> StrDict:
    """
    Use :class:`click.DateTime` as option type and convert the default value
    to an ISO string.
    """
    type_info = {
        "type": click.DateTime(
            ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"]
        ),
    }
    if default is not attrs.NOTHING:
        type_info["default"] = default.isoformat()
    return type_info


def handle_enum(type: t.Type[Enum], default: t.Any) -> StrDict:
    """
    Use :class:`EnumChoice` as option type and use the enum value's name as
    default.
    """
    type_info = {"type": click.Choice(list(type.__members__))}
    if default is not attrs.NOTHING:
        # Convert Enum instance to string
        type_info["default"] = default.name

    return type_info


#: Default handlers for click option types.
DEFAULT_TYPES: t.Dict[type, TypeHandlerFunc] = {
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

            def handle_mytype(type: type, default: Any) -> t.Dict[str, Any]:
                type_info = {
                    "type": ClickType(...)
                }
                if default is not attrs.NOTHING:
                    type_info["default"] = default.stringify()
                return type_info

        You can use :func:`handle_datetime` and :func:`handle_enum` as
        a sample.

        t.Types without a handler get no special treatment and cause options to
        look like this: :samp:`click.option(..., type=field_type,
        default=field_default)`.

    Generic types:
        Handlers for generic types cannot be changed.  They either create an
        option with :samp:`multiple=True` or :samp:`nargs={x}`.  Nested types
        are recursively resolved.

        t.Types that cause :samp:`multiple=True`:

        - :class:`typing.List`
        - :class:`typing.Sequence`
        - :class:`typing.MutableSequence`
        - :class:`typing.Set`
        - :class:`typing.FrozenSet`
        - :class:`typing.MutableSet`

        t.Types that cause :samp:`nargs={x}`:

        - :class:`typing.Tuple`
        - :class:`typing.NamedTuple`

        Dicts are not (yet) supported.
    """

    def __init__(
        self,
        types: t.Optional[t.Dict[type, TypeHandlerFunc]] = None,
    ) -> None:
        self.types = types or DEFAULT_TYPES
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

    def get_type(self, otype: t.Optional[type], default: t.Any) -> StrDict:
        """
        Analyses the option type and returns updated options.
        """
        origin = get_origin(otype)
        args = get_args(otype)

        if otype is None:
            return self._handle_basic_types(otype, default)

        elif origin is None:
            for target_type, get_type_info in self.types.items():
                if issubclass(otype, target_type):
                    return get_type_info(otype, default)

            return self._handle_basic_types(otype, default)

        else:
            if origin in self.list_types:
                return self._handle_list(otype, default, args)
            elif origin in self.tuple_types:
                return self._handle_tuple(otype, default, args)
            elif origin in self.mapping_types:
                return self._handle_dict(otype, default, args)

            raise TypeError(f"Cannot create click type for: {otype}")

    def _handle_basic_types(
        self, type: t.Optional[type], default: t.Any
    ) -> StrDict:
        if default is attrs.NOTHING:
            type_info = {"type": type}
        else:
            type_info = {"type": type, "default": default}
        return type_info

    def _handle_list(
        self, type: type, default: t.Any, args: t.Tuple[t.Any, ...]
    ) -> StrDict:
        # lists and list-like tuple
        type_info = self.get_type(args[0], attrs.NOTHING)
        if default is not attrs.NOTHING:
            default = [self.get_type(args[0], d)["default"] for d in default]
            type_info["default"] = default
        type_info["multiple"] = True
        return type_info

    def _handle_tuple(
        self, type: type, default: t.Any, args: t.Tuple[t.Any, ...]
    ) -> StrDict:
        if len(args) == 2 and args[1] == ...:
            return self._handle_list(type, default, args)
        else:
            # "struct" variant of tuple
            if default is attrs.NOTHING:
                default = [attrs.NOTHING] * len(args)
            dicts = [self.get_type(a, d) for a, d in zip(args, default)]
            type_info = {
                "type": tuple(d["type"] for d in dicts),
                "nargs": len(dicts),
            }
            if all("default" in d for d in dicts):
                type_info["default"] = tuple(d["default"] for d in dicts)
            return type_info

    def _handle_dict(
        self, type: type, default: t.Any, args: t.Tuple[t.Any, ...]
    ) -> StrDict:
        def cb(
            ctx: click.Context,
            param: click.Option,
            value: t.Optional[t.Iterable[str]],
        ) -> t.Dict[str, str]:
            if not value:
                return {}
            splitted = [v.partition("=") for v in value]
            items = {k: v for k, _, v in splitted}
            return items

        type_info = {
            "metavar": "KEY=VALUE",
            "multiple": True,
            "callback": cb,
        }
        if default is not attrs.NOTHING:
            default = [f"{k}={v}" for k, v in default.items()]
            type_info["default"] = default
        return type_info


def _get_default(
    field: attrs.Attribute,
    path: str,
    settings: SettingsDict,
    converter: cattrs.Converter,
) -> t.Any:
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

    if isinstance(default, attrs.Factory):  # type: ignore
        if default.takes_self:
            # There is no instance yet.  Passing ``None`` migh be more correct
            # than passing a fake instance, because it raises an error instead
            # of silently creating a false value. :-?
            default = default.factory(None)
        else:
            default = default.factory()

    return default


def _mk_option(
    option: t.Callable[..., Decorator],
    path: str,
    field: attrs.Attribute,
    default: t.Any,
    type_handler: TypeHandler,
) -> Decorator:
    """
    Recursively creates click options and returns them as a list.
    """
    user_config = field.metadata.get(METADATA_KEY, {}).get(CLICK_KEY, {})

    param_decls: t.Tuple[str, ...]
    user_param_decls: t.Union[str, t.Sequence[str]]
    user_param_decls = user_config.pop("param_decls", ())
    if not user_param_decls:
        option_name = path.replace(".", "-").replace("_", "-")
        if field.type and field.type is bool:
            param_decls = (f"--{option_name}/--no-{option_name}",)
        else:
            param_decls = (f"--{option_name}",)
    elif isinstance(user_param_decls, str):
        param_decls = (user_param_decls,)
    else:
        param_decls = tuple(user_param_decls)

    # The option type specifies the default option kwargs
    kwargs = type_handler.get_type(field.type, default)

    # The type's kwargs should not be able to set these values since they are
    # needed for everything to work:
    kwargs["show_default"] = True
    kwargs["expose_value"] = False
    kwargs["callback"] = _make_callback(path, kwargs.get("callback"))

    # Get "help" from the user_config *now*, because we may need to update it
    # below.  Also replace "None" with "".
    kwargs["help"] = user_config.pop("help", None) or ""

    if isinstance(field.repr, _SecretRepr):
        kwargs["show_default"] = False
        if default is not attrs.NOTHING:  # pragma: no cover
            kwargs["help"] = f"{kwargs['help']}  [default: {field.repr('')}]"

    if default is attrs.NOTHING:
        kwargs["required"] = True

    # The user has the last word, though.
    kwargs.update(user_config)

    return option(*param_decls, **kwargs)


def _make_callback(path: str, type_callback: t.Optional[Callback]) -> Callback:
    """
    Generate a callback that adds option values to the settings instance in the
    context.  It also calls a type's callback if there should be one.
    """

    def cb(ctx: click.Context, param: click.Option, value: t.Any) -> t.Any:
        if type_callback is not None:
            value = type_callback(ctx, param, value)

        if ctx.obj is None:
            ctx.obj = {}
        settings = ctx.obj.setdefault(CTX_KEY, {})
        _set_path(settings, path, value)
        return value

    return cb
