import logging
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Union,
)

import toml

from ._dict_utils import _merge_dicts, _set_path
from .exceptions import (
    ConfigFileLoadError,
    ConfigFileNotFoundError,
    InvalidOptionsError,
    UnknownFormatError,
)
from .types import OptionList, SettingsDict


LOGGER = logging.getLogger(__name__)


class Loader(Protocol):
    """
    Protocol for settings loaders.
    """

    def load(self, options: OptionList) -> SettingsDict:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.

        Return:
            A dict with the loaded settings.
        """
        ...


class FileFormat(Protocol):
    """
    Protocol for file format loaders for the :class:`FileLoader`.
    """

    def load_file(self, path: Path, section: str) -> SettingsDict:
        """
        Loads settings from a given file and return them as a dict.

        Args:
            path: The path to the config file.
            section: The config file section to load settings from.

        Returns:
            A dict with the loaded settings.

        Raises:
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
        """
        ...


class PythonFormat:
    def load_file(self, path: Path, section: str) -> SettingsDict:
        return {}


class TomlFormat:
    def load_file(self, path: Path, section: str) -> SettingsDict:
        """
        Load settings from a TOML file and return them as a dict.

        Args:
            options: The list of available settings.
            path: The path to the config file.
            section: The config file section to load settings from.

        Returns:
            A dict with the loaded settings.

        Raises:
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
        """
        sections = section.split(".")
        try:
            settings = toml.load(path.open())
        except FileNotFoundError as e:
            raise ConfigFileNotFoundError(str(e)) from e
        except (PermissionError, toml.TomlDecodeError) as e:
            raise ConfigFileLoadError(str(e)) from e
        for s in sections:
            try:
                settings = settings[s]
            except KeyError:
                return {}
        return settings


class FileLoader:
    """
    Load settings from config files.

    Settings of multiple files will be merged.  The last file has the highest
    precedence.  Files specified via an environment variable are loaded after
    the files passed to this class.

    Mandatory files can be prefixed with ``!``.  Optional files will be ignored
    if they don't exist.

    Args:
        formats: A dict mapping glob patterns to :class:`FileFormat` instances.
        files: A list of filenames to try to load.
        section: The name of the config file section to load data from.
        env_var: Name of the environment variable that may hold additional
            file paths.  If it is ``None``, only files from *files* will be
            loaded.
    """

    def __init__(
        self,
        formats: Dict[str, FileFormat],
        files: Iterable[Union[str, Path]],
        section: str,
        env_var: Optional[str] = None,
    ):
        self.files = files
        self.section = section
        self.env_var = env_var
        self.formats = formats

    def load(self, options: OptionList) -> SettingsDict:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.

        Return:
            A dict with the loaded settings.

        Raise:
            UnknownFormat: When no :class:`FileFormat` is configured for a
                loaded file.
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
            InvalidOptionError: If invalid settings have been found.
        """
        paths = self._get_config_filenames(self.files, self.env_var)
        merged_settings: Dict[str, Any] = {}
        for path in paths:
            settings = self._load_file(path, options)
            _merge_dicts(merged_settings, settings)
        return merged_settings

    def _load_file(self, path: Path, options: OptionList) -> Dict[str, Any]:
        """
        Load a file and return its cleaned contents

        Args:
            path: Path to the config file
            options: The list of available settings.

        Return:
            A dict with the cleaned settings.

        Raise:
            UnknownFormat: When no :class:`FileFormat` is configured for
                *path*.
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
            InvalidOptionError: If invalid settings have been found.
        """
        # "clean_settings()" must be called for each loaded file individually
        # because of the "-"/"_" normalization.  This also allows us to tell
        # the user the exact file that contains errors.
        for pattern, parser in self.formats.items():
            if fnmatch(path.name, pattern):
                settings = parser.load_file(path, self.section)
                settings = clean_settings(settings, options, path)
                return settings

        raise UnknownFormatError(f"Nor loader configured for: {path}")

    @staticmethod
    def _get_config_filenames(
        config_files: Iterable[Union[str, Path]],
        config_files_var: Optional[str],
    ) -> List[Path]:
        """
        Concatenate *config_files* and files from env var *config_files_var*.

        Mandatory files can be prefixed with ``!``.  Optional files will be
        stripped from the result if they don't exist.

        Args:
            config_files: A list of paths to settings files.
            config_files_var: The name of the environment variable that may
            hold additional config file names.

        Return:
            A list of paths to existing config files.  Paths of files that
            don't exist are stripped from the input.

        Raise:
            ConfigFileNotFound: When a mandatory file does not exist.
            ConfigFileNotReadable: When a config file exists but cannot be
                read.
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
                if from_envvar:
                    LOGGER.warning(
                        f"Config file from {config_files_var} not found: "
                        f"{fname}"
                    )
                else:
                    LOGGER.info(f"Config file not found: {fname}")
            else:
                LOGGER.debug(f"Loading settings from: {path}")
                paths.append(Path(fname))

        return paths


class EnvLoader:
    """
    Loads settings from environment variables.

    Args:
        prefix: Prefix for environment variables, e.g., ``MYAPP_``.
    """

    def __init__(self, prefix: str):
        self.prefix = prefix

    def load(self, options: OptionList) -> SettingsDict:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.

        Return:
            A dict with the loaded settings.
        """
        prefix = self.prefix
        LOGGER.debug(f"Looking for env vars with prefix: {prefix}")

        env = os.environ
        values: Dict[str, Any] = {}
        for o in options:
            varname = f"{prefix}{o.path.upper().replace('.', '_')}"
            if varname in env:
                LOGGER.debug(f"Env var found: {varname}")
                _set_path(values, o.path, env[varname])
            else:
                LOGGER.debug(f"Env var not found: {varname}")

        return values


def clean_settings(
    settings: SettingsDict, options: OptionList, source: Any
) -> Dict[str, Any]:
    """
    Recursively check settings for invalid entries and raise an error.

    An error is not raised until all options have been checked.  It then lists
    all invalid options that have been found.

    Args:
        settings: The settings to be cleaned.
        options: The list of available settings.
        source: Source of the settings (e.g., path to a config file).
                It should have a useful string representation.

    Raises:
        InvalidOptionError: If invalid settings have been found.
    """
    invalid_paths = []
    valid_paths = {o.path for o in options}
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
        raise InvalidOptionsError(
            f"Invalid options found in {source}: {joined_paths}"
        )

    return cleaned
