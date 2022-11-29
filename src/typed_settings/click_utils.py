"""
Utilities for generating Click options.
"""
from datetime import datetime
from enum import Enum
from functools import update_wrapper
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

import attrs
import click
from attr._make import _Nothing as NothingType

from ._compat import PY_38
from ._core import _load_settings, default_loaders
from ._dict_utils import _deep_options, _group_options, _merge_dicts, _set_path
from .attrs import CLICK_KEY, METADATA_KEY, _SecretRepr
from .cli_utils import (
    Default,
    StrDict,
    TypeArgsMaker,
    TypeHandlerFunc,
    get_default,
)
from .converters import BaseConverter, default_converter, from_dict
from .loaders import Loader
from .types import ST, OptionInfo, Secret, SettingsClass, SettingsDict, T


if PY_38:
    from typing import Protocol
else:
    from typing import _Protocol as Protocol  # type: ignore


__all__ = [
    "click_options",
    "pass_settings",
    "DecoratorFactory",
    "ClickOptionFactory",
    "OptionGroupFactory",
    "handle_datetime",
    "handle_enum",
    "DEFAULT_TYPES",
    "ClickHandler",
]


CTX_KEY = "settings"


DefaultType = Union[None, NothingType, T]
Callback = Callable[[click.Context, click.Option, Any], Any]
AnyFunc = Callable[..., Any]
Decorator = Callable[[AnyFunc], AnyFunc]


def click_options(
    settings_cls: Type[ST],
    loaders: Union[str, Sequence[Loader]],
    converter: Optional[BaseConverter] = None,
    type_args_maker: Optional[TypeArgsMaker] = None,
    argname: Optional[str] = None,
    decorator_factory: "Optional[DecoratorFactory]" = None,
) -> Callable[[Callable], Callable]:
    """
    **Decorator:** Generate :mod:`click` options for a CLI which override
    settings loaded via :func:`.load_settings()`.

    Args:
        settings_cls: The settings class to generate options for.

        loaders: Either a string with your app name or a list of
            :class:`.Loader`\\ s.  If it's a string, use it with
            :func:`~typed_settings.default_loaders()` to get the default
            loaders.

        converter: An optional :class:`~cattrs.Converter` used for converting
            option values to the required type.

            By default, :data:`typed_settings.default_converter()` is used.

        type_args_maker: The type args maker that is used to generate keyword
            arguments for :func:`click.option()`.  By default, use
            :class:`.TypeArgsMaker` with :class:`ClickHandler`.

        argname: An optional argument name for the settings instance that is
            passed to the CLI.  If it is set, the settings instances is no
            longer passed as positional argument but as key word argument.

            This allows a CLI function to be decorated with this function
            multiple times.

        decorator_factory: A class that generates Click decorators for options
            and settings classes.  This allows you to, e.g., use
            `option groups`_ via :class:`OptionGroupFactory`.  The default
            generates normal Click options via :class:`ClickOptionFactory`.

            .. _option groups: https://click-option-group.readthedocs.io

    Return:
        A decorator for a click command.

    Raise:
        ValueError: If settings default or passed CLI options have invalid
            values.
        TypeError: If the settings class uses unsupported types.
        cattrs.StructureHandlerNotFoundError: If cattrs has no handler for a
            given type.
        cattrs.BaseValidationError: If cattrs structural validation fails.

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
           ... def cli(settings: Settings) -> None:
           ...     print(settings)

    .. versionchanged:: 1.0.0
       Instead of a list of loaders, you can also just pass an application
       name.
    .. versionchanged:: 1.1.0
       Added the *argname* parameter.
    .. versionchanged:: 1.1.0
       Added the *decorator_factory* parameter.
    .. versionchanged:: 2.0.0
       Renamed *type_handler* to *type_args_maker* and changed it's type to
       ``TypeArgsMaker``.
    """
    cls = attrs.resolve_types(settings_cls)
    options = [
        opt for opt in _deep_options(cls) if opt.field.init is not False
    ]
    grouped_options = _group_options(cls, options)

    if isinstance(loaders, str):
        loaders = default_loaders(loaders)

    settings_dict = _load_settings(cls, options, loaders)

    converter = converter or default_converter()
    type_args_maker = type_args_maker or TypeArgsMaker(ClickHandler())
    decorator_factory = decorator_factory or ClickOptionFactory()

    wrapper = _get_wrapper(
        cls,
        settings_dict,
        options,
        grouped_options,
        converter,
        type_args_maker,
        argname,
        decorator_factory,
    )
    return wrapper


