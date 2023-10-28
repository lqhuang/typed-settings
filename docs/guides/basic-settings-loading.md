```{currentmodule} typed_settings
```

# Basic Settings Loading

Typed Settings exposes two functions for loading settings: {func}`load()` and {func}`load_settings()`.
This page describes the difference between these two.

## Simple API: `load()`


The {func}`load()` function provides a simplified API for the common case.
It uses the following configuration:

- First load from TOML files (see {class}`~typed_settings.loaders.FileLoader`).
- Then load from environment variables (see {class}`~typed_settings.loaders.EnvLoader`).
- Derives settings for these loaders from your `appname` (but some settings can be overridden, see below).
- Don't use any post processors.
- Use the default converter returned by {func}`default_converter()`.

What you can configure:

- Change the config file section (default: `{appname}`).
- Change the name for the environment variable that lists paths for settings files or disable this feature (default: `{APPNAME}_SETTINGS`).
- Change the prefix for environment varialbes for options (default: `{APPNAME}_`).

One use case for it is loading settings from a {file}`pyproject.toml`:

```{code-block} python
:caption: example.py

import typed_settings as ts

@ts.settings
class Settings:
    option_one: str
    option_two: int

settings = ts.load(
    cls=Settings,
    appname="example",
    config_files=[ts.find("pyproject.toml")],
    config_file_section="tool.example",
)
print(settings)
```

```{code-block} toml
:caption: pyproject.toml
[project]
# ...

[tool.example]
option_one = "value"
```

```{code-block} console
$ EXAMPLE_OPTION_TWO=2 python example.py
Settings(option_one='value', option_two=2)
```

## Full API: `load_settings()`

The function {func}`load_settings()` lets you configure everything in detail.

Here is the same example from above but without shortcuts for loader configuration:

```{code-block} python
:caption: example.py

import attrs
import typed_settings as ts
import typed_settings.converters
import typed_settings.loaders

@ts.settings
class Settings:
    option_one: str
    option_two: int

settings = ts.load_settings(
    cls=Settings,
    loaders=[
      typed_settings.loaders.FileLoader(
          files=[ts.find("pyproject.toml")],
          formats={"*.toml": typed_settings.loaders.TomlFormat("tool.example")},
      ),
      typed_settings.loaders.EnvLoader(prefix="EXAMPLE_"),
    ],
    processors=[],
    converter=typed_settings.converters.default_converter(),
)
print(settings)
```

```{code-block} toml
:caption: pyproject.toml
[project]
# ...

[tool.example]
option_one = "value"
```

```{code-block} console
$ EXAMPLE_OPTION_TWO=2 python example.py
Settings(option_one='value', option_two=2)
```

```{note}
`load(cls, **kwargs)` is basically the same as `load_settings(cls, default_loaders(**kwargs), default_converter())`.
```

---

The following pages will demonstrate it's usage for various use cases.
