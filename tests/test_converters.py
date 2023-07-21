"""
Tests for `typed_settings.attrs.converters`.
"""
import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union

import attrs
import pytest

from typed_settings import converters
from typed_settings._compat import PY_39
from typed_settings.attrs import option, secret, settings


class LeEnum(Enum):
    spam = "Le Spam"
    eggs = "Le Eggs"


@settings
class S:
    u: str = option()
    p: str = secret()


def custom_converter(v: Union[str, Path]) -> Path:
    return Path(v).resolve()


@attrs.frozen
class Child:
    x: int
    y: Path = attrs.field(converter=custom_converter)


@attrs.frozen(kw_only=True)
class Parent:
    child: Child
    a: float
    b: float = attrs.field(default=3.14, validator=attrs.validators.le(2))
    c: LeEnum
    d: datetime
    e: List[Child]
    f: Set[datetime]


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
    def test_to_bool(self, val: str, expected: bool) -> None:
        """
        Only a limited set of values can be converted to a bool.
        """
        assert converters.to_bool(val, bool) is expected

    @pytest.mark.parametrize("val", ["", [], "spam", 2, -1])
    def test_to_bool_error(self, val: Any) -> None:
        """
        In contrast to ``bool()``, `to_bool` does no take Pythons default
        truthyness into account.

        Everything that is not in the sets above raises an error.
        """
        pytest.raises(ValueError, converters.to_bool, val, bool)


class TestToDt:
    """Tests for `to_dt`."""

    def test_from_dt(self) -> None:
        """
        Existing datetimes are returned unchanged.
        """
        dt = datetime(2020, 5, 4, 13, 37)
        result = converters.to_dt(dt, datetime)
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
    def test_from_str(self, value: str, expected: datetime) -> None:
        """
        Existing datetimes are returned unchanged.
        """
        result = converters.to_dt(value, datetime)
        assert result == expected

    def test_invalid_input(self) -> None:
        """
        Invalid inputs raises a TypeError.
        """
        with pytest.raises(TypeError):
            converters.to_dt(3)  # type: ignore


class TestToEnum:
    """Tests for `to_enum`."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (LeEnum.spam, LeEnum.spam),
            ("spam", LeEnum.spam),
        ],
    )
    def test_to_enum(self, value: Any, expected: LeEnum) -> None:
        """
        `to_enum()` accepts Enums and member names.
        """
        assert converters.to_enum(value, LeEnum) is expected


class TestToPath:
    """Tests for `to_path`."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("spam", Path("spam")),
            (Path("eggs"), Path("eggs")),
        ],
    )
    def test_to_path(self, value: Any, expected: Path) -> None:
        assert converters.to_path(value, Path) == expected


class TestToResolvedPath:
    """Tests for `to_resolved_path`."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("spam", Path.cwd().joinpath("spam")),
            (Path("eggs"), Path.cwd().joinpath("eggs")),
        ],
    )
    def test_to_resolved_path(self, value: Any, expected: Path) -> None:
        assert converters.to_resolved_path(value, Path) == expected


@pytest.mark.parametrize("converter", [converters.get_default_cattrs_converter()])
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
        (
            Parent,
            {
                "a": "3.14",
                "b": 1,
                "c": "eggs",
                "d": "2023-05-04T13:37:42+00:00",
                "e": [{"x": 0, "y": "a"}, {"x": 1, "y": "b"}],
                "f": ["2023-05-04T13:37:42+00:00", "2023-05-04T13:37:42+00:00"],
                "child": {"x": 3, "y": "c"},
            },
            Parent(
                a=3.14,
                b=1,
                c=LeEnum.eggs,
                d=datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc),
                e=[
                    Child(0, Path.cwd().joinpath("a")),
                    Child(1, Path.cwd().joinpath("b")),
                ],
                f={datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc)},
                child=Child(3, Path.cwd().joinpath("c")),
            ),
        ),
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
def test_supported_types(
    converter: converters.Converter, typ: type, value: Any, expected: Any
) -> None:
    """
    All oficially supported types can be converted.

    Please create an issue if something is missing here.
    """
    assert converter.structure(value, typ) == expected


@pytest.mark.parametrize("val", [{"foo": 3}, {"opt", "x"}])
def test_unsupported_values(val: dict) -> None:
    """
    An InvalidValueError is raised if a settings dict cannot be converted
    to the settings class.
    """

    @settings
    class Settings:
        opt: int

    converter = converters.default_converter()
    with pytest.raises(TypeError):
        converter.structure(val, Settings)


STRLIST_TEST_DATA = [
    (List[int], [1, 2, 3]),
    (Sequence[int], [1, 2, 3]),
    (Set[int], {1, 2, 3}),
    (FrozenSet[int], frozenset({1, 2, 3})),
    (Tuple[int, ...], (1, 2, 3)),
    (Tuple[int, int, int], (1, 2, 3)),
]

if PY_39:
    STRLIST_TEST_DATA.extend(
        [
            (list[int], [1, 2, 3]),
            (set[int], {1, 2, 3}),
            (tuple[int, ...], (1, 2, 3)),
        ]
    )


@pytest.mark.parametrize(
    "input, kw", [("1:2:3", {"sep": ":"}), ("[1,2,3]", {"fn": json.loads})]
)
@pytest.mark.parametrize("typ, expected", STRLIST_TEST_DATA)
def test_strlist_hook(input: str, kw: dict, typ: type, expected: Any) -> None:
    @settings
    class Settings:
        a: typ  # type: ignore

    converter = converters.get_default_cattrs_converter()
    converters.register_strlist_hook(converter, **kw)
    inst = converter.structure({"a": input}, Settings)
    assert inst == Settings(expected)


def test_strlist_hook_either_arg() -> None:
    """
    Either "sep" OR "fn" can be passed to "register_str_list_hook()"
    """
    converter = converters.get_default_cattrs_converter()
    with pytest.raises(ValueError, match="You may either pass"):
        converters.register_strlist_hook(
            converter, sep=":", fn=lambda v: [v]
        )  # pragma: no cover
