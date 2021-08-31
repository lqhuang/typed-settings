"""
if converter is None:
converter = default_converter
Core functionality for loading settings.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Type, Union

import attr
import cattr

from ._dict_utils import _deep_options, _merge_dicts, _set_path
from .attrs import METADATA_KEY
from .attrs import converter as default_converter
from .loaders import EnvLoader, FileLoader, Loader, TomlFormat
from .types import AUTO, OptionList, T, _Auto


LOGGER = logging.getLogger(METADATA_KEY)


def default_loaders(
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    *,
    config_file_section: Union[str, _Auto] = AUTO,
    config_files_var: Union[None, str, _Auto] = AUTO,
    env_prefix: Union[None, str, _Auto] = AUTO,
) -> List[Loader]:
    loaders: List[Loader] = []

    section = (
        appname
        if isinstance(config_file_section, _Auto)
        else config_file_section
    )
    var_name = (
        f"{appname.upper()}_SETTINGS".replace("-", "_")
        if isinstance(config_files_var, _Auto)
        else config_files_var
    )
    loaders.append(
        FileLoader(
            files=config_files,
            env_var=var_name,
            section=section,
            formats={"*.toml": TomlFormat()},
        )
    )

    if env_prefix is None:
        LOGGER.debug("Loading settings from env vars is disabled.")
    else:
        prefix = (
            f"{appname.upper()}_"
            if isinstance(env_prefix, _Auto)
            else env_prefix
        )
        loaders.append(EnvLoader(prefix=prefix))

    return loaders


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
    loaders = default_loaders(
        appname=appname,
        config_files=config_files,
        config_file_section=config_file_section,
        config_files_var=config_files_var,
        env_prefix=env_prefix,
    )
    settings = _load_settings(
        options=_deep_options(cls),
        loaders=loaders,
    )
    return default_converter.structure_attrs_fromdict(settings, cls)


def load_settings(
    cls: Type[T],
    loaders: List[Loader],
    converter: cattr.Converter = None,
) -> T:
    if converter is None:
        converter = default_converter
    settings = _load_settings(
        options=_deep_options(cls),
        loaders=loaders,
    )
    return converter.structure_attrs_fromdict(settings, cls)


def _load_settings(
    options: OptionList,
    loaders: List[Loader],
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

    loaded_settings = [loader.load(options) for loader in loaders]

    for ls in loaded_settings:
        _merge_dicts(settings, ls)

    return settings
