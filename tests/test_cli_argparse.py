"""
Tests for "typed_settings.argparse_utils".
"""
import sys
from pathlib import Path
from typing import Any, Callable, List, TypeVar

import attrs
import pytest

from typed_settings import (
    cli_argparse,
    cli_utils,
    constants,
    default_converter,
    default_loaders,
    option,
    settings,
)


T = TypeVar("T")


Invoke = Callable[..., Any]


Cli = Callable[[], Any]


@settings
class Settings:
    """A simple settings class for testing."""

    o: int


@pytest.fixture(name="invoke")
def _invoke(monkeypatch: pytest.MonkeyPatch) -> Invoke:
    def invoke(cli: Callable[[], Any], *args: str) -> Any:
        with monkeypatch.context() as m:
            m.setattr(sys, "argv", [cli.__name__, *list(args)])
            return cli()

    return invoke


def test_cli(invoke: Invoke) -> None:
    """
    Basic test "cli()" - simple CLI for a simple settings class.
    """

    @cli_argparse.cli(Settings, "test")
    def cli(settings: Settings) -> None:
        assert settings == Settings(3)

    invoke(cli, "--o=3")


def test_cli_explicit_config(invoke: Invoke) -> None:
    """
    Basic test "cli()" with explicit loaders, converter config.
    """
    loaders = default_loaders("test")
    converter = default_converter()
    tam = cli_utils.TypeArgsMaker(cli_argparse.ArgparseHandler())

    @cli_argparse.cli(
        Settings,
        loaders=loaders,
        converter=converter,
        type_args_maker=tam,
    )
    def cli(settings: Settings) -> None:
        assert settings == Settings(3)

    invoke(cli, "--o=3")


def test_cli_desc_from_func(invoke: Invoke, capsys: pytest.CaptureFixture) -> None:
    """
    The CLI function's docstring is used as argparse CLI description.
    """

    @cli_argparse.cli(Settings, "test")
    def cli(settings: Settings) -> None:
        """
        Le description.
        """

    with pytest.raises(SystemExit):
        invoke(cli, "--help")

    out, err = capsys.readouterr()
    assert out.startswith("usage: cli [-h] --o INT\n\nLe description.\n")
    assert err == ""


def test_cli_desc_from_kwarg(invoke: Invoke, capsys: pytest.CaptureFixture) -> None:
    """
    The argparse CLI description can be explicitly configured with a keyword arg.
    """

    @cli_argparse.cli(Settings, "test", description="Le description")
    def cli(settings: Settings) -> None:
        """
        spam spam spam.
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
    parser, merged_settings = cli_argparse.make_parser(Settings, "test")
    namespace = parser.parse_args(["--o", "3"])
    result = cli_argparse.namespace2settings(
        Settings, namespace, merged_settings=merged_settings
    )
    assert result == Settings(3)


def test_manual_parser_explicit_config() -> None:
    """
    Basic test for "make_parser()" and "namespace2settings"() with explicit
    config.
    """
    loaders = default_loaders("test")
    converter = default_converter()
    tam = cli_utils.TypeArgsMaker(cli_argparse.ArgparseHandler())
    parser, merged_settings = cli_argparse.make_parser(
        Settings,
        loaders=loaders,
        converter=converter,
        type_args_maker=tam,
    )
    namespace = parser.parse_args(["--o", "3"])
    result = cli_argparse.namespace2settings(
        Settings,
        namespace,
        merged_settings=merged_settings,
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
        cli_argparse.make_parser(Settings, "test")


def test_attrs_meta_not_modified() -> None:
    """
    The attrs meta data with with user defined argparse config is not modified.

    Regression test for #29.
    """

    @settings
    class S:
        opt: int = option(help="spam", argparse={"param_decls": "-o"})

    meta = attrs.fields(S).opt.metadata[constants.METADATA_KEY]

    assert meta[cli_argparse.METADATA_KEY] == {"help": "spam", "param_decls": "-o"}

    cli_argparse.make_parser(S, "test")
    cli_argparse.make_parser(S, "test")

    assert meta[cli_argparse.METADATA_KEY] == {"help": "spam", "param_decls": "-o"}


def test_resolve_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke: Invoke
) -> None:
    """
    Relative paths passed via the command line are resolved based on the user's CWD.
    """

    @settings
    class Settings:
        a: Path = Path("default")
        b: Path = Path("default")  # Load from file
        c: Path = Path("default")  # Load from env var
        d: Path = Path("default")  # Load from cli arg

    spath = tmp_path.joinpath("settings.toml")
    spath.write_text('[test]\nb = "file"\n')
    monkeypatch.setenv("TEST_C", "env")

    # chdir *before* creating the CLI, b/c it will load the defaults immediately:
    subdir = tmp_path.joinpath("sub")
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    result = Settings()  # Will be update by the CLI

    @cli_argparse.cli(Settings, default_loaders("test", [spath]))
    def cli(settings: Settings) -> Settings:
        return settings

    result = invoke(cli, "--d", "arg")
    assert result == Settings(
        a=subdir.joinpath("default"),
        b=spath.parent.joinpath("file"),
        c=subdir.joinpath("env"),
        d=subdir.joinpath("arg"),
    )


def test_multiple_invocations(invoke: Invoke) -> None:
    """
    A CLI function can be invoked multiple times w/o carrying state from call to call.
    """

    @settings
    class S:
        o: int = 0

    loaded_settings: List[S] = []

    @cli_argparse.cli(S, "example")
    def cli(settings: S) -> None:
        loaded_settings.append(settings)

    # The order of these invocations is important:
    invoke(cli, "--o=3")
    invoke(cli)
    assert loaded_settings == [S(3), S(0)]


def test_default_factory_multiple_invocations(invoke: Invoke) -> None:
    """
    Default factories are not invoked by click when the CLI is generated.
    They are evaluate during the "convert" phase each time the CLI is invoked.
    """

    @settings
    class S:
        o: int = option(factory=lambda: len(loaded_settings) + 1)

    loaded_settings: List[S] = []

    @cli_argparse.cli(S, "example")
    def cli(settings: S) -> None:
        loaded_settings.append(settings)

    invoke(cli)
    invoke(cli)
    invoke(cli, "--o=100")
    assert loaded_settings == [S(1), S(2), S(100)]
