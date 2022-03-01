======
Guides
======

.. currentmodule:: typed_settings

``load()`` vs. ``load_settings()``
==================================

Typed Settings exposes two functions for loading settings: :func:`load()` and :func:`load_settings()`.
The former is designed to make the common use cases easy.
The latter makes special cases possible and lets you configure everything in detail.

``load()``
----------

- Uses the file and environment variable loader.

- Only supports TOML files.

- Derives settings for loaders from your *appname* (but some settings can be overridden).

- Uses a default Cattrs converter.


``load_settings()``
-------------------

- You need to explicitly pass the list of loaders.

- You need to explicitly configure each loader.

- You can pass a custom/extended Cattrs converter.

.. note::

   ``load(cls, ...)`` is basically the same as ``load_settings(cls, default_loaders(...), default_converter())``.


.. _guide-settings-from-env-vars:

Settings from Environment Variables
===================================

Typed Settings loads environment variables that match :code:`{PREFIX}{OPTION_NAME}`.

:samp:`{PREFIX}` is an option for the :class:`~typed_settings.loaders.EnvLoader`.
It should be UPPER_CASE and end with an `_`, but this is not enforced.
:samp:`{PREFIX}` can also be an empty string.

If you use :func:`load()` (or :func:`default_loaders()`), :samp:`{PREFIX}` is derived from the *appname* argument.  For example, :code:`"appname"` becomes :code:`"APPNAME_"`.
You can override it with the *env_prefix* argument.
You can also completely disable environment variable loading by setting *env_prefix* to :code:`None`.

Values loaded from environment variables are strings.
They are converted to the type specified in the settings class via a Cattrs converter.
The :func:`~typed_settings.converters.default_converter()` supports the most common types like booleans, dates, enums and paths.

.. warning::

   Never pass secrets via environment variables!

   It's far easier for environment variables to leak outside than for config files.
   You may, for example, accidentally leak your env via your CI/CD pipeline,
   or you may be affected by a `security incident`_ for which you can't do anything.

   Write your secret to a file and pass its path via a variable like :code:`MYAPP_API_TOKEN_FILE=/private/token` (instead of just :code:`MYAPP_API_TOKEN="3KX93ad..."`) to your app.
   Alternatively, store it in a structured config file that you directly load with Typed Settings.

   .. _security incident: https://thehackernews.com/2021/09/travis-ci-flaw-exposes-secrets-of.html


Nested settings
---------------

Settings classes can be nested but environment variables have a flat namespace.
So Typed Settings builds a flat list of all option and uses the "dotted path" to an attribute (e.g., :code:`attrib.nested_attrib.nested_nested_attrib`) for mapping flat names to nested attributes.

Here's an example:

.. code-block:: python

    >>> import os
    >>> import typed_settings as ts
    >>>
    >>> @ts.settings
    ... class Nested:
    ...     attrib1: int = 0
    ...     attrib2: bool = True
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     nested: Nested = Nested()
    ...     attrib: str = ""
    >>>
    >>> os.environ["MYAPP_ATTRIB"] = "spam"
    >>> os.environ["MYAPP_NESTED_ATTRIB1"] = "42"
    >>> os.environ["MYAPP_NESTED_ATTRIB2"] = "0"
    >>>
    >>> ts.load(Settings, "myapp")
    Settings(nested=Nested(attrib1=42, attrib2=False), attrib='spam')

.. warning::

   :code:`Settings` should not define an attribute :code:`nested_attrib1` as it would conflict with :code:`nested.attrib1`.
   If you added this attribute to the example above, the value ``42`` would be assigned to both options.


Overriding the var name for a single option
-------------------------------------------

Sometimes, you may want to read an option from another variable than Typed Settings would normally do.
For example, you company's convention might be to use :code:`SSH_PRIVATE_KEY_FILE`, but your app would look for :code:`MYAPP_SSH_KEY_FILE`:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     ssh_key_file: str = ""
    >>>
    >>> ts.load(Settings, "myapp")
    Settings(ssh_key_file='')

In order to read from the desired env var, you can use :func:`os.getenv()` and assign its result as default for your option:

.. code-block:: python

    >>> import os
    >>>
    >>> os.environ["SSH_PRIVATE_KEY_FILE"] = "/run/private/id_ed25519"
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     ssh_key_file: str = os.getenv("SSH_PRIVATE_KEY_FILE", "")
    >>>
    >>> ts.load(Settings, "myapp")
    Settings(ssh_key_file='/run/private/id_ed25519')


