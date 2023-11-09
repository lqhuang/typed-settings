:tocdepth: 2

=============
API Reference
=============

This is the full list of all public classes and functions.

.. currentmodule:: typed_settings


Core
====

.. automodule:: typed_settings

Functions
---------

.. autofunction:: load
.. autofunction:: load_settings
.. autofunction:: default_loaders
.. autofunction:: find
.. autofunction:: convert

Classes
-------

.. autoclass:: SettingsState


Aliases
-------

Aliases for more convenient imports.

.. class:: Secret

   Alias for :class:`typed_settings.types.Secret`

.. class:: SecretStr

   Alias for :class:`typed_settings.types.SecretStr`

.. function:: settings()

   Alias for :func:`typed_settings.cls_attrs.settings()`

.. function:: option()

   Alias for :func:`typed_settings.cls_attrs.option()`

.. function:: secret()

   Alias for :func:`typed_settings.cls_attrs.secret()`

.. function:: evolve()

   Alias for :func:`typed_settings.cls_attrs.evolve()`

.. function:: combine()

   Alias for :func:`typed_settings.cls_attrs.combine()`

.. function:: default_converter()

   Alias for :func:`typed_settings.converters.default_converter()`

.. function:: register_strlist_hook()

   Alias for :func:`typed_settings.converters.register_strlist_hook()`

.. function:: cli()

   Alias for :func:`typed_settings.cli_argparse.cli()`.

.. function:: click_options()

   Alias for :func:`typed_settings.cli_click.click_options()`.

.. function:: pass_settings()

   Alias for :func:`typed_settings.cli_click.pass_settings()`.


Dict Utils
==========

.. automodule:: typed_settings.dict_utils
   :members:


Exceptions
==========

.. automodule:: typed_settings.exceptions
   :members:


Loaders
=======

.. automodule:: typed_settings.loaders
   :members:
   :special-members: __call__


Processors
==========

.. automodule:: typed_settings.processors
   :members:
   :special-members: __call__


Converters
==========

.. automodule:: typed_settings.converters
   :members:


Constants
=========

.. automodule:: typed_settings.constants
   :members:


Types
=====

.. automodule:: typed_settings.types
   :members:


Settings Classes: attrs
=======================

.. automodule:: typed_settings.cls_attrs

Classes and Fields
------------------

Helpers for creating ``attrs`` classes and fields with sensible defaults for Typed Settings.
They are all also available directly from the :mod:`typed_settings` module.

.. currentmodule:: typed_settings.cls_attrs

.. _func-settings:

.. function:: settings(maybe_cls=None, *, these=None, repr=None, unsafe_hash=None, hash=None, init=None, slots=True, frozen=False, weakref_slot=True, str=False, auto_attribs=None, kw_only=False, cache_hash=False, auto_exc=True, eq=None, order=False, auto_detect=True, getstate_setstate=None, on_setattr=None, field_transformer=None, match_args=True)

    An alias to :func:`attrs.define()`.

.. function:: option(*, default=NOTHING, validator=None, repr=True, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None, click=None, argparse=None)

    A wrapper for :func:`attrs.field()` that makes it easier to pass Typed Settings specific metadata to it.

    Additional Parameters:
      - **help** (str_ | None_): The help string for Click or argparse options.

      - **click** (dict_ | None_): Additional keyword arguments to pass to :func:`click.option()`.
        They can override *everything* that Typed Settings automatically generated for you.
        If that dict contains a ``help``, it overrides the value of the *help* argument.
        In addition, it can contain the key ``param_decls: str | Sequence(str)`` to override the automatically generated ones.

      - **argparse** (dict_ | None_): Additional keyword arguments to pass to :meth:`~argparse.ArgumentParser.add_argument()`.
        They can override *everything* that Typed Settings automatically generated for you.
        If that dict contains a ``help``, it overrides the value of the *help* argument.
        In addition, it can contain the key ``param_decls: str | Sequence(str)`` to override the automatically generated ones.

    .. _none: https://docs.python.org/3/library/constants.html#None
    .. _dict: https://docs.python.org/3/library/functions.html#dict
    .. _str: https://docs.python.org/3/library/functions.html#str


.. function:: secret(*, default=NOTHING, validator=None, repr=True, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None, click=None, argparse=None)


    An alias to :func:`option()` but with a default repr that hides secrets.

    When printing a settings instances, secret settings will represented with
    `*******` instead of their actual value.

    See :func:`option()` for help on the additional parameters.

    Example:

      >>> from typed_settings import settings, secret
      >>>
      >>> @settings
      ... class Settings:
      ...     password: str = secret()
      ...
      >>> Settings(password="1234")
      Settings(password='*******')


Helpers
-------

.. autofunction:: combine

.. autofunction:: evolve

Settings Classes: Utils
=======================

.. automodule:: typed_settings.cls_utils
   :members:


CLI: Argparse
=============

.. automodule:: typed_settings.cli_argparse

Decorators and Functions
------------------------

Decorators and functions for creating :mod:`argparse` options from Typed
Settings options.

.. autofunction:: cli
.. autofunction:: make_parser
.. autofunction:: namespace2settings


Type handling
-------------

Argparse type handling for the
:class:`~typed_settings.cli_utils.TypeArgsMaker`.

.. autofunction:: handle_datetime
.. autofunction:: handle_enum
.. autofunction:: handle_path
.. autodata:: DEFAULT_TYPES
.. autoclass:: ArgparseHandler


CLI: Click
==========

.. automodule:: typed_settings.cli_click

Decorators
----------

Decorators for creating :mod:`click` options from Typed Settings
options.

.. autofunction:: click_options
.. autofunction:: pass_settings


Generating Click options and option groups
------------------------------------------

Classes for customizing how Cli options are created and grouped.

.. autoclass:: DecoratorFactory
   :members:

.. autoclass:: ClickOptionFactory
   :members:

.. autoclass:: OptionGroupFactory
   :members:


Type handling
-------------

Click type handling for the
:class:`~typed_settings.cli_utils.TypeArgsMaker`.

.. autofunction:: handle_datetime
.. autofunction:: handle_enum
.. autodata:: DEFAULT_TYPES
.. autoclass:: ClickHandler


CLI: Utils
==========

.. automodule:: typed_settings.cli_utils
   :members:
   :special-members: __call__


MyPy
====

.. automodule:: typed_settings.mypy
