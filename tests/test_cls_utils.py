"""
Tests for "typed_settings.cls_utils".
"""
import dataclasses
from typing import Callable, Optional

import attrs
import pydantic
import pytest

from typed_settings import cls_utils, types


@attrs.define
class AttrsCls:
    """
    Test class for "attrs".
    """

    x: int = 0


@pytest.mark.parametrize("cls", [AttrsCls])
def test_deep_options(cls: type) -> None:
    """
    "deep_options()" converts similar classes of all suported class libs to the same
    result.
    """
    option_list = cls_utils.deep_options(cls)
    assert option_list == (
        types.OptionInfo(
            parent_cls=cls,
            path="x",
            cls=int,
            default=0,
            has_no_default=False,
            default_is_factory=False,
        ),
    )


def test_deep_options_typerror() -> None:
    """
    A TypeError is raised for non supported classes.
    """

    class C:
        x: int = 0

    pytest.raises(TypeError, cls_utils.deep_options, C)


class TestGroupOptions:
    """
    Tests for "group_options()".
    """

    def test_typerror(self) -> None:
        """
        A TypeError is raised for non supported classes.
        """

        class C:
            x: int = 0

        pytest.raises(TypeError, cls_utils.group_options, [])

    def test_only_scalars(self) -> None:
        """
        If there are only scalar settings, create s single group.
        """

        @attrs.define
        class Parent:
            a: str
            b: int

        opts = cls_utils.deep_options(Parent)
        grouped = cls_utils.group_options(Parent, opts)
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

        opts = cls_utils.deep_options(Parent)
        grouped = cls_utils.group_options(Parent, opts)
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

        opts = cls_utils.deep_options(Parent)
        grouped = cls_utils.group_options(Parent, opts)
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

        opts = cls_utils.deep_options(Parent)
        grouped = cls_utils.group_options(Parent, opts)
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

        opts = cls_utils.deep_options(Parent)
        grouped = cls_utils.group_options(Parent, opts)
        assert grouped == [
            (Child, opts[0:2]),
            (Child2, opts[2:4]),
        ]


class TestAttrs:
    """Tests for attrs classes."""

    def test_check_true(self) -> None:
        """
        "check()" detects "attrs" classes.
        """

        @attrs.define
        class C:
            x: int

        assert cls_utils.Attrs.check(C)

    def test_check_false(self) -> None:
        """
        "check()" only detects "attrs" classes.
        """

        class C:
            x: int

        assert not cls_utils.Attrs.check(C)

    def test_check_not_installed(self, unimport: Callable[[str], None]) -> None:
        """
        "check()" returns ``False`` if attrs is not installed.
        """

        @attrs.define
        class C:
            x: int

        unimport("attrs")

        assert not cls_utils.Attrs.check(C)

    def test_iter_fields(self) -> None:
        """
        "iter_fields()" yields an option info for all options, including nested
        classes.
        """

        def factory_fn() -> Optional[int]:
            return None  # pragma: no cover

        @attrs.define
        class GrandChild:
            x: Optional[int] = attrs.field(factory=factory_fn)

        @attrs.define
        class Child:
            x: "float"  # Test resolving types
            y: GrandChild

        @attrs.define
        class Parent:
            x: str
            y: Child
            z: str = "default"

        option_infos = cls_utils.Attrs.iter_fields(Parent)
        assert option_infos == (
            types.OptionInfo(
                parent_cls=Parent,
                path="x",
                cls=str,
                default=attrs.NOTHING,
                has_no_default=True,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=Child,
                path="y.x",
                cls=float,
                default=attrs.NOTHING,
                has_no_default=True,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=GrandChild,
                path="y.y.x",
                cls=Optional[int],  # type: ignore[arg-type]
                default=attrs.Factory(factory_fn),
                has_no_default=False,
                default_is_factory=True,
            ),
            types.OptionInfo(
                parent_cls=Parent,
                path="z",
                cls=str,
                default="default",
                has_no_default=False,
                default_is_factory=False,
            ),
        )

    def test_unresolved_types(self) -> None:
        """Raise a NameError when types cannot be resolved."""

        @attrs.define
        class C:
            name: str
            x: "X"  # type: ignore  # noqa: F821

        with pytest.raises(NameError, match="name 'X' is not defined"):
            cls_utils.Attrs.iter_fields(C)

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
            cls_utils.Attrs.iter_fields(Node)

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
            cls_utils.Attrs.iter_fields(Parent)

    def test_no_init_no_option(self) -> None:
        """
        No option is generated for an attribute if "init=False".
        """

        @attrs.frozen
        class Nested1:
            a: int = 0
            nb1: int = attrs.field(init=False)

        @attrs.frozen
        class Nested2:
            a: int = 0
            nb2: int = attrs.field(init=False)

        @attrs.frozen
        class Settings:
            a: int = 0
            na: int = attrs.field(init=False)
            n1: Nested1 = Nested1()
            n2: Nested2 = Nested2()

        options = [o.path for o in cls_utils.Attrs.iter_fields(Settings)]
        assert options == ["a", "n1.a", "n2.a"]

    def test_fields_to_parent_classes(self) -> None:
        """
        If there are only scalar settings, create s single group.
        """

        @attrs.define
        class Child1:
            x: int

        @attrs.define
        class Child2:
            x: float

        @attrs.define
        class Parent:
            a: str
            b: Child1
            c: Child2
            d: int

        result = cls_utils.Attrs.fields_to_parent_classes(Parent)
        assert result == {
            "a": Parent,
            "b": Child1,
            "c": Child2,
            "d": Parent,
        }


