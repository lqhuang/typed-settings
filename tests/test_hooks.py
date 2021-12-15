"""
Tests for `typed_settings.attrs.hooks`.
"""
import functools
import json
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    FrozenSet,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import attr
import pytest

from typed_settings.attrs.hooks import auto_convert, auto_serialize
from typed_settings.attrs.validators import le


auto_converter = functools.partial(attr.frozen, field_transformer=auto_convert)


class TestTransformHook:
    """
    Tests for `attrs(tranform_value_serializer=func)`
    """

    def test_hook_applied(self):
        """
        The transform hook is applied to all attributes.  Types can be missing,
        explicitly set, or annotated.
        """
        results = []

        def hook(cls, attribs):
            results[:] = [(a.name, a.type) for a in attribs]
            return attribs

        @attr.s(field_transformer=hook)
        class C:
            x = attr.ib()
            y = attr.ib(type=int)
            z: float = attr.ib()

        assert results == [("x", None), ("y", int), ("z", float)]

    def test_hook_applied_auto_attrib(self):
        """
        The transform hook is applied to all attributes and type annotations
        are detected.
        """
        results = []

        def hook(cls, attribs):
            results[:] = [(a.name, a.type) for a in attribs]
            return attribs

        @attr.s(auto_attribs=True, field_transformer=hook)
        class C:
            x: int
            y: str = attr.ib()

        assert results == [("x", int), ("y", str)]

    def test_hook_applied_modify_attrib(self):
        """
        The transform hook can modify attributes.
        """

        def hook(cls, attribs):
            return [a.evolve(converter=a.type) for a in attribs]

        @attr.s(auto_attribs=True, field_transformer=hook)
        class C:
            x: int = attr.ib(converter=int)
            y: float

        c = C(x="3", y="3.14")
        assert c == C(x=3, y=3.14)

    def test_hook_remove_field(self):
        """
        It is possible to remove fields via the hook.
        """

        def hook(cls, attribs):
            return [a for a in attribs if a.type is not int]

        @attr.s(auto_attribs=True, field_transformer=hook)
        class C:
            x: int
            y: float

        assert attr.asdict(C(2.7)) == {"y": 2.7}

    def test_hook_add_field(self):
        """
        It is possible to add fields via the hook.
        """

        def hook(cls, attribs):
            a1 = attribs[0]
            a2 = a1.evolve(name="new")
            return [a1, a2]

        @attr.s(auto_attribs=True, field_transformer=hook)
        class C:
            x: int

        assert attr.asdict(C(1, 2)) == {"x": 1, "new": 2}

    def test_hook_with_inheritance(self):
        """
        The hook receives all fields from base classes.
        """

        def hook(cls, attribs):
            assert [a.name for a in attribs] == ["x", "y"]
            # Remove Base' "x"
            return attribs[1:]

        @attr.s(auto_attribs=True)
        class Base:
            x: int

        @attr.s(auto_attribs=True, field_transformer=hook)
        class Sub(Base):
            y: int

        assert attr.asdict(Sub(2)) == {"y": 2}


class TestAsDictHook:
    def test_asdict(self):
        """
        asdict() calls the hooks in attrs classes and in other datastructures
        like lists or dicts.
        """

        def hook(inst, a, v):
            if isinstance(v, datetime):
                return v.isoformat()
            return v

        @attr.dataclass
        class Child:
            x: datetime
            y: List[datetime]

        @attr.dataclass
        class Parent:
            a: Child
            b: List[Child]
            c: Dict[str, Child]
            d: Dict[str, datetime]

        inst = Parent(
            a=Child(1, [datetime(2020, 7, 1)]),
            b=[Child(2, [datetime(2020, 7, 2)])],
            c={"spam": Child(3, [datetime(2020, 7, 3)])},
            d={"eggs": datetime(2020, 7, 4)},
        )

        result = attr.asdict(inst, value_serializer=hook)
        assert result == {
            "a": {"x": 1, "y": ["2020-07-01T00:00:00"]},
            "b": [{"x": 2, "y": ["2020-07-02T00:00:00"]}],
            "c": {"spam": {"x": 3, "y": ["2020-07-03T00:00:00"]}},
            "d": {"eggs": "2020-07-04T00:00:00"},
        }

    def test_asdict_calls(self):
        """
        The correct instances and attribute names are passed to the hook.
        """
        calls = []

        def hook(inst, a, v):
            calls.append((inst, a.name if a else a, v))
            return v

        @attr.dataclass
        class Child:
            x: int

        @attr.dataclass
        class Parent:
            a: Child
            b: List[Child]
            c: Dict[str, Child]

        inst = Parent(a=Child(1), b=[Child(2)], c={"spam": Child(3)})

        attr.asdict(inst, value_serializer=hook)
        assert calls == [
            (inst, "a", inst.a),
            (inst.a, "x", inst.a.x),
            (inst, "b", inst.b),
            (inst.b[0], "x", inst.b[0].x),
            (inst, "c", inst.c),
            (None, None, "spam"),
            (inst.c["spam"], "x", inst.c["spam"].x),
        ]


class LeEnum(Enum):
    spam = "Le Spam"
    eggs = "Le Eggs"


@auto_converter
class Child:
    x: int = attr.ib()
    y: int = attr.ib(converter=int)


@auto_converter(kw_only=True)
class Parent:
    child: Child
    a: float
    c: LeEnum
    d: datetime
    e: "List[Child]"
    f: Set[datetime]
    b: float = attr.field(default=3.14, validator=le(2))


