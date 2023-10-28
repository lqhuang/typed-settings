```{currentmodule} typed_settings
```

(guide-working-with-config-files)=
# Config Files

## Basics

Besides environment variables, configuration files are another basic way to configure applications.

There are several locations where configuration files are usually stored:

- In the system's main configuration directory (e.g., {file}`/etc/myapp/settings.toml`)
- In your users' home (e.g., {file}`~/.config/myapp.toml` or {file}`~/.myapp.toml`)
- In your project's root directory (e.g., {file}`~/Projects/myapp/pyproject.toml`)
- In your current working directory
- At a location pointed to by an environment variable (e.g., {code}`MYAPP_SETTINGS=/run/private/secrets.toml`)
- …

As you can see, there are many possibilities and depending on your app, any of them may make sense (or not).

That's why Typed Settings has *no* default search paths for config files but lets you very flexibly configure them:

- You can specify a static list of search paths
- You can search for specific files at runtime
- You can specify search paths at runtime via an environment variable

When multiple files are configured, Typed Settings loads every file that it finds.
Each file that is loaded updates the settings that have been loaded so far.

## Optional and Mandatory Config Files

Config files – no matter how they are configured – are *optional* by default.
That means that no error is raised if some (or all) of the files do not exist:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    option1: str = "default"
    option2: str = "default"


# Not an error:
print(ts.load(Settings, "myapp", config_files=["/spam"]))
```
```{code-block} console
$ python example.py
Settings(option1='default', option2='default')
```

You can mark files as *mandatory* by prefixing them with {code}`!`:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    option1: str = "default"
    option2: str = "default"


# Raises an error:
print(ts.load(Settings, "myapp", config_files=["!/spam"]))
```
```{code-block} console
$ python example.py
Mandatory config file not found: /spam
Traceback (most recent call last):
...
FileNotFoundError: [Errno 2] No such file or directory: '/spam'
```

## Static Search Paths

You can pass a static list of files to {func}`load()` and {func}`~typed_settings.loaders.FileLoader`.
Paths can be strings or instances of {class}`pathlib.Path`.
If multiple files are found, they are loaded from left to right.  That means that the last file has the highest precedence.

The following example first loads a global configuration file and overrides it with user specific settings:

```python
from pathlib import Path

import typed_settings as ts


@ts.settings
class Settings:
    option: str = ""


config_files = [
    "/etc/myapp/settings.toml",
    Path.home().joinpath(".config", "myapp.toml"),
]
ts.load(Settings, "myapp", config_files)
```

```{tip}
You should not hard-code configuration directories like {file}`/etc` or {file}`~/.config`.
The library [platformdirs] (a friendly fork of the inactive Appdirs) determines the correct paths depending on the user's operating system.

[platformdirs]: https://platformdirs.readthedocs.io/en/latest/
```

## Finding Files at Runtime

Some tools, especially those that are used for software development (i.e. linters or code formatters), search for their configuration in the current (Git) project.

The function {func}`find()` does exactly that: It searches for a given filename from the current working directory upwards until it hits a defined stop directory or file.
By default it stops when the current directory contains a {file}`.git` or {file}`.hg` folder.
When the file is not found, it returns {file}`./{filename}`.

You can append the {class}`pathlib.Path` that this function returns to the list of static config files as described in the section above:

```python
import typed_settings as ts


@ts.settings
class Settings:
    option: str = ""


config_files = [
    Path.home().joinpath(".config", "mylint.toml"),
    ts.find("mylint.toml"),
]
ts.load(Settings, "mylint", config_files)
```

(guide-using-pyproject-toml)=

## Using `pyproject.toml`

Since Typed Settings supports TOML files out-of-the box, you may wish to use {file}`pyproject.toml` for your tool's configuration.

There are two things you need to do:

