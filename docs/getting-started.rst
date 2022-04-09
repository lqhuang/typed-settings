===============
Getting Started
===============

.. currentmodule:: typed_settings

This page briefly explains how to install and use Typed Settings.
It gives you an overview of the most important features without going into detail.
At the end you'll find some hints how to proceed from here.


Installation
============

Install *typed-settings* into your virtualenv_:

.. code-block:: console

   $ python -m pip install typed-settings
   ...
   Successfully installed ... typed-settings-x.y.z


Basic Settings Definition and Loading
=====================================


Settings are defined as `attrs classes`_.
You can either use the decorators provided by ``attrs`` or the :func:`settings` decorator which is an alias to :func:`attrs.define()`:

.. code-block:: python

   >>> import typed_settings as ts
   >>>
   >>> @ts.settings
   ... class Settings:
   ...     username: str = ""
   ...     password: str = ts.secret(default="")
   ...
   >>> Settings("monty", "S3cr3t!")
   Settings(username='monty', password=***)

:func:`secret()` is a wrapper for :func:`attrs.field()` and masks secrets when the settings instance is being printed.

Settings should (but are not required to) define defaults for all options.
If an option has no default and no config value can be found for it, an error will be raised by ``attrs``.

In real life, you don't manually instantiate your settings.
Instead, you call the function :func:`load()`:

.. code-block:: python

   >>> ts.load(Settings, appname="myapp")
   Settings(username='', password=***)

The first argument of that function is your settings class and an instance of that class is returned by it.
The second argument is your *appname*.
That value is being used to determine the config file section and prefix for environment variables.
You can override both, though.

.. note::

   :func:`load()` is designed to be easy to use and cover most use cases.
   There is also :func:`load_settings()`, which allows you to explicitly specify which loaders to use with which configuration,
   and how loaded settings are converted to the correct type.

.. _attrs classes: https://www.attrs.org/en/stable/examples.html
.. _virtualenv: https://virtualenv.pypa.io/en/stable/


Settings from Environment Variables
===================================

The easiest way to override an option's default value is to set an environment variable.
Typed Settings will automatically look for environment variables matching :samp:`{APPNAME}_{OPTION_NAME}` (in all caps):

.. code-block:: python

   >>> # Temporarily set some environment variables:
   >>> monkeypatch = getfixture("monkeypatch")
   >>> monkeypatch.setenv("MYAPP_USERNAME", "monty")
   >>> monkeypatch.setenv("MYAPP_PASSWORD", "S3cr3t!")
   >>>
   >>> ts.load(Settings, appname="myapp")
   Settings(username='monty', password=***)
   >>>
   >>> monkeypatch.undo()

You can optionally change the prefix or disable loading environment variables completely.
The guide :ref:`guide-settings-from-env-vars` shows you how.

.. warning::

   Never pass secrets via environment variables!

   It's far easier for environment variables to leak outside than for config files.
   You may, for example, accidentally leak your env via your CI/CD pipeline,
   or you may be affected by a `security incident`_ for which you can't do anything.

   Write your secret to a file and pass its path via a variable like :code:`MYAPP_API_TOKEN_FILE=/private/token` (instead of just :code:`MYAPP_API_TOKEN="3KX93ad..."`) to your app.
   Alternatively, store it in a structured config file that you directly load with Typed Settings.

   .. _security incident: https://thehackernews.com/2021/09/travis-ci-flaw-exposes-secrets-of.html


Settings from Config Files
==========================

To pass secrets or to persist settings (and avoid exporting environment variables again and again), you may want to use config files.
Typed Settings supports TOML files (`Why?`_) out-of-the-box and looks for the *appname* section by default:

.. code-block:: python

   >>> from pathlib import Path
   >>>
   >>> # Create a temporary config file:
   >>> tmp_path: Path = getfixture("tmp_path")
   >>> settings_file = tmp_path.joinpath("settings.toml")
   >>> settings_file.write_text("""
   ... [myapp]
   ... username = "monty"
   ... password = "S3cr3t!"
   ... """)
   49
   >>> ts.load(Settings, appname="myapp", config_files=[settings_file])
   Settings(username='monty', password=***)

You can also load settings from multiple files.
Subsequent files override the settings of their predecessors.

Appart from TOML, support for Python files is also built-in and you can add loaders for other file formats, too.