class TestDataclasses:
    """Tests for dataclasses."""

    def test_check_true(self) -> None:
        """
        "check()" detects dataclasses.
        """

        @dataclasses.dataclass
        class C:
            x: int

        assert cls_utils.Dataclasses.check(C)

    def test_check_false(self) -> None:
        """
        "check()" only detects dataclasses.
        """

        class C:
            x: int

        assert not cls_utils.Dataclasses.check(C)

    def test_iter_fields(self) -> None:
        """
        "iter_fields()" yields an option info for all options, including nested
        classes.
        """

        @dataclasses.dataclass
        class GrandChild:
            x: Optional[int] = None

        @dataclasses.dataclass
        class Child:
            x: "float"  # Test resolving types
            y: GrandChild

        @dataclasses.dataclass
        class Parent:
            x: str
            y: Child
            z: str = "default"

        option_infos = cls_utils.Dataclasses.iter_fields(Parent)
        assert option_infos == (
            types.OptionInfo(
                parent_cls=Parent,
                path="x",
                cls=str,
                default=dataclasses.MISSING,
                has_no_default=True,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=Child,
                path="y.x",
                cls=float,
                default=dataclasses.MISSING,
                has_no_default=True,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=GrandChild,
                path="y.y.x",
                cls=Optional[int],  # type: ignore[arg-type]
                default=None,
                has_no_default=False,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=Parent,
                path="z",
                cls=str,
                default="default",
                has_no_default=False,
                default_is_factory=False,
            ),
        )

    def test_unresolved_types(self) -> None:
        """Raise a NameError when types cannot be resolved."""

        @dataclasses.dataclass
        class C:
            name: str
            x: "X"  # type: ignore  # noqa: F821

        with pytest.raises(NameError, match="name 'X' is not defined"):
            cls_utils.Dataclasses.iter_fields(C)

    def test_direct_recursion(self) -> None:
        """
        We do not (and cannot easily) detect recursion.  A NameError is already
        raised when we try to resolve all types.  This is good enough.
        """

        @dataclasses.dataclass
        class Node:
            name: str
            child: "Node"

        with pytest.raises(NameError, match="name 'Node' is not defined"):
            cls_utils.Dataclasses.iter_fields(Node)

    def test_indirect_recursion(self) -> None:
        """
        We cannot (easily) detect indirect recursion but it is an error
        nonetheless.  This is not Dark!
        """

        @dataclasses.dataclass
        class Child:
            name: str
            parent: "Parent"

        @dataclasses.dataclass
        class Parent:
            name: str
            child: "Child"

        with pytest.raises(NameError, match="name 'Child' is not defined"):
            cls_utils.Dataclasses.iter_fields(Parent)

    def test_no_init_no_option(self) -> None:
        """
        No option is generated for an attribute if "init=False".
        """

        @dataclasses.dataclass(frozen=True)
        class Nested1:
            a: int = 0
            nb1: int = dataclasses.field(default=0, init=False)

        @dataclasses.dataclass(frozen=True)
        class Nested2:
            a: int = 0
            nb2: int = dataclasses.field(default=0, init=False)

        @dataclasses.dataclass
        class Settings:
            a: int = 0
            na: int = dataclasses.field(init=False)
            n1: Nested1 = Nested1()  # noqa: RUF009
            n2: Nested2 = Nested2()  # noqa: RUF009

        options = [o.path for o in cls_utils.Dataclasses.iter_fields(Settings)]
        assert options == ["a", "n1.a", "n2.a"]

    def test_fields_to_parent_classes(self) -> None:
        """
        If there are only scalar settings, create s single group.
        """

        @dataclasses.dataclass
        class Child1:
            x: int

        @dataclasses.dataclass
        class Child2:
            x: float

        @dataclasses.dataclass
        class Parent:
            a: str
            b: Child1
            c: Child2
            d: int

        result = cls_utils.Dataclasses.fields_to_parent_classes(Parent)
        assert result == {
            "a": Parent,
            "b": Child1,
            "c": Child2,
            "d": Parent,
        }


