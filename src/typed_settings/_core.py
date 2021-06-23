"""
Core functionality for loading settings.
"""
import logging
import os
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
)

import attr
import toml  # type: ignore

from ._dict_utils import FieldList, _deep_fields, _merge_dicts, _set_path
from .attrs import METADATA_KEY


LOGGER = logging.getLogger(METADATA_KEY)


class _Auto:
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

T = TypeVar("T")


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
    fields = _deep_fields(cls)
    settings = _load_settings(
        fields=fields,
        appname=appname,
        config_files=config_files,
        config_file_section=config_file_section,
        config_files_var=config_files_var,
        env_prefix=env_prefix,
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
    fields: FieldList,
    appname: str,
    config_files: Iterable[Union[str, Path]],
    config_file_section: Union[str, _Auto],
    config_files_var: Union[None, str, _Auto],
    env_prefix: Union[None, str, _Auto],
) -> Dict[str, Any]:
    """
    Loads settings for *fields* and returns them as dict.

    This function makes it easier to extend settings since it returns a dict
    that can easily be updated (as compared to frozen settings instances).

    See :func:`load_settings() for details on the arguments.
    """
    settings: Dict[str, Any] = {}

    # Populate dict with default settings.  This avoids problems with nested
    # settings classes for which no settings are loaded.
    for path, field, _cls in fields:
        if field.default is attr.NOTHING:
            continue
        if isinstance(field.default, attr.Factory):  # type: ignore
            continue
        _set_path(settings, path, field.default)

    loaded_settings = [
        _from_toml(
            fields=fields,
            appname=appname,
            files=config_files,
            section=config_file_section,
            var_name=config_files_var,
        ),
        # _from_dotenv(),
        _from_env(fields=fields, appname=appname, prefix=env_prefix),
    ]
    for ls in loaded_settings:
        _merge_dicts(settings, ls)
    return settings


def _from_toml(
    fields: FieldList,
    appname: str,
    files: Iterable[Union[str, Path]],
    section: Union[str, _Auto],
    var_name: Union[None, str, _Auto],
) -> Dict[str, Any]:
    """
    Loads settings from toml files.

    Settings of multiple files will be merged.  The last file has the highest
    precedence.

    Args:
        fields: The list of available settings.
        appname: Appname to derive *section* and *var_name* from.
        files: A list of filenames to try to load.
        section: The name of the TOML file section to load data from.  Will be
          :code:`{appname}` if it is :data:`AUTO`.
        var_name: Name of the environment variable that may hold additional
          file paths.  Will be :code:`{APPNAME}_SETTINGS` if it is
          :data:`AUTO`.

    Returns:
        A dict with the loaded settings.
    """
    section = appname if isinstance(section, _Auto) else section
    var_name = (
        f"{appname.upper()}_SETTINGS".replace("-", "_")
        if isinstance(var_name, _Auto)
        else var_name
    )

    paths = _get_config_filenames(files, var_name)
    settings: Dict[str, Any] = {}
    for path in paths:
        toml_settings = _load_toml(fields, path, section)
        _merge_dicts(settings, toml_settings)
    return settings


def _get_config_filenames(
    config_files: Iterable[Union[str, Path]],
    config_files_var: Optional[str],
) -> List[Path]:
    """
    Concatenates *config_files* and files from env var *config_files_var*.

    Mandatory files can be prefixed with ``!``.  Optional files will be
    stripped from the result if they don't exist.

    Args:
        config_files: A list of paths to settings files.
        config_files_var: The name of the environment variable that may held
          additional settings file names.

    Returns:
        A list of paths to existing config files.  Paths of files that don't
        exist are stripped from the input.
    """
    candidates = [(False, str(f)) for f in config_files]
    if config_files_var:
        LOGGER.debug(f"Env var for config files: {config_files_var}")
        candidates += [
            (True, fname)
            for fname in os.getenv(config_files_var, "").split(":")
        ]
    else:
        LOGGER.debug("Env var for config files not set")

    paths = []
    for from_envvar, fname in candidates:
        _, flag, fname = fname.rpartition("!")
        if not fname:
            continue
        is_mandatory = flag == "!"
        try:
            path = Path(fname).resolve(strict=True)
        except FileNotFoundError:
            if is_mandatory:
                LOGGER.error(f"Mandatory config file not found: {fname}")
                raise
            elif from_envvar:
                LOGGER.warning(
                    f"Config file from {config_files_var} not found: {fname}"
                )
            else:
                LOGGER.info(f"Config file not found: {fname}")
        else:
            LOGGER.debug(f"Loading settings from: {path}")
            paths.append(Path(fname))

    return paths


def _load_toml(fields: FieldList, path: Path, section: str) -> Dict[str, Any]:
    """
    Loads settings from a TOML file and returns them.

    Args:
        fields: The list of available settings.
        path: The path to the config file.
        section: The config file section to load settings from.

    Returns:
        A dict with the loaded settings.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """
    sections = section.split(".")
    settings = toml.load(path.open())
    for s in sections:
        try:
            settings = settings[s]
        except KeyError:
            return {}
    settings = _clean_settings(fields, settings, path)
    return settings


def _clean_settings(
    fields: FieldList, settings: Mapping[str, Any], path: Path
) -> Dict[str, Any]:
    """
    Recursively check settings for invalid entries and raise an error.

    Args:
        fields: The list of available settings.
        settings: The settings to be cleaned.

    Raises:
        ValueError: if invalid settings are found
    """
    invalid_paths = []
    valid_paths = {path for path, _field, _cls in fields}
    cleaned: Dict[str, Any] = {}

    def _iter_dict(d: Mapping[str, Any], prefix: str) -> None:
        for key, val in d.items():
            key = key.replace("-", "_")
            path = f"{prefix}{key}"

            if path in valid_paths:
                _set_path(cleaned, path, val)
                continue

            if isinstance(val, dict):
                _iter_dict(val, f"{path}.")
            else:
                invalid_paths.append(path)

    _iter_dict(settings, "")

    if invalid_paths:
        joined_paths = ", ".join(sorted(invalid_paths))
        raise ValueError(f"Invalid settings found in {path}: {joined_paths}")

    return cleaned


def _from_env(
    fields: FieldList, appname: str, prefix: Union[None, str, _Auto]
) -> Dict[str, Any]:
    """
    Loads settings from environment variables.

    Args:
        fields: The list of available settings.
        appname: Appname to derive *prefix* from.
        prefix: Prefix for environment variables.  Will be :code:`{APPNAME_}`
          if it is :data:`Auto`.  If it is ``None``, no vars will be loaed.

    Returns:
        A dict with the loaded settings.
    """
    if prefix is None:
        LOGGER.debug("Loading settings from env vars is disabled.")
        return {}
    prefix = f"{appname.upper()}_" if isinstance(prefix, _Auto) else prefix
    LOGGER.debug(f"Looking for env vars with prefix: {prefix}")

    env = os.environ
    values: Dict[str, Any] = {}
    for path, _field, _cls in fields:
        varname = f"{prefix}{path.upper().replace('.', '_')}"
        if varname in env:
            LOGGER.debug(f"Env var found: {varname}")
            _set_path(values, path, env[varname])
        else:
            LOGGER.debug(f"Env var not found: {varname}")

    return values
