==================
Core Functionality
==================

.. currentmodule:: typed_settings

This page explains Typed Setting's core functionality of loading settings and customizing the process.


Settings Classes
================

Settings classes are normal Attrs_ classes with type hints:

.. code-block:: python

    >>> import attrs
    >>>
    >>> @attrs.define
    ... class Settings:
    ...     username: str
    ...     password: str

Typed Settings provides an alias to :func:`attrs.define` named :func:`settings()`.

It also defines wrappers for :func:`attrs.field()`: :func:`option()` and :func:`secret()`.
These wrappers make it easier to add extra metadata for :doc:`CLI options <cli>`.
:func:`secret()` also adds basic protection against :ref:`leaking secrets <secrets>`:

.. code-block:: python

   >>> import typed_settings as ts
   >>>
   >>> @ts.settings
   ... class Settings:
   ...      username: str
   ...      password: str = ts.secret()

Dataclasses and Pydantic models cannot be used as settings classes (yet?).

.. hint::

   Using :func:`settings()` keeps your input a bit cleaner,
   but using :func:`attrs.define()` causes fewer problems with type checkers (see :ref:`sec-mypy`).

   You *should* use :func:`attrs.define` if possible and
   :func:`settings()` *may* be deprecated at some point.

   However, for the sake of brevity we will use :func:`settings()` in most examples.

.. _attrs: https://www.attrs.org/en/stable/


.. _secrets:

Secrets
-------

Secrets, even when stored in an encrypted vault, most of the time end up as plain strings in your app.
And plain strings tend to get printed.
This can be log messages, debug :func:`print()`\ s, tracebacks, you name it:

.. code-block:: python

   >>> @ts.settings
   ... class Settings:
   ...      username: str
   ...      password: str
   ...
   >>> settings = Settings("spam", "eggs")
   >>> print(f"Settings loaded: {settings}")
   Settings loaded: Settings(username='spam', password='eggs')

Oops!

.. danger::

   Never use environment variables to pass secrets to your application!

   It's far easier for environment variables to leak outside than for config files.
   You may, for example, accidentally leak your env via your CI/CD pipeline,
   or you may be affected by a `security incident`_ for which you can't do anything.

   The most secure thing is to use an encrypted vault to store your secrets.
   If that is not possible, store them in a config file.

   If you *have* to use environment variables, write the secret to a file and use the env var to point to that file,
   e.g., :code:`MYAPP_API_TOKEN_FILE=/private/token` (instead of just :code:`MYAPP_API_TOKEN="3KX93ad..."`).
   `GitLab CI/CD`_ supports this, for example.

   .. _gitlab ci/cd: https://docs.gitlab.com/ee/ci/variables/#cicd-variable-types
   .. _security incident: https://thehackernews.com/2021/09/travis-ci-flaw-exposes-secrets-of.html

You can add basic leaking prevention by using :func:`secret()` for creating an option field:

.. code-block:: python

   >>> @ts.settings
   ... class Settings:
   ...      username: str
   ...      password: str = ts.secret()
   ...
   >>> settings = Settings("spam", "eggs")
   >>> print(f"Settings loaded: {settings}")
   Settings loaded: Settings(username='spam', password='*******')

However, we would still leak the secret if we print the field directly:

.. code-block:: python

   >>> print(f"{settings.username=}, {settings.password=}")
   settings.username='spam', settings.password='eggs'

You can use :class:`~typed_settings.types.SecretStr` instead of :class:`str` to protect against this:

.. code-block:: python

   >>> from typed_settings.types import SecretStr
   >>>
   >>> @ts.settings
   ... class Settings:
   ...      username: str
   ...      password: SecretStr = ts.secret()
   ...
   >>> settings = Settings("spam", SecretStr("eggs"))
   >>> print(f"Settings loaded: {settings}")
   Settings loaded: Settings(username='spam', password='*******')
   >>> print(f"{settings.username=}, {settings.password=}")
   settings.username='spam', settings.password='*******'

The good thing about :class:`~typed_settings.types.SecretStr` that it is a drop-in replacement for normal strings.
That bad thing is, that is still not a 100% safe (and maybe, that it only works for strings):

.. code-block:: python

   >>> print(settings.password)
   eggs
   >>> print(f"Le secret: {settings.password}")
   Le secret: eggs

