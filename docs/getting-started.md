# Getting Started

```{currentmodule} typed_settings
```

This page briefly explains how to install and use Typed Settings.
It gives you an overview of the most important features without going into detail.
At the end you'll find some hints how to proceed from here.

## Installation

Install {program}`typed-settings` into your [virtualenv]:

% skip: start

```console
$ python -m pip install typed-settings
```

Typed Settings has some optional dependencies for features that some people might not need:

Enable settings classes via {program}`attrs` and the {func}`settings()`, {func}`option()`, and {func}`secret()` shortcuts:
: ```console
  $ python -m pip install typed-settings[attrs]
  ```

Enable settings classes via {program}`Pydantic`:
: ```console
  $ python -m pip install typed-settings[pydantic]
  ```

Enable the powerful and fast {program}`cattrs` converter:
: ```console
  $ python -m pip install typed-settings[cattrs]
  ```

Support for {program}`Click` options:
: ```console
  $ python -m pip install typed-settings[click]
  ```

Support for {program}`Click` and {program}`click-option-groups`:
: ```console
  $ python -m pip install typed-settings[option-groups]
  ```

Support for value interpolation with {program}`Jinja` templates:
: ```console
  $ python -m pip install typed-settings[jinja]
  ```

Install all optional requirements:
: ```console
  $ python -m pip install typed-settings[all]
  ```

````{hint}
You can install multiple features by separating them with a `,`:

```console
$ python -m pip install typed-settings[click,jinja]
```
````

% skip: end


## Basic Settings Definition and Loading

Settings are defined as [attrs classes].
You can either use the decorators provided by `attrs` or the {func}`~typed_settings.cls_attrs.settings()` decorator which is an alias to {func}`attrs.define()`:

```python
import typed_settings as ts


@ts.settings
class Settings:
    username: str = ""
    password: ts.SecretStr = ""


settings = Settings("monty", ts.SecretStr("S3cr3t!"))
assert str(settings) == "Settings(username='monty', password='*******')"
```

{func}`~typed_settings.cls_attrs.secret()` is a wrapper for {func}`attrs.field()` and masks secrets when the settings instance is being printed.

Settings should (but are not required to) define defaults for all options.
If an option has no default and no config value can be found for it, an error will be raised by `attrs`.

In real life, you don't manually instantiate your settings.
Instead, you call the function {func}`load()`:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    username: str = ""
    password: ts.SecretStr = ""


settings = ts.load(Settings, appname="myapp")
print(settings)
```
```{code-block} console
$ python example.py
Settings(username='', password='')
```

The first argument of that function is your settings class and an instance of that class is returned by it.
The second argument is your *appname*.
That value is being used to determine the config file section and prefix for environment variables.
You can override both, though.

```{note}
{func}`load()` is designed to be easy to use and cover most use cases.
There is also {func}`load_settings()`, which allows you to explicitly specify which loaders to use with which configuration,
and how loaded settings are converted to the correct type.
```

## Settings from Environment Variables

The easiest way to override an option's default value is to set an environment variable.
Typed Settings will automatically look for environment variables matching {samp}`{APPNAME}_{OPTION_NAME}` (in all caps):

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    username: str = ""
    password: ts.SecretStr = ""


settings = ts.load(Settings, appname="myapp")
print(settings)
```
```{code-block} console
$ export MYAPP_USERNAME='monty'
$ export MYAPP_PASSWORD='S3cr3t!'
$ python example.py
Settings(username='monty', password='*******')
```

You can optionally change the prefix or disable loading environment variables completely.
The guide {ref}`guide-settings-from-env-vars` shows you how.

```{warning}
Never pass secrets via environment variables!

It's far easier for environment variables to leak outside than for config files.
You may, for example, accidentally leak your env via your CI/CD pipeline,
or you may be affected by a [security incident] for which you can't do anything.

Write your secret to a file and pass its path via a variable like {code}`MYAPP_API_TOKEN_FILE=/private/token` (instead of just {code}`MYAPP_API_TOKEN="3KX93ad..."`) to your app.
Alternatively, store it in a structured config file that you directly load with Typed Settings.
```

## Settings from Config Files

