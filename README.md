# Typed Settings

Load and merge settings from multiple different sources and present them in a structured, typed, and validated way!

## Why?

There are many different config file formats and libraries.
Many of them have a narrow scope, don't integrate well with other libs, or lack in typing support.

Typed Settings' goal is to enable you to load settings from any source (e.g., env vars, config files, vaults)
and can convert values to anything you need.

You can extend Typed Settings to support config sources that aren't supported yet
and its extensive documentation will help you on your way.

## What can it be used for?

You can use Typed Settings in any context, e.g.:

- server processes
- containerized apps
- command line applications
- scripts and tools for scientific experiments and data analysis

## What does it do?

- It loads settings from multiple sources (e.g., env vars, config files, secret vaults) in a unified way and merges the loaded values.
  You can add loaders for sources we cannot imagine yet.

- It can post-process loaded values.
  This allows value interpolation/templating or calling helpers that retrieve secrets from vaults.
  You can create and add any processors you can image if the built-in ones are not enough.

- You can add a CLI on top to let users update the loaded settings via command line arguments.
  [Click](https://click.palletsprojects.com) and [argparse](https://docs.python.org/3/library/argparse.html) are currently supported.

- Settings are cleanly structured and typed.
  The type annotations are used to convert the loaded settings to the proper types.
  This also includes higher level structures like dates, paths and various collections (lists, dicts, …).
  You can use [attrs](https://www.attrs.org), [dataclasses](https://docs.python.org/3/library/dataclasses.html), or [Pydantic](https://docs.pydantic.dev/latest/) to write settings classes.

  Types Settings uses the powerful and fast [cattrs](https://cattrs.readthedocs.io)) by default and falls back to an internal converter if **cattrs** is not installed.

- No mandatory requirements.  Typed Settings works out-of-the box with dataclasses, argparse and its own converter.

The documentation contains a [full list](https://typed-settings.readthedocs.io/en/latest/why.html#comprehensive-list-of-features) of all features.


## Installation

Install and update using [pip](https://pip.pypa.io/en/stable/quickstart/):

```console
$ python -m pip install typed-settings
```

Typed Settings as **no required dependencies** (except for tomli on older Python versions).
You can install dependencies for optional features via

```console
$ python -m pip install typed-settings[<feature>,...]
```

Available features:

- `typed-settings[attrs]`: Enable settings classes via **attrs**.
- `typed-settings[pydantic]`: Enable settings classes via **Pydantic**.
- `typed-settings[cattrs]`: Enable usage of the powerful and fast **cattrs** converter.
- `typed-settings[click]`: Enable support for **Click** options.
- `typed-settings[option-groups]`: Enable support for **Click** and **Click option groups**.
- `typed-settings[jinja]`: Enable support for value interpolation with **Jinja** templates.
- `typed-settings[all]`: Install all optional requirements.

## Examples

### Hello, World!, with env. vars.

This is a very simple example that demonstrates how you can load settings from environment variables.

```python
# example.py
import attrs
import typed_settings as ts

@attrs.frozen
class Settings:
    option: str

settings = ts.load(cls=Settings, appname="example")
print(settings)
```

```console
$ EXAMPLE_OPTION="Hello, World!" python example.py
Settings(option='Hello, World!')
```


### Nested classes and config files

Settings classes can be nested.
Config files define a different section for each class.

```python
# example.py
import attrs
import click

import typed_settings as ts

@attrs.frozen
class Host:
    name: str
    port: int

@attrs.frozen
class Settings:
    host: Host
    endpoint: str
    retries: int = 3

settings = ts.load(
    cls=Settings, appname="example", config_files=["settings.toml"]
)
print(settings)
```

```toml
# settings.toml
[example]
endpoint = "/spam"

[example.host]
name = "example.com"
port = 443
```

```console
$ python example.py
Settings(host=Host(name='example.com', port=443), endpoint='/spam', retries=3)
```


### Configurable settings loaders

The first example used a convenience shortcut with pre-configured settings loaders.
However, Typed Settings lets you explicitly configure which loaders are used and how they work:

```python
# example.py
import attrs
import typed_settings as ts

@attrs.frozen
class Settings:
    option: str

settings = ts.load_settings(
    cls=Settings,
    loaders=[
        ts.FileLoader(
            files=[],
            env_var="EXAMPLE_SETTINGS",
            formats={
                "*.toml": ts.TomlFormat("example"),
            },
        ),
        ts.EnvLoader(prefix="EXAMPLE_"),
      ],
)
print(settings)
```

```console
$ EXAMPLE_OPTION="Hello, World!" python example.py
Settings(option='Hello, World!')
```

In order to write your own loaders or support new file formats, you need to implement the `Loader` or `FileFormat` [protocols](https://typed-settings.readthedocs.io/en/latest/apiref.html#module-typed_settings.loaders).

You can also pass a custom [cattrs converter](https://cattrs.readthedocs.io/en/latest/index.html) to add support for additional Python types.


### Command Line Interfaces

Typed Settings can generate a command line interfaces (CLI) based on your settings.
These CLIs will load settings as described above and let users override the loades settings with command line argumments.

Typed Settings supports `argparse` and `click`.


#### Argparse

```python
# example.py
import attrs
import typed_settings as ts

@attrs.frozen
class Settings:
    a_str: str = ts.option(default="default", help="A string")
    an_int: int = ts.option(default=3, help="An int")

@ts.cli(Settings, "example")
def main(settings):
    print(settings)

if __name__ == "__main__":
    main()
```

```console
$ python example.py --help
usage: example.py [-h] [--a-str TEXT] [--an-int INT]

options:
  -h, --help    show this help message and exit

Settings:
  Settings options

  --a-str TEXT  A string [default: default]
  --an-int INT  An int [default: 3]
$ python example.py --a-str=spam --an-int=1
Settings(a_str='spam', an_int=1)
```

#### Click


```python
# example.py
import attrs
import click
import typed_settings as ts

@attrs.frozen
class Settings:
    a_str: str = ts.option(default="default", help="A string")
    an_int: int = ts.option(default=3, help="An int")

@click.command()
@ts.click_options(Settings, "example")
def main(settings):
    print(settings)

if __name__ == "__main__":
    main()
```

```console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --a-str TEXT      A string  [default: default]
  --an-int INTEGER  An int  [default: 3]
  --help            Show this message and exit.
$ python example.py --a-str=spam --an-int=1
Settings(a_str='spam', an_int=1)
```

## Project Links

- [Changelog](https://typed-settings.readthedocs.io/en/latest/changelog.html)
- [Documentation](https://typed-settings.readthedocs.io)
- [GitLab](https://gitlab.com/sscherfke/typed-settings/)
- [Issues and Bugs](https://gitlab.com/sscherfke/typed-settings/-/issues)
- [PyPI](https://pypi.org/project/typed-settings/)
