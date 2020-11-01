from datetime import datetime
from enum import Enum

import pytest

from typed_settings.attrs import option, secret, settings


class LeEnum(Enum):
    spam = "Le Spam"
    eggs = "Le Eggs"


@settings
class Settings:
    u: str = option()
    p: str = secret()


class TestAttrExtensions:
    """Tests for attrs extensions."""

    @pytest.fixture
    def inst(self):
        return Settings(u="spam", p="42")

    def test_secret_str(self, inst):
        assert str(inst) == "Settings(u='spam', p=***)"

    def test_secret_repr(self, inst):
        assert repr(inst) == "Settings(u='spam', p=***)"


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
        (Settings, {"u": "user", "p": "pwd"}, Settings("user", "pwd")),
        # Container types
        # TODO: List[int]
        # TODO: List[attrs]
        # TODO: Dict[str, str]
        # TODO: Dict[str, attr]
        # TODO: Tuple (list like)
        # TODO: Tuple (struct like)
        # "Special types"
        # TODO: Any
        # TODO: Optional
        # TODO: Union
    ],
)
def test_supported_types(typ, value, expected):
    """
    All oficially supported types can be converted by attrs.

    Please create an issue if something is missing here.
    """

    @settings
    class S:
        opt: typ

    assert S(value).opt == expected
