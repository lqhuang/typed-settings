=========
Changelog
=========

0.11.0 (2021-10-02)
===================

- 💥 Use cattrs_ instead of `attrs auto-convert hooks`_.  This makes
  converters more robust and easier to extend.

- 💥 The signature of `load_settings()` has changed.  `load()` is now
  the pre-configured convenience loader while `load_settings()` allows
  full customization of all settings loaders and value converters.

- ✨ Loaders can now be extended by users.  Typed settings bundles a file loader and an environment loader.
  New loaders must implement the Loader_ protocol.

- ✨ The file loader can be extended to support additional file formats.
  File loaders must implement the FileFormat protocol.

- ✨ Add experimental support for Python config files.

- ✨ Environment variables can now contain list values.  Theses lists can eitehr be JSON or simple *{separator}* spearted lists (the separator can be configured, e.g., ``:`` or ``,``).

- 🗑 The attrs specific converters and hooks are deprecated and will be
  removed in a future release.

.. _attrs auto-convert hooks: https://www.attrs.org/en/stable/extending.html#automatic-field-transformation-and-modification
.. _cattrs: https://cattrs.readthedocs.io/en/latest/index.html
.. _fileformat: https://typed-settings.readthedocs.io/en/latest/apiref.html#typed_settings.loaders.FileFormat
.. _loader: https://typed-settings.readthedocs.io/en/latest/apiref.html#typed_settings.loaders.Loader


0.10.0 (2021-06-23)
===================

- 💥 Settings classes are now mutable by default.
  This makes especially testing and monkeypatching a lot easier.
  Since settings classes are normal **attrs** classes, you can make your settings immutable again by passing ``frozen=True`` to the class decorator.

- ✨ ``load()`` is now the new main function for loading settings.
  It has the same signature as ``load_settings()`` (See: `#8`_).

- ✨ ``find()`` searches for a given config file from the current working dir upwards.

- ✨ The ``to_bool()`` converter converts bools from addional values.

- 🗑 The signature of ``load_settings()`` will change in a backwar sincompatible way in the next release.
  Please use ``load()``  instead (See: `#8`_).

- 🐍 Add support for **Python 3.10**.

- 🏗  Add support for **click 8**.

.. _#8: https://gitlab.com/sscherfke/typed-settings/-/issues/8


0.9.2 (2021-02-10)
==================

- 🐛 Fixed `#3`_: Only replace `-` with `_` for sections and option names, but not for dict keys.
- 🐛 Remove debug printa.

.. _#3: https://gitlab.com/sscherfke/typed-settings/-/issues/3


0.9.1 (2020-12-01)
==================

- 🐛 Fixed `#6`_: Properly handle attrs default factories in options.

.. _#6: https://gitlab.com/sscherfke/typed-settings/-/issues/6


0.9 (2020-11-29)
================

- 💥 A ``ValueError`` is now raised when a config file contains invalid options.

- 💥 Click options without a default (or loaded value) are now marked as ``required=True``.

- ✨ Click options support more types (datetimes, lists, tuples, ...)

  - List like types use ``multiple=True``
  - Tuple uses ``nargs=X``

  Click types can also be exteded by users now.

- ✨ Options can specify a help string for Click options via the ``click_help`` parameter.

- ✨ Improve handling of container types (like ``set``) in the attrs auto-converter.

- 🐛 Click help strings no longer show values of secret options.

- 📝 Improve *Why Typed Settings* docs.

- 📝 Improve docs for attrs converters/validators/hooks.

- ✅ Increase test coverage to 100%.


0.8 (2020-11-05)
================

- ✨ Depend on attrs 20.3 and implement auto-converters for attribute values.

- ✨ Properly convert env. vars. with "bool strings" to real booleans.

- 📝 Use Furo_ as documentation theme

- 📝 Update docs:

  - Improve landing page
  - Add Getting Started section to docs
  - Add examples to example guide
  - Add doctests and test examples

- 🐛 Replace "-" in env. var. names with "_"

.. _furo: https://github.com/pradyunsg/furo


0.7 (2020-10-13)
================

- 🐛 Fix loaded settings not being used as option defaults with click.
- 📝 Add API reference to docs.


0.6 (2020-10-11)
================

- ✨ Add ``pass_settings`` decorator that pass settings to nested Click commands.
- 📝 Initialize documentaion at https://typed-settings.readthedocs.io
- 📝 Improve README and automatically test examples


0.5 (2020-09-30)
================

- ✨ Click options for basic data types (``bool``, ``int``, ``str``, ``Enum``) can be generated now.
- 🐛 Fix bug that prevented nested settings classes from automatically being instantiated when no settings for them were loaded.


0.4 (2020-09-25)
================

- ✨ Add convenience wrappers for attrs:

  - ``settings`` is an alias for ``attr.frozen``
  - ``option`` is an alias for ``attr.field``
  - ``secret`` is an alias for ``attr.field`` and masks the options's value with ``***`` when the settings classes is printed.

- ✨ Add ``update_settings()`` method which is useful for overriding settings in tests.
- ✨ Mandatory config files can be prefixed with ``!`` (e.g., ``!./credentials.toml``).
  An error is raised if a mandatory config file does not exist.
- 💥 Flip *appname* and *settings_cls* args of ``load_settings()``.
- ♻️ Refactor internals to improve extensibility.
- 🚀 Add pre-commit hooks


0.3 (2020-09-17)
================

- 📦 Improve packaging
- 👷 Add code linting and improve CI
- ♻️ Refactorings


0.2 (2020-09-02)
================

- ✨ Make sure env vars can be read
- ✅ Add tests for ``load_settings()``


0.1 (2020-08-28)
================

- 🎉 Initial PoC