.. _guide-working-with-config-files:

Working with Config Files
=========================

Besides environment variables, configuration files are another basic way to configure applications.

There are several locations where configuration files are usually stored:

- In the system's main configuration directory (e.g., :file:`/etc/myapp/settings.toml`)
- In your users' home (e.g., :file:`~/.config/myapp.toml` or :file:`~/.myapp.toml`)
- In your project's root directory (e.g., :file:`~/Projects/myapp/pyproject.toml`)
- In your current working directory
- At a location pointed to by an environment variable (e.g., :code:`MYAPP_SETTINGS=/run/private/secrets.toml`)
- …

As you can see, there are many possibilities and depending on your app, any of them may make sense (or not).

That's why Typed Settings has *no* default search paths for config files but lets you very flexibly configure them:

- You can specify a static list of search paths
- You can search for specific files at runtime
- You can specify search paths at runtime via an environment variable

When multiple files are configured, Typed Settings loads every file that it finds.
Each file that is loaded updates the settings that have been loaded so far.


Optional and Mandatory Config Files
-----------------------------------

Config files – no matter how they are configured – are *optional* by default.
That means that no error is raised if some (or all) of the files do not exist:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     option1: str = "default"
    ...     option2: str = "default"
    >>>
    >>> # Not an error:
    >>> ts.load(Settings, "myapp", config_files=["/spam"])
    Settings(option1='default', option2='default')

You can mark files as *mandatory* by prefixing them with :code:`!`:

.. code-block:: python

    >>> # Raises an error:
    >>> ts.load(Settings, "myapp", config_files=["!/spam"])
    Traceback (most recent call last):
    ...
    FileNotFoundError: [Errno 2] No such file or directory: '/spam'


Static Search Paths
-------------------

You can pass a static list of files to :func:`load()` and :func:`~typed_settings.loaders.FileLoader`.
Paths can be strings or instances of :class:`pathlib.Path`.
If multiple files are found, they are loaded from left to right.  That means that the last file has the highest precedence.

The following example first loads a global configuration file and overrides it with user specific settings:

.. code-block:: python

    >>> from pathlib import Path
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     option: str = ""
    >>>
    >>> config_files = [
    ...     "/etc/myapp/settings.toml",
    ...     Path.home().joinpath(".config", "myapp.toml"),
    ... ]
    >>> ts.load(Settings, "myapp", config_files)
    Settings(option='')

.. note::

    You should not hard-code configuration directories like :file:`/etc` or :file:`~/.config`.
    The library platformdirs_ (a friendly fork of the inactive Appdirs) determines the correct paths depending on the user's operating system.


    .. _platformdirs: https://platformdirs.readthedocs.io/en/latest/


Finding Files at Runtime
------------------------

Especially tools that are used for software development (i.e. linters or code formatters) search for their configuration in the current (Git) project.

The function :func:`find()` does exactly that: It searches for a given filename from the current working directory upwards until it hits a defined stop directory or file.
By default it stops when the current directory contains a :file:`.git` or :file:`.hg` folder.
When the file is not found, it returns :file:`./{filename}`.

You can append the :class:`pathlib.Path` that this function returns to the list of static config files as described in the section above:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     option: str = ""
    >>>
    >>> config_files = [
    ...     Path.home().joinpath(".config", "mylint.toml"),
    ...     ts.find("mylint.toml"),
    ... ]
    >>> ts.load(Settings, "mylint", config_files)
    Settings(option='')


.. _guide-using-pyproject-toml:

Using ``pyproject.toml``
^^^^^^^^^^^^^^^^^^^^^^^^

Since Typed Settings supports TOML files out-of-the box, you may wish to use :file:`pyproject.toml` for your tool's configuration.

There are just two things you need to do:

- Use :func:`find()` to find the :file:`project.toml` from anywhere in your project.
- Override the default section name and `use the "tool." prefix`_.

To demonstrate this, we'll first create a "fake project" and change our working directory to its :file:`src` directory:

