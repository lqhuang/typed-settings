from typing import Any, Dict, List, Tuple

from attr import Attribute, fields, has, resolve_types


FieldList = List[Tuple[str, Attribute, type]]


def _deep_fields(cls: type) -> FieldList:
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
                result.append((f"{prefix}{field.name}", field, r_cls))

    iter_attribs(cls, "")
    return result


def _get_path(dct: Dict[str, Any], path: str) -> Any:
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


def _set_path(dct: Dict[str, Any], path: str, val: Any) -> None:
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


def _merge_dicts(d1: Dict[str, Any], d2: Dict[str, Any]) -> None:
    """
    Recursively merges *d2* into *d1*.  *d1* is modified in place.

    Args:
        d1: The base dict that will be modified.
        d2: The dict that will be merged into d1, remains unchanged.

    """
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict):
            _merge_dicts(d1[k], d2[k])
        else:
            d1[k] = v
