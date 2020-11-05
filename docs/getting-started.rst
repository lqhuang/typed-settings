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
You can either use the decorators provided by attrs or the :func:`settings` decorator that comes with Typed Settings.
This decorator is an alias to :func:`attr.frozen()`, but it additionally defines an auto-converter for option values:

.. code-block:: python

   >>> import typed_settings as ts
   >>>
   >>> @ts.settings
   ... class Settings:
   ...     host: str = ""
   ...     port: int = 0
   ...
   >>> Settings("example.com", "433")
   Settings(host='example.com', port=433)

As you can see, the string ``"433"`` has automatically been converted into an int when we created the instance.

Settings should (but are not required to) define defaults for all options.
If an option has no default and no config value can be found for it, attrs will raise an error.

In real life, you don't manually instantiate your settings.
Instead, you call the function :func:`load_settings()`:

.. code-block:: python

   >>> ts.load_settings(Settings, appname="myapp")
   Settings(host='', port=0)

The first argument of that function is your settings class and an instance of that class is returned by it.
The second argument is your *appname*.
That value is being used to determine the config file section and prefix for environment variables.
You can override both, though.

.. _attrs classes: https://www.attrs.org/en/stable/examples.html
.. _virtualenv: https://virtualenv.pypa.io/en/stable/


Settings from Environment Variables
===================================

The easiest way to override an option's default value is to set an environment variable.
Typed Settings will automatically look for environment variables matching :samp:`{APPNAME}_{OPTION_NAME}` (in all caps):

.. code-block:: python

   >>> import os
   >>>
   >>> # Temporarily set some environment variables:
   >>> monkeypatch = getfixture("monkeypatch")
   >>> monkeypatch.setattr(os, "environ", {"MYAPP_HOST": "env-host", "MYAPP_PORT": "443"})
   >>>
   >>> ts.load_settings(Settings, appname="myapp")
   Settings(host='env-host', port=443)
   >>>
   >>> monkeypatch.undo()

You can optionally change the prefix or disable loading environment variables completely.
The guide :ref:`guide-settings-from-env-vars` shows you how.


Settings from Config Files
==========================

To persist settings and avoid exporting environment variables again and again, you may want to use config files.
Typed Settings uses TOML files for this (`Why?`_) and looks for the *appname* section by default:

.. code-block:: python

   >>> from pathlib import Path
   >>>
   >>> # Create a temporary config file:
   >>> tmp_path: Path = getfixture("tmp_path")
   >>> settings_file = tmp_path.joinpath("settings.toml")
   >>> settings_file.write_text("""
   ... [myapp]
   ... host = "file-host"
   ... port = 22
   ... """)
   38
   >>> ts.load_settings(Settings, appname="myapp", config_files=[settings_file])
   Settings(host='file-host', port=22)

You can also load settings from multiple files.
Subsequent files override the settings of their predecessors.

.. _why?: https://www.python.org/dev/peps/pep-0518/#other-file-formats


Dynamically Specifying Config Files
===================================

You may not always know the paths of config files in advance,
or you want to allow your users to specify additional ones.
Typed Settings looks for an environment variable named :samp:`{APPNAME}_SETTINGS` (you can change or disable this).
The variable can contain one ore more paths separated by a colon (``:``):

.. code-block:: python

   >>> monkeypatch.setenv("MYAPP_SETTINGS", str(settings_file))
   >>>
   >>> ts.load_settings(Settings, appname="myapp")
   Settings(host='file-host', port=22)
   >>>
   >>> monkeypatch.undo()

Config files specified via an environment variable are loaded *after* statically defined ones.

By default, no error will be raised if a config file does not exist.
However, you can mark files as *mandatory* if you want an error instead.
You can read more about this in the guide :ref:`guide-working-with-config-files`.


Command Line Options with Click
===============================

Some tools (like :ref:`example-pytest` or :ref:`example-twine`) allow you store settings in a config file and override them on-the-fly via command line options.

Typed Settings can integrate with click_ and automatically create command line options for your settings.
When you run your app, settings will first be loaded from config files
and environment variables.
The loaded values then serve as defaults for the correspoinding click options.

Your CLI function receives all options as the single instance of your settings class:

.. code-block:: python

   >>> import click
   >>> import click.testing
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
     --host TEXT     [default: ]
     --port INTEGER  [default: 0]
     --help          Show this message and exit.
   <BLANKLINE>
   >>> print(runner.invoke(cli, ["--host=cli-host", "--port=23"]).output)
   Settings(host='cli-host', port=23)
   <BLANKLINE>

.. _click: https://click.palletsprojects.com


Updating Settings
=================

Loaded settings are frozen (read-only) by default.
This is usually desirable because it prevents you and your users from (accidentally) changing settings while the app is running,
which in turn might result in undefined or unpredictable behavior of your app (a.k.a. *bugs*).

Especially for testing, you may want to modify your settings, though.
You can either

- create an updated *copy* of your settings via :func:`update_settings()` (this is the pure way) or
- let your settings be mutable in the first place by passing :code:`frozen=False` to the class decorator (this is the pragmatic way):

.. code-block:: python

   >>> settings = Settings()
   >>> updated = ts.update_settings(settings, "host", "updated.com")
   >>> print(settings)
   Settings(host='', port=0)
   >>> print(updated)
   Settings(host='updated.com', port=0)
   >>> settings is updated
   False
   >>>
   >>> @ts.settings(frozen=False)
   ... class MutableSettings:
   ...     option: str = ""
   ...
   >>> settings = MutableSettings()
   >>> settings.option = "spam"
   >>> print(settings)
   MutableSettings(option='spam')

The function :func:`update_settings()` has a similar interface as :code:`setattr()`.
The main differences:

- It returns an updated copy of the passed object instead of modifying it in-place.
- The attribute name may be a dot-separated path to update nested settings.

Please see :ref:`guide-updating-settings` for details.


How to Proceed
==============

If you have read this far, you should now have a basic understanding of how Typed Settings works and what it is capable of (`No, I still don't have a clue!`_).

.. _no, i still don't have a clue!: https://gitlab.com/sscherfke/typed-settings/-/issues/new?issue[title]=Please%20improve%20Quickstart%20section%20XYZ

Depending on what kind of learner you are, you can now either

- continue reading the :doc:`guides` that explain all of Typed Settings' features in-depth or
- take a lookt at the :doc:`examples` that demonstrate how Typed Settings can be used or how to achieve different kinds of goals.