def _get_wrapper(
    cls: Type[ST],
    settings_dict: SettingsDict,
    options: List[OptionInfo],
    grouped_options: List[Tuple[type, List[OptionInfo]]],
    converter: BaseConverter,
    type_args_maker: TypeArgsMaker,
    argname: Optional[str],
    decorator_factory: "DecoratorFactory",
) -> Callable[[Callable], Callable]:
    def pass_settings(f: AnyFunc) -> Decorator:
        """
        Create a *cls* instances from the settings dict stored in
        :attr:`click.Context.obj` and passes it to the decorated function *f*.
        """

        def new_func(*args: Any, **kwargs: Any) -> Any:
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
                default = get_default(
                    oinfo.field, oinfo.path, settings_dict, converter
                )
                option = _mk_option(
                    option_decorator,
                    oinfo.path,
                    oinfo.field,
                    default,
                    type_args_maker,
                )
                f = option(f)
            f = decorator_factory.get_group_decorator(g_cls)(f)

        f = pass_settings(f)
        return f

    return wrap


def pass_settings(
    f: Optional[AnyFunc] = None, *, argname: Optional[str] = None
) -> AnyFunc:
    """
    **Decorator:** Mark a callback as wanting to receive the innermost settings
    instance as first argument.

    If you specify an *argname* in :func:`click_options()`, you must specify
    the same name here in order to get the correct settings instance.  The
    settings instance is then passed as keyword argument.

    Args:
        argname: An optional argument name.  If it is set, the settings
            instance is no longer passed as positional argument but as key
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
        def new_func(*args: Any, **kwargs: Any) -> Any:
            ctx = click.get_current_context()
            node: Optional[click.Context] = ctx
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

    def get_option_decorator(self) -> Callable[..., Decorator]:
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

    def get_option_decorator(self) -> Callable[..., Decorator]:
        """
        Return :func:`click.option()`.
        """
        return click.option

    def get_group_decorator(self, settings_cls: SettingsClass) -> Decorator:
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

    def get_option_decorator(self) -> Callable[..., Decorator]:
        """
        Return :class:`click_option_group.optgroup` option.
        """
        return self.optgroup.option

    def get_group_decorator(self, settings_cls: SettingsClass) -> Decorator:
        """
        Return a :class:`click_option_group.optgroup` group instantiated with
        the first line of *settings_cls*'s docstring.
        """
        try:
            name = settings_cls.__doc__.strip().splitlines()[0]  # type: ignore
        except (AttributeError, IndexError):
            name = f"{settings_cls.__name__} options"
        return self.optgroup.group(name)


def handle_datetime(
    type: type, default: Default, is_optional: bool
) -> StrDict:
    """
    Use :class:`click.DateTime` as option type and convert the default value
    to an ISO string.
    """
    kwargs: StrDict = {
        "type": click.DateTime(
            ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"]
        ),
    }
    if isinstance(default, datetime):
        kwargs["default"] = default.isoformat()
    elif is_optional:
        kwargs["default"] = None
    return kwargs


def handle_enum(
    type: Type[Enum], default: Default, is_optional: bool
) -> StrDict:
    """
    Use :class:`click.Choice` as option type and use the enum value's name as
    default.
    """
    kwargs: StrDict = {"type": click.Choice(list(type.__members__))}
    if isinstance(default, type):
        # Convert Enum instance to string
        kwargs["default"] = default.name
    elif is_optional:
        kwargs["default"] = None

    return kwargs


#: Default handlers for click option types.
DEFAULT_TYPES: Dict[type, TypeHandlerFunc] = {
    datetime: handle_datetime,
    Enum: handle_enum,
}


class ClickHandler:
    """
    Implementation of the :class:`~typed_settings.cli_utils.TypeHandler`
    protocol for Click.

    Args:
        extra_types: A dict mapping types to specialized handler functions.
            Use :data:`DEFAULT_TYPES` by default.

    .. versionadded:: 2.0.0
    """

    def __init__(
        self, extra_types: Optional[Dict[type, TypeHandlerFunc]] = None
    ) -> None:
        self.extra_types = extra_types or DEFAULT_TYPES

    def get_scalar_handlers(self) -> Dict[type, TypeHandlerFunc]:
        return self.extra_types

    def handle_scalar(
        self,
        type: Optional[type],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        kwargs: StrDict = {"type": type}
        if default not in (None, attrs.NOTHING):
            kwargs["default"] = default
        elif is_optional:
            kwargs["default"] = None
        if type and issubclass(type, bool):
            kwargs["is_flag"] = True

        return kwargs

    def handle_tuple(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Optional[Tuple],
        is_optional: bool,
    ) -> StrDict:
        kwargs = {
            "type": types,
            "nargs": len(types),
            "default": default,
        }
        return kwargs

    def handle_collection(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Optional[Collection[Any]],
        is_optional: bool,
    ) -> StrDict:
        kwargs = type_args_maker.get_kwargs(types[0], attrs.NOTHING)
        kwargs["default"] = default
        kwargs["multiple"] = True
        return kwargs

    def handle_mapping(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Default,
        is_optional: bool,
    ) -> StrDict:
        def cb(
            ctx: click.Context,
            param: click.Option,
            value: Optional[Iterable[str]],
        ) -> Optional[Dict[str, str]]:
            if not value:
                return {}
            splitted = [v.partition("=") for v in value]
            items = {k: v for k, _, v in splitted}
            return items

        kwargs = {
            "metavar": "KEY=VALUE",
            "multiple": True,
            "callback": cb,
        }
        if not isinstance(default, Mapping):
            default = {}
        kwargs["default"] = [f"{k}={v}" for k, v in default.items()]

        return kwargs


def _mk_option(
    option_fn: Callable[..., Decorator],
    path: str,
    field: attrs.Attribute,
    default: Any,
    type_args_maker: TypeArgsMaker,
) -> Decorator:
    """
    Recursively creates click options and returns them as a list.
    """
    user_config = field.metadata.get(METADATA_KEY, {}).get(CLICK_KEY, {})

    # The option type specifies the default option kwargs
    kwargs = type_args_maker.get_kwargs(field.type, default)

    param_decls: Tuple[str, ...]
    user_param_decls: Union[str, Sequence[str]]
    user_param_decls = user_config.pop("param_decls", ())
    if not user_param_decls:
        option_name = path.replace(".", "-").replace("_", "-")
        if kwargs.get("is_flag"):
            param_decls = (f"--{option_name}/--no-{option_name}",)
        else:
            param_decls = (f"--{option_name}",)
    elif isinstance(user_param_decls, str):
        param_decls = (user_param_decls,)
    else:
        param_decls = tuple(user_param_decls)

    # The type's kwargs should not be able to set these values since they are
    # needed for everything to work:
    kwargs["show_default"] = True
    kwargs["expose_value"] = False
    kwargs["callback"] = _make_callback(
        path, kwargs.get("callback"), user_config.pop("callback", None)
    )

    # Get "help" from the user_config *now*, because we may need to update it
    # below.  Also replace "None" with "".
    kwargs["help"] = user_config.pop("help", None) or ""

    if isinstance(field.repr, _SecretRepr):
        kwargs["show_default"] = False
        if "default" in kwargs:  # pragma: no cover
            kwargs[
                "help"
            ] = f"{kwargs['help']}  [default: {Secret(kwargs['default'])}]"

    if "default" not in kwargs:
        kwargs["required"] = True

    # The user has the last word, though.
    kwargs.update(user_config)

    return option_fn(*param_decls, **kwargs)


def _make_callback(
    path: str,
    type_callback: Optional[Callback],
    user_callback: Optional[Callback],
) -> Callback:
    """
    Generate a callback that adds option values to the settings instance in the
    context.

    It also calls a type's callback if there should be one.
    """

    def cb(ctx: click.Context, param: click.Option, value: Any) -> Any:
        if type_callback is not None:
            value = type_callback(ctx, param, value)
        if user_callback is not None:
            value = user_callback(ctx, param, value)

        if ctx.obj is None:
            ctx.obj = {}
        settings = ctx.obj.setdefault(CTX_KEY, {})
        _set_path(settings, path, value)
        return value

    return cb
