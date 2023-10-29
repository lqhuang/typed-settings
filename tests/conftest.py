"""
Shared fixtures for all tests.
"""
import dataclasses
import os
import sys
from pathlib import Path
from typing import Callable, Dict, Tuple

import pytest

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

try:
    import pydantic

    class HostPydantic(pydantic.BaseModel):
        """Host settings."""

        name: str
        port: int

    class SettingsPydantic(pydantic.BaseModel):
        """Main settings."""

        host: HostPydantic
        url: str
        default: int = 3

    SETTINGS_CLASSES["pydantic"] = (SettingsPydantic, HostPydantic)
except ImportError:
    # "pydantic" is not available in the nox session "test_no_optionals"
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
    Update ``PATH`` in ``os.environ`` to point to a mocked 1Password CLI.
    """
    here = Path(__file__).parent
    path = os.getenv("PATH")
    path = f"{here}:{path}"
    monkeypatch.setitem(os.environ, "PATH", path)


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
