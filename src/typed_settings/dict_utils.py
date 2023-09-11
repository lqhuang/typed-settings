"""
Utility functions for working settings dicts and serilizing nested settings.
"""
from itertools import groupby
from typing import Any, Generator, List, Sequence, Tuple, Type, cast

import attrs

from .attrs import METADATA_KEY, _SecretRepr
from .types import (
    SECRETS_TYPES,
    ST,
    LoadedSettings,
    LoadedValue,
    MergedSettings,
    OptionInfo,
    OptionList,
    SettingsDict,
)


__all__ = [
    "deep_options",
    "group_options",
    "iter_settings",
    "get_path",
    "set_path",
    "merge_settings",
    "update_settings",
    "flat2nested",
]


def deep_options(cls: Type[ST]) -> OptionList:
    """
    Recursively iterates *cls* and nested attrs classes and returns a flat
    list of *(path, Attribute, type)* tuples.

    Args:
        cls: The class whose attributes will be listed.

    Returns:
        The flat list of attributes of *cls* and possibly nested attrs classes.
        *path* is a dot (``.``) separted path to the attribute, e.g.
        ``"parent_attr.child_attr.grand_child_attr``.

    Raises:
        NameError: if the type annotations can not be resolved.  This is, e.g.,
          the case when recursive classes are being used.
    """
    cls = attrs.resolve_types(cls)  # type: ignore[type-var]
    result = []

    def iter_attribs(r_cls: type, prefix: str) -> None:
        for field in attrs.fields(r_cls):
            if field.init is False:
                continue
            if field.type is not None and attrs.has(field.type):
                iter_attribs(field.type, f"{prefix}{field.name}.")
            else:
                is_nothing = field.default is attrs.NOTHING
                is_factory = isinstance(field.default, cast(type, attrs.Factory))
                oinfo = OptionInfo(
                    parent_cls=r_cls,
                    path=f"{prefix}{field.name}",
                    cls=field.type,
                    is_secret=(
                        isinstance(field.repr, _SecretRepr)
                        or (
                            isinstance(field.type, type)
                            and issubclass(field.type, SECRETS_TYPES)
                        )
                    ),
                    default=field.default,
                    has_no_default=is_nothing,
                    default_is_factory=is_factory,
                    converter=field.converter,
                    metadata=field.metadata.get(METADATA_KEY, {}),
                )
                result.append(oinfo)

    iter_attribs(cls, "")
    return tuple(result)


def group_options(cls: type, options: OptionList) -> List[Tuple[type, OptionList]]:
    """
    Group (nested) options by parent class.

    If *cls* does not contain nested settings classes, return a single
    group for *cls* with all its options.

    If *cls* only contains nested subclasses, return one group per class
    containing all of that classes (posibly nested) options.

    If *cls* has multiple attributtes with the same nested settings class,
    create one group per attribute.

    If *cls* contains a mix of scalar options and nested options, return a
    mix of both.  Scalar options schould be grouped (on top or bottom) or else
    multiple groups for the main settings class will be created.

    See the tests for details.

    Args:
        cls: The settings class
        options: The list of all options of the settings class.

    Return:
        A list of tuples matching a grouper class to all settings within that
        group.
    """
    group_classes = {
        field.name: (field.type if attrs.has(field.type) else cls)
        for field in attrs.fields(cls)
    }

    def keyfn(o: OptionInfo) -> Tuple[str, type]:
        """
        Group by prefix and also return the corresponding group class.
        """
        base, *remainder = o.path.split(".")
        prefix = base if remainder else ""
        return prefix, group_classes[base]

    grouper = groupby(options, key=keyfn)
    grouped_options = [(g_cls[1], tuple(g_opts)) for g_cls, g_opts in grouper]
    return grouped_options


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
