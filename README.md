# Typed Settings

PoC for library for managing (typed) settings – for server processes as
well as commandline programms.


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


## Example

```python
from attr import frozen, field
import click

import typed_settings as ts


@frozen
class Host:
    name: str
    port: int = field(converter=int)


@frozen(kw_only=True)
class Settings:
    url: str
    default: int = 3
    host: Host = field(converter=lambda d: Host(**d))


settings = ts.load_settings(
    settings_cls=Settings, appname='example', config_files=['settings.toml']
)
print(settings)


@click.command()
@ts.click_options(Settings, 'example', ['settings.toml'])
def main(settings):
    print(settings)


if __name__ == '__main__':
    main()
```
