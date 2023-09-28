"""
Tests for "typed_settings.processors".
"""
from typing import Callable, Type, Union

import pytest

from typed_settings import processors, settings
from typed_settings.cls_utils import deep_options


@settings
class ChildA:
    """A nested class."""

    aa: str
    ab: str


@settings
class ChildB:
    """A nested class."""

    ba: str
    bb: str


@settings
class Settings:
    """A parent class."""

    a: ChildA
    b: ChildB
    c: str
    d: str


OPTIONS = deep_options(Settings)


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
def test_url_processor(value: str, expected: str) -> None:
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
def test_handle_script_error(cmd: str, code: int, stdout: str, stderr: str) -> None:
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


def test_handle_op(mock_op: None) -> None:
    """
    The 1Password handler retrievs the secret from the "op" CLI.
    """
    result = processors.handle_op("Test/Test/password", "op://")
    assert result == "eggs"


class TestFormatProcessor:
    """
    Tests for "format_processor()".
    """

    DATA = [
        pytest.param(
            {"c": "spam"},
            {"c": "spam"},
            id="str-no-template",
        ),
        pytest.param(
            {"c": 3},
            {"c": 3},
            id="int-no-template",
        ),
        pytest.param(
            {"c": "spam", "d": "{c}"},
            {"c": "spam", "d": "spam"},
            id="template-after-value",
        ),
        pytest.param(
            {"c": "{d}", "d": "spam"},
            {"c": "spam", "d": "spam"},
            id="template-before-value",
        ),
        pytest.param(
            {"a": {"aa": "spam"}, "c": "{a[aa]}"},
            {"a": {"aa": "spam"}, "c": "spam"},
            id="refer-to-child",
        ),
        pytest.param(
            {"a": {"aa": "{c}"}, "c": "spam"},
            {"a": {"aa": "spam"}, "c": "spam"},
            id="refer-to-parent",
        ),
        pytest.param(
            {"a": {"aa": "{a[ab]}", "ab": "spam"}},
            {"a": {"aa": "spam", "ab": "spam"}},
            id="refer-to-self",
        ),
        pytest.param(
            {"a": {"aa": "{b[ba]}"}, "b": {"ba": "spam"}},
            {"a": {"aa": "spam"}, "b": {"ba": "spam"}},
            id="refer-to-sibling",
        ),
        pytest.param(
            {
                "a": {
                    "aa": "{c}",
                    "ab": "{b[ba]}",
                },
                "b": {
                    "ba": "{a[aa]}",
                    "bb": "{b[ba]}",
                },
                "c": "{d}",
                "d": "spam",
            },
            {
                "a": {
                    "aa": "spam",
                    "ab": "spam",
                },
                "b": {
                    "ba": "spam",
                    "bb": "spam",
                },
                "c": "spam",
                "d": "spam",
            },
            id="chain-templates",
        ),
        pytest.param(
            {"c": "{d}"},
            {"c": "{d}"},
            id="simple-value-not-defined",
        ),
        pytest.param(
            {"c": "{a.aa}", "a": {"aa": {"spam"}}},
            {"c": "{a.aa}", "a": {"aa": {"spam"}}},
            id="invalid-attr-access",
        ),
        pytest.param(
            {"c": "spam", "d": "{c"},
            {"c": "spam", "d": "{c"},
            id="invalid-template-1",
        ),
        pytest.param(
            {"c": "spam", "d": "{{c}"},
            {"c": "spam", "d": "{{c}"},
            id="invalid-template-2",
        ),
        pytest.param(
            {"c": "spam", "d": "{{}{}}"},
            {"c": "spam", "d": "{{}{}}"},
            id="invalid-template-3",
        ),
        pytest.param(
            {"c": "spam", "d": "{{}}"},
            {"c": "spam", "d": "{}"},
            id="invalid-template-4",
        ),
        pytest.param(
            {"c": "{d}", "d": "{c}"},
            RecursionError,
            id="recursion",
        ),
        pytest.param(
            {"c": "{c}"},
            {"c": "{c}"},
            id="self-recursion",
        ),
    ]

    @pytest.mark.parametrize("data, expected", DATA)
    def test_format_processor(
        self, data: dict, expected: Union[dict, Type[Exception]]
    ) -> None:
        """
        Values are recursively rendered with "str.format()" and errors are
        never raised.
        """
        if isinstance(expected, dict):
            result = processors.FormatProcessor()(data, Settings, OPTIONS)
            assert result == expected
        else:
            with pytest.raises(expected):
                processors.FormatProcessor()(data, Settings, OPTIONS)


