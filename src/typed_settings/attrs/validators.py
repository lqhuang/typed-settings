"""
Additional attrs validators
"""
import operator

from attr import attrib, attrs


__all__ = [
    "lt",
    "le",
    "ge",
    "gt",
    "maxlen",
]


@attrs(repr=False, frozen=True, slots=True)
class _NumberValidator:
    bound = attrib()
    compare_op = attrib()
    compare_func = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not self.compare_func(value, self.bound):
            raise ValueError(
                "'{name}' must be {op} {bound}: {value}".format(
                    name=attr.name,
                    op=self.compare_op,
                    bound=self.bound,
                    value=value,
                )
            )

    def __repr__(self):
        return "<Validator for x {op} {bound}>".format(
            op=self.compare_op, bound=self.bound
        )


def lt(val):
    """
    A validator that raises `ValueError` if the initializer is called
    with a number larger or equal to *val*.

    :param int val: Exclusive upper bound for values
    """
    return _NumberValidator(val, "<", operator.lt)


def le(val):
    """
    A validator that raises `ValueError` if the initializer is called
    with a number greater than *val*.

    :param int val: Inclusive upper bound for values
    """
    return _NumberValidator(val, "<=", operator.le)


def ge(val):
    """
    A validator that raises `ValueError` if the initializer is called
    with a number smaller than *val*.

    :param int val: Inclusive lower bound for values
    """
    return _NumberValidator(val, ">=", operator.ge)


def gt(val):
    """
    A validator that raises `ValueError` if the initializer is called
    with a number smaller or equal to *val*.

    :param int val: Exclusive lower bound for values
    """
    return _NumberValidator(val, ">", operator.gt)


@attrs(repr=False, frozen=True, slots=True)
class _MaxLengthValidator:
    max_length = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if len(value) > self.max_length:
            raise ValueError(
                "Length of '{name}' must be <= {max}: {len}".format(
                    name=attr.name, max=self.max_length, len=len(value)
                )
            )

    def __repr__(self):
        return "<maxlen validator for {max}>".format(max=self.max_length)


def maxlen(length):
    """
    A validator that raises `ValueError` if the initializer is called
    with a string or iterable that is longer than *length*.

    :param int length: Maximum length of the string or iterable
    """
    return _MaxLengthValidator(length)
