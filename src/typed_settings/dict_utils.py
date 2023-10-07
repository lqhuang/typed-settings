"""
Utility functions for working settings dicts and serilizing nested settings.
"""
from typing import Any, Generator, Sequence, Tuple

from .types import (
    LoadedSettings,
    LoadedValue,
    MergedSettings,
    OptionList,
    SettingsDict,
)


__all__ = [
    "iter_settings",
    "get_path",
    "set_path",
    "merge_settings",
    "update_settings",
    "flat2nested",
]


def iter_settings(
    dct: SettingsDict, options: OptionList
) -> Generator[Tuple[str, Any], None, None]:
    """
    Iterate over the (possibly nested) options dict *dct* and yield
    *(option_path, value)* tuples.

    Args:
        dct: The dict of settings as returned by a loader.
        options: The list of all available options for a settings class.

    Return:
        A generator yield *(opton_path, value)* tuples.
    """
    for option in options:
        try:
            yield option.path, get_path(dct, option.path)
        except KeyError:
            continue


def get_path(dct: SettingsDict, path: str) -> Any:
    """
    Performs a nested dict lookup for *path* and returns the result.

    Calling ``get_path(dct, "a.b")`` is equivalent to ``dict["a"]["b"]``.

    Args:
        dct: The source dict
        path: The path to look up.  It consists of the dot-separated nested
          keys.

    Returns:
        The looked up value.

    Raises:
        KeyError: if a key in *path* does not exist.
    """
    for part in path.split("."):
        dct = dct[part]
    return dct


def set_path(dct: SettingsDict, path: str, val: Any) -> None:
    """
    Sets a value to a nested dict and automatically creates missing dicts
    should they not exist.

    Calling ``set_path(dct, "a.b", 3)`` is equivalent to ``dict["a"]["b"]
    = 3``.

    Args:
        dct: The dict that should contain the value
        path: The (nested) path, a dot-separated concatenation of keys.
        val: The value to set
    """
    *parts, key = path.split(".")
    for part in parts:
        dct = dct.setdefault(part, {})
    dct[key] = val


def merge_settings(
    options: OptionList, settings: Sequence[LoadedSettings]
) -> MergedSettings:
    """
    Merge a sequence of settings dicts to a flat dict that maps option paths to the
    corresponding option values.

    Args:
        options: The list of all available options.
        settings: A sequence of loaded settings.

    Return:
        A dict that maps option paths to :class:`.LoadedValue` instances.

    The simplified input settings look like this::

        [
            ("loader a", {"spam": 1, "eggs": True}),
            ("loader b", {"spam": 2, "nested": {"x": "test"}}),
        ]

    The simpliefied output looks like this::

        {
            "spam": ("loader b", 2),
            "eggs": ("loader a", True),
            "nested.x": ("loader b", "test"),
        }
    """
    rsettings = settings[::-1]
    merged_settings: MergedSettings = {}
    for option_info in options:
        for loaded_settings in rsettings:
            try:
                value = get_path(loaded_settings.settings, option_info.path)
            except KeyError:
                pass
            else:
                merged_settings[option_info.path] = LoadedValue(
                    value, loaded_settings.meta
                )
                break
    return merged_settings


def update_settings(
    merged_settings: MergedSettings, settings: SettingsDict
) -> MergedSettings:
    """
    Return a copy of *merged_settings* updated with the values from *settings*.

    The loader meta data is not changed.

    Args:
        merged_settings: The merged settnigs dict to be updated.
        settings: The settings dict with additional values.

    Return:
        A copy of the input merged settings updated with the values from *settings*.
    """
    updated: MergedSettings = {}
    for path, (value, meta) in merged_settings.items():
        try:
            value = get_path(settings, path)
        except KeyError:
            pass
        updated[path] = LoadedValue(value, meta)
    return updated


def flat2nested(merged_settings: MergedSettings) -> SettingsDict:
    """
    Convert the flat *merged_settings* to a nested settings dict.
    """
    settings: SettingsDict = {}
    for path, loaded_value in merged_settings.items():
        set_path(settings, path, loaded_value.value)
    return settings