The generic class :class:`~typed_settings.types.Secret` makes accidental secrets leakage nearly impossible,
since it also protects an object's string representation.
However, it is no longer a drop-in replacement for strings
as you have to call its :meth:`typed_settings.types.Secret.get_secret_value()` method to retrieve the actual value:

.. code-block:: python

   >>> from typed_settings.types import Secret
   >>>
   >>> @ts.settings
   ... class Settings:
   ...      username: str
   ...      password: SecretStr
   ...
   >>> settings = Settings("spam", Secret("eggs"))
   >>> print(f"Settings loaded: {settings}")
   Settings loaded: Settings(username='spam', password=Secret('*******'))
   >>> print(settings.password)
   *******
   >>> print(f"Le secret: {settings.password}")
   Le secret: *******
   >>> settings.password.get_secret_value()
   'eggs'

:class:`~typed_settings.types.SecretStr()` and `~typed_settings.secret()` usually form the best compromise between usability and safety.

But now matter what you use, you should explicitly test the (log) output of your code to make sure, secrets are not contained at all or are masked at least.


.. _sec-mypy:

Mypy
----

Unfortunately, mypy_ still gets confused when you alias :func:`attrs.define` (or even import it from any module other than :mod:`attr` or :mod:`attrs`).

Accessing your settings class' attributes does work without any problems,
but when you manually instantiate your class, mypy will issue a ``call-arg`` error.

The `suggested workaround`_ is to create a simple mypy plugin,
so Typed Settings ships with a simple mypy plugin in :mod:`typed_settings.mypy`.

You can activate the plugin via your :file:`pyproject.toml` or :file:`mypy.ini`:

.. code-block:: toml
   :caption: pyproject.toml

    [tool.mypy]
    plugins = ["typed_settings.mypy"]

.. code-block:: ini
   :caption: mypy.ini

    [mypy]
    plugins=typed_settings.mypy


.. _mypy: http://mypy-lang.org/
.. _suggested workaround:
   https://www.attrs.org/en/stable/extending.html?highlight=mypy#wrapping-the-decorator


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

.. danger::

   Never pass secrets via environment variables!

   See :ref:`secrets` for details.


Nested settings
---------------

Settings classes can be nested but environment variables have a flat namespace.
So Typed Settings builds a flat list of all options and uses the "dotted path" to an attribute (e.g., :code:`attrib.nested_attrib.nested_nested_attrib`) for mapping flat names to nested attributes.

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
For example, your company's convention might be to use :code:`SSH_PRIVATE_KEY_FILE`, but your app would look for :code:`MYAPP_SSH_KEY_FILE`:

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

Some tools, especially those that are used for software development (i.e. linters or code formatters), search for their configuration in the current (Git) project.

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

Multiple paths are separated by :code:`:`, similarly to the ``$PATH`` variable.
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
(or *env_var* if you use the :class:`~typed_settings.loaders.FileLoader` directly):

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

The list of static files (passed to :func:`load()` or :class:`~typed_settings.loaders.FileLoader`) is always loaded first.
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

Before we start, we'll need a setting class and Python config file:

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


Post-processing Settings
========================

Processors are applied after all settings have been loaded but before the loaded settings are converted to your settings class.

.. note::

   This approach allows you to, e.g., use template strings where an ``int`` is expected –
   as long as the template results in a valid ``int``.

As with loaders, you can configure a list of processors that are applied one after another.

Interpolation
-------------

*Interpolation* is basically a simple form of templating.
The stdlib's configparser_ uses old-school string formatting for this.
Typed Settings uses new style format strings:

.. code-block:: python

   >>> @ts.settings
   ... class Settings:
   ...     a: str
   ...     b: str
   ...
   >>> config_file = getfixture("tmp_path").joinpath("settings.toml")
   >>> config_file.write_text("""\
   ... [example]
   ... a = "spam"
   ... b = "{a}{a}"
   ... """)
   34
   >>>
   >>> ts.load_settings(
   ...     cls=Settings,
   ...     loaders=ts.default_loaders("example", [config_file]),
   ...     processors=[ts.processors.FormatProcessor()],
   ... )
   Settings(a='spam', b='spamspam')

You can access nested settings like dictionary items but you have to leave out the quotes.
It is also okay to refer to values that are themselves format strings:

