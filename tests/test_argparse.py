import sys
from typing import Any, Callable, TypeVar

import attrs
import pytest

from typed_settings import (
    argparse_utils,
    cli_utils,
    default_converter,
    default_loaders,
    option,
    settings,
)
from typed_settings.attrs import ARGPARSE_KEY, METADATA_KEY


T = TypeVar("T")


Invoke = Callable[..., Any]


Cli = Callable[[], Any]


@settings
class Settings:
    o: int


@pytest.fixture(name="invoke")
def _invoke(monkeypatch: pytest.MonkeyPatch) -> Invoke:
    def invoke(cli: Callable[[], Any], *args: str) -> Any:
        with monkeypatch.context() as m:
            m.setattr(sys, "argv", [cli.__name__] + list(args))
            return cli()

    return invoke


def test_cli(invoke: Invoke) -> None:
    """
    Basic test "cli()" - simple CLI for a simple settings class.
    """

    @argparse_utils.cli(Settings, "test")
    def cli(settings: Settings) -> None:
        assert settings == Settings(3)

    invoke(cli, "--o=3")


def test_cli_explicit_config(invoke: Invoke) -> None:
    """
    Basic test "cli()" with explicit loaders, converter config.
    """

    loaders = default_loaders("test")
    converter = default_converter()
    tam = cli_utils.TypeArgsMaker(argparse_utils.ArgparseHandler())

    @argparse_utils.cli(
        Settings,
        loaders=loaders,
        converter=converter,
        type_args_maker=tam,
    )
    def cli(settings: Settings) -> None:
        assert settings == Settings(3)

    invoke(cli, "--o=3")


def test_cli_desc_from_func(
    invoke: Invoke, capsys: pytest.CaptureFixture
) -> None:
    @argparse_utils.cli(Settings, "test")
    def cli(settings: Settings) -> None:
        """
        Le description
        """

    with pytest.raises(SystemExit):
        invoke(cli, "--help")

    out, err = capsys.readouterr()
    assert out.startswith("usage: cli [-h] --o INT\n\nLe description\n")
    assert err == ""


def test_cli_desc_from_kwarg(
    invoke: Invoke, capsys: pytest.CaptureFixture
) -> None:
    @argparse_utils.cli(Settings, "test", description="Le description")
    def cli(settings: Settings) -> None:
        """
        spam spam spam
        """

    with pytest.raises(SystemExit):
        invoke(cli, "--help")

    out, err = capsys.readouterr()
    assert out.startswith("usage: cli [-h] --o INT\n\nLe description\n")
    assert err == ""


def test_manual_parser() -> None:
    """
    Basic test for "make_parser()" and "namespace2settings"().
    """

    parser = argparse_utils.make_parser(Settings, "test")
    namespace = parser.parse_args(["--o", "3"])
    result = argparse_utils.namespace2settings(Settings, namespace)
    assert result == Settings(3)


def test_manual_parser_explicit_config() -> None:
    """
    Basic test for "make_parser()" and "namespace2settings"() with explicit
    config.
    """

    loaders = default_loaders("test")
    converter = default_converter()
    tam = cli_utils.TypeArgsMaker(argparse_utils.ArgparseHandler())
    parser = argparse_utils.make_parser(
        Settings,
        loaders=loaders,
        converter=converter,
        type_args_maker=tam,
    )
    namespace = parser.parse_args(["--o", "3"])
    result = argparse_utils.namespace2settings(
        Settings,
        namespace,
        converter=converter,
    )
    assert result == Settings(3)


def test_invalid_bool_flag() -> None:
    """
    Only "long" boolean flags (--flag) are supported, but not short ones (-f).
    """

    @settings
    class Settings:
        flag: bool = option(argparse={"param_decls": ("-f")})

    with pytest.raises(ValueError, match="boolean flags.*--.*supported"):
        argparse_utils.make_parser(Settings, "test")


def test_attrs_meta_not_modified() -> None:
    """
    The attrs meta data with with user defined argparse config is not modified.

    Regression test for #29.
    """

    @settings
    class S:
        opt: int = option(help="spam", argparse={"param_decls": "-o"})

    meta = attrs.fields(S).opt.metadata[METADATA_KEY]

    assert meta[ARGPARSE_KEY] == {"help": "spam", "param_decls": "-o"}

    argparse_utils.make_parser(S, "test")
    argparse_utils.make_parser(S, "test")

    assert meta[ARGPARSE_KEY] == {"help": "spam", "param_decls": "-o"}
