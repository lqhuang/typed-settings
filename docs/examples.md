---
tocdepth: '2'
---

# Examples

```{currentmodule} typed_settings
```

This pages demonstrates Typed Setting's features in a real application context.
We'll reimplement the settings loading functionality of various existing (and probably well-known) tools and libraries.
In this way we combine the known with the new.

## Black

[Black](https://github.com/psf/black>) – the uncompromising code formatter - uses a project's {file}`pyproject.toml` for its settings.
It finds the file even when you are in a sub directory of the project.
Settings can be overridden by command line arguments.

### What you'll learn

- Using {file}`pyproject.toml` and finding it from sub directories.
- Using an {class}`~enum.Enum` for settings values.
- Adding command line arguments.

### The settings file

```{literalinclude} examples/black-pyproject.toml/pyproject.toml
:caption: pyproject.toml
```

### The code

First we define our settings class and the Enum that holds all supported Python versions.

We then create a click command.
The decorator {func}`click_options()` creates command line options and makes Click pass an instance of our settings class to the CLI function.

The decorator needs to know our settings class and which loaders to use.

We'll use the default loaders and tell them:

- how our app is called
- which config files to load (find "pyproject.toml")
- the config file section to read from
- to disable loading settings from environment variables

```{literalinclude} examples/black-pyproject.toml/black.py
:emphasize-lines: 9-29,32-43
```

### Trying it out

Before we run our code, we'll take a look at the generated `--help`.
Note, that the default line length is 79, which we read from {file}`pyproject.toml`.

```{literalinclude} examples/black-pyproject.toml/test.console
:emphasize-lines: 1,11
:language: console
```

(example-python-gitlab)=

## Python-Gitlab

[Python-gitlab](https://python-gitlab.readthedocs.io) is a GitLab API client.
It loads configuration from a config file in your home directory.
That file has multiple sections:
One for general settings and one for each GitLab account that you use.

### What you'll learn

- Loading config files from a fixed location.
- Loading different settings types from a single file.
- Using secret settings.

### The settings file

```{literalinclude} examples/python-gitlab/python-gitlab.toml
:caption: python-gitlab.toml
```

### The code

We need two different settings schemes: One for the global settings and one for the GitLab account settings.
We declare our API tokens as secret settings
This way, they won't be shown in clear text when we print our settings.

We also need to call {func}`load()` twice.
Both calls use the same application name and load the same config files, but they read different sections from it.

```{note}
We load the the settings file from the current working directory in this example.
In real life, you should use [platformdirs](https://github.com/platformdirs/platformdirs) as shown in the commented line.
```

```{literalinclude} examples/python-gitlab/python_gitlab.py
```

### Trying it out

```{literalinclude} examples/python-gitlab/test.console
:emphasize-lines: 1
:language: console
```

As you can see, we loaded the `[general]` section and the `[gitlab-com]` section.

Also note that the API token is not displayed in clear text but as `***`.
This makes it safe to pass loaded settings to your [favorite logger](https://structlog.org).

(example-twine)=

## .pypirc

The file {file}`~/.pypirc` is, for example, used by [twine](https://twine.readthedocs.io) which publishes your Python packages to [PyPI](https://pypi.org/).

### What you'll learn

- Loading config files from a fixed location.
- Loading different settings types from a single file.
- Avoiding a `[global]` section for just listing other sections.
- Using secret settings.

This example is implemented in two variants.

### Original

The original version uses a `[global]` section to list all configured accounts.
A config file section must exist for each entry in that list.

It's implementation is very similar to the {ref}`example-python-gitlab` example.

#### The settings file

```{literalinclude} examples/pypirc_0/pypirc.toml
:caption: pypirc.toml
```

#### The code

```{literalinclude} examples/pypirc_0/pypirc_0.py
```

#### Trying it out

```{literalinclude} examples/pypirc_0/test.console
:language: console
```

### Improved

The second one uses nested settings classes and TOML's support for dictionaries to avoid the `[global]` section.

The main difference is that {code}`Settings.repos` is now a {code}`dict[str, Repository]` instead of a {code}`list[str]`,
so it's a lot easier to load and acces the repo settings.

#### The settings file

```{literalinclude} examples/pypirc_1/pypirc.toml
:caption: pypirc.toml
```

#### The code

```{literalinclude} examples/pypirc_1/pypirc_1.py
```

#### Trying it out

```{literalinclude} examples/pypirc_1/test.console
:language: console
```

(example-pytest)=

## Pytest

[Pytest](https://docs.pytest.org) is *the* testing framework for Python.

You can configure it with a config file and override each option via a command line flag.

Pytest is also dynamically extensible with plugins.
Plugins can add new config options and command line arguments.
To keep the `--help` output somewhat readable, all options are grouped by plugin.

### What you'll learn

- Dynamically creating settings for applications with a plug-in system.
- Customizing how click options are created.  This includes:
  - Setting help texts
  - Changing the parameter declaration ("what the option looks like")
  - Creating switches for boolean options
- Creating command line applications for your settings
- Using click options groups for nested settings

### The code

We first create two settings classes for our plugins: {code}`Coverage` and :`Emoji`.

The option {code}`Coverage.src` override its option name to be {samp}`--cov` instead of {samp}`--{prefix}-src`.

We then define Pytest's base settings.
They also override the Click parameter declarations and add help texts for the options.

The next step is to combine the base settings with the settings of of all Plugins.
We use {func}`~typed_settings.cls_attrs.combine()` for that which is a convenience wrapper around {func}`attrs.make_class()`.

Now that we have a class that contains Pytests own settings as well as the settings of all plugins,
we can create a command line application.
We create option groups by passing {class}`~typed_settings.cli_click.OptionGroupFactory` to {func}`.click_options()`.

```{literalinclude} examples/pytest-plugins/pytest.py
```

### Trying it out

```{literalinclude} examples/pytest-plugins/test.console
:emphasize-lines: 1,18
:language: console
```

You can see that the help output contains all options from Pytest itself and all loaded plugins.
Their options are also nicely grouped together and have help texts.

The second invocation prints the loaded settings.
You can see how the combined settings class looks like.
