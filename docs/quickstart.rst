==========
Quickstart
==========

This document

Installation
============

Install *typed-settings* into your virtualenv_:

.. code-block:: console

   $ python -m pip install typed-settings
   ...
   Successfully installed ... typed-settings-x.y.z


Basic Settings Definition and Loading
=====================================

In larger applications, you should create your settings in a :file:`settings.py` module, but you can also use any other module.
Settings are defined as `attrs classes`_.
Typed Settings, though, provides a :func:`~typed_settings.settings` decorator,
which is an alias to :func:`attr.frozen()` and additionally contains an auto-converter for attribute values:

.. code-block:: pycon

   >>> import typed_settings as ts
   >>>
   >>> @ts.settings
   ... class Settings:
   ...     host: str = ""
   ...     port: int = 0
   ...
   >>> Settings("example.com", "433")
   Settings(host='example.com', port=433)

Settings should (but are not required to) define defaults for all options.
If a default is missing and no config value for an option can be found, you'll get an error.

As you can see, the string ``"433"`` has automatically been converted into an int when we created the instance.

In real life, you don't manually instantiate your settings.
Instead, you call the function :func:`load_settings()`:

.. code-block:: pycon

   >>> ts.load_settings(Settings, "myapp")
   Settings(host='', port=0)

The first argument of that function is your settings class and an instance of that class is returned by it.
The second argument is your *appname*.
That value is being used to determine the config file section and prefix for environment variables.

.. _attrs classes: https://www.attrs.org/en/stable/examples.html
.. _virtualenv: https://virtualenv.pypa.io/en/stable/


Settings from Environment Variables
===================================


Settings from Config Files
==========================


Dynamically Specifying Config Files
===================================


Command Line Options with Click
===============================
