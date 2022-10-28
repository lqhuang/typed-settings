from typing import List

import attrs
import pytest

from typed_settings import cli_utils, default_converter


@pytest.mark.parametrize(
    "default, path, type, settings, expected",
    [
        (attrs.NOTHING, "a", int, {"a": 3}, 3),
        (attrs.NOTHING, "a", int, {}, attrs.NOTHING),
        (2, "a", int, {}, 2),
        (attrs.Factory(list), "a", List[int], {}, []),
    ],
)
def test_get_default(
    self,
    default: object,
    path: str,
    type: type,
    settings: dict,
    expected: object,
):
    converter = default_converter()
    field = attrs.Attribute(  # type: ignore[call-arg,var-annotated]
        "test", default, None, None, None, None, None, None, type=type
    )
    result = cli_utils.get_default(field, path, settings, converter)
    assert result == expected


def test_get_default_factory(self):
    """
    If the factory "takes self", ``None`` is passed since we do not yet
    have an instance.
    """

    def factory(self) -> str:
        assert self is None
        return "eggs"

    default = attrs.Factory(factory, takes_self=True)
    field = attrs.Attribute(
        "test", default, None, None, None, None, None, None
    )
    result = cli_utils.get_default(field, "a", {}, default_converter())
    assert result == "eggs"
