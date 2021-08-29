import pytest

from typed_settings._dict_utils import _deep_options
from typed_settings.attrs import option, settings
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
    return _deep_options(settings_cls)
