"""
This module contains the settings loaders provided by Typed Settings and the
protocol specification that they must implement.
"""
import importlib.util
import logging
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Union,
    cast,
)

from ._compat import PY_311


if PY_311:
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

from . import cls_utils
from .dict_utils import set_path
from .exceptions import (
    ConfigFileLoadError,
    ConfigFileNotFoundError,
    InvalidOptionsError,
    UnknownFormatError,
)
from .types import (
    LoadedSettings,
    LoaderMeta,
    OptionInfo,
    OptionList,
    SettingsClass,
    SettingsDict,
)


__all__ = [
    "Loader",
    "DictLoader",
    "InstanceLoader",
    "EnvLoader",
    "FileLoader",
    "FileFormat",
    "PythonFormat",
    "TomlFormat",
    "OnePasswordLoader",
    "clean_settings",
]


LOGGER = logging.getLogger("typed_settings")


class Loader(Protocol):
    """
    **Protocol** that settings loaders must implement.

    Loaders must be callables (e.g., functions) with the specified signature.

    .. versionchanged:: 1.0.0
       Renamed ``load()`` to ``__call__()`` and also pass the settings
       class.
    """

    def __call__(
        self, settings_cls: SettingsClass, options: OptionList
    ) -> Union[LoadedSettings, Iterable[LoadedSettings]]:
        """
        Load settings for the given options.

        Args:
            settings_cls: The base settings class for all options.
            options: The list of available settings.

        Return:
            A dict with the loaded settings.
        """
        ...


class FileFormat(Protocol):
    """
    **Protoco** that file format loaders for :class:`FileLoader` must
    implement.

    File format loaders must be callables (e.g., functions) with the specified
    signature.

    .. versionchanged:: 1.0.0
       Renamed ``load_file()`` to ``__call__()`` and also pass the settings
       class.
    """

    def __call__(
        self, path: Path, settings_cls: SettingsClass, options: OptionList
    ) -> SettingsDict:
        """
        Load settings from a given file and return them as a dict.

        Args:
            path: The path to the config file.
            settings_cls: The base settings class for all options.
            options: The list of available settings.

        Return:
            A dict with the loaded settings.

        Raise:
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
        """
        ...


class _DefaultsLoader:
    """
    Return the default settings for a given settings class.

    Args:
        base_dir: Resolve relative paths in default settings relative to this directory.
            By default, use the user's current working directory.

            For tools like linters or test runners, you may want to use the root
            directory of the app that the tool operates in.
    """

    def __init__(self, base_dir: Path = Path()) -> None:
        self.base_dir = base_dir

    def __call__(
        self, settings_cls: SettingsClass, options: OptionList
    ) -> LoadedSettings:
        settings: SettingsDict = {}

        # Populate dict with default settings.  This avoids problems with nested
        # settings classes for which no settings are loaded.
        for opt in options:
            if opt.has_no_default:
                continue
            if opt.default_is_factory:
                # Do not invoke default factories yet.  This should be done as late as
                # possible.  This is especially required for CLIs if you want to invoke
                # the same instance multiple times (e.g., in tests).
                continue
            set_path(settings, opt.path, opt.default)

        return LoadedSettings(settings, LoaderMeta(self, base_dir=self.base_dir))


class DictLoader:
    """
    Load settings from a dict of values.

    This is mainly for testing purposes.

    Args:
        settings: A (nested) dict of settings

    .. versionadded:: 23.1.0
    """

    def __init__(self, settings: dict) -> None:
        self.settings = settings

    def __call__(
        self, settings_cls: SettingsClass, options: OptionList
    ) -> LoadedSettings:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.
        """
        return LoadedSettings(self.settings, LoaderMeta(self))


class InstanceLoader:
    """
    Load settings from an instance of the settings class.

    Args:
        instance: The settings instance from which to load option values.

    .. versionadded:: 1.0.0
    """

    def __init__(self, instance: object) -> None:
        self.instance = instance

    def __call__(
        self, settings_cls: SettingsClass, options: OptionList
    ) -> LoadedSettings:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.
        """
        if not isinstance(self.instance, settings_cls):
            raise ValueError(
                f'"self.instance" is not an instance of {settings_cls}: '
                f"{type(self.instance)}"
            )
        cls_handler = cls_utils.find_handler(type(self.instance))
        return LoadedSettings(cls_handler.asdict(self.instance), LoaderMeta(self))


