from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest

from typed_settings.attrs import option, secret, settings


class LeEnum(Enum):
    spam = "Le Spam"
    eggs = "Le Eggs"


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

    def test_secret_repr(self, inst):
        assert repr(inst) == "S(u='spam', p=***)"


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
        (S, {"u": "user", "p": "pwd"}, S("user", "pwd")),
        # Container types
        (List[int], [1, 2], [1, 2]),
        (List[S], [{"u": 1, "p": 2}], [S("1", "2")]),
        (Dict[str, int], {"a": 1, "b": 3.1}, {"a": 1, "b": 3}),
        (Dict[str, S], {"a": {"u": "u", "p": "p"}}, {"a": S("u", "p")}),
        (Tuple[str, ...], [1, "2", 3], ("1", "2", "3")),
        (Tuple[int, bool, str], [0, "0", 0], (0, False, "0")),
        # "Special types"
        (Any, 2, 2),
        (Any, "2", "2"),
        (Any, None, None),
        (Optional[str], 1, "1"),
        (Optional[S], None, None),
        (Optional[S], {"u": "u", "p": "p"}, S("u", "p")),
        (Optional[LeEnum], "Le Spam", LeEnum.spam),
        (Union[None, S, List[str]], None, None),
        (Union[None, S, List[str]], {"u": "u", "p": "p"}, S("u", "p")),
        (Union[None, S, List[str]], [1, 2], ["1", "2"]),
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