.. _why?: https://www.python.org/dev/peps/pep-0518/#other-file-formats
.. TODO Add refs to file format guide


Dynamically Finding Config Files
================================

Sometimes, tools do not know the location of their config file in advance.
Take `black <https://black.readthedocs.io>`_, for example, which searches for :file:`pyproject.toml` from the current working dir upwards until it reaches the project or file system root.

You can do the same with Typed Settings:

.. code-block:: python

   >>> monkeypatch.chdir(tmp_path)
   >>>
   >>> ts.load(Settings, appname="myapp", config_files=[ts.find("settings.toml")])
   Settings(username='monty', password=***)
   >>>
   >>> monkeypatch.undo()

:func:`~typed_settings.find()` returns a single path, so you can combine its result with a static list of files as shown in the section above.


Dynamically Specifying Config Files
===================================

A third way to specify config files is via an environment variable.
By default, Typed Settings looks for a variable named :samp:`{APPNAME}_SETTINGS` (you can change or disable this).
The variable can contain one ore more paths separated by a colon (``:``):

.. code-block:: python

   >>> monkeypatch.setenv("MYAPP_SETTINGS", str(settings_file))
   >>>
   >>> ts.load(Settings, appname="myapp")
   Settings(username='monty', password=***)
   >>>
   >>> monkeypatch.undo()

Config files specified via an environment variable are loaded *after* statically defined ones.

Normally, no error will be raised if a config file does not exist.
However, you can mark files as *mandatory* if you want an error instead.
You can read more about this in the guide :ref:`guide-working-with-config-files`.


Command Line Options with Click
===============================

Some tools (like :ref:`example-pytest` or :ref:`example-twine`) allow you store settings in a config file and override them on-the-fly via command line options.

Typed Settings can integrate with click_ and automatically create command line options for your settings.
When you run your app, settings will first be loaded from config files and environment variables.
The loaded values then serve as defaults for the corresponding Click options.

Your CLI function receives all options as the single instance of your settings class:

.. code-block:: python

   >>> import click
   >>> import click.testing
   >>>
   >>> @ts.settings
   ... class Settings:
   ...     username: str = ts.option(help="Your username")
   ...     password: str = ts.secret(default="", help="Your password")
   >>>
   >>> @click.command()
   ... @ts.click_options(Settings, "myapp")
   ... def cli(settings):
   ...     print(settings)
   ...
   >>> # The "CliRunner" allows us to run our CLI right here in the Python shell:
   >>> runner = click.testing.CliRunner()
   >>> print(runner.invoke(cli, ["--help"]).output)
   Usage: cli [OPTIONS]
   <BLANKLINE>
   Options:
     --username TEXT  Your username  [required]
     --password TEXT  Your password  [default: ***]
     --help           Show this message and exit.
   <BLANKLINE>
   >>> print(runner.invoke(cli, ["--username=guido", "--password=1234"]).output)
   Settings(username='guido', password=***)
   <BLANKLINE>

.. _click: https://click.palletsprojects.com


Frozen Settings and Updating Them
=================================

Settings are mutable by default but can optionally be made immutable:

.. code-block:: python

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

However, this does not extend to mutable option values:

.. code-block:: python

   >>> settings.y.append(4)
   >>> print(settings)
   FrozenSettings(x=3, y=[4])

Immutable settings can be desirable because they prevent you or your users from (accidentally) changing them while the app is running.

However, when you are testing your app, you may still want to modify your settings.
You can create an updated copy of your settings via :func:`evolve()`, which is a recursive version of :func:`attrs.evolve()`:

.. code-block:: python

   >>> updated = ts.evolve(settings, x=7)
   >>> print(settings)
   FrozenSettings(x=3, y=[4])
   >>> print(updated)
   FrozenSettings(x=7, y=[4])
   >>> settings is updated
   False


How to Proceed
==============

If you have read this far, you should now have a basic understanding of how Typed Settings works and what it is capable of (`No, I still don't have a clue!`_).

.. _no, i still don't have a clue!: https://gitlab.com/sscherfke/typed-settings/-/issues/new?issue[title]=Please%20improve%20Getting%20Startet%20section%20XYZ

Depending on what kind of learner you are, you can now either

- continue reading the :doc:`guides` that explain all of Typed Settings' features in-depth or
- take a lookt at the :doc:`examples` that demonstrate how Typed Settings can be used or how to achieve different kinds of goals.
