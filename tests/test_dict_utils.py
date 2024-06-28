"""
Tests for "typed_settings.dict_utils".
"""

import dataclasses
from typing import Any, Dict, List, Type, Union

import attrs
import pytest

from typed_settings import dict_utils, types


def test_iter_settings():
    """
    "iter_settings()" iterates the settings.  It ignores invalid settings keys
    or non-existing settings.
    """

    @dataclasses.dataclass
    class ListSettings:
        w: int

    option_infos = [
        types.OptionInfo(
            parent_cls=type,
            path=path,
            cls=int,
            default=attrs.NOTHING,
            has_no_default=True,
            default_is_factory=False,
        )
        for path in ["a", "b.x", "b.y", "c"]
    ]
    option_infos.append(
        types.OptionInfo(
            parent_cls=type,
            path="u",
            cls=List[int],
            default=attrs.NOTHING,
            has_no_default=True,
            default_is_factory=False,
        )
    )
    option_infos.append(
        types.OptionInfo(
            parent_cls=type,
            path="v",
            cls=List[ListSettings],
            default=attrs.NOTHING,
            has_no_default=True,
            default_is_factory=False,
        )
    )
    option_infos.append(
        types.OptionInfo(
            parent_cls=type,
            path="x",
            cls=List[str],
            default=attrs.NOTHING,
            has_no_default=True,
            default_is_factory=False,
        )
    )
    settings = {
        "a": 0,
        "b": {
            "y": 1,
        },
        "z": 2,
        "u": [4, 5],
        "v": [
            {
                "w": 6,
            }
        ],
        "x": "hello:world",
    }
    result = list(dict_utils.iter_settings(settings, option_infos))
    assert result == [
        ("a", 0),
        ("b.y", 1),
        ("u.0", 4),
        ("u.1", 5),
        ("v.0.w", 6),
        ("x", "hello:world"),
    ]


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a", 1),
        ("b.c", 2),
        ("b.d.e", 3),
        ("x", KeyError),
        ("b.x", KeyError),
        ("u.0", 4),
        ("u.1", 5),
        ("u.2", IndexError),
    ],
)
def test_get_path(path: str, expected: Union[int, Type[Exception]]) -> None:
    """Tests for get_path()."""
    dct = {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3,
            },
        },
        "u": [4, 5],
    }
    if isinstance(expected, int):
        assert dict_utils.get_path(dct, path) == expected
    else:
        pytest.raises(expected, dict_utils.get_path, dct, path)


def test_set_path() -> None:
    """We can set arbitrary paths, nested dicts will be created as needed."""
    dct: Dict[str, Any] = {}
    dict_utils.set_path(dct, "a", 0)
    dict_utils.set_path(dct, "a", 1)
    dict_utils.set_path(dct, "b.d.e", 3)
    dict_utils.set_path(dct, "b.c", 2)
    dict_utils.set_path(dct, "u.0", 4)
    dict_utils.set_path(dct, "u.1", 5)
    dict_utils.set_path(dct, "u", [None, None])
    dict_utils.set_path(dct, "u.1", 5)
    dict_utils.set_path(dct, "v", [{}])
    dict_utils.set_path(dct, "v.0.w", 6)
    assert dct == {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3,
            },
        },
        "u": [None, 5],
        "v": [{"w": 6}],
    }


def test_merge_settings() -> None:
    """
    When settings are merged, merging only applies to keys for options, not list or
    dict values.
    """
    option_infos = tuple(
        types.OptionInfo(
            parent_cls=type,
            path=path,
            cls=tuple,
            default=attrs.NOTHING,
            has_no_default=True,
            default_is_factory=False,
        )
        for path in ["1a", "1b.2a", "1b.2b.3a", "1b.2b.3b", "1c", "1d", "1e"]
    )
    d1 = types.LoadedSettings(
        {
            "1a": 3,
            "1b": {"2a": "spam", "2b": {"3a": "foo"}},
            "1c": [{"2a": 3.14}, {"2b": 34.3}],  # Do not merge lists
            "1d": 4,
            "1e": {"default": "default"},  # Do not merge dicts
        },
        types.LoaderMeta("l1"),
    )
    d2 = types.LoadedSettings(
        {
            "1b": {"2a": "eggs", "2b": {"3b": "bar"}},
            "1c": [{"2a": 23}, {"2b": 34.3}],
            "1d": 5,
            "1e": {"update": "value"},
        },
        types.LoaderMeta("l2"),
    )
    result = dict_utils.merge_settings(option_infos, [d1, d2])
    assert result == {
        "1a": types.LoadedValue(3, types.LoaderMeta("l1")),
        "1b.2a": types.LoadedValue("eggs", types.LoaderMeta("l2")),
        "1b.2b.3a": types.LoadedValue("foo", types.LoaderMeta("l1")),
        "1b.2b.3b": types.LoadedValue("bar", types.LoaderMeta("l2")),
        "1c": types.LoadedValue([{"2a": 23}, {"2b": 34.3}], types.LoaderMeta("l2")),
        "1d": types.LoadedValue(5, types.LoaderMeta("l2")),
        "1e": types.LoadedValue({"update": "value"}, types.LoaderMeta("l2")),
    }


def test_update_settings() -> None:
    """
    When updating settings, the input remains unmodified and an updated dopy is
    returned.
    """
    merged = {
        "1a": types.LoadedValue(1, types.LoaderMeta("l1")),
        "1b": types.LoadedValue(1, types.LoaderMeta("l1")),
        "1c": types.LoadedValue(1, types.LoaderMeta("l1")),
    }
    result = dict_utils.update_settings(merged, {"1b": 2})
    assert merged == {
        "1a": types.LoadedValue(1, types.LoaderMeta("l1")),
        "1b": types.LoadedValue(1, types.LoaderMeta("l1")),
        "1c": types.LoadedValue(1, types.LoaderMeta("l1")),
    }
    assert result == {
        "1a": types.LoadedValue(1, types.LoaderMeta("l1")),
        "1b": types.LoadedValue(2, types.LoaderMeta("l1")),
        "1c": types.LoadedValue(1, types.LoaderMeta("l1")),
    }


def test_flat2nested() -> None:
    """
    "flat2nested" converts a flat dict "option_path: value" to a nested dict.  The
    keys no longer contain dots.
    """
    merged = {
        "1a": types.LoadedValue(3, types.LoaderMeta("l1")),
        "1b.2a": types.LoadedValue("eggs", types.LoaderMeta("l2")),
        "1b.2b.3a": types.LoadedValue("foo", types.LoaderMeta("l1")),
        "1b.2b.3b": types.LoadedValue("bar", types.LoaderMeta("l2")),
        "1c": types.LoadedValue([{"2a": 23}, {"2b": 34.3}], types.LoaderMeta("l2")),
        "1d": types.LoadedValue(5, types.LoaderMeta("l2")),
        "1e": types.LoadedValue({"update": "value"}, types.LoaderMeta("l2")),
    }
    result = dict_utils.flat2nested(merged)
    assert result == {
        "1a": 3,
        "1b": {"2a": "eggs", "2b": {"3a": "foo", "3b": "bar"}},
        "1c": [{"2a": 23}, {"2b": 34.3}],
        "1d": 5,
        "1e": {"update": "value"},
    }
