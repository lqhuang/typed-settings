from functools import update_wrapper
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar, Union
from pathlib import Path
import os

import attr
import click
import toml


class _Auto(object):
    """
    Sentinel class to indicate the lack of a value when ``None`` is ambiguous.

    ``_Auto`` is a singleton. There is only ever one of it.
    """

    _singleton = None

    def __new__(cls):
        if _Auto._singleton is None:
            _Auto._singleton = super(_Auto, cls).__new__(cls)
        return _Auto._singleton

    def __repr__(self):
        return "AUTO"


AUTO = _Auto()
"""
Sentinel to indicate the lack of a value when ``None`` is ambiguous.
"""

T = TypeVar('T')


def load_settings(
    appname: str,
    settings_cls: Type[T],
    config_files: Iterable[Union[str, Path]] = (),
    config_file_section: Union[_Auto, str] = AUTO,
    config_files_var: Union[None, _Auto, str] = AUTO,
    settings_env_prefix: Union[None, _Auto, str] = AUTO,
) -> T:
    """Loads settings for *appname* and returns an instance of *settings_cls*

    Settings can be loaded from *config_files* and/or from the files specified via the
    *config_files_var* environment variable.  Settings can also be overridden via
    environment variables named like the corresponding setting and prefixed with
    *settings_env_prefix*.

    Settings precedence (from lowest to highest priority):

    - Default value from *settings_cls*
    - First file from *config_files*
    - ...
    - Last file from *config_files*
    - First file from *config_files_var*
    - ...
    - Last file from *config_files_var*
    - Environment variable *settings_env_prefix*_{SETTING}

    Args:
      appname: Your application's name.  Used to derive defaults for the remaining args.

      settings_cls: Attrs class with default settings.

      config_files: Load settings from these TOML files.

      config_file_section: Name of your app's section in the config file.  By default,
        use *appname*.

      config_files_var: Load list of settings files from this environment variable.
        By default, use *APPNAME*_SETTINGS.  Multiple paths have to be separated by ":".
        Each settings file will update its predecessor, so the last file will have the
        highest priority.

        Set to ``None`` to disable this feature.

      settings_env_prefix: Load settings from environment variables with this prefix.
        By default, use *APPNAME_*.  Set to ``None`` to disable loading env vars.

    Returns:
      An instance of *settings_cls* populated with settings from settings files and
      environment variables.

    Raises:
      TypeError: Config values cannot be converted to the required type
      ValueError: Config values don't meet their requirements

    """
    if config_file_section is AUTO:
        config_file_section = appname
    if config_files_var is AUTO:
        config_files_var = f'{appname.upper()}_SETTINGS'
    if settings_env_prefix is AUTO:
        settings_env_prefix = f'{appname.upper()}_'

    settings: Dict[str, Any] = {}
    paths = _get_settings_filenames(config_files, config_files_var)
    for path in paths:
        s = toml.load(path.open())
        _dict_merge(settings, s.get(config_file_section, {}))
    # _dict_merge(settings, _get_env_dict(settings_cls, os.environ, settings_env_prefix))

    settings = _clean_settings(settings, settings_cls)

    return settings_cls(**settings)


def click_options(settings_cls, appname, config_files):
    def pass_settings(f):
        """Similar to :func:`pass_context`, but only pass the object on the
        context onwards (:attr:`Context.obj`).  This is useful if that object
        represents the state of a nested system.
        """

        def new_func(*args, **kwargs):
            return f(click.get_current_context().obj['settings'], *args, **kwargs)

        return update_wrapper(new_func, f)

    def cb(c, p, v):
        if c.obj is None:
            c.obj = {}
        if 'settings' not in c.obj:
            c.obj['settings'] = {}#typed_settings.load_settings(cls=settings_cls)
        c.obj['settings'][p.name] = v
        return v

    def wrap(f):
        f = click.option(
            '--spam', callback=cb, expose_value=False, is_eager=True
        )(f)
        f = click.option(
            '--eggs', callback=cb, expose_value=False, is_eager=True
        )(f)
        f = pass_settings(f)
        return f
    return wrap


def _get_settings_filenames(
    config_files: Iterable[Union[str, Path]],
    config_files_var: Optional[str],
) -> List[Path]:
    candidates = list(config_files)
    if config_files_var:
        candidates += os.getenv(config_files_var, '').split(':')
    return [p for f in candidates if (p := Path(f)).is_file()]


def _dict_merge(d1, d2):
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict):
            _dict_merge(d1[k], d2[k])
        else:
            d1[k] = d2[k]


def _clean_settings(settings: Dict[str, Any], cls: Type[T]) -> Dict[str, Any]:
    settings = {
        a.name: settings[a.name] for a in attr.fields(cls) if a.name in settings
    }
    return settings


def _get_env_var_names(cls: Type[T], prefix: str) -> List[str]:
    names = [f'{prefix}{a.name.upper()}' for a in attr.fields(cls)]


def _get_env_dict(cls, env, prefix) -> dict:
    prefix_len = len(prefix)
    values = {}
    def check(r_cls, r_values, r_prefix):
        for a in attr.fields(r_cls):
            val = getattr(r_cls, a.name)
            if attr.has(val):
                r_values[a.name] = {}
                check(val, r_values[a.name], f'{r_prefix}{a.name.upper()}_')
            else:
                varname = f'{r_prefix}{a.name.upper()}'
                if varname in env:
                    r_values[a.name] = env[varname]

    check(cls, values, prefix)
    return values
