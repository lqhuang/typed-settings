"""
Test that all public functions are properly exposed.
"""
import pytest

import typed_settings as ts


@ts.settings
class Settings:
    u: str = ts.option()
    p: str = ts.secret()


def test_load_settings(tmp_path):
    """We can load settings with a class decorated with our decorator."""
    f = tmp_path.joinpath("cfg.toml")
    f.write_text('[test]\nu = "spam"\np = "eggs"\n')
    settings = ts.load_settings(Settings, "test", [f])
    assert settings == Settings("spam", "eggs")


def test_update_settings():
    s = Settings("spam", "eggs")
    u = ts.update_settings(s, "p", "bacon")
    assert u == Settings("spam", "bacon")


class TestAttrExtensions:
    """Tests for attrs extensions."""

    @pytest.fixture
    def inst(self):
        return Settings(u="spam", p="42")

    def test_secret_str(self, inst):
        assert str(inst) == "Settings(u='spam', p=***)"

    def test_secret_repr(self, inst):
        assert repr(inst) == "Settings(u='spam', p=***)"