class TestJinjaProcessor:
    """
    Tests for "jinja_processor()".
    """

    DATA = [
        pytest.param(
            {"c": "spam"},
            {"c": "spam"},
            id="str-no-template",
        ),
        pytest.param(
            {"c": 3},
            {"c": 3},
            id="int-no-template",
        ),
        pytest.param(
            {"c": "spam", "d": "{{ c }}"},
            {"c": "spam", "d": "spam"},
            id="template-after-value",
        ),
        pytest.param(
            {"c": "{{ d }}", "d": "spam"},
            {"c": "spam", "d": "spam"},
            id="simple-template-before-value",
        ),
        pytest.param(
            {"a": {"aa": "spam"}, "c": "{{ a.aa }}"},
            {"a": {"aa": "spam"}, "c": "spam"},
            id="refer-to-child",
        ),
        pytest.param(
            {"a": {"aa": "spam"}, "c": "{{ a['aa'] }}"},
            {"a": {"aa": "spam"}, "c": "spam"},
            id="refer-to-child-item-access",
        ),
        pytest.param(
            {"a": {"aa": "{{ c }}"}, "c": "spam"},
            {"a": {"aa": "spam"}, "c": "spam"},
            id="refer-to-parent",
        ),
        pytest.param(
            {"a": {"aa": "{{ a.ab }}", "ab": "spam"}},
            {"a": {"aa": "spam", "ab": "spam"}},
            id="refer-to-self",
        ),
        pytest.param(
            {"a": {"aa": "{{ b.ba }}"}, "b": {"ba": "spam"}},
            {"a": {"aa": "spam"}, "b": {"ba": "spam"}},
            id="refer-to-sibling",
        ),
        pytest.param(
            {
                "a": {
                    "aa": "{{ c }}",
                    "ab": "{{ b.ba }}",
                },
                "b": {
                    "ba": "{{ a.aa }}",
                    "bb": "{{ b.ba }}",
                },
                "c": "{{ d }}",
                "d": "spam",
            },
            {
                "a": {
                    "aa": "spam",
                    "ab": "spam",
                },
                "b": {
                    "ba": "spam",
                    "bb": "spam",
                },
                "c": "spam",
                "d": "spam",
            },
            id="chain-templates",
        ),
        pytest.param(
            {
                "a": {
                    "aa": "{{ c }}",
                    "ab": "{{ b.ba }}",
                },
                "b": {
                    "ba": "{% if a.aa == 'spam' %}x{% else %}y{% endif %}",
                    "bb": "{{ b.ba }}",
                },
                "c": "{{ d }}",
                "d": "spam",
            },
            {
                "a": {
                    "aa": "spam",
                    "ab": "x",
                },
                "b": {
                    "ba": "x",
                    "bb": "x",
                },
                "c": "spam",
                "d": "spam",
            },
            id="if-expressions",
        ),
        pytest.param(
            {"c": "{}"},
            {"c": "{}"},
            id="format-string",
        ),
        pytest.param(
            {"c": "{{}}"},
            {"c": "{{}}"},
            id="empty-template",
        ),
        pytest.param(
            {"c": "{{ d }}"},
            {"c": ""},
            id="value-not-defined",
        ),
        pytest.param(
            {"c": "spam", "d": "{{ c"},
            {"c": "spam", "d": "{{ c"},
            id="invalid-template-1",
        ),
        pytest.param(
            {"c": "spam", "d": "{{c}"},
            {"c": "spam", "d": "{{c}"},
            id="invalid-template-2",
        ),
        pytest.param(
            {"c": "spam", "d": "{{}{}}"},
            {"c": "spam", "d": "{{}{}}"},
            id="invalid-template-3",
        ),
        pytest.param(
            {"c": "{{ d }}", "d": "{{ c }}"},
            RecursionError,
            id="recursion",
        ),
        pytest.param(
            {"c": "{{ c }}"},
            RecursionError,
            id="self-recursion",
        ),
    ]

    @pytest.mark.parametrize("data, expected", DATA)
    def test_jinja_processor(
        self, data: dict, expected: Union[dict, Type[Exception]]
    ) -> None:
        """
        Values are recursively rendered with Jinja2 and an error is never
        raised.
        """
        if isinstance(expected, dict):
            result = processors.JinjaProcessor()(data, Settings, OPTIONS)
            assert result == expected
        else:
            with pytest.raises(expected):
                processors.JinjaProcessor()(data, Settings, OPTIONS)

    def test_jinja_not_installed(self, unimport: Callable[[str], None]) -> None:
        unimport("jinja2")
        with pytest.raises(ModuleNotFoundError, match="not installed"):
            processors.JinjaProcessor()