class TestPydantic:
    """Tests for Pydantic classes."""

    def test_check_true(self) -> None:
        """
        "check()" detects dataclasses.
        """

        class C(pydantic.BaseModel):
            x: int

        assert cls_utils.Pydantic.check(C)

    def test_check_false(self) -> None:
        """
        "check()" only detects dataclasses.
        """

        class C:
            x: int

        assert not cls_utils.Pydantic.check(C)

    def test_check_not_installed(self, unimport: Callable[[str], None]) -> None:
        """
        "check()" returns ``False`` if Pydantic is not installed.
        """

        class C(pydantic.BaseModel):
            x: int

        unimport("pydantic")

        assert not cls_utils.Pydantic.check(C)

    def test_iter_fields(self) -> None:
        """
        "iter_fields()" yields an option info for all options, including nested
        classes.
        """
        from pydantic_core._pydantic_core import PydanticUndefined

        class GrandChild(pydantic.BaseModel):
            x: Optional[int] = None

        class Child(pydantic.BaseModel):
            x: "float"  # Test resolving types
            y: GrandChild

        class Parent(pydantic.BaseModel):
            x: str
            y: Child
            z: str = "default"

        option_infos = cls_utils.Pydantic.iter_fields(Parent)
        assert option_infos == (
            types.OptionInfo(
                parent_cls=Parent,
                path="x",
                cls=str,
                default=PydanticUndefined,
                has_no_default=True,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=Child,
                path="y.x",
                cls=float,
                default=PydanticUndefined,
                has_no_default=True,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=GrandChild,
                path="y.y.x",
                cls=Optional[int],  # type: ignore[arg-type]
                default=None,
                has_no_default=False,
                default_is_factory=False,
            ),
            types.OptionInfo(
                parent_cls=Parent,
                path="z",
                cls=str,
                default="default",
                has_no_default=False,
                default_is_factory=False,
            ),
        )

    @pytest.mark.skip(reason="Types are not resolved for Pydantic")
    def test_unresolved_types(self) -> None:  # pragma: no cover
        """Raise a NameError when types cannot be resolved."""

        class C(pydantic.BaseModel):
            name: str
            x: "X"  # type: ignore  # noqa: F821

        with pytest.raises(NameError, match="name 'X' is not defined"):
            cls_utils.Pydantic.iter_fields(C)

    @pytest.mark.skip(reason="RecursionError")
    def test_direct_recursion(self) -> None:  # pragma: no cover
        """
        We do not (and cannot easily) detect recursion.  A NameError is already
        raised when we try to resolve all types.  This is good enough.
        """

        class Node(pydantic.BaseModel):
            name: str
            child: "Node"

        with pytest.raises(NameError, match="name 'Node' is not defined"):
            cls_utils.Pydantic.iter_fields(Node)

    @pytest.mark.skip(reason="RecursionError")
    def test_indirect_recursion(self) -> None:  # pragma: no cover
        """
        We cannot (easily) detect indirect recursion but it is an error
        nonetheless.  This is not Dark!
        """

        class Child(pydantic.BaseModel):
            name: str
            parent: "Parent"

        class Parent(pydantic.BaseModel):
            name: str
            child: "Child"

        with pytest.raises(NameError, match="name 'Child' is not defined"):
            cls_utils.Pydantic.iter_fields(Parent)

    def test_fields_to_parent_classes(self) -> None:
        """
        If there are only scalar settings, create s single group.
        """

        class Child1(pydantic.BaseModel):
            x: int

        class Child2(pydantic.BaseModel):
            x: float

        class Parent(pydantic.BaseModel):
            a: str
            b: Child1
            c: Child2
            d: int

        result = cls_utils.Pydantic.fields_to_parent_classes(Parent)
        assert result == {
            "a": Parent,
            "b": Child1,
            "c": Child2,
            "d": Parent,
        }
