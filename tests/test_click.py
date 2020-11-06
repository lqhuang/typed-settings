from enum import Enum
from pathlib import Path
from typing import Any, Callable, List

import click
import click.testing
import pytest

from typed_settings import (
    click_options,
    option,
    pass_settings,
    secret,
    settings,
)


def make_cli(settings_cls: type) -> Callable[..., Any]:
    @pytest.fixture
    def cli(self, tmp_path):
        """
        Creates a click command for ``Settings`` and returns a functions that
        invokes a click test runner with the passed arguments.

        The result object will habe a ``settings`` attribute that holds the
        generated ``Settings`` instance for verification.

        """

        class Runner(click.testing.CliRunner):
            settings: object

            def invoke(self, *args, **kwargs):
                result = super().invoke(*args, **kwargs)
                try:
                    result.settings = self.settings
                except AttributeError:
                    result.settings = None
                return result

        runner = Runner()

        @click.group(invoke_without_command=True)
        @click_options(
            settings_cls, "test", [tmp_path.joinpath("settings.toml")]
        )
        def cli(settings):
            runner.settings = settings

        def run(*args, **kwargs):
            return runner.invoke(cli, args, **kwargs)

        return run

    return cli


class ClickTestBase:

    _help: List[str] = []
    _defaults: Any = None
    _options: List[str] = []
    _values: Any = None

    def test_help(self, cli):
        result = cli("--help")

        # fmt: off
        assert result.output.splitlines()[:-1] == [
            "Usage: cli [OPTIONS] COMMAND [ARGS]...",
            "",
            "Options:",
        ] + self._help
        assert result.exit_code == 0
        # fmt: on

    def test_defaults(self, cli):
        result = cli()
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == self._defaults

    def test_options(self, cli):
        result = cli(*self._options)
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == self._values


class TestClickBool(ClickTestBase):
    @settings
    class S:
        a: bool
        b: bool = True
        c: bool = False

    cli = make_cli(S)

    _help = [
        "  --a / --no-a  [default: False]",
        "  --b / --no-b  [default: True]",
        "  --c / --no-c  [default: False]",
    ]
    _defaults = S(False, True, False)
    _options = ["--no-a", "--no-b", "--c"]
    _values = S(False, False, True)


class TestIntFloatStr(ClickTestBase):
    @settings
    class S:
        a: str = option(default="spam")
        b: str = secret(default="spam")
        c: int = 0
        d: float = 0

    cli = make_cli(S)

    _help = [
        "  --a TEXT     [default: spam]",
        "  --b TEXT     [default: spam]",
        "  --c INTEGER  [default: 0]",
        "  --d FLOAT    [default: 0]",
    ]
    _defaults = S()  # type: ignore
    _options = ["--a=eggs", "--b=pwd", "--c=3", "--d=3.1"]
    _values = S(a="eggs", b="pwd", c=3, d=3.1)


# class TestMandatory(ClickTestBase):
#
#     @settings
#     class S:
#         a: str
#
#     cli = make_cli(S)
#
#     _help = (
#         "  --a TEXT\n"
#         "  --b TEXT\n"
#     )
#     _defaults = S()
#     _options = ["--a=eggs1", "--b=eggs2"]
#     _values = S(a="eggs1", b="eggs2")


# class TestDateTime(ClickTestBase):
#     pass


class LeEnum(Enum):
    spam = "le spam"
    eggs = "Le eggs"


class TestEnum(ClickTestBase):
    @settings
    class S:
        a: LeEnum = LeEnum.spam

    cli = make_cli(S)

    _help = ["  --a [spam|eggs]  [default: spam]"]
    _defaults = S(LeEnum.spam)
    _options = ["--a=eggs"]
    _values = S(LeEnum.eggs)


class TestPath(ClickTestBase):
    @settings
    class S:
        a: Path = Path("/")

    cli = make_cli(S)

    _help = ["  --a PATH  [default: /]"]
    _defaults = S()
    _options = ["--a=/spam"]
    _values = S(Path("/spam"))


class TestNested(ClickTestBase):
    @settings
    class S:
        @settings
        class Nested:
            a: str = "nested"
            b: int = option(default=0, converter=int)  # type: ignore

        n: Nested = Nested()  # type: ignore

    cli = make_cli(S)

    _help = [
        "  --n-a TEXT     [default: nested]",
        "  --n-b INTEGER  [default: 0]",
    ]
    _defaults = S()
    _options = ["--n-a=eggs", "--n-b=3"]
    _values = S(S.Nested("eggs", 3))


def test_long_name():
    """
    Underscores in option names are replaces with "-" in Click options.
    """

    @settings
    class S:
        long_name: str = "val"

    @click.command()
    @click_options(S, "test")
    def cli(settings):
        pass

    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.output == (
        "Usage: cli [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  --long-name TEXT  [default: val]\n"
        "  --help            Show this message and exit.\n"
    )
    assert result.exit_code == 0


def test_click_default_from_settings(monkeypatch, tmp_path):
    """
    If a setting is set in a config file, that value is being used as default
    for click options - *not* the default defined in the Settings class.
    """

    tmp_path.joinpath("settings.toml").write_text('[test]\na = "x"\n')
    spath = tmp_path.joinpath("settings2.toml")
    print(spath)
    spath.write_text('[test]\nb = "y"\n')
    monkeypatch.setenv("TEST_SETTINGS", str(spath))
    monkeypatch.setenv("TEST_C", "z")

    @settings
    class Settings:
        a: str
        b: str
        c: str
        d: str

    @click.command()
    @click_options(Settings, "test", [tmp_path.joinpath("settings.toml")])
    def cli(settings):
        print(settings)

    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.output == (
        "Usage: cli [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  --a TEXT  [default: x]\n"
        "  --b TEXT  [default: y]\n"
        "  --c TEXT  [default: z]\n"
        "  --d TEXT\n"
        "  --help    Show this message and exit.\n"
    )
    assert result.exit_code == 0


class TestPassSettings:
    """Tests for pass_settings()."""

    @settings
    class Settings:
        opt: str = ""

    def test_pass_settings(self):
        """
        A subcommand can receive the settings via the `pass_settings`
        decorator.
        """

        @click.group()
        @click_options(self.Settings, "test")
        def cli(settings):
            pass

        @cli.command()
        @pass_settings
        def cmd(settings):
            print(settings)
            assert settings == self.Settings(opt="spam")

        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["--opt=spam", "cmd"])
        assert result.output == "TestPassSettings.Settings(opt='spam')\n"
        assert result.exit_code == 0

    def test_pass_settings_no_settings(self):
        """
        Pass ``None`` if no settings are defined.
        """

        @click.group()
        def cli():
            pass

        @cli.command()
        @pass_settings
        def cmd(settings):
            print(settings)
            assert settings is None

        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["cmd"])
        assert result.output == "None\n"
        assert result.exit_code == 0
