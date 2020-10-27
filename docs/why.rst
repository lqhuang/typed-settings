===================
Why Typed Settings?
===================

Comprehensive List of Features
==============================


- Default settings are defined by app and can be overridden by config files, environment variables and click options.

- Settings are defined as attrs classes with types, converters and validators.

- Options can be basic data types (bool, int, float, str), Enums, lists of basic types, or nested settings classes.

  - An error is raised if options have an unsupported type

- Settings can be loaded from multiple config files.

  - Settings files can be optional or mandatory.
  - Config files are allowed to contain settings for multiple apps (like ``pyproject.toml``)
  - Paths to config files have to be explicitly named.  There are no implicit defauls search paths.
  - Additional paths for config files can be specified via an environment variable.  As in ``PATH``, multiple paths are separated by a ``:``.  The last file in the list has the highest priority.
  - Extra options in config files (that do not map to an attribute in the settings class) are errors

- Environment variables with a defined prefix override settings from config files.

  - This can optionally be disabled.
  - Allowed values for booleans: ``1``, ``True``, ``true``, ``yes`` and ``0``, ``False``, ``false``, ``no``

- Click_ options for some or all settings can be generated.  They are passed to the cli function as a single object (instead of individually).

  - Click options support the same types as normal options
  - Options can define a help-string for Click options (and mybe other usefull arguments)

- Settings must be explicitly loaded, either via ``typed_settings.load_settings()`` or via ``typed_settings.click_options()``.

  - Both functions allow you to customize config file paths, prefixes et cetera.

- Use logging for

  - Config files that are being loaded
  - Not found config files (warn for optional, error for mandtory files (in addition to an exception))
  - Name of settings files env var
  - Names of env vars loaded

.. _click: https://click.palletsprojects.com/


Why TOML and not …?
===================


What about Dynaconf?
====================


What about Environconfig?
=========================


What about Pydantic?
====================