.. code-block:: python

    >>> # Create a "project" in a temp. directory
    >>> config = """[tool.myapp]
    ... option = "spam"
    ... """
    >>> project_dir = getfixture("tmp_path")
    >>> project_dir.joinpath("src").mkdir()
    >>> project_dir.joinpath("pyproject.toml").write_text(config)
    29
    >>> # Change to the "src" dir of our "porject"
    >>> monkeypatch = getfixture("monkeypatch")
    >>> with monkeypatch.context() as m:
    ...     m.chdir(project_dir / "src")
    ...

Now, we should be able to find the :file:`pyproject.toml` and load our settings from it:

.. code-block:: python

    ...     ts.load(
    ...          Settings,
    ...          "myapp",
    ...          [ts.find("pyproject.toml")],
    ...          config_file_section="tool.myapp",
    ...     )
    Settings(option='spam')

.. _use the "tool." prefix: https://www.python.org/dev/peps/pep-0518/#id28


Dynamic Search Paths via Environment Variables
----------------------------------------------

Sometimes, you don't know the location of your configuration files in advance.
Sometimes, you don't even know where to search for them.
This may, for example, be the case when your app runs in a container and the configuration files are mounted to an arbitrary location inside the container.

For these cases, Typed Settings can read search paths for config files from an environment variable.
If you use :func:`load()`, its name is derived from the *appname* argument and is :samp:`{APPNAME}_SETTINGS`.

Multiple paths are separated by :code:`:`, similarly to the :envvar:`PATH` variable.
However, in contrast to :code:`PATH`, *all* existing files are loaded one after another:

.. code-block:: python

   >>> @ts.settings
   ... class Settings:
   ...     option1: str = "default"
   ...     option2: str = "default"
   >>>
   >>> # Create two config files and expose their paths via an env var
   >>> project_dir = getfixture("tmp_path")
   >>> f1 = project_dir.joinpath("conf1.toml")
   >>> f1.write_text("""[myapp]
   ... option1 = "spam"
   ... option2 = "spam"
   ... """)
   42
   >>> f2 = project_dir.joinpath("conf2.toml")
   >>> f2.write_text("""[myapp]
   ... option1 = "eggs"
   ... """)
   25
   >>> with monkeypatch.context() as m:
   ...     # Export the env var that holds the paths to our config files
   ...     m.setenv("MYAPP_SETTINGS", f"{f1}:{f2}")
   ...
   ...     # Loading the files from the env var is enabled by default
   ...     ts.load(Settings, "myapp")
   Settings(option1='eggs', option2='spam')

You can override the default using the *config_files_var* argument
(or *env_var* if you use the :class:`FileLoader` directly):

.. code-block:: python

   >>> with monkeypatch.context() as m:
   ...     m.setenv("MY_SETTINGS", str(f2))
   ...     ts.load(Settings, "myapp", config_files_var="MY_SETTINGS")
   Settings(option1='eggs', option2='default')

If you set it to :code:`None`, loading filenames from an environment variable is disabled:

.. code-block:: python

   >>> with monkeypatch.context() as m:
   ...     m.setenv("MYAPP_SETTINGS", f"{f1}:{f2}")
   ...     ts.load(Settings, "myapp", config_files_var=None)
   Settings(option1='default', option2='default')


Config File Precedence
----------------------

Typed-Settings loads all files that it finds and merges their contents with all previously loaded settings.

The list of static files (passed to :func:`load()` or :class:`FileLoader`) is always loaded first.
The files specified via an environment variable are loaded afterwards:

.. code-block:: python

   >>> with monkeypatch.context() as m:
   ...     m.setenv("MYAPP_SETTINGS", f"loaded_3rd.toml:loaded_4th.toml")
   ...     s = ts.load(Settings, "myapp", ["loaded_1st.toml", ts.find("loaded_2nd.toml")])


Dynamic Options
===============

The benefit of class based settings is that you can use properties to create "dynamic" or "aggregated" settings.

Imagine, you want to configure the URL for a REST API but the only part that usually changes with every deployment is the hostname.

For these cases, you can make each part of the URL configurable and create a property that returns the full URL:

.. code-block:: python

    >>> @ts.settings
    ... class ServiceConfig:
    ...     scheme: str = "https"
    ...     host: str = "example.com"
    ...     port: int = 443
    ...     path: Path() = Path("api")
    ...
    ...     @property
    ...     def url(self) -> str:
    ...         return f"{self.scheme}://{self.host}:{self.port}/{self.path}"
    ...
    >>> print(ServiceConfig().url)
    https://example.com:443/api

