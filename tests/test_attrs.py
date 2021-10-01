import pytest

from typed_settings.attrs import option, secret, settings


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
