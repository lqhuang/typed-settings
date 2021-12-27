==============
Typed Settings
==============

*Safe and flexible settings with types*

`Home <https://typed-settings.readthedocs.io/en/latest>`_ |
`PyPI <https://pypi.org/project/typed-settings/>`_ |
`Repo <https://gitlab.com/sscherfke/typed-settings>`_ |
`Issues <https://gitlab.com/sscherfke/typed-settings/-/issues>`_

----

Typed Settings allows you to cleanly structure and validate your settings with `attrs <https://www.attrs.org>`_ classes.
Type annotations will be used to automatically convert values to the proper type (using `cattrs <https://cattrs.readthedocs.io>`_).
You can currently load settings from these sources:

- TOML files (multiple, if you want to).  Paths can be statically specified or dynamically set via an environment variable.
- Environment variables
- `click <https://click.palletsprojects.com>`_ command line options

You can use Typed settings, e.g., for

- server processes
- containerized apps
- command line applications


Installation
============

Install and update using `pip <https://pip.pypa.io/en/stable/quickstart/>`_:

.. code-block:: console

   $ python -m pip install typed-settings


Example
=======

This is a very simple example that demonstrates how you can load settings from environment variables.

.. code-block:: python

   # example.py
   import typed_settings as ts

   @ts.settings
   class Settings:
       option_one: str
       option_two: int

   settings = ts.load(
       cls=Settings,
       appname="example",
       config_files=ts.find("settings.toml"),  # Paths can also be set via env var
   )
   print(settings)

.. code-block:: toml

   # settings.toml
   [example]
   option_one = "value"

.. code-block:: console

   $ EXAMPLE_OPTION_TWO=2 python example.py
   Settings(option_one="value", option_two=2)


Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   why.rst
   getting-started.rst
   guides.rst
   examples.rst
   apiref.rst
   changelog.rst



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
