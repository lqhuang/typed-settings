from functools import update_wrapper
from pathlib import Path
from typing import Any, Callable, Iterable, Type, Union

import attr

from ._core import AUTO, T, _Auto, _load_settings
from ._dict_utils import _deep_fields, _merge_dicts, _set_path


AnyFunc = Callable[..., Any]
Decorator = Callable[[AnyFunc], AnyFunc]


def click_options(
    settings_cls: Type[T],
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    config_file_section: Union[_Auto, str] = AUTO,
    config_files_var: Union[None, _Auto, str] = AUTO,
    env_prefix: Union[None, _Auto, str] = AUTO,
) -> Callable[[Callable], Callable]:
    """
    Generates :mod:`click` options for a CLI which override settins loaded via
    :func:`.load_settings()`.

    A single *settings_cls* instance is passed to the decorated function

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
    try:
        import click
    except ImportError as e:
        raise ModuleNotFoundError(
            'You need to install "click" to use this feature'
        ) from e

    fields = _deep_fields(settings_cls)

    def pass_settings(f: AnyFunc) -> Decorator:
        """
        Creates a *settings_cls* instances from the settings dict stored in
        :attr:`click.Context.obj` and passes it to the decorated function *f*.
        """

        def new_func(*args, **kwargs):
            ctx = click.get_current_context()
            try:
                settings = _load_settings(
                    fields=fields,
                    appname=appname,
                    config_files=config_files,
                    config_file_section=config_file_section,
                    config_files_var=config_files_var,
                    env_prefix=env_prefix,
                )
                _merge_dicts(settings, ctx.obj.get("settings"))
                ctx.obj["settings"] = settings_cls(**settings)
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
            option = _mk_option(click.option, path, field)
            f = option(f)
        f = pass_settings(f)
        return f

    return wrap


def _mk_option(option, path, field) -> Decorator:
    """Recursively creates click options and returns them as a list."""

    def cb(ctx, _param, value):
        if ctx.obj is None:
            ctx.obj = {}
        settings = ctx.obj.setdefault("settings", {})
        _set_path(settings, path, value)
        return value

    kwargs = {}
    if field.default is not attr.NOTHING:
        kwargs["default"] = field.default

    opt_name = path.replace(".", "-")
    param_decl = f"--{opt_name}"
    if field.type is bool:
        param_decl = f"{param_decl}/--no-{opt_name}"

    return option(
        param_decl,
        type=field.type,
        show_default=True,
        callback=cb,
        expose_value=False,
        is_eager=True,
        **kwargs,
    )
