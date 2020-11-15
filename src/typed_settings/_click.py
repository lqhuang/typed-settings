from datetime import datetime
from enum import Enum
from functools import update_wrapper
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Type, Union

import attr
import click

from ._core import AUTO, T, _Auto, _load_settings
from ._dict_utils import _deep_fields, _get_path, _merge_dicts, _set_path
from .attrs import METADATA_KEY, _SecretRepr
from .attrs._compat import get_args, get_origin


AnyFunc = Callable[..., Any]
Decorator = Callable[[AnyFunc], AnyFunc]


class EnumChoice(click.Choice):
    """*Click* parameter type for representing enums."""

    def __init__(self, enum_type: Type[Enum]):
        self.__enum = enum_type
        super().__init__(enum_type.__members__)

    def convert(
        self,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Enum:
        return self.__enum[super().convert(value, param, ctx)]


def click_options(
    cls: Type[T],
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    config_file_section: Union[_Auto, str] = AUTO,
    config_files_var: Union[None, _Auto, str] = AUTO,
    env_prefix: Union[None, _Auto, str] = AUTO,
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

    def pass_settings(f: AnyFunc) -> Decorator:
        """
        Creates a *cls* instances from the settings dict stored in
        :attr:`click.Context.obj` and passes it to the decorated function *f*.
        """

        def new_func(*args, **kwargs):
            ctx = click.get_current_context()
            try:
                _merge_dicts(settings, ctx.obj.get("settings"))
                ctx.obj["settings"] = cls(**settings)
            except (
                AttributeError,
                FileNotFoundError,
                TypeError,
                ValueError,
            ) as e:
                raise click.ClickException(e)
            return f(ctx.obj["settings"], *args, **kwargs)

        return update_wrapper(new_func, f)

    def wrap(f):
        for path, field, _cls in reversed(fields):
            try:
                default = _get_path(settings, path)
            except KeyError:
                default = field.default
            if isinstance(default, attr.Factory):
                if default.takes_self:
                    default = default.factory(None)
                else:
                    default = default.factory()
            option = _mk_option(click.option, path, field, default)
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


def _mk_option(
    option: Callable[..., Decorator],
    path: str,
    field: attr.Attribute,
    default: Any,
) -> Decorator:
    """
    Recursively creates click options and returns them as a list.
    """

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
        if default is not attr.NOTHING:
            kwargs["help"] = f"{kwargs['help']}  [default: {field.repr('')}]"

    if default is attr.NOTHING:
        kwargs["required"] = True

    opt_name = path.replace(".", "-").replace("_", "-")
    param_decl = f"--{opt_name}"

    if field.type:
        if field.type is bool:
            param_decl = f"{param_decl}/--no-{opt_name}"
        kwargs.update(_get_type(field.type, default))

    return option(param_decl, **kwargs)


def _get_type(otype: type, default: Any) -> Dict[str, Any]:
    """
    Analyses the option type and returns updated options.
    """
    type_info: Dict[str, Any] = {}
    origin = get_origin(otype)
    args = get_args(otype)

    if origin is None and issubclass(otype, (bool, int, float, str, Path)):
        if default is attr.NOTHING:
            type_info = {"type": otype}
        else:
            type_info = {"type": otype, "default": default}

    elif origin is None and issubclass(otype, datetime):
        type_info["type"] = click.DateTime(
            [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S%z",
            ]
        )
        if default is not attr.NOTHING:
            type_info["default"] = default.isoformat()

    elif origin is None and issubclass(otype, Enum):
        type_info["type"] = EnumChoice(otype)
        if default is not attr.NOTHING:
            # Convert Enum instance to string
            type_info["default"] = default.name

    elif origin in {list, set, frozenset} or (
        origin is tuple and len(args) == 2 and args[1] == ...
    ):
        # lists and list-like tuple
        type_info = _get_type(args[0], attr.NOTHING)
        if default is not attr.NOTHING:
            default = [_get_type(args[0], d)["default"] for d in default]
            type_info["default"] = default
        type_info["multiple"] = True

    elif origin is tuple:
        # "struct" variant of tuple
        if default is attr.NOTHING:
            default = [attr.NOTHING] * len(args)
        dicts = [_get_type(a, d) for a, d in zip(args, default)]
        type_info = {
            "type": tuple(d["type"] for d in dicts),
            "nargs": len(dicts),
        }
        if all("default" in d for d in dicts):
            type_info["default"] = tuple(d["default"] for d in dicts)

    else:
        raise TypeError(f"Cannot create click type for: {otype}")

    return type_info
