# Typed Settings

*Safe and flexible settings with types*

[Home](https://typed-settings.readthedocs.io/en/latest) |
[PyPI](https://pypi.org/project/typed-settings/) |
[Repo](https://gitlab.com/sscherfke/typed-settings) |
[Issues](https://gitlab.com/sscherfke/typed-settings/-/issues)

______________________________________________________________________

Typed Settings is a settings loading library.
You can use it, e.g., for:

- server processes
- containerized apps
- command line applications

Typed Settings allows you to load settings from various sources (e.g., config files, environment variables or secret vaults) and merge them.
You can even generate CLI options for your settings for [argparse](https://docs.python.org/3/library/argparse.html) and [Click](https://click.palletsprojects.com) apps.
Loaded settings can be post processed, e.g., to interpolated values from other loaded settings.

Settings are converted to instances of typed classes.
You can use [attrs](https://www.attrs.org), [dataclasses](https://docs.python.org/3/library/dataclasses.html), or [Pydantic](https://docs.pydantic.dev/latest/).
You have the choice between a built-in converter and the powerful [cattrs](https://cattrs.readthedocs.io).

Typed Settings provides good defaults for the common case and is also highly customizable and extendable.
It has no mandatory requirements so that it is lightweight by default.
You can also [vendor](https://gitlab.com/sscherfke/typed-settings-vendoring) it with your application.

See [](#list-of-features) for details.

## Example

This is a very simple example that demonstrates how you can load settings from a config file and environment variables.

```{code-block} python
:caption: example.py

import attrs
import typed_settings as ts

@attrs.frozen
class Settings:
    option_one: str
    option_two: int

settings = ts.load(
    cls=Settings,
    appname="example",
    config_files=[ts.find("settings.toml")],
)
print(settings)
```

```{code-block} toml
:caption: settings.toml

[example]
option_one = "value"
```

```{code-block} console
$ EXAMPLE_OPTION_TWO=2 python example.py
Settings(option_one='value', option_two=2)
```

## Installation

% skip: start

Install and update using [pip](https://pip.pypa.io/en/stable/quickstart/):

```console
$ python -m pip install typed-settings
```

Typed Settings as **no required dependencies** (except for tomli on older Python versions).
You can install dependencies for optional features via

```console
$ python -m pip install typed-settings[<feature>]
```

Available features:

- `typed-settings[attrs]`: Enable settings classes via {program}`attrs`.
- `typed-settings[pydantic]`: Enable settings classes via {program}`Pydantic`.
- `typed-settings[cattrs]`: Enable usage of the powerful and fast {program}`cattrs` converter.
- `typed-settings[click]`: Enable support for {program}`Click` options.
- `typed-settings[option-groups]`: Enable support for {program}`Click** and **Click option groups`.
- `typed-settings[jinja]`: Enable support for value interpolation with {program}`Jinja` templates.
- `typed-settings[all]`: Install all optional requirements.

% skip: end

## Documentation

```{toctree}
:caption: 'Contents:'
:maxdepth: 2

why
getting-started
examples
guides/index
apiref
development
changelog
license
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
