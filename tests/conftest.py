"""
Shared fixtures for all tests.
"""
import sys
from typing import Any, Callable, Dict, Optional

import attrs
import pytest

from typed_settings import _onepassword
from typed_settings.dict_utils import deep_options
from typed_settings.types import OptionList


# Test with frozen settings.  If it works this way, it will also work with
# mutable settings but not necessarily the other way around.
@attrs.frozen
class Host:
    """Host settings."""

    name: str
    port: int = attrs.field(converter=int)


@attrs.frozen
class Settings:
    """Main settings."""

    host: Host
    url: str
    default: int = 3


@pytest.fixture
def settings_cls() -> type:
    """
    Return an example settings class.
    """
    return Settings


@pytest.fixture
def options(settings_cls: type) -> OptionList:
    """
    Return the option list for the example settings class.
    """
    return deep_options(settings_cls)


@pytest.fixture
def mock_op(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock one password and return example data.
    """

    def get_item(item: str, vault: Optional[str] = None) -> Dict[str, Any]:
        if item == "Test" and vault in {"Test", "", None}:
            return {"username": "spam", "password": "eggs"}
        raise ValueError("op error")  # pragma: no cover

    def get_resource(resource: str) -> str:
        if resource == "op://Test/Test/password":
            return "eggs"
        raise ValueError("op error")  # pragma: no cover

    monkeypatch.setattr(_onepassword, "get_item", get_item)
    monkeypatch.setattr(_onepassword, "get_resource", get_resource)


@pytest.fixture
def unimport(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """
    Return a function for unimporting modules and preventing reimport.

    Needed to test optional dependencies.
    """

    def unimport_module(modname: str) -> None:
        # Remove if already imported
        monkeypatch.delitem(sys.modules, modname, raising=False)
        # Prevent import:
        monkeypatch.setattr(sys, "path", [])

    return unimport_module
