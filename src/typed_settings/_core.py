"""
Core functionality for loading settings.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Type, Union

import attr

from ._dict_utils import _deep_options, _merge_dicts, _set_path
from .attrs import METADATA_KEY
from .loaders import EnvLoader, FileLoader, Loader, TomlFormat
from .types import AUTO, OptionList, SettingsDict, T, _Auto


LOGGER = logging.getLogger(METADATA_KEY)


def load(
    cls: Type[T],
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    *,
    config_file_section: Union[str, _Auto] = AUTO,
    config_files_var: Union[None, str, _Auto] = AUTO,
    env_prefix: Union[None, str, _Auto] = AUTO,
) -> T:
    """
    Loads settings for *appname* and returns an instance of *cls*

    Settings can be loaded from *config_files* and/or from the files specified
    via the *config_files_var* environment variable.  Settings can also be
    overridden via environment variables named like the corresponding setting
    and prefixed with *env_prefix*.

    Settings precedence (from lowest to highest priority):

    - Default value from *cls*
    - First file from *config_files*
    - ...
    - Last file from *config_files*
    - First file from *config_files_var*
    - ...
    - Last file from *config_files_var*
    - Environment variable :code:`{env_prefix}_{SETTING}`

    Config files (both, explicitly specified, and loaded from an environment
    variable) are optional by default.  You can prepend an ``!`` to their path
    to mark them as mandatory (e.g., `!/etc/credentials.toml`).  An error is
    raised if a mandatory file does not exist.

    Args:
        cls: Attrs class with default settings.

        appname: Your application's name.  Used to derive defaults for the
          remaining args.

        config_files: Load settings from these TOML files.

        config_file_section: Name of your app's section in the config file.
          By default, use *appname*.

        config_files_var: Load list of settings files from this environment
          variable.  By default, use :code:`{APPNAME}_SETTINGS`.  Multiple
          paths have to be separated by ":".  Each settings file will update
          its predecessor, so the last file will have the highest priority.

          Set to ``None`` to disable this feature.

        env_prefix: Load settings from environment variables with this prefix.
          By default, use *APPNAME_*.  Set to ``None`` to disable loading env
          vars.

    Returns:
        An instance of *cls* populated with settings from settings
        files and environment variables.

    Raises:
        FileNotFoundError: If a mandatory config file does not exist.
        TypeError: If config values cannot be converted to the required type.
        ValueError: If config values don't meet their requirements.
        ValueError: If a config file contains an invalid option.
    """
    options = _deep_options(cls)
    settings = _load_settings(
        options=options,
        appname=appname,
        loaders=[
            FileLoader(
                files=config_files,
                env_var=config_files_var,
                section=config_file_section,
                formats={"*.toml": TomlFormat()},
            ),
            EnvLoader(prefix=env_prefix),
        ],
    )
    return cls(**settings)  # type: ignore


def load_settings(*args, **kwargs):
    import warnings

    warnings.warn(
        (
            'The signature of "load_settings()" will introduce breaking '
            'changes in v0.11 or v1.0.  Please use "load()" instead.'
        ),
        DeprecationWarning,
    )
    return load(*args, **kwargs)


def _load_settings(
    *,
    options: OptionList,
    appname: str,
    loaders: List[Loader],
    # config_files: Iterable[Union[str, Path]],
    # config_file_section: Union[str, _Auto],
    # config_files_var: Union[None, str, _Auto],
    # env_prefix: Union[None, str, _Auto],
) -> Dict[str, Any]:
    """
    Loads settings for *options* and returns them as dict.

    This function makes it easier to extend settings since it returns a dict
    that can easily be updated (as compared to frozen settings instances).

    See :func:`load_settings() for details on the arguments.
    """
    settings: Dict[str, Any] = {}

    # Populate dict with default settings.  This avoids problems with nested
    # settings classes for which no settings are loaded.
    for opt in options:
        if opt.field.default is attr.NOTHING:
            continue
        if isinstance(opt.field.default, attr.Factory):  # type: ignore
            continue
        _set_path(settings, opt.path, opt.field.default)

    loaded_settings = [loader.load(options, appname) for loader in loaders]

    for ls in loaded_settings:
        _merge_dicts(settings, ls)

    return settings
