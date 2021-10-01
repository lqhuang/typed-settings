"""
Tests for `typed_settings.attrs.converters`.
"""
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import attr
import pytest

from typed_settings.attrs import option, secret, settings
from typed_settings.attrs.converters import (
    to_attrs,
    to_iterable,
    to_mapping,
    to_tuple,
    to_union,
)
from typed_settings.converters import (
    default_converter,
    from_dict,
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


class TestToAttrs:
    """Tests for `to_attrs`."""

    def test_from_data(self):
        """
        Dicts can be converted to class instances.
        """

        @attr.s
        class C:
            x = attr.ib()
            y = attr.ib()

        converter = to_attrs(C)
        assert converter({"x": 2, "y": 3}) == C(2, 3)

    def test_from_inst(self):
        """
        Existing instances remain unchanged.
        """

        @attr.s
        class C:
            x = attr.ib()
            y = attr.ib()

        inst = C(2, 3)
        converter = to_attrs(C)
        assert converter(inst) is inst

    @pytest.mark.skipif(
        sys.version_info < (3, 6),
        reason="__init_subclass__ is not yet supported",
    )
    def test_from_dict_factory(self):
        """
        Classes can specify a "from_dict" factory that will be called.
        """

        @attr.s
        class Animal:
            type = attr.ib()
            __classes__ = {}

            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__(**kwargs)
                cls.__classes__[cls.__name__] = cls

            @classmethod
            def from_dict(cls, **attribs):
                cls_name = attribs["type"]
                return cls.__classes__[cls_name](**attribs)

        @attr.s(kw_only=True)
        class Cat(Animal):
            x = attr.ib()

        @attr.s(kw_only=True)
        class Dog(Animal):
            x = attr.ib()
            y = attr.ib(default=3)

        converter = to_attrs(Animal)
        assert converter({"type": "Cat", "x": 2}) == Cat(type="Cat", x=2)
        assert converter({"type": "Dog", "x": 2}) == Dog(type="Dog", x=2, y=3)

    def test_invalid_cls(self):
        """
        Raise TypeError when neither a dict nor an instance of the class is
        passed.
        """

        @attr.s
        class C:
            x = attr.ib()
            y = attr.ib()

        converter = to_attrs(C)
        with pytest.raises(TypeError):
            converter([2, 3])


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
            ("Le Spam", LeEnum.spam),
        ],
    )
    def test_to_enum(self, value, expected):
        """
        `to_enum()` accepts Enums, enum values and enum attribute names.
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


class TestToIterable:
    """Tests for `to_iterable`."""

    @pytest.mark.parametrize("cls", [list, set, tuple])
    def test_to_iterable(self, cls):
        """
        An iterable's data and the iterable itself can be converted to
        different types.
        """
        converter = to_iterable(cls, int)
        assert converter(["1", "2", "3"]) == cls([1, 2, 3])


class TestToTuple:
    """Tests for `to_tuple`."""

    @pytest.mark.parametrize("cls", [tuple])
    def test_to_tuple(self, cls):
        """
        Struct-like tuples can contain different data types.
        """
        converter = to_tuple(cls, [int, float, str])
        assert converter(["1", "2.2", "s"]) == cls([1, 2.2, "s"])

    @pytest.mark.parametrize("val", [["1", "2.2", "s"], ["1"]])
    def test_tuple_wrong_input_length(self, val):
        """
        Input data must have exactly as many elements as the tuple definition
        has converters.
        """
        converter = to_tuple(tuple, [int, float])
        with pytest.raises(
            TypeError,
            match="Value must have 2 items but has: {}".format(len(val)),
        ):
            converter(val)


class TestToMapping:
    """Tests for `to_mapping`."""

    @pytest.mark.parametrize("cls", [dict])
    def test_to_dict(self, cls):
        """
        Keys and values of dicts can be converted to (different) types.
        """
        converter = to_mapping(cls, int, float)
        assert converter({"1": "2", "2": "2.5"}) == cls([(1, 2.0), (2, 2.5)])


class TestToUnion:
    """Tests for `to_union`."""

    @pytest.mark.parametrize(
        "types, val, expected_type, expected_val",
        [
            ([type(None), int], None, type(None), None),
            ([type(None), int], "3", int, 3),
            ([int, float], "3", int, 3),
            ([int, float], 3.2, float, 3.2),  # Do not cast 3.2 to int!
            ([int, float], "3.2", float, 3.2),
            ([int, float, str], "3.2s", str, "3.2s"),
            ([int, float, bool, str], "3.2", str, "3.2"),
            ([int, float, bool, str], True, bool, True),
            ([int, float, bool, str], "True", str, "True"),
            ([int, float, bool, str], "", str, ""),
        ],
    )
    def test_to_union(self, types, val, expected_type, expected_val):
        """
        Union data is converted to the first matching type.  If the input data
        already has a valid type, it is returned without conversion.  For
        example, floats will not be converted to ints when the type is
        "Union[int, float]".
        """
        converter = to_union(types)
        result = converter(val)
        assert type(result) is expected_type
        assert result == expected_val

    def test_to_union_error(self):
        """
        A ValueError is raised when "to_union()" cannot convert a value.
        """
        converter = to_union([int])
        with pytest.raises(ValueError):
            converter("spam")


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
        # Enums are parsed from their "value"
        (LeEnum, "Le Eggs", LeEnum.eggs),
        # (Nested) attrs classes
        (S, {"u": "user", "p": "pwd"}, S("user", "pwd")),
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
        (Optional[LeEnum], "Le Spam", LeEnum.spam),
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
