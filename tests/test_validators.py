"""
Tests for `typed_settings.attrs.validators`.
"""
import attr
import pytest
from attr import fields

from typed_settings.attrs import validators as validator_module
from typed_settings.attrs.validators import ge, gt, le, lt, maxlen


class TestLtLeGeGt:
    """
    Tests for `maxlen`.
    """

    BOUND = 4

    def test_in_all(self):
        """
        validator is in ``__all__``.
        """
        assert all(
            f.__name__ in validator_module.__all__ for f in [lt, le, ge, gt]
        )

    @pytest.mark.parametrize("v", [lt, le, ge, gt])
    def test_retrieve_bound(self, v):
        """
        The configured bound for the comparison can be extracted from the
        Attribute.
        """

        @attr.s
        class Tester:
            value = attr.ib(validator=v(self.BOUND))

        assert fields(Tester).value.validator.bound == self.BOUND

    @pytest.mark.parametrize(
        "v, value",
        [
            (lt, 3),
            (le, 3),
            (le, 4),
            (ge, 4),
            (ge, 5),
            (gt, 5),
        ],
    )
    def test_check_valid(self, v, value):
        """Silent if value {op} bound."""

        @attr.s
        class Tester:
            value = attr.ib(validator=v(self.BOUND))

        Tester(value)  # shouldn't raise exceptions

    @pytest.mark.parametrize(
        "v, value",
        [
            (lt, 4),
            (le, 5),
            (ge, 3),
            (gt, 4),
        ],
    )
    def test_check_invalid(self, v, value):
        """Raise ValueError if value {op} bound."""

        @attr.s
        class Tester:
            value = attr.ib(validator=v(self.BOUND))

        with pytest.raises(ValueError):
            Tester(value)

    @pytest.mark.parametrize("v", [lt, le, ge, gt])
    def test_repr(self, v):
        """
        __repr__ is meaningful.
        """
        nv = v(23)
        assert repr(nv) == "<Validator for x {op} {bound}>".format(
            op=nv.compare_op, bound=23
        )


class TestMaxlen:
    """
    Tests for `maxlen`.
    """

    MAX_LENGTH = 4

    def test_in_all(self):
        """
        validator is in ``__all__``.
        """
        assert maxlen.__name__ in validator_module.__all__

    def test_retrieve_maxlen(self):
        """
        The configured max. length can be extracted from the Attribute
        """

        @attr.s
        class Tester:
            value = attr.ib(validator=maxlen(self.MAX_LENGTH))

        assert fields(Tester).value.validator.max_length == self.MAX_LENGTH

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "foo",
            "spam",
            [],
            list(range(MAX_LENGTH)),
            {"spam": 3, "eggs": 4},
        ],
    )
    def test_check_valid(self, value):
        """
        Silent if len(value) <= maxlen.
        Values can be strings and other iterables.
        """

        @attr.s
        class Tester:
            value = attr.ib(validator=maxlen(self.MAX_LENGTH))

        Tester(value)  # shouldn't raise exceptions

    @pytest.mark.parametrize(
        "value",
        [
            "bacon",
            list(range(6)),
        ],
    )
    def test_check_invalid(self, value):
        """
        Raise ValueError if len(value) > maxlen.
        """

        @attr.s
        class Tester:
            value = attr.ib(validator=maxlen(self.MAX_LENGTH))

        with pytest.raises(ValueError):
            Tester(value)

    def test_repr(self):
        """
        __repr__ is meaningful.
        """
        assert repr(maxlen(23)) == "<maxlen validator for 23>"
