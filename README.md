[![Documentation Status](https://readthedocs.org/projects/typed-settings/badge/?version=latest)](https://typed-settings.readthedocs.io/en/latest/?badge=latest)
[![Pipeline Status](https://gitlab.com/sscherfke/typed-settings/badges/main/pipeline.svg)](https://gitlab.com/sscherfke/typed-settings/-/commits/main)
[![Coverage Report](https://gitlab.com/sscherfke/typed-settings/badges/main/coverage.svg)](https://gitlab.com/sscherfke/typed-settings/-/commits/main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# Typed Settings

This package allows you to cleanly structure your settings with [attrs](https://www.attrs.org) classes.
Type annotations will be used to automatically convert values to the
proper type[^1].
You can currently load settings from these sources:

- TOML files (multiple, if you want to).  Paths can statically specified or dynamically set via a environment variable.
- Environment variables
- [click](https://click.palletsprojects.com) command line options

You can use Typed settings, e.g., for

- server processes
- containerized apps
- command line applications

[^1]: Not yet: https://github.com/python-attrs/attrs/pull/653

## Examples

### Hello, World!, with env. vars.

This is a very simple example that demonstrates how you can load settings from environment variables.

```python
# example.py
import typed_settings as ts

@ts.settings
class Settings:
    option: str

settings = ts.load_settings(cls=Settings, appname="example")
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
import click

import typed_settings as ts

@ts.settings
class Host:
    name: str
    port: int = ts.option(converter=int)

@ts.settings(kw_only=True)
class Settings:
    host: Host = ts.option(converter=lambda d: Host(**d))
    endpoint: str
    retries: int = 3

settings = ts.load_settings(
    cls=Settings, appname='example', config_files=['settings.toml']
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


### Click

Optionally, click options can be generated for each option.  Config files and environment variables will still be read and can be overriden by passing command line options.


```python
# example.py
import click
import typed_settings as ts

@ts.settings
class Settings:
    a_str: str = "default"
    an_int: int = 3

@click.command()
@ts.click_options(Settings, 'example')
def main(settings):
    print(settings)

if __name__ == '__main__':
    main()
```

```console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --a-str TEXT      [default: default]
  --an-int INTEGER  [default: 3]
  --help            Show this message and exit.
$ python example.py --a-str=spam --an-int=1
Settings(a_str='spam', an_int=1)
```


## Requirements

- Default settings are defined by app and can be overridden by config
  files, environment variables and click options.

- You define settings as attrs class with types, converters and
  validators.

- Attributes are basic data types (bool, int, float, str), lists of
  basic types, or nested settings classes.

- Settings can be loaded from multiple config files.

- Config files are allowed to contain settings for multiple apps (like
  `pyproject.toml`)

- Paths to config files have to be explicitly named.  Most defaults are
  not useful in many cases and have to be changed anyways.

- Additional paths for config files can be specified via an environment
  variable.  As in `PATH`, multiple paths are separated by a `:`.  The
  last file in the list has the highest priority.

- Environment variables with a defined prefix override settings from
  config files.  This can optionally be disabled.

- [Click](https://click.palletsprojects.com/) options for some or all
  settings can be generated.  They are passed to the cli function as
  a single object (instead of individually).

- Settings must be explicitly loaded, either via
  `typed_settings.load_settings()` or via
  `typed_settings.click_options()`.

- Both functions allow you to customize config file paths, prefixes et
  cetera.