To pass secrets or to persist settings (and avoid exporting environment variables again and again), you may want to use config files.
Typed Settings supports TOML files ([Why?]) out-of-the-box and looks for the *appname* section by default:

```{code-block} toml
:caption: settings.toml

[myapp]
username = "monty"
password = "S3cr3t!"
```

```{code-block} python
:caption: example.py

from pathlib import Path

import typed_settings as ts


@ts.settings
class Settings:
    username: str = ""
    password: ts.SecretStr = ""


settings = ts.load(Settings, appname="myapp", config_files=["settings.toml"])
print(settings)
```

```console
$ python example.py
Settings(username='monty', password='*******')
```

You can also load settings from multiple files.
Subsequent files override the settings of their predecessors.

Appart from TOML, support for Python files is also built-in and you can add loaders for other file formats, too.

% TODO Add refs to file format guide

## Dynamically Finding Config Files

Sometimes, tools do not know the location of their config file in advance.
Take [black](https://black.readthedocs.io), for example, which searches for {file}`pyproject.toml` from the current working dir upwards until it reaches the project or file system root.

You can do the same with Typed Settings:

```{code-block} toml
:caption: settings.toml

[myapp]
username = "monty"
password = "S3cr3t!"
```

```{code-block} python
:caption: settings.py

from pathlib import Path

import typed_settings as ts


@ts.settings
class Settings:
    username: str = ""
    password: ts.SecretStr = ""


settings = ts.load(Settings, appname="myapp", config_files=[ts.find("settings.toml")])
print(settings)
```

```console
$ python settings.py
Settings(username='monty', password='*******')
```

{func}`~typed_settings.find()` returns a single path, so you can combine its result with a static list of files as shown in the section above.

## Dynamically Specifying Config Files

A third way to specify config files is via an environment variable.
By default, Typed Settings looks for a variable named {samp}`{APPNAME}_SETTINGS` (you can change or disable this).
The variable can contain one ore more paths separated by a colon (`:`):

```{code-block} toml
:caption: settings.toml

[myapp]
username = "monty"
password = "S3cr3t!"
```

```{code-block} python
:caption: settings.py
:emphasize-lines: 13

from pathlib import Path

import typed_settings as ts


@ts.settings
class Settings:
    username: str = ""
    password: ts.SecretStr = ""


settings = ts.load(Settings, appname="myapp")
print(settings)
```

```{code-block} console
$ export MYAPP_SETTINGS="settings.toml"
$ python settings.py
Settings(username='monty', password='*******')
```

Config files specified via an environment variable are loaded *after* statically defined ones.

Normally, no error will be raised if a config file does not exist.
However, you can mark files as *mandatory* if you want an error instead.
You can read more about this in the guide {ref}`guide-working-with-config-files`.

## Command Line Interfaces

Some tools (like {ref}`example-pytest` or {ref}`example-twine`) allow you store settings in a config file and override them on-the-fly via command line options.

Typed Settings can integrate with [argparse] and [click] and
can automatically create command line options for your settings.
When you run your app, settings will first be loaded from config files and environment variables.
The loaded values then serve as defaults for the corresponding CLI options.

Your CLI function receives all options as the single instance of your settings class.

Below you'll find two examples how to generate an Argparse and a Click CLI.

### Argparse

```{code-block} python
:caption: cli.py

import typed_settings as ts


@ts.settings
class Settings:
    username: str = ts.option(help="Your username")
    password: str = ts.secret(help="Your password")


@ts.cli(Settings, "myapp")
def cli(settings: Settings) -> None:
    """My App"""
    print(settings)


if __name__ == "__main__":
    cli()
```

```console
$ python cli.py --help
usage: cli.py [-h] --username TEXT --password TEXT

My App

options:
  -h, --help       show this help message and exit

Settings:
  Settings options

  --username TEXT  Your username [required]
  --password TEXT  Your password [required]
$ python cli.py --username="guido" --password="1234"
Settings(username='guido', password='*******')
```

### Click

```{code-block} python
:caption: cli.py

import click
import typed_settings as ts


@ts.settings
class Settings:
    username: str = ts.option(help="Your username")
    password: ts.SecretStr = ts.secret(help="Your password")


@click.command()
@ts.click_options(Settings, "myapp")
def cli(settings):
    """My App"""
    print(settings)


if __name__ == "__main__":
    cli()
```

```console
$ python cli.py --help
Usage: cli.py [OPTIONS]

  My App

Options:
  --username TEXT  Your username  [required]
  --password TEXT  Your password  [required]
  --help           Show this message and exit.
$ python cli.py --username="guido" --password="1234"
Settings(username='guido', password='*******')
```

______________________________________________________________________

See {doc}`guides/clis-argparse-or-click` for details.

(relative-paths)=

## (Relative) Paths

Since version 23.1.0, Typed Settings automatically resolves all loaded paths relative to the source they are loaded from.

Paths loaded from config files are resolved relative to the parent directory of the respective file.
Paths loaded by other loaders (e.g., from environment variables or command line args) are resolved relative to the user's current working directory *(CWD)*.

But why is this useful?

Imagine the following scenario:

- You use the {file}`pyproject.toml` to configure include/exclude lists for files.
- These lists can also be overwritten via command line arguments.
- The user invokes your application from a sub directory (e.g., {file}`tests/`).
- The settings passed to your application contain the path {file}`spam.txt` in the exclude list.

If that {file}`spam.txt` originated from {file}`pyproject.toml`,
it should probably be relative to the project root.
If it was passed via the command line,
it should probably be relative to the {file}`tests/` directory, though.

Your app has no chance to differentiate between those two situations.
That's why typed settings resolves paths by default.

```{admonition} How does it work?
:class: hint

Every loader stores some meta data in a context object.
This includes the "current working directory" from the loader's point of view.

Typed settings keeps this context for each loaded option value.
When option values are converted to the target type,
the corresponding loader context is restored.
That means, Python's *CWD* is temporarily set to the loaders *CWD* so that relative paths are resolved as expected.
```

```{admonition} How to disable this behavior?
:class: tip

If you don't want paths to be resolved,
manually create a converter via {func}`~typed_settings.converters.default_converter()`  with `resolve_paths=False` and
pass that converter to {func}`~typed_settings.load_settings()`.
```

## Frozen Settings and Updating Them

Settings are mutable by default but can optionally be made immutable:

```
>>> import typed_settings as ts
>>>
>>> @ts.settings(frozen=True)
... class FrozenSettings:
...     x: int
...     y: list
...
>>> settings = FrozenSettings(3, [])
>>> settings.x = 4
Traceback (most recent call last):
  ...
attr.exceptions.FrozenInstanceError
```

However, this does not extend to mutable option values:

```
>>> settings.y.append(4)
>>> print(settings)
FrozenSettings(x=3, y=[4])
```

Immutable settings can be desirable because they prevent you or your users from (accidentally) changing them while the app is running.

However, when you are testing your app, you may still want to modify your settings.
You can create an updated copy of your settings via {func}`~typed_settings.cls_attrs.evolve()`, which is a recursive version of {func}`attrs.evolve()`:

```
>>> updated = ts.evolve(settings, x=7)
>>> print(settings)
FrozenSettings(x=3, y=[4])
>>> print(updated)
FrozenSettings(x=7, y=[4])
>>> settings is updated
False
```

## How to Proceed

If you have read this far, you should now have a basic understanding of how Typed Settings works and what it is capable of ([No, I still don't have a clue!]).

Depending on what kind of learner you are, you can now either

- continue reading the {doc}`guides/index` that explain all of Typed Settings' features in-depth or
- take a lookt at the {doc}`examples` that demonstrate how Typed Settings can be used or how to achieve different kinds of goals.

[argparse]: https://docs.python.org/3/library/argparse.html
[attrs classes]: https://www.attrs.org/en/stable/examples.html
[click]: https://click.palletsprojects.com
[no, i still don't have a clue!]: https://gitlab.com/sscherfke/typed-settings/-/issues/new?issue[title]=Please%20improve%20Getting%20Startet%20section%20XYZ
[security incident]: https://thehackernews.com/2021/09/travis-ci-flaw-exposes-secrets-of.html
[virtualenv]: https://virtualenv.pypa.io/en/stable/
[why?]: https://www.python.org/dev/peps/pep-0518/#other-file-formats