Another use case is loading data from files, e.g., secrets like SSH keys:

.. code-block:: python

    >>> from pathlib import Path
    >>>
    >>> @ts.settings
    ... class SSH:
    ...     key_file: Path
    ...
    ...     @property
    ...     def key(self) -> str:
    ...         return self.key_file.read_text()
    ...
    >>> key_file = getfixture("tmp_path").joinpath("id_1337")
    >>> key_file.write_text("le key")
    6
    >>> print(SSH(key_file=key_file).key)
    le key


Adding Support for Additional File Types
========================================

The function :func:`load()` uses a :class:`~typed_settings.loaders.FileLoader` that only supports TOML files.
However, the supported file formats are not hard-coded but can be configured and extended.

If you use :func:`load_settings()`, you can (and must) pass a custom :class:`~typed_settings.loaders.FileLoader` instance that can be configured with loaders for different file formats.

Before we start, we'll need a setting class and Pyton config file:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     option1: str = "default"
    ...     option2: str = "default"
    >>>
    >>> py_file = getfixture("tmp_path").joinpath("conf.py")
    >>> py_file.write_text("""
    ... class MYAPP:
    ...     OPTION1 = "spam"
    ... """)
    35

We now create our loaders configuration.
The :code:`formats` argument expects a dictionary that maps :mod:`glob` patterns to file format loaders:

.. code-block:: Python

    >>> from typed_settings.loaders import PythonFormat, TomlFormat
    >>>
    >>> file_loader = ts.FileLoader(
    ...     formats={
    ...         "*.toml": TomlFormat(section="myapp"),
    ...         "*.py": PythonFormat("MYAPP", key_transformer=PythonFormat.to_lower),
    ...     },
    ...     files=[py_file],
    ...     env_var=None,
    ... )

Now we can load settings from Python files:

.. code-block:: python

    >>> ts.load_settings(Settings, loaders=[file_loader])
    Settings(option1='spam', option2='default')


Writing Your Own File Format Loader
-----------------------------------

File format loaders must implement the :class:`~typed_settings.loaders.FileFormat` protocol:

- They have to be callables (i.e., functions or a classes with a :meth:`~object.__call__()` method).
- They have to accept a :class:`~pathlib.Path`, the user's settings class and a list of :class:`typed_settings.types.OptionInfo` instances.
- They have to return a dictionary with the loaded settings.

.. admonition:: Why return a :code:`dict` and not a settings instance?
   :class: hint

   (File format) loaders return a dictionary with loaded settings instead of instances of the user's settings class.

   The reason for this is simply, that dicts can easier be created and merged than class instances.

   Typed Settings validates and cleans the settings of all loaders automatically and
   converts them to instances of your settings class.
   So there's no need for you to do it on your own in your loader.

A very simple JSON loader could look like this:


.. code-block:: python

    >>> import json
    >>>
    >>> def load_json(path, _settings_cls, _options):
    ...     return json.load(path.open())

If you want to use this in production, you should add proper error handling and documentation, though.
You can take the :class:`~typed_settings.loaders.TomlFormat` as `an example <_modules/typed_settings/loaders.html#TomlFormat>`_.

Using your file format loader works like in the example above:

.. code-block:: python

    >>> json_file = getfixture("tmp_path").joinpath("conf.json")
    >>> json_file.write_text('{"option1": "spam", "option2": "eggs"}')
    38
    >>>
    >>> file_loader = ts.FileLoader(
    ...     formats={"*.json": load_json},
    ...     files=[json_file],
    ...     env_var=None,
    ... )
    >>> ts.load_settings(Settings, loaders=[file_loader])
    Settings(option1='spam', option2='eggs')


Writing Custom Loaders
======================

When you want to load settings from a completely new source, you can implement your own :class:`~typed_settings.loaders.Loader` (which is similar -- but not equal -- to :class:`~typed_settings.loaders.FileFormat`):

- It has to be a callable (i.e., a function or a class with a :meth:`~object.__call__()` method).
- It has to accept the user's settings class and a list of :class:`typed_settings.types.OptionInfo` instances.
- It has to return a dictionary with the loaded settings.

