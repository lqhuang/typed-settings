"""
Test that all public functions are properly exposed.
"""
import pytest

import typed_settings as ts


@ts.settings
class Settings:
    u: str = ts.option()
    p: str = ts.secret()


@ts.settings(frozen=True)
class FrozenSettings:
    u: str = ts.option()
    p: str = ts.secret()


classes = [Settings, FrozenSettings]


@pytest.mark.parametrize("cls", classes)
def test_load_settings(cls, tmp_path):
    """We can load settings with a class decorated with our decorator."""
    f = tmp_path.joinpath("cfg.toml")
    f.write_text('[test]\nu = "spam"\np = "eggs"\n')
    settings = ts.load_settings(cls, "test", [f])
    assert settings == cls("spam", "eggs")
