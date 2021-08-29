from enum import Enum

import click

import typed_settings as ts


class PyVersion(Enum):
    py37 = "3.7"
    py38 = "3.8"
    py39 = "3.9"


@ts.settings
class Settings:
    line_length: int = 88
    skip_string_normalization: bool = False
    # target_version: Optional[PyVersion] = None  # Does not yet work
    target_version: PyVersion = PyVersion.py37


@click.command()
@ts.click_options(
    Settings,
    ts.default_loaders(
        appname="black",
        config_files=[ts.find("pyproject.toml")],
        config_file_section="tool.black",
        env_prefix=None,
    ),
)
def cli(settings):
    print(settings)


if __name__ == "__main__":
    cli()