In the following example, we'll write a class that loads settings from an instance of the settings class.
This maybe useful for libraries that want to give using applications the possibility to specify application specific defaults for that library.

This time, we need some setup, because the settings instance has to be passed when we configure our loaders.
When the settings are actually loaded and our :code:`InstanceLoader` is invoked, it converts the instances to a dictionary with settings and returns it:

.. code-block:: python

    >>> import attrs
    >>>
    >>> class InstanceLoader:
    ...     def __init__(self, instance):
    ...         self.instance = instance
    ...
    ...     def __call__(self, settings_cls, options):
    ...         if not isinstance(self.instance, settings_cls):
    ...             raise ValueError(
    ...                 f'"self.instance" is not an instance of {settings_cls}: '
    ...                 f"{type(self.instance)}"
    ...             )
    ...         return attrs.asdict(self.instance)


Using the new loader works the same way as we've seen before:

.. code-block:: python

    >>> inst_loader = InstanceLoader(Settings("a", "b"))
    >>> ts.load_settings(Settings, loaders=[inst_loader])
    Settings(option1='a', option2='b')

.. tip::

   Classes with just an :code:`__init__()` and a single method can also be implemented as partial functions:

   .. code-block:: python

        >>> from functools import partial
        >>>
        >>> def load_from_instance(instance, settings_cls, options):
        ...     if not isinstance(instance, settings_cls):
        ...         raise ValueError(
        ...             f'"instance" is not an instance of {settings_cls}: '
        ...             f"{type(instance)}"
        ...         )
        ...     return attrs.asdict(instance)
        ...
        >>> inst_loader = partial(load_from_instance, Settings("a", "b"))
        >>> ts.load_settings(Settings, loaders=[inst_loader])
        Settings(option1='a', option2='b')

.. note::

   The :class:`~typed_settings.loaders.InstanceLoader` was added to Typed Settings in version 1.0.0 but we'll keep this example.


Command Line Arguments with Click
=================================

You can generate Click command line options for your settings that let your users override settings loaded from other sources (like config files).

The general algorithm for generating a Click_ CLI for your settings looks like this:

#. You decorate a Click command with :func:`click_options()` which roughly works like :func:`click.make_pass_decorator()`.

#. The decorator will immediately (namely, at module import time)

   - load your settings (e.g., from config files or env vars),
   - create a :func:`click.option()` for each setting and use the loaded settings value as default for that option.

#. You add a positional argument to your CLI function.

#. When you run your CLI, the decorator :

   - updates the settings with option values from the command line,
   - passes the updated settings instances as positional argument to your CLI function.

.. _click: https://click.palletsprojects.com

Take this minimal example:

.. code-block:: python

    >>> import click
    >>> import click.testing
    >>> import typed_settings as ts
    >>>
    >>> monkeypatch.setenv("EXAMPLE_SPAM", "23")
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     spam: int = 42
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> runner = click.testing.CliRunner()
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>
    >>> print(runner.invoke(cli, ["--spam=3"]).output)
    Settings(spam=3)
    <BLANKLINE>


The code above is roughly equivalent to:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = 42
    ...
    >>> defaults = ts.load(Settings, "example")
    >>>
    >>> @click.command()
    ... @click.option("--spam", type=int, default=defaults.spam, show_default=True)
    ... def cli(spam: int):
    ...     print(spam)
    ...
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>
    >>> print(runner.invoke(cli, ["--spam=3"]).output)
    3
    <BLANKLINE>

The major difference between the two is that Typed Settings passes the complete settings instances and not individual options.


Configuring Loaders and Converters
----------------------------------

When you just pass an application name to :func:`click_options()` (as in the example above),
it uses :func:`default_loaders()` to get the default loaders and :func:`default_converter()` to get the default converter.

Instead of passing an app name, you can pass your own list of loaders to :func:`click_options()`:

.. code-block:: python

    >>> # Only load envs vars, no config files
    >>> loaders = ts.default_loaders(
    ...     appname="example",
    ...     config_files=(),
    ...     config_files_var=None,
    ... )
    >>> @click.command()
    ... @ts.click_options(Settings, loaders)
    ... def cli(settings: Settings):
    ...     pass

In a similar fashion, you can use your own converter:

.. code-block:: python

    >>> converter = ts.default_converter()
    >>> # converter.register_structure_hook(my_type, my_converter)
    >>>
    >>> @click.command()
    ... @ts.click_options(Settings, "example", converter=converter)
    ... def cli(settings: Settings):
    ...     pass


