from itertools import groupby
from typing import Any, List, Tuple

import attrs

from .types import OptionInfo, OptionList, SettingsClass, SettingsDict


def _deep_options(cls: SettingsClass) -> OptionList:
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
    cls = attrs.resolve_types(cls)
    result = []

    def iter_attribs(r_cls: type, prefix: str) -> None:
        for field in attrs.fields(r_cls):
            if field.type is not None and attrs.has(field.type):
                iter_attribs(field.type, f"{prefix}{field.name}.")
            else:
                result.append(
                    OptionInfo(f"{prefix}{field.name}", field, r_cls)
                )

    iter_attribs(cls, "")
    return result


def _group_options(
    cls: type, options: OptionList
) -> List[Tuple[type, List[OptionInfo]]]:
    """
    Group (nested) options by parent class.

    If *cls* does not contain nested settings classes, return a single
    group for *cls* with all its options.

    If *cls* only contains nested subclasses, return one group per class
    contain all of that classes (posibly nested) options.

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
    grouped_options = [(g_cls[1], list(g_opts)) for g_cls, g_opts in grouper]
    return grouped_options


def _get_path(dct: SettingsDict, path: str) -> Any:
    """
    Performs a nested dict lookup for *path* and returns the result.

    Calling ``_get_path(dct, "a.b")`` is equivalent to ``dict["a"]["b"]``.

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


def _set_path(dct: SettingsDict, path: str, val: Any) -> None:
    """
    Sets a value to a nested dict and automatically creates missing dicts
    should they not exist.

    Calling ``_set_path(dct, "a.b", 3)`` is equivalent to ``dict["a"]["b"]
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


def _merge_dicts(
    fields: OptionList, base: SettingsDict, updates: SettingsDict
) -> None:
    """
    Merge all paths/keys that are in *fields* from *updates* into *base*.

    The goal is to only merge settings but not settings values that are
    dictionaries.

    Args:
        options: The list of option fields.
        base: Base dictionary that gets modified.
        update: Dictionary from which the updates are read.
    """
    for field in fields:
        try:
            value = _get_path(updates, field.path)
        except KeyError:
            pass
        else:
            _set_path(base, field.path, value)
