"""
Tests for "typed_settings.cls_attrs".
"""
import typing as t

import attrs
import pytest

from typed_settings import cli_argparse, cli_click, constants
from typed_settings.cls_attrs import (
    SECRET,
    combine,
    evolve,
    option,
    secret,
    settings,
)


FieldFunc = t.Callable[..., t.Any]


@settings
class S:
    """A simple settings class with the TS aliases for attrs."""

    u: str = option()
    p: str = secret()


class TestFieldExtensions:
    """Tests for attrs field extensions."""

    @pytest.fixture
    def inst(self) -> S:
        """
        Return an instance of "S".
        """
        return S(u="spam", p="42")

    @pytest.fixture(params=[option, secret])
    def field_func(self, request: pytest.FixtureRequest) -> FieldFunc:
        """
        Generate two test params, one for "option", one for "secret".
        """
        return request.param

    def test_secret_repr_repr(self) -> None:
        """
        Secrets are represented by "***" and not printed directly.
        """
        assert str(SECRET) == "***"

    def test_secret_str(self, inst: S) -> None:
        """
        Values of secrets are obfuscated in the string repr.
        """
        assert str(inst) == "S(u='spam', p='*******')"

    def test_secret_repr_call(self, inst: S) -> None:
        """
        Values of secrets are obfuscated in the repr.
        """
        assert repr(inst) == "S(u='spam', p='*******')"

    def test_meta_not_set(self, field_func: FieldFunc) -> None:
        """
        The "help" and "click" entries are always present in the metadata,
        even if they are not explicitly set.
        """

        @settings
        class S:
            o: str = field_func()

        field = attrs.fields(S).o
        assert field.metadata == {
            constants.METADATA_KEY: {
                "help": None,
                cli_click.METADATA_KEY: {"help": None},
                cli_argparse.METADATA_KEY: {"help": None},
            },
        }

    def test_meta_help(self, field_func: FieldFunc) -> None:
        """
        "help" is stored directly in the meta and in the CLI options dicts.
        """

        @settings
        class S:
            o: str = field_func(help="spam")

        field = attrs.fields(S).o
        assert field.metadata == {
            constants.METADATA_KEY: {
                "help": "spam",
                cli_click.METADATA_KEY: {"help": "spam"},
                cli_argparse.METADATA_KEY: {"help": "spam"},
            },
        }

    def test_meta_help_override(self, field_func: FieldFunc) -> None:
        @settings
        class S:
            o: str = field_func(help="spam", click={"help": "eggs"})

        field = attrs.fields(S).o
        assert field.metadata == {
            constants.METADATA_KEY: {
                "help": "spam",
                cli_click.METADATA_KEY: {"help": "eggs"},
                cli_argparse.METADATA_KEY: {"help": "spam"},
            },
        }

    def test_meta_click_params(self, field_func: FieldFunc) -> None:
        """
        "help" can be overwritten via "click" options.
        """

        @settings
        class S:
            o: str = field_func(click={"param_decls": ("-o",)})

        field = attrs.fields(S).o
        assert field.metadata == {
            constants.METADATA_KEY: {
                "help": None,
                cli_click.METADATA_KEY: {"help": None, "param_decls": ("-o",)},
                cli_argparse.METADATA_KEY: {"help": None},
            },
        }

    def test_meta_merge(self, field_func: FieldFunc) -> None:
        """
        If metadata is already present, it is not overridden.
        """

        @settings
        class S:
            o: str = field_func(
                metadata={"spam": "eggs"},
                help="halp!",
                click={"param_decls": ("-o",)},
            )

        field = attrs.fields(S).o
        assert field.metadata == {
            "spam": "eggs",
            constants.METADATA_KEY: {
                "help": "halp!",
                cli_click.METADATA_KEY: {"help": "halp!", "param_decls": ("-o",)},
                cli_argparse.METADATA_KEY: {"help": "halp!"},
            },
        }


