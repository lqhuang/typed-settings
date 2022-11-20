"""
Show off the generated CLIs.

By (un)commenting the proper imports and decorators, you can use:

- an Argparse cli
- a Click cli
- a Click cli with rich-click styling
"""
import click  # noqa
import rich_click

import typed_settings as ts


@ts.settings
class Settings:
    host: str = ts.option(help="The server's host name")
    port: int = ts.option(default=8000, help="The server's port")
    admin_user: str = ts.option(default="admin", help="Default admin username")
    admin_pass: str = ts.secret(default="admin", help="Default admin password")
    dev_mode: bool = ts.option(
        default=False,
        help="If true, watch for file changes and reload the server",
    )


@rich_click.command()
# @click.command()
@ts.click_options(Settings, "myapp")
# @ts.cli(Settings, "myapp")
def cli(settings: Settings) -> None:
    """
    Start MyApp and let it listen on the configured HOST:PORT.
    """
    print(settings)


if __name__ == "__main__":
    cli()
