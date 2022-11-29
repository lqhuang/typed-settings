:tocdepth: 4

=============
API Reference
=============

This is the full list of all public classes and functions.

.. currentmodule:: typed_settings


Core
====

Core Functions
--------------

.. automodule:: typed_settings
.. autofunction:: load
.. autofunction:: load_settings
.. autofunction:: default_loaders
.. autofunction:: find


Aliases
-------

.. function:: settings()

   Alias for :func:`typed_settings.attrs.settings()`

.. function:: option()

   Alias for :func:`typed_settings.attrs.option()`

.. function:: secret()

   Alias for :func:`typed_settings.attrs.secret()`

.. function:: evolve()

   Alias for :func:`typed_settings.attrs.evolve()`

.. function:: combine()

   Alias for :func:`typed_settings.attrs.combine()`

.. function:: default_converter()

   Alias for :func:`typed_settings.converters.default_converter()`

.. function:: register_strlist_hook()

   Alias for :func:`typed_settings.converters.register_strlist_hook()`

.. function:: cli()

   Alias for :func:`typed_settings.argparse_utils.cli()`.

.. function:: click_options()

   Alias for :func:`typed_settings.click_utils.click_options()`.

.. function:: pass_settings()

   Alias for :func:`typed_settings.click_utils.pass_settings()`.


Exceptions
----------

.. automodule:: typed_settings.exceptions
   :members:


Loaders
-------

.. automodule:: typed_settings.loaders
   :members:
   :special-members: __call__


Types
-----

.. automodule:: typed_settings.types
   :members:


Attrs & Cattrs
==============

Classes and Fields
------------------

Helpers for creating ``attrs`` classes and fields with sensible details for Typed Settings.
They are all also available directly from the :mod:`typed_settings` module.

.. currentmodule:: typed_settings.attrs

.. _func-settings:

.. function:: settings(maybe_cls=None, *, these=None, repr=None, hash=None, init=None, slots=True, frozen=True, weakref_slot=True, str=False, auto_attribs=None, kw_only=False, cache_hash=False, auto_exc=True, eq=None, order=False, auto_detect=True, getstate_setstate=None, on_setattr=None, field_transformer=<function auto_convert>)

    An alias to :func:`attrs.define()`,
    configured with a *field_transformer* that automatically adds converters to all fields based on their annotated type.

    Supported concrete types:
        - :class:`bool` (from various strings used in env. vars., see
          :func:`.to_bool()`)
        - :class:`datetime.datetime`, (ISO format with support for ``Z`` suffix,
          see :func:`.to_dt()`).
        - Attrs/Settings classes
        - All other types use the *type* object itself as converter, this includes
          :class:`int`, :class:`float`, :class:`str`, and
          :class:`~enum.Enum`, :class:`pathlib.Path`, ….
        - ``typing.Any`` (no conversion is performed)

    Supported generic types:
        - ``typing.List[T]``, ``typing.Sequence[T]``, ``typing.MutableSequence[T]`` (converts to :class:`list`)
        - ``typing.Tuple[T, ...]`` (converts to :class:`tuple`)
        - ``typing.Tuple[X, Y, Z]`` (converts to :class:`tuple`)
        - ``typing.Dict[K, V]``, ``typing.Mapping[K, V]``, ``typing.MutableMapping[K, V]`` (converts to :class:`dict`)
        - ``typing.Optional[T]``, ``typing.Union[X, Y, Z]`` (converts to first matching type)


.. function:: option(*, default=NOTHING, validator=None, repr=True, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None, click=None)

    An alias to :func:`attrs.field()`

    Additional Parameters:
      - **help** (str_): The help string for Click options

      - **click** (dict_): Additional keyword arguments to pass to :func:`click.option()`.
        They can override *everything* that Typed Settings automatically generated for you.
        If that dict contains a ``help``, it overrides the value of the *help* argument.
        In addition, it can contain the key ``param_decls: str | Sequence(str)`` to override the automatically generated ones.

    .. _dict: https://docs.python.org/3/library/functions.html#dict
    .. _str: https://docs.python.org/3/library/functions.html#str


.. function:: secret(*, default=NOTHING, validator=None, repr=***, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None, click=None)

    An alias to :func:`option()` but with a default repr that hides screts.

    When printing a settings instances, secret settings will represented with
    `***` istead of their actual value.

    See :func:`option()` for help on the addional parameters.

    Example:

    .. code-block:: python

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


Converters
----------


.. automodule:: typed_settings.converters
   :members:


CLI Utils
=========

.. automodule:: typed_settings.cli_utils
   :members:
   :special-members: __call__


Argparse Options
================

.. automodule:: typed_settings.argparse_utils

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


Click Options
=============

.. automodule:: typed_settings.click_utils

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


MyPy
====

.. automodule:: typed_settings.mypy
