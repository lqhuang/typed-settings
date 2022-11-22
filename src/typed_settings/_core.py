"""
Core functionality for loading settings.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Type, Union

import attrs

from ._dict_utils import _deep_options, _merge_dicts, _set_path
from .attrs import METADATA_KEY
from .converters import BaseConverter, default_converter, from_dict
from .loaders import EnvLoader, FileLoader, Loader, TomlFormat
from .types import AUTO, ST, OptionList, SettingsClass, _Auto


LOGGER = logging.getLogger(METADATA_KEY)


def default_loaders(
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    *,
    config_file_section: Union[str, _Auto] = AUTO,
    config_files_var: Union[None, str, _Auto] = AUTO,
    env_prefix: Union[None, str, _Auto] = AUTO,
) -> List[Loader]:
    """
    Return a list of default settings loaders that are used by :func:`load()`.

    These loaders are:

    #. A :class:`.FileLoader` loader configured with the :class:`.TomlFormat`
    #. An :class:`.EnvLoader`

    The :class:`.FileLoader` will load files from *config_files* and from the
    environment variable *config_files_var*.

    Args:
        appname: Your application's name – used to derive defaults for the
          remaining args.

        config_files: Load settings from these files.  The last one has the
          highest precedence.

        config_file_section: Name of your app's section in the config file.
          By default, use *appname* (in lower case and with "_" replaced by
          "-".

        config_files_var: Load list of settings files from this environment
          variable.  By default, use :code:`{APPNAME}_SETTINGS`.  Multiple
          paths have to be separated by ":".  The last file has the highest
          precedence.  All files listed in this var have higher precedence than
          files from *config_files*.

          Set to ``None`` to disable this feature.

        env_prefix: Load settings from environment variables with this prefix.
          By default, use *APPNAME_*.

          Set to ``None`` to disable loading env vars.

    Return:
        A list of :class:`.Loader` instances.
    """
    loaders: List[Loader] = []

    section = (
        appname.lower().replace("_", "-")
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
            formats={"*.toml": TomlFormat(section)},
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
    cls: Type[ST],
    appname: str,
    config_files: Iterable[Union[str, Path]] = (),
    *,
    config_file_section: Union[str, _Auto] = AUTO,
    config_files_var: Union[None, str, _Auto] = AUTO,
    env_prefix: Union[None, str, _Auto] = AUTO,
) -> ST:
    """
    Load settings for *appname* and return an instance of *cls*

    This function is a shortcut for :func:`load_settings()` with
    :func:`default_loaders()`.

    Settings are loaded from *config_files* and from the files specified
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

        config_files: Load settings from these files.

        config_file_section: Name of your app's section in the config file.
          By default, use *appname* (in lower case and with "_" replaced by
          "-".

        config_files_var: Load list of settings files from this environment
          variable.  By default, use :code:`{APPNAME}_SETTINGS`.  Multiple
          paths have to be separated by ":".  The last file has the highest
          precedence.  All files listed in this var have higher precedence than
          files from *config_files*.

          Set to ``None`` to disable this feature.

        env_prefix: Load settings from environment variables with this prefix.
          By default, use *APPNAME_*.

          Set to ``None`` to disable loading env vars.

    Return:
        An instance of *cls* populated with settings from settings files and
        environment variables.

    Raise:
        UnknownFormatError: When no :class:`~typed_settings.loaders.FileFormat`
            is configured for a loaded file.
        ConfigFileNotFoundError: If *path* does not exist.
        ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
        InvalidOptionsError: If invalid settings have been found.
        InvalidValueError: If a value cannot be converted to the correct type.
    """
    loaders = default_loaders(
        appname=appname,
        config_files=config_files,
        config_file_section=config_file_section,
        config_files_var=config_files_var,
        env_prefix=env_prefix,
    )
    settings = _load_settings(
        cls=cls,
        options=_deep_options(cls),
        loaders=loaders,
    )

    converter = default_converter()
    return from_dict(settings, cls, converter)


def load_settings(
    cls: Type[ST],
    loaders: Sequence[Loader],
    converter: Optional[BaseConverter] = None,
) -> ST:
    """
    Load settings defined by the class *cls* and return an instance of it.

    Args:
        cls: Attrs class with options (and default values).
        loaders: A list of settings :class:`.Loader`'s.
        converter: An optional :class:`cattrs.converters.BaseConverter` used
            for converting option values to the required type.

            By default, :func:`.default_converter()` is used.

    Return:
        An instance of *cls* populated with settings from the defined loaders.

    Raise:
        TsError: Depending on the configured loaders, any subclass of this
            exception.
    """
    if converter is None:
        converter = default_converter()
    settings = _load_settings(
        cls=cls,
        options=_deep_options(cls),
        loaders=loaders,
    )
    return from_dict(settings, cls, converter)


def _load_settings(
    cls: SettingsClass,
    options: OptionList,
    loaders: Sequence[Loader],
) -> Dict[str, Any]:
    """
    Loads settings for *options* and returns them as dict.

    This function makes it easier to extend settings since it returns a dict
    that can easily be updated.
    """
    settings: Dict[str, Any] = {}

    # Populate dict with default settings.  This avoids problems with nested
    # settings classes for which no settings are loaded.
    for opt in options:
        if opt.field.default is attrs.NOTHING:
            continue
        if isinstance(opt.field.default, attrs.Factory):  # type: ignore
            continue
        _set_path(settings, opt.path, opt.field.default)

    loaded_settings = [loader(cls, options) for loader in loaders]

    for ls in loaded_settings:
        _merge_dicts(options, settings, ls)

    return settings
