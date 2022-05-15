from typing import Any

from attr import fields, has, resolve_types

from .types import OptionInfo, OptionList, SettingsDict


def _deep_options(cls: type) -> OptionList:
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
    cls = resolve_types(cls)
    result = []

    def iter_attribs(r_cls: type, prefix: str) -> None:
        for field in fields(r_cls):
            if field.type is not None and has(field.type):
                iter_attribs(field.type, f"{prefix}{field.name}.")
            else:
                result.append(
                    OptionInfo(f"{prefix}{field.name}", field, r_cls)
                )

    iter_attribs(cls, "")
    return result


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