class TestEvolve:
    """
    Tests for `evolve`.

    Copied from attrs and adjusted/reduced.
    """

    def test_validator_failure(self) -> None:
        """
        TypeError isn't swallowed when validation fails within evolve.
        """

        @settings
        class C:
            a: int = option(validator=attrs.validators.instance_of(int))

        with pytest.raises(TypeError) as e:
            evolve(C(a=1), a="some string")
        m = e.value.args[0]

        assert m.startswith("'a' must be <class 'int'>")

    def test_private(self) -> None:
        """
        evolve() acts as `__init__` with regards to private attributes.
        """

        @settings
        class C:
            _a: str

        assert evolve(C(1), a=2)._a == 2  # type: ignore

        with pytest.raises(TypeError):
            evolve(C(1), _a=2)  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            evolve(C(1), a=3, _a=2)  # type: ignore[arg-type]

    def test_non_init_attrs(self) -> None:
        """
        evolve() handles `init=False` attributes.
        """

        @settings
        class C:
            a: str
            b: int = option(init=False, default=0)

        assert evolve(C(1), a=2).a == 2  # type: ignore

    def test_regression_attrs_classes(self) -> None:
        """
        evolve() can evolve fields that are instances of attrs classes.

        Regression test for #804
        """

        @settings
        class Child:
            param2: str

        @settings
        class Parent:
            param1: Child

        obj2a = Child(param2="a")
        obj2b = Child(param2="b")

        obj1a = Parent(param1=obj2a)

        assert Parent(param1=Child(param2="b")) == evolve(obj1a, param1=obj2b)

    def test_recursive(self) -> None:
        """
        evolve() recursively evolves nested attrs classes when a dict is
        passed for an attribute.
        """

        @settings
        class N2:
            e: int

        @settings
        class N1:
            c: N2
            d: int

        @settings
        class C:
            a: N1
            b: int

        c1 = C(N1(N2(1), 2), 3)
        c2 = evolve(c1, a={"c": {"e": 23}}, b=42)

        assert c2 == C(N1(N2(23), 2), 42)

    def test_recursive_attrs_classes(self) -> None:
        """
        evolve() can evolve fields that are instances of attrs classes.
        """

        @settings
        class Child:
            param2: str

        @settings
        class Parent:
            param1: Child

        obj2a = Child(param2="a")
        obj2b = Child(param2="b")

        obj1a = Parent(param1=obj2a)

        result = evolve(obj1a, param1=obj2b)
        assert result.param1 is obj2b  # type: ignore


class TestCombine:
    """
    Tests for "combine()".
    """

    def test_combine(self) -> None:
        """
        A base class and nested classes can be combined into a single, composed
        class.
        """

        @attrs.define
        class Nested1:
            a: str = ""

        @attrs.define
        class Nested2:
            a: str = ""

        # Dynamic composition
        @attrs.define
        class BaseSettings:
            a: str = ""

        Composed = combine(
            "Composed",
            BaseSettings,
            {"n1": Nested1(), "n2": Nested2()},
        )
        assert Composed.__name__ == "Composed"
        assert [
            (f.name, f.type, f.default) for f in attrs.fields(Composed)  # type: ignore
        ] == [
            ("a", str, ""),
            ("n1", Nested1, Nested1()),
            ("n2", Nested2, Nested2()),
        ]

    def test_duplicate_attrib(self) -> None:
        """
        Raise an error if a nested class placed with attrib name that is
        already used by the base class.
        """

        @attrs.define
        class Nested1:
            a: str = ""

        # Dynamic composition
        @attrs.define
        class BaseSettings:
            a: str = ""

        with pytest.raises(ValueError, match="Duplicate attribute for nested class: a"):
            combine(
                "Composed",
                BaseSettings,
                {"a": Nested1()},
            )

    def test_docstring(self) -> None:
        """
        The created class copies the costring from the base class.
        """

        @attrs.define
        class Nested1:
            a: str = ""

        # Dynamic composition
        @attrs.define
        class BaseSettings:
            """Le doc string."""

            a: str = ""

        Composed = combine("Composed", BaseSettings, {"n1": Nested1()})
        assert Composed.__doc__ == "Le doc string."
