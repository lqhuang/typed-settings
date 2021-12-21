===================
Why Typed Settings?
===================

Comprehensive List of Features
==============================

- Default settings are defined by your app and can be overridden by external sources (like config files, environment variables, command line options).

- Settings are defined as attrs classes with type hints and, optionally, validators.

  - Secrets are hidden when a settings instance is printed.

- Options can be basic data types (bool, int, float, str), Enums, lists of basic types, or nested settings classes (:ref:`full list <func-settings>`).

  - Cattrs_ is used for converting settings values to the desired type.
    You can add hooks for converting any types that are not supported out-of-the-box.

- You can configure from which sources settings are loaded.

  Typed Settings ships with a file loader and an environment variable
  loader.

  The file loader supports Toml and Python files.

  You can extend Typed Settings with custom loaders and add support for additional file formats.

- The file loader can load settings from multiple config files.

  - Settings files can be optional or mandatory.
  - Config files are allowed to contain settings for multiple apps (like :file:`pyproject.toml`)
  - Paths to config files have to be explicitly named.
    There are no implicit default search paths.
  - There is a helper for searching config files in the current project or file system.
  - Additional paths for config files can be specified via an environment variable.
    As in ``PATH``, multiple paths are separated by a ``:``.
    The last file in the list has the highest priority.
  - Extra options in config files (that do not map to an attribute in the settings class) are errors.

- Environment variables with a defined prefix override settings from config files.
  This can optionally be disabled.

- Click_ options for a settings class can be generated.
  They are passed to the cli function as a single object (instead of individually).

  - Click options support the same types as normal options.
  - Options can define a help-string for Click options.

- Settings must be explicitly loaded, either via :func:`typed_settings.load()`/:func`typed_settings.load_settings()` or via :func:`typed_settings.click_options()`.

  - Both functions allow you to customize config file paths, prefixes et cetera.

- Uses debug logging:

  - Config files that are being loaded or that cannot be found
  - Looked up env vars

.. _cattrs: https://cattrs.readthedocs.io
.. _click: https://click.palletsprojects.com


What about Dynaconf?
====================

Dynaconf_ seems quite similar to :program:`TS` on a first glance, but follows a different philosophy.

Settings can be loaded from multiple config files and overridden by environment variables,
but you don't predefine the structure of your settings in advance.
This makes defining defaults and validators for options a bit more tedious, but it is possible nonetheless.

Environment variables use the prefix :code:`DYNACONF_` by default which may lead to conflicts with other apps.

:program:`Dynaconf` supports a lot more file formats than :program:`TS` and can read secrets from :program:`HashiCorp Vault` and :program:`Redis`.
:program:`TS` may add support for these, though.

Settings can contain template vars (for Python format strings or Jinja_) which are replaced with the values of loaded settings.
Supported for this in :program:`TS` is planned_.

:program:`Dynaconf` allows you to place the settings for all deployment environments (e.g., *production* and *testing)* into a single config file.
I like to put these into different files since your configuration may consist of additional files (like SSH keys) that also differ between environments.

It seems like it is also not intended to share config files with other applications, e.g. in :file:`pyproject.toml`.

:program:`Dynaconf` can easily integrate with :program:`Flask` and :program:`Django`, but not with :program:`click`.


.. _dynaconf: https://www.dynaconf.com
.. _jinja: https://jinja.palletsprojects.com
.. _planned: https://gitlab.com/sscherfke/typed-settings/-/issues/2


What about environ-config?
==========================

`Environ-config`_ stems from the author of :program:`attrs` and uses :program:`attrs` classes to define the structure of your settings.

Settings can only be loaded from environment variables.
Secrets can also be read from :program:`HashiCorp Vault`, :program:`envconsul` and ``ini`` files.

Additional config files are not supported which `may lead to problems`_ if your app needs more complex configuration.

:program:`Click` is not supported.

It provides helpful debug logging and built-in dynamic docstring generation for the settings class.


.. _environ-config: https://github.com/hynek/environ-config
.. _may lead to problems: https://hitchdev.com/strictyaml/why-not/environment-variables-as-config/


What about Pydantic?
====================

Pydantic_ is more comparable to :program:`attrs` but also offers integrated settings loading (amongst many other features).

Settings classes are, as in :program:`TS` and :program:`environ-config`, predefined.
Option values are automatically converted and can easily be validated.

Settings can only be loaded from environment variables (and :file:`.env` files), though.

.. _pydantic: https://pydantic-docs.helpmanual.io/