Order of Decorators
-------------------

Click passes the settings instance to your CLI function as positional argument.
If you use other decorators that behave similarly (e.g., :func:`click.pass_context`),
the order of decorators and arguments matters.

The innermost decorator (the one closest to the :code:`def`) will be passed as first argument,
The second-innermost as second argument and so forth:

.. code-block:: python

    >>> @click.command()
    ... @ts.click_options(Settings, loaders)
    ... @click.pass_context
    ... def cli(ctx: click.Context, settings: Settings):
    ...     print(ctx, settings)
    ...
    >>> print(runner.invoke(cli, []).stdout)
    <click.core.Context object at 0x...> Settings(spam=23)
    <BLANKLINE>


Help!
-----

As you may have noticed in the examples above, the generated options were lacking a proper help string.
You can add one via :func:`ts.option()` and :func:`ts.secret()`:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=23, help="Amount of SPAM required")
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  Amount of SPAM required  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>


Extending supported types
-------------------------

Typed Settings and it's Click utilities support the data types for the most common use cases out-of-the-box
(in fact, it was quite hard to come up with an example that makes at least *some* sense …;-)).

But let's assume you have a dataclass class that represents an RGB color and
you want to use a single command line option for it (like :samp:`--color {R G B}`).

.. code-block:: python

    >>> import attrs
    >>> import dataclasses
    >>>
    >>> @dataclasses.dataclass
    ... class RGB:
    ...     r: int = 0
    ...     g: int = 0
    ...     b: int = 0
    ...
    >>> @ts.settings
    ... class Settings:
    ...     color: RGB = RGB(0, 0, 0)

.. note::

   If we used ``attrs`` instead of :mod:`dataclasses` here, Typed Settings would automatically generate three options ``--color-r``, ``--color-g``, and ``--color-b``.

Since Cattrs has no built-in support for dataclasses, we need to register a converter for it:

.. code-block:: python

    >>> converter = ts.default_converter()
    >>> converter.register_structure_hook(
    ...     RGB, lambda val, cls: val if isinstance(val, RGB) else cls(*val)
    ... )

Typed Settings uses a :class:`~typed_settings.click_utils.TypeHandler` to generate type specific arguments for :func:`click.option()`.
The :class:`~typed_settings.click_utils.TypeHandler` takes a dictionary that maps Python types to handler functions.
These functions receive that type and the default value for the option.
They return a dictionary with keyword arguments for :func:`click.option()`.

For our use case, we need an :code:`int` options that takes exactly three arguments and has the metavar :code:`R G B`.
If (and only if) there is a default value for our option, we want to use it.

.. code-block:: python

    >>> from typed_settings.click_utils import DEFAULT_TYPES, StrDict, TypeHandler
    >>>
    >>> def handle_rgb(_type: type, default: object) -> StrDict:
    ...     type_info = {
    ...         "type": int,
    ...         "nargs": 3,
    ...         "metavar": "R G B",
    ...     }
    ...     if default is not attrs.NOTHING:
    ...         type_info["default"] = dataclasses.astuple(default)
    ...     return type_info

We now update the dict with built-in type handlers with our own and
create a new :class:`~typed_settings.click_utils.TypeHandler` instance with it:

.. code-block:: python

    >>> type_dict = {
    ...     **DEFAULT_TYPES,
    ...     RGB: handle_rgb,
    ... }
    >>> type_handler = TypeHandler(type_dict)

Finally, we need to pass the type handler as well as our updated converter to :func:`click_options()` and we are ready to go:

.. code-block:: python

    >>> @click.command()
    ... @ts.click_options(Settings, "example", converter, type_handler=type_handler)
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> # Check if our metavar and default value is used:
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --color R G B  [default: 0, 0, 0]
      --help         Show this message and exit.
    <BLANKLINE>
    >>> # Try passing our own color:
    >>> print(runner.invoke(cli, "--color 23 42 7".split()).output)
    Settings(color=RGB(r=23, g=42, b=7))
    <BLANKLINE>

The way described above should be sufficient for most extensions.
However, if you need to achieve something more complicated, like adding support for new kinds of container types, you can also sub-class :class:`~typed_settings.click_utils.TypeHandler()`.