- Use {func}`find()` to find the {file}`project.toml` from anywhere in a project.
- Override the default section name and [use the "tool." prefix](https://www.python.org/dev/peps/pep-0518/#id28).

```{code-block} python
:caption: example.py

from pathlib import Path

import typed_settings as ts


@ts.settings
class Settings:
    src_dir: Path = Path()


settings = ts.load(
      Settings,
      "myapp",
      [ts.find("pyproject.toml")],
      config_file_section="tool.myapp",
)
assert settings.src_dir.is_dir()
print(settings)
```

To demonstrate this, we'll first create a "fake project" with a {file}`pyproject.toml` and a {file}`src/` directory.

We will also `cd` into the `src/` directory to demonstrate that relative paths loaded from config files are by default resolved relative to the corresponding config file ()
and change our working directory to its {file}`src` directory (see [](#relative-paths) for details).

```{code-block} toml
:caption: myproject/pyproject.oml

[tool.myapp]
src_dir = "src"
```
```{code-block} console
$ mkdir -p myproject/src
$ cd myproject/src
$ python ../../example.py
Settings(src_dir=PosixPath('/.../myproject/src'))
```

```{hint}
If you added CLI options to the example above and
invoked it with from `src/` with `python ../../example.py --src-dir=.`,
`src_dir` would be relative to the current working directory and be resolved to `.../myproject/src`.
```

### Using an additional tool specific config file

Things get a little more complicated when you want to use {file}`pyproject.toml` as well as a tool specific configuration file.

You have to use {func}`load_settings()` in this case and
configure it with a {class}`~typed_settings.loaders.FileLoader`.
This loader must in turn be configured with two {class}`~typed_settings.loaders.TomlFormat` instances --
one for the {file}`pyproject.toml` and one for "normal" TOML files:

```{code-block} python
:caption: example.py

from pathlib import Path

import typed_settings as ts
import typed_settings.loaders


@ts.settings
class Settings:
    a: str = "default"
    b: str = "default"
    c: str = "default"


settings = ts.load_settings(
      Settings,
      loaders=[
          typed_settings.loaders.FileLoader(
              formats={
                  "pyproject.toml": typed_settings.loaders.TomlFormat("tool.myapp"),
                  "*.toml": typed_settings.loaders.TomlFormat("myapp"),
              },
              files=[
                  ts.find("pyproject.toml"),  # Read this file first so that
                  ts.find("myapp.toml"),  # this file has a higher precedence
              ],
          )
      ],
)
print(settings)
```
```{code-block} toml
:caption: pyproject.toml

[tool.myapp]
a = "from pyproject"
b = "from pyproject"
```
```{code-block} toml
:caption: myapp.toml

[myapp]
a = "from myapp"
```
```{code-block} console
$ python example.py
Settings(a='from myapp', b='from pyproject', c='default')
```


## Dynamic Search Paths via Environment Variables

Sometimes, you don't know the location of your configuration files in advance.
Sometimes, you don't even know where to search for them.
This may, for example, be the case when your app runs in a container and the configuration files are mounted to an arbitrary location inside the container.

For these cases, Typed Settings can read search paths for config files from an environment variable.
If you use {func}`load()`, its name is derived from the *appname* argument and is {samp}`{APPNAME}_SETTINGS`.

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    option1: str = "default"
    option2: str = "default"


settings = ts.load(Settings, "myapp")
print(settings)
```
```{code-block} toml
:caption: conf1.toml

[myapp]
option1 = "spam"
option2 = "spam"
```
```{code-block} toml
:caption: conf2.toml

[myapp]
option1 = "eggs"
```

Multiple paths are separated by `:`, similarly to the `$PATH` variable.
However, in contrast to {code}`PATH`, *all* existing files are loaded one after another:

```{code-block} console
$ export MYAPP_SETTINGS="conf1.toml:conf2.toml"
$ python example.py
Settings(option1='eggs', option2='spam')
```

You can override the default using the *config_files_var* argument:

```{code-block} python
:caption: example.py
:emphasize-lines: 10

import typed_settings as ts


@ts.settings
class Settings:
    option1: str = "default"
    option2: str = "default"


settings = ts.load(Settings, "myapp", config_files_var="MY_SETTINGS")
print(settings)
```
```{code-block} console
$ export MY_SETTINGS="conf2.toml"
$ python example.py
Settings(option1='eggs', option2='default')
```

If you set it to {code}`None`, loading filenames from an environment variable is disabled:

```{code-block} python
:caption: example.py
:emphasize-lines: 10

import typed_settings as ts


@ts.settings
class Settings:
    option1: str = "default"
    option2: str = "default"


settings = ts.load(Settings, "myapp", config_files_var=None)
print(settings)
```
```{code-block} console
$ export MYAPP_SETTINGS="conf1.toml:conf2.toml"
$ python example.py
Settings(option1='default', option2='default')
```

## Config File Precedence

Typed-Settings loads all files that it finds and merges their contents with all previously loaded settings.

The list of static files (passed to {func}`load()` or {class}`~typed_settings.loaders.FileLoader`) is always loaded first.
The files specified via an environment variable are loaded afterwards:


## Adding Support for Additional File Types

The function {func}`load()` uses a {class}`~typed_settings.loaders.FileLoader` that (currently) only supports TOML files (via {class}`~typed_settings.loaders.TomlFormat`).

However, the supported file formats are not hard-coded but can be configured and extended.

If you use {func}`load_settings()`, you can (and must) pass a custom {class}`~typed_settings.loaders.FileLoader` instance that can be configured with loaders for different file formats.

Let's assume we also want to load settings from Python files
because we need its flexibility for some dynamic option values:

```{code-block} python
:caption: conf.py

class MYAPP:
    OPTION1 = "spam"
```
```{warning}
The Python format is not used by default since it allows users to feed arbitrary Python code into your application.

You should only use it if you control your app _and_ the config files and
realy need the added flexibility!
```

Not let's configure our app accordingly:

```{code-block} python
:caption: example.py

import typed_settings as ts
from typed_settings.loaders import PythonFormat, TomlFormat


@ts.settings
class Settings:
    option1: str = "default"
    option2: str = "default"


file_loader = ts.FileLoader(
    formats={
        # A dict mapping glob patterns for config file to FileFormats
        "*.toml": TomlFormat(section="myapp"),
        "*.py": PythonFormat("MYAPP", key_transformer=PythonFormat.to_lower),
    },
    files=["conf.py"],
    env_var=None,
)
settings = ts.load_settings(Settings, loaders=[file_loader])
print(settings)
```

Now we can load settings from Python files:

```{code-block} console
$ python example.py
Settings(option1='spam', option2='default')
```


### Writing a File Format Loader

File format loaders must implement the {class}`~typed_settings.loaders.FileFormat` protocol:

- They have to be callables (i.e., functions, or a classes with a {meth}`~object.__call__()` method).
- They have to accept a {class}`~pathlib.Path`, the user's settings class and a list of {class}`typed_settings.types.OptionInfo` instances.
- They have to return a dictionary with the loaded settings.

~~~{admonition} Why return a {code}`dict` and not a settings instance?
:class: hint

(File format) loaders return a dictionary with loaded settings instead of instances of the user's settings class.

There are two reasons for this:
- The a config file might not contain values for all options, so it might not be possible to instantiate the settings class.
- Dicts can easier be created (most libs for TOML, JSON, or YAML return dicts) an merged than class instances.

Typed Settings validates and cleans the loaded settings from all loaders automatically and
converts them to instances of your settings class.
~~~

A very simple JSON loader could look like this:

```python
import json

def load_json(path, _settings_cls, _options):
    return json.load(path.open())
```

If you want to use this in production, you should add proper error handling and documentation, though.
You can take the {class}`~typed_settings.loaders.TomlFormat` as an example.

Using your file format loader works like in the examples above:

```{code-block} python
:caption: example.py

import json

import typed_settings as ts


@ts.settings
class Settings:
    option1: str
    option2: str


def load_json(path, _settings_cls, _options):
    return json.load(path.open())


file_loader = ts.FileLoader(
    formats={"*.json": load_json},
    files=["!conf.json"],
)
settings = ts.load_settings(Settings, loaders=[file_loader])
print(settings)
```
```{code-block} json
:caption: conf.json

{
    "option1": "spam",
    "option2": "eggs"
}
```
```{code-block} console
$ python example.py
Settings(option1='spam', option2='eggs')
```
