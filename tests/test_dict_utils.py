import attr
import pytest

from typed_settings import _dict_utils as du


def mkattr(name: str, typ: type) -> attr.Attribute:
    """Creates an Attribute with *name* and *type*."""
    return attr.Attribute(  # type: ignore
        name, attr.NOTHING, None, True, None, None, True, False, type=typ
    )


class TestDeepFields:
    """Tests for _deep_fields()."""

    def test_deep_fields(self):
        @attr.dataclass
        class GrandChild:
            x: int

        @attr.dataclass
        class Child:
            x: float
            y: GrandChild

        @attr.dataclass
        class Parent:
            x: str
            y: Child
            z: str

        fields = du._deep_fields(Parent)
        assert fields == [
            ("x", mkattr("x", str), Parent),
            ("y.x", mkattr("x", float), Child),
            ("y.y.x", mkattr("x", int), GrandChild),
            ("z", mkattr("z", str), Parent),
        ]

    def test_unresolved_types(self):
        """Raise a NameError when types cannot be resolved."""

        @attr.dataclass
        class C:
            name: str
            x: "X"  # type: ignore  # noqa: F821

        with pytest.raises(NameError, match="name 'X' is not defined"):
            du._deep_fields(C)

    def test_direct_recursion(self):
        """
        We do not (and cannot easily) detect recursion.  A NameError is already
        raised when we try to resolve all types.  This is good enough.
        """

        @attr.dataclass
        class Node:
            name: str
            child: "Node"

        with pytest.raises(NameError, match="name 'Node' is not defined"):
            du._deep_fields(Node)

    def test_indirect_recursion(self):
        """
        We cannot (easily) detect indirect recursion but it is an error
        nonetheless.  This is not Dark!
        """

        @attr.dataclass
        class Child:
            name: str
            parent: "Parent"

        @attr.dataclass
        class Parent:
            name: str
            child: "Child"

        with pytest.raises(NameError, match="name 'Child' is not defined"):
            du._deep_fields(Parent)


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
def test_get_path(path, expected):
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


def test_set_path():
    """We can set arbitrary paths, nested dicts will be created as needed."""
    dct = {}
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


def test_dict_merge():
    """Dicts must be merged recursively.  Lists are just overridden."""
    d1 = {
        "1a": 3,
        "1b": {"2a": "spam", "2b": {"3a": "foo"}},
        "1c": [{"2a": 3.14}, {"2b": 34.3}],
        "1d": 4,
    }
    d2 = {
        "1b": {"2a": "eggs", "2b": {"3b": "bar"}},
        "1c": [{"2a": 23}, {"2b": 34.3}],
        "1d": 5,
    }
    du._merge_dicts(d1, d2)
    assert d1 == {
        "1a": 3,
        "1b": {"2a": "eggs", "2b": {"3a": "foo", "3b": "bar"}},
        "1c": [{"2a": 23}, {"2b": 34.3}],
        "1d": 5,
    }