.. code-block:: python

   >>> @ts.settings
   ... class Nested:
   ...     x: str
   ...
   >>> @ts.settings
   ... class Settings:
   ...     a: str
   ...     b: str
   ...     nested: Nested
   ...
   >>> config_file = getfixture("tmp_path").joinpath("settings.toml")
   >>> config_file.write_text("""\
   ... [example]
   ... a = "{nested[x]}"
   ... b = "spam"
   ...
   ... [example.nested]
   ... x = "{b}"
   ... """)
   67
   >>>
   >>> ts.load_settings(
   ...     cls=Settings,
   ...     loaders=ts.default_loaders("example", [config_file]),
   ...     processors=[ts.processors.FormatProcessor()],
   ... )
   Settings(a='spam', b='spam', nested=Nested(x='spam'))

.. _configparser: https://docs.python.org/3/library/configparser.html#interpolation-of-values


Templating
----------

If interpolation via format strings is not expressive enough,
you can also use templating via Jinja_.
This works very similarly to how Ansible_ templates its variables.

The package :program:`jinja2` is required for this feature:

.. code-block:: bash

   $ pip install -U jinja2

.. code-block:: python

   >>> @ts.settings
   ... class Settings:
   ...     a: str
   ...     b: str
   ...
   >>> config_file = getfixture("tmp_path").joinpath("settings.toml")
   >>> config_file.write_text("""\
   ... [example]
   ... a = "spam"
   ... b = "{{ a }}{{ a }}"
   ... """)
   42
   >>>
   >>> ts.load_settings(
   ...     cls=Settings,
   ...     loaders=ts.default_loaders("example", [config_file]),
   ...     processors=[ts.processors.JinjaProcessor()],
   ... )
   Settings(a='spam', b='spamspam')

You can access nested settings by normal attribute access.
It is also okay to refer to values that are themselves templates:

.. code-block:: python

   >>> @ts.settings
   ... class Nested:
   ...     x: str
   ...
   >>> @ts.settings
   ... class Settings:
   ...     a: bool
   ...     b: str
   ...     nested: Nested
   ...
   >>> config_file = getfixture("tmp_path").joinpath("settings.toml")
   >>> _ = config_file.write_text("""\
   ... [example]
   ... a = "{{ nested.x }}"
   ... b = "spam"
   ...
   ... [example.nested]
   ... x = "{% if b == 'spam'%}True{% else %}False{% endif %}"
   ... """)
   >>>
   >>> ts.load_settings(
   ...     cls=Settings,
   ...     loaders=ts.default_loaders("example", [config_file]),
   ...     processors=[ts.processors.JinjaProcessor()],
   ... )
   Settings(a=True, b='spam', nested=Nested(x='True'))

.. _ansible: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html#simple-variables
.. _jinja: http://jinja.pocoo.org/


Loading Secrets via Helper Scripts
----------------------------------

The :class:`~typed_settings.processors.UrlProcessor` allows you to reference and query external resources,
e.g., scripts or secrets in a given location.

You pass a mapping of URL schemas and handlers to it.
If a settings value starts with one of the configured schemas,
the corresponding handler is invoked and the original settings value is replaced with the handler's result.

.. hint::

   The URL processor is not very strict in what "schemas" it accepts.
   You can pass any string to it as the following example shows.

Let's create a settings class and define some exemplary default values:

.. code-block:: python

   >>> @ts.settings
   ... class Settings:
   ...     a: str = "script://echo password"
   ...     b: str = "helper: echo password"
   ...     c: str = "raw://script://echo password"

The first two values indicate that the script :code:`echo password` should be run and its output (``"password"``) be used as new settings value.

The ``raw://`` schema for the setting ``c`` works like an escape sequence if the literal value should be ``script://echo password``.

You configure the :class:`~typed_settings.processors.UrlProcessor` by passing a dict that maps your prefixes / schemas to handler functions:

.. code-block:: python

   >>> url_processor = ts.processors.UrlProcessor({
   ...     "raw://": ts.processors.handle_raw,
   ...     "script://": ts.processors.handle_script,
   ...     "helper: ": ts.processors.handle_script,
   ... })

We can pass the processor to :func:`load_settings()` and check the result:

.. code-block:: python

   >>> ts.load_settings(
   ...     cls=Settings,
   ...     loaders=[],
   ...     processors=[url_processor],
   ... )
   Settings(a='password', b='password', c='script://echo password')


1Password
=========

