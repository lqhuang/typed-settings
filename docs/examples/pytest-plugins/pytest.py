from typing import Tuple

import click

import typed_settings as ts
from typed_settings.click_utils import OptionGroupFactory


@ts.settings
class Coverage:
    """
    Coverage settings
    """

    src: str = ts.option(default="", click={"param_decls": ("--cov", "src")})
    report: str = ""


@ts.settings
class Emoji:
    """
    Emoji settings
    """

    enable: bool = True


@ts.settings
class Base:
    """
    Main settings
    """

    marker: str = ts.option(
        default="",
        help="only run tests which macht the given substring expression",
        click={"param_decls": ("-m",)},
    )
    exitfirst: bool = ts.option(
        default=False,
        help="Exit instantly on first error or failed test",
        click={"param_decls": ("--exitfirst", "-x"), "is_flag": True},
    )
    stepwise: bool = ts.option(
        default=False,
        help=(
            "Exit on test failure and continue from last failing test next "
            "time"
        ),
        click={"param_decls": ("--stepwise", "--sw"), "is_flag": True},
    )


Settings = ts.combine(
    "Settings",
    Base,
    {
        # Imagine, this dict comes from a "load_plugins()" function :)
        "cov": Coverage(),
        "emoji": Emoji(),
    },
)


@click.command()
@click.argument("file_or_dir", nargs=-1)
@ts.click_options(Settings, "pytest", decorator_factory=OptionGroupFactory())
def cli(
    settings: Settings,  # type: ignore[valid-type]
    file_or_dir: Tuple[str, ...],
):
    print(settings)


if __name__ == "__main__":
    cli()
