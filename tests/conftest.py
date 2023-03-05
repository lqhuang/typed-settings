from typing import Any, Dict, Optional

import pytest

from typed_settings import _onepassword
from typed_settings.attrs import option, settings
from typed_settings.dict_utils import deep_options
from typed_settings.types import OptionList


# Test with frozen settings.  If it works this way, it will also work with
# mutable settings but not necessarily the other way around.
@settings(frozen=True)
class Host:
    name: str
    port: int = option(converter=int)


@settings(frozen=True)
class Settings:
    host: Host
    url: str
    default: int = 3


@pytest.fixture
def settings_cls() -> type:
    return Settings


@pytest.fixture
def options(settings_cls: type) -> OptionList:
    return deep_options(settings_cls)


@pytest.fixture
def mock_op(monkeypatch: pytest.MonkeyPatch) -> None:
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