class EnvLoader:
    """
    Load settings from environment variables.

    Args:
        prefix: Prefix for environment variables, e.g., ``MYAPP_``.
    """

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def __call__(
        self, settings_cls: SettingsClass, options: OptionList
    ) -> LoadedSettings:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.
        """
        LOGGER.debug(f"Looking for env vars with prefix: {self.prefix}")

        env = os.environ
        values: SettingsDict = {}
        for o in options:
            varname = self.get_envvar(o)
            if varname in env:
                LOGGER.debug(f"Env var found: {varname}")
                set_path(values, o.path, env[varname])
            else:
                LOGGER.debug(f"Env var not found: {varname}")

        return LoadedSettings(values, LoaderMeta(self))

    def get_envvar(self, option: OptionInfo) -> str:
        """
        Return the envvar name for the he given option.
        """
        return f"{self.prefix}{option.path.upper().replace('.', '_')}"


class FileLoader:
    """
    Load settings from config files.

    Settings of multiple files will be merged.  The last file has the highest
    precedence.  Files specified via an environment variable are loaded after
    the files passed to this class, i.e.:

    - First file from *files*
    - ...
    - Last file from *files*
    - First file from *env_var*
    - ...
    - Last file from *env_var*

    Mandatory files can be prefixed with ``!``.  Optional files will be ignored
    if they don't exist.

    Args:
        formats: A dict mapping glob patterns to :class:`FileFormat` instances.
        files: A list of filenames to try to load.
        env_var: Name of the environment variable that may hold additional file
            paths.  If it is ``None``, only files from *files* will be loaded.
    """

    def __init__(
        self,
        formats: Dict[str, FileFormat],
        files: Iterable[Union[str, Path]],
        env_var: Optional[str] = None,
    ) -> None:
        self.files = files
        self.env_var = env_var
        self.formats = formats

    def __call__(
        self, settings_cls: SettingsClass, options: OptionList
    ) -> List[LoadedSettings]:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.

        Raise:
            UnknownFormatError: When no :class:`FileFormat` is configured for a
                loaded file.
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
            InvalidOptionsError: If invalid settings have been found.
        """
        paths = self._get_config_filenames(self.files, self.env_var)
        loaded_settings: List[LoadedSettings] = []
        for path in paths:
            settings = self._load_file(path, settings_cls, options)
            meta = LoaderMeta(f"{type(self).__name__}[{path}]", base_dir=path.parent)
            loaded_settings.append(LoadedSettings(settings, meta))
        return loaded_settings

    def _load_file(
        self,
        path: Path,
        settings_cls: SettingsClass,
        options: OptionList,
    ) -> SettingsDict:
        """
        Load a file and return its cleaned contents.
        """
        # "clean_settings()" must be called for each loaded file individually
        # because of the "-"/"_" normalization.  This also allows us to tell
        # the user the exact file that contains errors.
        for pattern, ffloader in self.formats.items():
            if fnmatch(path.name, pattern):
                settings = ffloader(path, settings_cls, options)
                settings = clean_settings(settings, options, path)
                return settings

        raise UnknownFormatError(f"No loader configured for: {path}")

    @staticmethod
    def _get_config_filenames(
        files: Iterable[Union[str, Path]], env_var: Optional[str]
    ) -> List[Path]:
        """
        Concatenate *config_files* and files from env var *config_files_var*.
        """
        candidates = [(False, str(f)) for f in files]
        if env_var:
            LOGGER.debug(f"Env var for config files: {env_var}")
            candidates += [(True, fname) for fname in os.getenv(env_var, "").split(":")]
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
                    LOGGER.warning(f"Config file from {env_var} not found: {fname}")
                else:
                    LOGGER.info(f"Config file not found: {fname}")
            else:
                LOGGER.debug(f"Loading settings from: {path}")
                paths.append(path)

        return paths


