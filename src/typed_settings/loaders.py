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

from ._dict_utils import _deep_options, _merge_dicts, _set_path
from .types import OptionList, SettingsDict, _Auto


LOGGER = logging.getLogger(__name__)


class Loader(Protocol):
    def load(self, options: OptionList, appname: str) -> SettingsDict:
        ...


class FileFormat(Protocol):
    def load_file(
        self, options: OptionList, path: Path, section: str
    ) -> SettingsDict:
        ...


class PythonFormat:
    def load_file(
        self, options: OptionList, path: Path, section: str
    ) -> SettingsDict:
        return {}


class TomlFormat:
    def load_file(
        self, options: OptionList, path: Path, section: str
    ) -> SettingsDict:
        """
        Loads settings from a TOML file and returns them.

        Args:
            options: The list of available settings.
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
        settings = _clean_settings(options, settings, path)
        return settings

    @staticmethod
    def _clean_settings(
        options: OptionList, settings: Mapping[str, Any], path: Path
    ) -> Dict[str, Any]:
        """
        Recursively check settings for invalid entries and raise an error.

        Args:
            options: The list of available settings.
            settings: The settings to be cleaned.

        Raises:
            ValueError: if invalid settings are found
        """
        invalid_paths = []
        valid_paths = {path for path, _field, _cls in options}
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
            raise ValueError(
                f"Invalid settings found in {path}: {joined_paths}"
            )

        return cleaned


class FileLoader:
    def __init__(
        self,
        files: Iterable[Union[str, Path]],
        section: Union[str, _Auto],
        env_var: Union[None, str, _Auto],
        formats: Dict[str, FileFormat],
    ):
        self.files = files
        self.section = section
        self.env_var = env_var
        self.formats = formats

    def load(self, options: OptionList, appname: str) -> SettingsDict:
        """
        Loads settings from toml files.

        Settings of multiple files will be merged.  The last file has the highest
        precedence.

        Args:
            options: The list of available settings.
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
        files = self.files
        section = self.section
        var_name = self.env_var
        formats = self.formats
        section = appname if isinstance(section, _Auto) else section
        var_name = (
            f"{appname.upper()}_SETTINGS".replace("-", "_")
            if isinstance(var_name, _Auto)
            else var_name
        )

        paths = self._get_config_filenames(files, var_name)
        settings: Dict[str, Any] = {}
        for path in paths:
            for pattern, parser in formats.items():
                if fnmatch(path.name, pattern):
                    loaded_settings = parser.load(options, path, section)
                    _merge_dicts(settings, loaded_settings)
                    break
            else:
                raise RuntimeError(f"Nor parser configured for: {path}")
        return settings

    @staticmethod
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


class EnvLoader:
    def __init__(self, prefix: Union[None, str, _Auto]):
        self._prefix = prefix

    def load(self, options: OptionList, appname: str) -> SettingsDict:
        """
        Loads settings from environment variables.

        Args:
            options: The list of available settings.
            appname: Appname to derive *prefix* from.
            prefix: Prefix for environment variables.  Will be
              :code:`{APPNAME_}` if it is :data:`Auto`.  If it is ``None``,
              no vars will be loaed.

        Returns:
            A dict with the loaded settings.
        """
        prefix = self._prefix
        if prefix is None:
            LOGGER.debug("Loading settings from env vars is disabled.")
            return {}
        prefix = f"{appname.upper()}_" if isinstance(prefix, _Auto) else prefix
        LOGGER.debug(f"Looking for env vars with prefix: {prefix}")

        env = os.environ
        values: Dict[str, Any] = {}
        for path, _field, _cls in options:
            varname = f"{prefix}{path.upper().replace('.', '_')}"
            if varname in env:
                LOGGER.debug(f"Env var found: {varname}")
                _set_path(values, path, env[varname])
            else:
                LOGGER.debug(f"Env var not found: {varname}")

        return values
