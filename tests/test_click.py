from enum import Enum
from pathlib import Path

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


class LeEnum(Enum):
    spam = "le spam"
    eggs = "Le eggs"


@settings
class Nested:
    a: str = "nested"
    b: int = option(default=0, converter=int)


@settings(kw_only=True)
class Settings:
    a: str
    b: str = secret()
    c: str = option(default="spam")
    d: int = 0
    e: float = 0
    f: bool = False
    g: bool = True
    h: LeEnum = option(
        default=LeEnum.spam,
        converter=lambda v: LeEnum(v) if isinstance(v, str) else v,  # type: ignore  # noqa
    )
    p: Path = Path("/")
    n: Nested = option(
        default=Nested(),
        converter=lambda d: Nested(**d) if isinstance(d, dict) else d,  # type: ignore  # noqa
    )
    long_name: str = option(default="val")


@pytest.fixture
def cli():
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
    @click_options(Settings, "test", ["settings.toml"])
    def cli(settings):
        runner.settings = settings

    def run(*args, **kwargs):
        return runner.invoke(cli, args, **kwargs)

    return run


class TestClickOptions:
    """Tests for click_options()."""

    def test_click_options(self, cli):
        """Make sure click options of various types work."""

        result = cli(
            "--a=eggs1",
            "--b=eggs2",
            "--c=eggs3",
            "--d=3",
            "--e=3.1",
            "--f",
            "--no-g",
            "--h=eggs",
            "--p=/spam",
            "--n-a=eggs4",
            "--n-b=3",
        )
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == Settings(
            a="eggs1",
            b="eggs2",
            c="eggs3",
            d=3,
            e=3.1,
            f=True,
            g=False,
            h=LeEnum.eggs,
            p=Path("/spam"),
            n=Nested("eggs4", 3),
        )

    def test_click_defaults(self, cli):
        """
        Most types do not accept "None" as value, so most options need to have
        a default value.
        """
        result = cli()
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == Settings(
            a=None,
            b=None,
        )

    def test_help(self, cli):
        """All options get a proper help string."""
        result = cli("--help")
        assert result.output == (
            "Usage: cli [OPTIONS] COMMAND [ARGS]...\n"
            "\n"
            "Options:\n"
            "  --a TEXT\n"
            "  --b TEXT\n"
            "  --c TEXT          [default: spam]\n"
            "  --d INTEGER       [default: 0]\n"
            "  --e FLOAT         [default: 0]\n"
            "  --f / --no-f      [default: False]\n"
            "  --g / --no-g      [default: True]\n"
            "  --h [spam|eggs]   [default: spam]\n"
            "  --p PATH          [default: /]\n"
            "  --n-a TEXT        [default: nested]\n"
            "  --n-b INTEGER     [default: 0]\n"
            "  --long-name TEXT  [default: val]\n"
            "  --help            Show this message and exit.\n"
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