class PythonFormat:
    """
    Support for Python files.  Read settings from the given *section*.

    Args:
        section: The config file section to load settings from.
    """

    def __init__(
        self,
        cls_name: str,
        key_transformer: Callable[[str], str] = lambda k: k,
        flat: bool = False,
    ) -> None:
        self.cls_name = cls_name
        self.key_transformer = key_transformer
        self.flat = flat

    @staticmethod
    def to_lower(text: str) -> str:
        """
        Transform *text* to lower case.
        """
        return text.lower()

    def __call__(
        self, path: Path, settings_cls: SettingsClass, options: OptionList
    ) -> SettingsDict:
        """
        Load settings from a Python file and return them as a dict.

        Args:
            path: The path to the config file.
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.

        Raise:
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
        """
        module = self._import_module(path)

        def cls2dict(cls: type) -> SettingsDict:
            d = dict(cls.__dict__)
            result = {}
            for k, v in d.items():
                if k.startswith("_"):
                    continue
                k = self.key_transformer(k)
                if isinstance(v, type):
                    v = cls2dict(v)
                result[k] = v
            return result

        try:
            cls = getattr(module, self.cls_name)
        except AttributeError:
            return {}
        settings = cls2dict(cls)
        if self.flat:
            for o in options:
                key = f"{o.path.replace('.', '_')}"
                if key in settings:
                    val = settings.pop(key)
                    set_path(settings, o.path, val)
        return settings

    def _import_module(self, path: Path) -> object:
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ConfigFileNotFoundError("No such file or directory: '{path}'")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise ConfigFileLoadError(str(e)) from e
        return module


class TomlFormat:
    """
    Support for TOML files.  Read settings from the given *section*.

    Args:
        section: The config file section to load settings from.
    """

    def __init__(self, section: str) -> None:
        self.section = section

    def __call__(
        self, path: Path, settings_cls: SettingsClass, options: OptionList
    ) -> SettingsDict:
        """
        Load settings from a TOML file and return them as a dict.

        Args:
            path: The path to the config file.
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.

        Raise:
            ConfigFileNotFoundError: If *path* does not exist.
            ConfigFileLoadError: If *path* cannot be read/loaded/decoded.
        """
        sections = self.section.split(".")
        try:
            with path.open("rb") as f:
                settings = tomllib.load(f)
        except FileNotFoundError as e:
            raise ConfigFileNotFoundError(str(e)) from e
        except (PermissionError, tomllib.TOMLDecodeError) as e:
            raise ConfigFileLoadError(str(e)) from e
        for s in sections:
            try:
                settings = settings[s]
            except KeyError:
                return {}
        return cast(SettingsDict, settings)


class OnePasswordLoader:
    """
    Load settings from an item stored in a 1Password vault.

    You must must have installed and set up the `1Password CLI`_ in order
    for this loader to work.

    .. _1Password CLI: https://developer.1password.com/docs/cli/

    Args:
        item: The item to load
        vault: The vault in which to look for *item*.  By default, search all
            vaults.
    """

    def __init__(self, item: str, vault: Optional[str] = None) -> None:
        self.item = item
        self.vault = vault

        from . import _onepassword

        self._op = _onepassword

    def __call__(self, settings_cls: type, options: OptionList) -> LoadedSettings:
        """
        Load settings for the given options.

        Args:
            options: The list of available settings.
            settings_cls: The base settings class for all options.

        Return:
            A dict with the loaded settings.
        """
        option_names = [o.path for o in options]
        settings = self._op.get_item(self.item, self.vault)
        settings = {k: v for k, v in settings.items() if k in option_names}
        return LoadedSettings(settings, LoaderMeta(self))


def clean_settings(
    settings: SettingsDict, options: OptionList, source: Any
) -> SettingsDict:
    """
    Recursively check settings for invalid entries and raise an error.

    An error is not raised until all options have been checked.  It then lists
    all invalid options that have been found.

    Args:
        settings: The settings to be cleaned.
        options: The list of available settings.
        source: Source of the settings (e.g., path to a config file).
                It should have a useful string representation.

    Return:
        The cleaned settings.
    Raise:
        InvalidOptionsError: If invalid settings have been found.
    """
    invalid_paths = []
    valid_paths = {o.path for o in options}
    cleaned: SettingsDict = {}

    def _iter_dict(d: SettingsDict, prefix: str) -> None:
        for key, val in d.items():
            key = key.replace("-", "_")
            path = f"{prefix}{key}"

            if path in valid_paths:
                set_path(cleaned, path, val)
                continue

            if isinstance(val, dict):
                _iter_dict(val, f"{path}.")
            else:
                invalid_paths.append(path)

    _iter_dict(settings, "")

    if invalid_paths:
        joined_paths = ", ".join(sorted(invalid_paths))
        raise InvalidOptionsError(f"Invalid options found in {source}: {joined_paths}")

    return cleaned
