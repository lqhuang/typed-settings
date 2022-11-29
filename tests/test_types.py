from typing import Any

import pytest
from typing_extensions import assert_type

from typed_settings import types


def test_auto_singleton():
    """
    `_Auto()`  is a singleton.
    """
    assert types._Auto() is types.AUTO


def test_auto_repr():
    """
    `_Auto()` has a nice repr.
    """
    assert repr(types._Auto()) == "AUTO"


class TestSecretStr:
    def test_repr(self) -> None:
        """
        The repr of a non empty string is seven *
        """
        secret = types.SecretStr("spam")
        assert repr(secret) == "'*******'"

    def test_empty_repr(self) -> None:
        """
        The repr of a non empty string is seven \\*.
        """
        secret = types.SecretStr("")
        assert repr(secret) == "''"

    def test_str(self) -> None:
        """
        The str repr is the original string.
        """
        secret = types.SecretStr("spam")
        assert str(secret) == "spam"

    def test_print(self, capsys: pytest.CaptureFixture) -> None:
        """
        Printing reveals the value.
        """
        secret = types.SecretStr("spam")
        print(secret)
        assert capsys.readouterr().out == "spam\n"

    def test_locals(self, capsys: pytest.CaptureFixture) -> None:
        """
        Printing locals does not leak the secrets.
        """
        secret = types.SecretStr("spam")
        print(locals())
        assert "'secret': '*******'" in capsys.readouterr().out


class TestSecret:
    def test_repr(self) -> None:
        """
        The repr of a non empty string is seven *
        """
        secret = types.Secret("spam")
        assert_type(secret, types.Secret[str])
        assert repr(secret) == "Secret('*******')"

    def test_empty_repr(self) -> None:
        """
        The repr of a non empty string is seven \\*.
        """
        secret = types.Secret("")
        assert repr(secret) == "Secret('')"

    @pytest.mark.parametrize("v", ["spam", 0, 3, [1], True, False])
    def test_str(self, v: Any) -> None:
        """
        The str repr is the original string.
        """
        secret = types.Secret(v)
        assert str(secret) == "*******"

    @pytest.mark.parametrize("v, t", [("", str), ([], list), ((), tuple)])
    def test_empty_str(self, v: Any, t: type) -> None:
        """
        The str repr of an empty collection secret is an empty string.
        """
        secret = types.Secret(v)
        assert str(secret) == str(v)

    def test_print(self, capsys: pytest.CaptureFixture) -> None:
        """
        Printing does not reveal the value.
        """
        secret = types.Secret("spam")
        print(secret)
        assert capsys.readouterr().out == "*******\n"

    def test_locals(self, capsys: pytest.CaptureFixture) -> None:
        """
        Printing locals does not leak the secret.
        """
        secret = types.Secret("spam")
        print(locals())
        assert "'secret': Secret('*******')" in capsys.readouterr().out

    @pytest.mark.parametrize("v", ["spam", 3, [1], True])
    def test_bool_true(self, v: Any) -> None:
        """
        The secret's bool representation is that of the wrapped secret.
        """
        assert bool(types.Secret(v))

    @pytest.mark.parametrize("v", ["", 0, [], False])
    def test_bool_false(self, v: Any) -> None:
        """
        The secret's bool representation is that of the wrapped secret.
        """
        assert not bool(types.Secret(v))

    def test_get_value(self) -> None:
        """
        The secret value must explicitly be retrieved.
        """
        secret = types.Secret(42)
        assert secret.get_secret_value() == 42