Typed Settings allows you to load settings from your 1Password vault.

There is a :class:`~typed_settings.loaders.OnePasswordLoader` that can load complete items from your vault,
and the :class:`~typed_settings.processors.UrlProcessor` handler :class:`~typed_settings.processors.handle_op` that queries 1Password via resource URLs (e.g., :samp:`op://{vault}/{item}/{field}`).

In order for this to work, you need to install and setup the `1Password CLI`_.
When you are done, you can verify that it works by running ``op item list`` in your terminal.

We'll assume that there is a vault named *Test* that contains an item *api-a*.
That item has the fields *username* and *credential*, and *hostname*.

.. image:: ../_static/1password-test-light.png
   :align: center
   :class: only-light
   :alt: A screenshot of 1Password showing the *Test* item from the *Test* vault.

.. image:: ../_static/1password-test-dark.png
   :align: center
   :class: only-dark
   :alt: A screenshot of 1Password showing the *Test* item from the *Test* vault.

.. _1Password CLI: https://developer.1password.com/docs/cli/

1Password Loader
----------------

The :class:`~typed_settings.loaders.OnePasswordLoader` needs to be configured with the item name to load and, optionally, the vault name.

You can define this statically or via another settings class,
which we'll do in the following example.

Let's assume we work on an API client that can be configured with several different instances of that API.
The config file might look like this:

.. code-block:: python

   config_file = getfixture("tmp_path").joinpath("myapi.toml")
   _ = config_file.write_text("""\
   [global]
   vault = "Test"
   default_item = "api-a"

   # Loaded from 1password
   # [api-a]
   # hostname = ...
   # username = ...
   # credential = ...

   [api-b]
   hostname = "https://api-b.example.com"
   username = "bot"
   credential = "1234"
   """)

.. important::

   The field name of the 1Password item *must* match the settings names in order for this to work!

Let's start by defining and loading the global settings:

.. code-block:: python

   @ts.settings
   class GlobalSettings:
       vault: str
       default_item: str
       verify_ssl: bool = True

   global_settings = ts.load(
       GlobalSettings, "myapi", [config_file], config_file_section="global"
   )
   assert global_settings == GlobalSettings(
       vault='Test', default_item='api-a', verify_ssl=True
   )

We can now define the API settings and load them:

.. code-block:: python

   @ts.settings
   class ApiSettings:
       hostname: str
       username: str
       credential: ts.types.SecretStr

   item = global_settings.default_item  # Or ask the user instead :)
   # Get the default loaders and let them look for "item" config:
   loaders = ts.default_loaders("api-a", [config_file])
   # Add the 1Password loader:
   op_loader = ts.loaders.OnePasswordLoader(item=item, vault=global_settings.vault)
   loaders.append(op_loader)

   api_settings = ts.load_settings(ApiSettings, loaders=loaders)
   assert api_settings == ApiSettings(
        hostname='https://api-a.example.com', username='user', credential='*******'
   )


URL Processor with 1Password handler
------------------------------------

The URL processor may be easier to use if you just want to get a single secret from a vault:

- You can specify the vault and item name in the URL and don't need to use another setting for this.
- The name of your option and the item's field name don't need to match.

We can change the example from above by removing the 1Password loader and adding processors instead.
We can also remove the *vault* option from the global settings:

.. code-block:: python

   config_file = getfixture("tmp_path").joinpath("myapi.toml")
   _ = config_file.write_text("""\
   [global]
   default_item = "api-a"

   [api-a]
   hostname = "https://api-a.example.com"
   username = "user"
   api-token = "op://Test/api-a/credential"

   [api-b]
   hostname = "https://api-b.example.com"
   username = "bot"
   credential = "op://Test/api-b/credential"
   """)

   # We'll skip loading the global settings for the sake of simplicity:
   item = "api-a"

   @ts.settings
   class ApiSettings:
       hostname: str
       username: str
       api_token: ts.types.SecretStr

   url_processor = ts.processors.UrlProcessor({
       "op://": ts.processors.handle_op,
       # You can add additional handlers to support more password managers
   })
   loaders = ts.default_loaders(item, [config_file])
   api_settings = ts.load_settings(ApiSettings, loaders=loaders, processors=[url_processor])
   assert api_settings == ApiSettings(
        hostname='https://api-a.example.com', username='user', api_token='*******'
   )
