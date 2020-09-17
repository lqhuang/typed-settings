import attr

import typed_settings as ts


@attr.frozen
class Settings:
    u: str
    p: str = ts.secret()


class TestAttrExtensions:
    """Tests for attrs extensions."""

    def test_secret_str(self):
        assert str(Settings(u="spam", p="42")) == "Settings(u='spam', p=***)"

    def test_secret_repr(self):
        assert repr(Settings(u="spam", p="42")) == "Settings(u='spam', p=***)"