class TestAutoConvertHook:
    """Tests for the bundled auto-convert hook."""

    DATA = {
        "a": "1",
        "b": "2",
        "c": "spam",
        "d": "2020-05-04T13:37:00",
        "e": [{"x": "23", "y": "42"}],
        "f": ["2020-05-04T13:37:00", "2020-05-04T13:37:00"],
        "child": {"x": 23, "y": "42"},  # Also tests int->str conversion
    }

    @pytest.fixture(scope="class")
    def parent(self):
        return Parent(**self.DATA)

    def test_auto_convert_hook(self, parent):
        """
        The auto_convert hook converts attrs classes, datetimes, enums and
        basic type as well as basic containers.

        This is a basic test to assert that this generally works.

        The tests "test_static_types()" and "test_generic_types()" test the
        full list of supported types.
        """
        assert parent == Parent(
            a=1.0,
            b=2.0,
            c=LeEnum.spam,
            d=datetime(2020, 5, 4, 13, 37),
            e=[Child(23, 42)],
            f={datetime(2020, 5, 4, 13, 37)},
            child=Child(23, 42),
        )

    def test_serialize_from_parent(self, parent):
        """
        The serialize_hook is able to serialize the same types as the
        auto_convert hook.

        The set with duplicate entries of attrib "f" is not the same as in the
        original dict!
        """
        d = attr.asdict(parent, value_serializer=auto_serialize)
        assert d == {
            "a": 1.0,
            "b": 2.0,
            "c": "spam",
            "d": "2020-05-04T13:37:00",
            "e": [{"x": 23, "y": 42}],
            "f": ["2020-05-04T13:37:00"],
            "child": {"x": 23, "y": 42},
        }

    def test_json_roundtrip(self, parent):
        """
        The roundtrip "inst -> JSON -> inst" results in the same instance.
        """
        d = attr.asdict(parent, value_serializer=auto_serialize)
        assert Parent(**json.loads(json.dumps(d))) == parent

    @pytest.mark.parametrize(
        "typ, value, expected",
        [
            (bool, True, True),
            (bool, "True", True),
            (bool, 1, True),
            (bool, False, False),
            (bool, "False", False),
            (bool, 0, False),
            (int, 23, 23),
            (int, "42", 42),
            (float, 3.14, 3.14),
            (float, ".815", 0.815),
            (str, "spam", "spam"),
            (datetime, "2020-05-04T13:37:00", datetime(2020, 5, 4, 13, 37)),
            (LeEnum, "eggs", LeEnum.eggs),
            (Child, {"x": "2", "y": "3"}, Child(2, 3)),
            (Any, 2, 2),
            (Any, "2", "2"),
            (Any, None, None),
        ],
    )
    def test_static_types(self, typ, value, expected):
        """
        All oficially supported types can be converted by attrs.

        Please create an issue if something is missing here.
        """

        @auto_converter
        class C:
            opt: typ

        c = C(value)
        assert c.opt == expected
        if typ is not Any:
            assert type(c.opt) is typ

    @pytest.mark.parametrize(
        "typ, value, expected_val, expected_type",
        [
            (List[int], [1, 2], [1, 2], list),
            (List[Child], [{"x": 1, "y": 2}], [Child(1, 2)], list),
            (
                List[Any],
                [True, None, 23, 3.14, "spam"],
                [True, None, 23, 3.14, "spam"],
                list,
            ),
            (Sequence[int], [1, 2], [1, 2], list),
            (MutableSequence[int], [1, 2], [1, 2], list),
            (Set[int], [1, 2], {1, 2}, set),
            (MutableSet[int], [1, 2], {1, 2}, set),
            (FrozenSet[int], [1, 2], frozenset({1, 2}), frozenset),
            (Tuple[str, ...], [1, "2", 3], ("1", "2", "3"), tuple),
            (Tuple[int, bool, str], [0, "no", 0], (0, False, "0"), tuple),
            (Dict[str, int], {"a": 1, "b": 3.1}, {"a": 1, "b": 3}, dict),
            (
                Dict[str, Child],
                {"a": {"x": "1", "y": "2"}},
                {"a": Child(1, 2)},
                dict,
            ),
            (
                Dict[Tuple[int, int], List[Dict[int, Child]]],
                {
                    ("1", "2"): [
                        {"3": {"x": "4", "y": "5"}},
                        {"6": {"x": "7", "y": "8"}},
                    ],
                },
                {(1, 2): [{3: Child(4, 5)}, {6: Child(7, 8)}]},
                dict,
            ),
            (Mapping[str, int], {"a": 1, "b": 3.1}, {"a": 1, "b": 3}, dict),
            (
                MutableMapping[str, int],
                {"a": 1, "b": 3.1},
                {"a": 1, "b": 3},
                dict,
            ),
            (Optional[str], 1, "1", str),
            (Optional[Child], None, None, type(None)),
            (Optional[Child], {"x": "1", "y": "2"}, Child(1, 2), Child),
            (Optional[LeEnum], "spam", LeEnum.spam, LeEnum),
            (Union[None, Child], None, None, type(None)),
            (Union[None, Child], {"x": "1", "y": "2"}, Child(1, 2), Child),
            (Union[None, List[str]], None, None, type(None)),
            (Union[None, List[str]], [1, 2], ["1", "2"], list),
        ],
    )
    def test_generic_types(self, typ, value, expected_val, expected_type):
        """
        All oficially supported types can be converted by attrs.

        Please create an issue if something is missing here.
        """

        @auto_converter
        class C:
            opt: typ

        c = C(value)
        assert c.opt == expected_val
        assert type(c.opt) is expected_type
