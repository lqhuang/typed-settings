"""
Test behavior when no optional dependencies are installed.
"""
import pytest

import typed_settings


try:
    import attrs, click  # noqa: E401, F401, I001

    pytestmark = pytest.mark.skip(reason="Optional dependencies are installed")
except ImportError:
    pass


@pytest.mark.parametrize(
    "dep, name",
    [
        ("attrs", "combine"),
        ("attrs", "evolve"),
        ("attrs", "option"),
        ("attrs", "secret"),
        ("attrs", "settings"),
        ("click", "click_options"),
        ("click", "pass_settings"),
    ],
)
def test_import_error(dep: str, name: str) -> None:
    """
    An ImportError is raised when trying to get an attrib from "typed_settings" that
    requires an optional import.
    """
    with pytest.raises(ImportError) as exc_info:
        getattr(typed_settings, name)
    assert dep in str(exc_info.value)


def test_attribute_not_found() -> None:
    """
    Names not provided by typed settings lead to an attribute error as expected.
    """
    with pytest.raises(AttributeError):
        _ = typed_settings.spam
