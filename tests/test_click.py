from pathlib import Path

import click
import click.testing
import pytest

from typed_settings import option, secret, settings
from typed_settings._click import click_options


@settings
class Host:
    name: str
    port: int = option(converter=int)


@settings(kw_only=True)
class Settings:
    username: str
    password: str = secret()
    path: Path = Path("/")
    host: Host = option(converter=lambda d: Host(**d))  # type: ignore


@click.command()
@click_options(Settings, "test", ["settings.toml"])
def cli(settings):
    click.echo(settings)


class TestClickOptions:
    """Tests for click_options()."""

    @pytest.fixture
    def run(self):
        """Returns a ``run(*args*)`` function for tests."""
        runner = click.testing.CliRunner()

        def run(*args, **kwargs):
            return runner.invoke(cli, args, **kwargs)

        return run

    def test_click_options(self, run):
        """Make sure click_options() works at all."""
        result = run(
            "--username=spam",
            "--password=eggs",
            "--path=/",
            "--host-name=example.com",
            "--host-port=23",
        )
        assert result.output == (
            "Settings(username='spam', password=***, path=PosixPath('/'), "
            "host=Host(name='example.com', port=23))\n"
        )
        assert result.exit_code == 0

    def test_help(self, run):
        """All options get a proper help string."""
        result = run("--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --host-port INTEGER\n"
            "  --host-name TEXT\n"
            "  --path PATH\n"
            "  --password TEXT\n"
            "  --username TEXT\n"
            "  --help               Show this message and exit.\n"
        )
        assert result.exit_code == 0
