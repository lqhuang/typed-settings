from typing import Any, Dict, Type, Union

import attrs
import pytest

from typed_settings import _dict_utils as du
from typed_settings.types import OptionInfo


def mkattr(name: str, typ: type) -> attrs.Attribute:
    """Creates an Attribute with *name* and *type*."""
    return attrs.Attribute(  # type: ignore
        name, attrs.NOTHING, None, True, None, None, True, False, type=typ
    )


class TestDeepOptions:
    """Tests for _deep_options()."""

    def test_deep_options(self) -> None:
        @attrs.define
        class GrandChild:
            x: int

        @attrs.define
        class Child:
            x: float
            y: GrandChild

        @attrs.define
        class Parent:
            x: str
            y: Child
            z: str

        options = du._deep_options(Parent)
        assert options == [
            OptionInfo("x", mkattr("x", str), Parent),
            OptionInfo("y.x", mkattr("x", float), Child),
            OptionInfo("y.y.x", mkattr("x", int), GrandChild),
            OptionInfo("z", mkattr("z", str), Parent),
        ]

    def test_unresolved_types(self) -> None:
        """Raise a NameError when types cannot be resolved."""

        @attrs.define
        class C:
            name: str
            x: "X"  # type: ignore  # noqa: F821

        with pytest.raises(NameError, match="name 'X' is not defined"):
            du._deep_options(C)

    def test_direct_recursion(self) -> None:
        """
        We do not (and cannot easily) detect recursion.  A NameError is already
        raised when we try to resolve all types.  This is good enough.
        """

        @attrs.define
        class Node:
            name: str
            child: "Node"

        with pytest.raises(NameError, match="name 'Node' is not defined"):
            du._deep_options(Node)

    def test_indirect_recursion(self) -> None:
        """
        We cannot (easily) detect indirect recursion but it is an error
        nonetheless.  This is not Dark!
        """

        @attrs.define
        class Child:
            name: str
            parent: "Parent"

        @attrs.define
        class Parent:
            name: str
            child: "Child"

        with pytest.raises(NameError, match="name 'Child' is not defined"):
            du._deep_options(Parent)


class TestGroupOptions:
    def test_only_scalars(self) -> None:
        """
        If there are only scalar settings, create s single group.
        """

        @attrs.define
        class Parent:
            a: str
            b: int

        opts = du._deep_options(Parent)
        grouped = du._group_options(Parent, opts)
        assert grouped == [
            (Parent, opts[0:2]),
        ]

    def test_nested(self) -> None:
        """
        Create one group for the parent class' attributs and one for each
        nested class.
        """

        @attrs.define
        class Child:
            x: float
            y: int

        @attrs.define
        class Child2:
            x: str
            y: str

        @attrs.define
        class Parent:
            a: int
            b: float
            c: Child
            d: Child2

        opts = du._deep_options(Parent)
        grouped = du._group_options(Parent, opts)
        assert grouped == [
            (Parent, opts[0:2]),
            (Child, opts[2:4]),
            (Child2, opts[4:6]),
        ]

    def test_mixed(self) -> None:
        """
        If the parent class' attributes are not orderd, multiple groups for
        the main class are genererated.
        """

        @attrs.define
        class Child:
            x: float

        @attrs.define
        class Child2:
            x: str

        @attrs.define
        class Parent:
            a: int
            c: Child
            b: float
            d: Child2

        opts = du._deep_options(Parent)
        grouped = du._group_options(Parent, opts)
        assert grouped == [
            (Parent, opts[0:1]),
            (Child, opts[1:2]),
            (Parent, opts[2:3]),
            (Child2, opts[3:4]),
        ]

    def test_duplicate_nested_cls(self) -> None:
        """
        If the same nested class appears multiple times (in direct succession),
        create *different* groups for each attribute.
        """

        @attrs.define
        class Child:
            x: float
            y: int

        @attrs.define
        class Parent:
            b: Child
            c: Child

        opts = du._deep_options(Parent)
        grouped = du._group_options(Parent, opts)
        assert grouped == [
            (Child, opts[0:2]),
            (Child, opts[2:4]),
        ]

    def test_deep_nesting(self) -> None:
        """
        Grouping options only takes top level nested classes into account.
        """

        @attrs.define
        class GrandChild:
            x: int

        @attrs.define
        class Child:
            x: float
            y: GrandChild

        @attrs.define
        class Child2:
            x: GrandChild
            y: GrandChild

        @attrs.define
        class Parent:
            c: Child
            d: Child2

        opts = du._deep_options(Parent)
        grouped = du._group_options(Parent, opts)
        assert grouped == [
            (Child, opts[0:2]),
            (Child2, opts[2:4]),
        ]


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a", 1),
        ("b.c", 2),
        ("b.d.e", 3),
        ("x", KeyError),
        ("b.x", KeyError),
    ],
)
def test_get_path(path: str, expected: Union[int, Type[Exception]]) -> None:
    """Tests for _get_path()."""
    dct = {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3,
            },
        },
    }
    if isinstance(expected, int):
        assert du._get_path(dct, path) == expected
    else:
        pytest.raises(expected, du._get_path, dct, path)


def test_set_path() -> None:
    """We can set arbitrary paths, nested dicts will be created as needed."""
    dct: Dict[str, Any] = {}
    du._set_path(dct, "a", 0)
    du._set_path(dct, "a", 1)
    du._set_path(dct, "b.d.e", 3)
    du._set_path(dct, "b.c", 2)
    assert dct == {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3,
            },
        },
    }


def test_dict_merge() -> None:
    """
    When dicts are merged, merging only applies to keys for options, not
    list or dict values.
    """
    options = [
        OptionInfo("1a", None, None),  # type: ignore
        OptionInfo("1b.2a", None, None),  # type: ignore
        OptionInfo("1b.2b.3a", None, None),  # type: ignore
        OptionInfo("1b.2b.3b", None, None),  # type: ignore
        OptionInfo("1c", None, None),  # type: ignore
        OptionInfo("1d", None, None),  # type: ignore
        OptionInfo("1e", None, None),  # type: ignore
    ]
    d1 = {
        "1a": 3,
        "1b": {"2a": "spam", "2b": {"3a": "foo"}},
        "1c": [{"2a": 3.14}, {"2b": 34.3}],  # Do not merge lists
        "1d": 4,
        "1e": {"default": "default"},  # Do not merge dicts
    }
    d2 = {
        "1b": {"2a": "eggs", "2b": {"3b": "bar"}},
        "1c": [{"2a": 23}, {"2b": 34.3}],
        "1d": 5,
        "1e": {"update": "value"},
    }
    du._merge_dicts(options, d1, d2)
    assert d1 == {
        "1a": 3,
        "1b": {"2a": "eggs", "2b": {"3a": "foo", "3b": "bar"}},
        "1c": [{"2a": 23}, {"2b": 34.3}],
        "1d": 5,
        "1e": {"update": "value"},
    }
