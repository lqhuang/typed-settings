"""
Tests for "typed_settings.dict_utils".
"""
from typing import Any, Dict, Type, Union

import attrs
import pytest

from typed_settings import dict_utils as du
from typed_settings import option, settings, types


def mkattr(name: str, typ: type) -> attrs.Attribute:
    """Creates an Attribute with *name* and *type*."""
    return attrs.Attribute(  # type: ignore
        name,
        attrs.NOTHING,
        None,
        True,
        None,
        None,
        True,
        False,
        type=typ,
        alias=name,
    )


class TestDeepOptions:
    """Tests for deep_options()."""

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

        options = du.deep_options(Parent)
        assert options == (
            types.OptionInfo("x", mkattr("x", str), Parent),
            types.OptionInfo("y.x", mkattr("x", float), Child),
            types.OptionInfo("y.y.x", mkattr("x", int), GrandChild),
            types.OptionInfo("z", mkattr("z", str), Parent),
        )

    def test_unresolved_types(self) -> None:
        """Raise a NameError when types cannot be resolved."""

        @attrs.define
        class C:
            name: str
            x: "X"  # type: ignore  # noqa: F821

        with pytest.raises(NameError, match="name 'X' is not defined"):
            du.deep_options(C)

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
            du.deep_options(Node)

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
            du.deep_options(Parent)

    def test_no_init_no_option(self) -> None:
        """
        No option is generated for an attribute if "init=False".
        """

        @settings
        class Nested1:
            a: int = 0
            nb1: int = option(init=False)

        @settings
        class Nested2:
            a: int = 0
            nb2: int = option(init=False)

        @settings
        class Settings:
            a: int = 0
            na: int = option(init=False)
            n1: Nested1 = Nested1()
            n2: Nested2 = Nested2()

        options = [o.path for o in du.deep_options(Settings)]
        assert options == ["a", "n1.a", "n2.a"]


class TestGroupOptions:
    """
    Tests for "group_options()".
    """

    def test_only_scalars(self) -> None:
        """
        If there are only scalar settings, create s single group.
        """

        @attrs.define
        class Parent:
            a: str
            b: int

        opts = du.deep_options(Parent)
        grouped = du.group_options(Parent, opts)
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

        opts = du.deep_options(Parent)
        grouped = du.group_options(Parent, opts)
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

        opts = du.deep_options(Parent)
        grouped = du.group_options(Parent, opts)
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

        opts = du.deep_options(Parent)
        grouped = du.group_options(Parent, opts)
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

        opts = du.deep_options(Parent)
        grouped = du.group_options(Parent, opts)
        assert grouped == [
            (Child, opts[0:2]),
            (Child2, opts[2:4]),
        ]


def test_iter_settings():
    """
    "iter_settings()" iterates the settings.  It ignores invalid settings keys
    or non-existing settings.
    """
    option_list = [
        types.OptionInfo("a", mkattr("a", int), None),
        types.OptionInfo("b.x", mkattr("x", int), None),
        types.OptionInfo("b.y", mkattr("y", int), None),
        types.OptionInfo("c", mkattr("c", int), None),
    ]
    settings = {
        "a": 0,
        "b": {
            "y": 1,
        },
        "z": 2,
    }
    result = list(du.iter_settings(settings, option_list))
    assert result == [
        ("a", 0),
        ("b.y", 1),
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
    """Tests for get_path()."""
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
        assert du.get_path(dct, path) == expected
    else:
        pytest.raises(expected, du.get_path, dct, path)


def test_set_path() -> None:
    """We can set arbitrary paths, nested dicts will be created as needed."""
    dct: Dict[str, Any] = {}
    du.set_path(dct, "a", 0)
    du.set_path(dct, "a", 1)
    du.set_path(dct, "b.d.e", 3)
    du.set_path(dct, "b.c", 2)
    assert dct == {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3,
            },
        },
    }


def test_merge_settings() -> None:
    """
    When settings are merged, merging only applies to keys for options, not list or
    dict values.
    """
    options = (
        types.OptionInfo("1a", None, None),  # type: ignore
        types.OptionInfo("1b.2a", None, None),  # type: ignore
        types.OptionInfo("1b.2b.3a", None, None),  # type: ignore
        types.OptionInfo("1b.2b.3b", None, None),  # type: ignore
        types.OptionInfo("1c", None, None),  # type: ignore
        types.OptionInfo("1d", None, None),  # type: ignore
        types.OptionInfo("1e", None, None),  # type: ignore
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
    result = du.merge_settings(options, [d1, d2])
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
    result = du.update_settings(merged, {"1b": 2})
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
    result = du.flat2nested(merged)
    assert result == {
        "1a": 3,
        "1b": {"2a": "eggs", "2b": {"3a": "foo", "3b": "bar"}},
        "1c": [{"2a": 23}, {"2b": 34.3}],
        "1d": 5,
        "1e": {"update": "value"},
    }
