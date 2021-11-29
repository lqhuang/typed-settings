import attr
import pytest

from typed_settings.attrs import SECRET, evolve, option, secret, settings


@settings
class S:
    u: str = option()
    p: str = secret()


class TestAttrExtensions:
    """Tests for attrs extensions."""

    @pytest.fixture
    def inst(self):
        return S(u="spam", p="42")

    def test_secret_str(self, inst):
        assert str(inst) == "S(u='spam', p=***)"

    def test_secret_repr_call(self, inst):
        assert repr(inst) == "S(u='spam', p=***)"

    def test_secret_repr_repr(self):
        assert str(SECRET) == "***"


class TestEvolve:
    """
    Tests for `evolve`.

    Copied from attrs and adjusted/reduced.
    """

    @pytest.fixture(scope="session", name="C")
    def fixture_C(self):
        """
        Return a simple but fully featured attrs class with an x and a y
        attribute.
        """
        import attr

        @attr.s
        class C(object):
            x: str
            y: str

        return C

    def test_validator_failure(self):
        """
        TypeError isn't swallowed when validation fails within evolve.
        """

        @settings
        class C(object):
            a: int = option(validator=attr.validators.instance_of(int))

        with pytest.raises(TypeError) as e:
            evolve(C(a=1), a="some string")
        m = e.value.args[0]

        assert m.startswith("'a' must be <class 'int'>")

    def test_private(self):
        """
        evolve() acts as `__init__` with regards to private attributes.
        """

        @settings
        class C(object):
            _a: str

        assert evolve(C(1), a=2)._a == 2

        with pytest.raises(TypeError):
            evolve(C(1), _a=2)

        with pytest.raises(TypeError):
            evolve(C(1), a=3, _a=2)

    def test_non_init_attrs(self):
        """
        evolve() handles `init=False` attributes.
        """

        @settings
        class C(object):
            a: str
            b: int = option(init=False, default=0)

        assert evolve(C(1), a=2).a == 2

    def test_regression_attrs_classes(self):
        """
        evolve() can evolve fields that are instances of attrs classes.

        Regression test for #804
        """

        @settings
        class Child(object):
            param2: str

        @settings
        class Parent(object):
            param1: Child

        obj2a = Child(param2="a")
        obj2b = Child(param2="b")

        obj1a = Parent(param1=obj2a)

        assert Parent(param1=Child(param2="b")) == evolve(obj1a, param1=obj2b)

    def test_recursive(self):
        """
        evolve() recursively evolves nested attrs classes when a dict is
        passed for an attribute.
        """

        @settings
        class N2(object):
            e: int

        @settings
        class N1(object):
            c: N2
            d: int

        @settings
        class C(object):
            a: N1
            b: int

        c1 = C(N1(N2(1), 2), 3)
        c2 = evolve(c1, a={"c": {"e": 23}}, b=42)

        assert c2 == C(N1(N2(23), 2), 42)

    def test_recursive_attrs_classes(self):
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
        assert result.param1 is obj2b
