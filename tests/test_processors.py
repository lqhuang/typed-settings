import pytest

from typed_settings import processors, settings
from typed_settings.dict_utils import deep_options


class TestUrlProcessor:
    """
    Tests for "UrlProcessor".
    """

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("spam", "spam"),
            ("raw://spam", "spam"),
            ("helper://echo spam", "spam"),
            ("script://echo spam", "spam"),
            # Only process a value once:
            ("raw://script://echo spam", "script://echo spam"),
            ("script://echo 'raw://spam'", "raw://spam"),
        ],
    )
    def test_call(self, value: str, expected: str) -> None:
        """
        The processor handles the configured protocols and changes the dict
        in-place.
        """

        @settings
        class Settings:
            o: str

        uh = processors.UrlProcessor(
            {
                "raw://": processors.handle_raw,
                "helper://": processors.handle_script,
                "script://": processors.handle_script,
            }
        )
        result = uh({"o": value}, Settings, deep_options(Settings))
        assert result == {"o": expected}


def test_handle_raw() -> None:
    """
    The handler returns the value unchanged.
    """
    result = processors.handle_raw("spam", "raw://")
    assert result == "spam"


def test_handle_script() -> None:
    """
    The script is run and its output returned stripped.
    """
    result = processors.handle_script("echo spam", "script://")
    assert result == "spam"


@pytest.mark.parametrize(
    "cmd, code, stdout, stderr",
    [
        ("xyz", 127, "", "/bin/sh.*xyz.*not found\n"),
        ("echo a; echo b 1>&2; exit 1", 1, "a\n", "b\n"),
    ],
)
def test_handle_script_error(
    cmd: str, code: int, stdout: str, stderr: str
) -> None:
    """
    Raise ValueError if the command cannot be found or fails.  Include stdout
    and stderr in exception.
    """
    msg = (
        f"Helper script failed: script://{cmd}\n"
        f"EXIT CODE: {code}\n"
        f"STDOUT:\n{stdout}"
        f"STDERR:\n{stderr}"
    )
    with pytest.raises(ValueError, match=msg):
        processors.handle_script(cmd, "script://")


def test_handle_op() -> None:
    """
    The 1Password handler retrievs the secret from the "op" CLI.
    """
    result = processors.handle_op("Test/Test/password", "op://")
    assert result == "eggs"
