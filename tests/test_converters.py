"""
Tests for `typed_settings.attrs.converters`.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

import pytest

from typed_settings.attrs import option, secret, settings
from typed_settings.converters import (
    default_converter,
    from_dict,
    register_strlist_hook,
    to_bool,
    to_dt,
    to_enum,
    to_path,
)


class LeEnum(Enum):
    spam = "Le Spam"
    eggs = "Le Eggs"


@settings
class S:
    u: str = option()
    p: str = secret()


class TestToDt:
    """Tests for `to_dt`."""

    def test_from_dt(self):
        """
        Existing datetimes are returned unchanged.
        """
        dt = datetime(2020, 5, 4, 13, 37)
        result = to_dt(dt, datetime)
        assert result is dt

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("2020-05-04 13:37:00", datetime(2020, 5, 4, 13, 37)),
            ("2020-05-04T13:37:00", datetime(2020, 5, 4, 13, 37)),
            (
                "2020-05-04T13:37:00Z",
                datetime(2020, 5, 4, 13, 37, tzinfo=timezone.utc),
            ),
            (
                "2020-05-04T13:37:00+00:00",
                datetime(2020, 5, 4, 13, 37, tzinfo=timezone.utc),
            ),
            (
                "2020-05-04T13:37:00+02:00",
                datetime(
                    2020,
                    5,
                    4,
                    13,
                    37,
                    tzinfo=timezone(timedelta(seconds=7200)),
                ),
            ),
        ],
    )
    def test_from_str(self, value, expected):
        """
        Existing datetimes are returned unchanged.
        """
        result = to_dt(value, datetime)
        assert result == expected

    def test_invalid_input(self):
        """
        Invalid inputs raises a TypeError.
        """
        with pytest.raises(TypeError):
            to_dt(3)


class TestToBool:
    """Tests for `to_bool`."""

    @pytest.mark.parametrize(
        "val, expected",
        [
            (True, True),
            ("True", True),
            ("TRUE", True),
            ("true", True),
            ("t", True),
            ("yes", True),
            ("Y", True),
            ("on", True),
            ("1", True),
            (1, True),
            (False, False),
            ("False", False),
            ("false", False),
            ("fAlse", False),
            ("NO", False),
            ("n", False),
            ("off", False),
            ("0", False),
            (0, False),
        ],
    )
    def test_to_bool(self, val, expected):
        """
        Only a limited set of values can be converted to a bool.
        """
        assert to_bool(val, bool) is expected

    @pytest.mark.parametrize("val", ["", [], "spam", 2, -1])
    def test_to_bool_error(self, val):
        """
        In contrast to ``bool()``, `to_bool` does no take Pythons default
        truthyness into account.

        Everything that is not in the sets above raises an error.
        """
        pytest.raises(ValueError, to_bool, val, bool)


class TestToEnum:
    """Tests for `to_enum`."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (LeEnum.spam, LeEnum.spam),
            ("spam", LeEnum.spam),
        ],
    )
    def test_to_enum(self, value, expected):
        """
        `to_enum()` accepts Enums and member names.
        """
        assert to_enum(value, LeEnum) is expected


class TestToPath:
    """Tests for `to_path`."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("spam", Path("spam")),
            (Path("eggs"), Path("eggs")),
        ],
    )
    def test_to_path(self, value, expected):
        assert to_path(value, Path) == expected


@pytest.mark.parametrize(
    "typ, value, expected",
    [
        # Bools can be parsed from a defined set of values
        (bool, True, True),
        (bool, "True", True),
        (bool, "true", True),
        (bool, "yes", True),
        (bool, "1", True),
        (bool, 1, True),
        (bool, False, False),
        (bool, "False", False),
        (bool, "false", False),
        (bool, "no", False),
        (bool, "0", False),
        (bool, 0, False),
        # Other simple types
        (int, 23, 23),
        (int, "42", 42),
        (float, 3.14, 3.14),
        (float, ".815", 0.815),
        (str, "spam", "spam"),
        (datetime, "2020-05-04T13:37:00", datetime(2020, 5, 4, 13, 37)),
        # Enums are parsed from their "key"
        (LeEnum, "eggs", LeEnum.eggs),
        # (Nested) attrs classes
        (S, {"u": "user", "p": "pwd"}, S("user", "pwd")),
        (S, S("user", "pwd"), S("user", "pwd")),
        # Container types
        (List[int], [1, 2], [1, 2]),
        (List[S], [{"u": 1, "p": 2}], [S("1", "2")]),
        (Dict[str, int], {"a": 1, "b": 3.1}, {"a": 1, "b": 3}),
        (Dict[str, S], {"a": {"u": "u", "p": "p"}}, {"a": S("u", "p")}),
        (Tuple[str, ...], [1, "2", 3], ("1", "2", "3")),
        (Tuple[int, bool, str], [0, "0", 0], (0, False, "0")),
        # "Special types"
        (Any, 2, 2),
        (Any, "2", "2"),
        (Any, None, None),
        (Optional[str], 1, "1"),
        (Optional[S], None, None),
        (Optional[S], {"u": "u", "p": "p"}, S("u", "p")),
        (Optional[LeEnum], "spam", LeEnum.spam),
    ],
)
def test_supported_types(typ, value, expected):
    """
    All oficially supported types can be converted by attrs.

    Please create an issue if something is missing here.
    """

    @settings
    class Settings:
        opt: typ

    inst = from_dict({"opt": value}, Settings, default_converter())
    assert inst.opt == expected


STRLIST_TEST_DATA = [
    (List[int], [1, 2, 3]),
    (Sequence[int], [1, 2, 3]),
    (Set[int], {1, 2, 3}),
    (FrozenSet[int], frozenset({1, 2, 3})),
    (Tuple[int, ...], (1, 2, 3)),
    (Tuple[int, int, int], (1, 2, 3)),
]

if sys.version_info[:2] >= (3, 9):
    STRLIST_TEST_DATA.extend(
        [
            (list[int], [1, 2, 3]),
            (set[int], {1, 2, 3}),
            (tuple[int, ...], (1, 2, 3)),  # type: ignore
        ]
    )


@pytest.mark.parametrize(
    "input, kw, typ, expected",
    [
        (input, kw, typ, expected)
        for (input, kw), (typ, expected) in product(
            [("1:2:3", {"sep": ":"}), ("[1,2,3]", {"fn": json.loads})],
            STRLIST_TEST_DATA,
        )
    ],
)
def test_strlist_hook(input, kw, typ, expected):
    @settings
    class Settings:
        a: typ

    converter = default_converter()
    register_strlist_hook(converter, **kw)
    inst = from_dict({"a": input}, Settings, converter)
    assert inst == Settings(expected)
