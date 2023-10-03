"""
Shared fixtures for all tests.
"""
import dataclasses
import sys
from typing import Any, Callable, Dict, Optional, Tuple

import pytest

from typed_settings import _onepassword
from typed_settings.cls_utils import deep_options
from typed_settings.types import OptionList


# Test with frozen settings.  If it works this way, it will also work with
# mutable settings but not necessarily the other way around.
@dataclasses.dataclass(frozen=True)
class Host:
    """Host settings."""

    name: str
    port: int


@dataclasses.dataclass(frozen=True)
class Settings:
    """Main settings."""

    host: Host
    url: str
    default: int = 3


SettingsClasses = Tuple[type, type]


SETTINGS_CLASSES: Dict[str, SettingsClasses] = {"dataclasses": (Settings, Host)}

try:
    import attrs

    @attrs.frozen
    class HostAttrs:
        """Host settings."""

        name: str
        port: int

    @attrs.frozen
    class SettingsAttrs:
        """Main settings."""

        host: HostAttrs
        url: str
        default: int = 3

    SETTINGS_CLASSES["attrs"] = (SettingsAttrs, HostAttrs)
except ImportError:
    # "attrs" is not available in the nox session "test_no_optionals"
    pass


@pytest.fixture(params=list(SETTINGS_CLASSES))
def settings_clss(request: pytest.FixtureRequest) -> SettingsClasses:
    """
    Return an example settings class.
    """
    return SETTINGS_CLASSES[request.param]


@pytest.fixture
def options(settings_clss: SettingsClasses) -> OptionList:
    """
    Return the option list for the example settings class.
    """
    main, _host = settings_clss
    return deep_options(main)


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
