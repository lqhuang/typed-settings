=============
API Reference
=============

This is the full list of all public classes and functions.

.. currentmodule:: typed_settings


Core
====


Core Functions
--------------

Core functions for loading and working with settings.

.. currentmodule:: typed_settings
.. autofunction:: default_converter
.. autofunction:: default_loaders
.. autofunction:: find
.. autofunction:: load
.. autofunction:: load_settings


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


Attrs
======

Classes and Fields
------------------

Helpers for creating :mod:`attrs` classes and fields with sensible details for Typed Settings.
They are all also available directly from the :mod:`typed_settings` module.

.. currentmodule:: typed_settings.attrs

.. _func-settings:

.. function:: settings(maybe_cls=None, *, these=None, repr=None, hash=None, init=None, slots=True, frozen=True, weakref_slot=True, str=False, auto_attribs=None, kw_only=False, cache_hash=False, auto_exc=True, eq=None, order=False, auto_detect=True, getstate_setstate=None, on_setattr=None, field_transformer=<function auto_convert>)

    An alias to :func:`attrs.frozen`,
    configured with a *field_transformer* that automatically adds converters to all fields based on their annotated type.

    Supported concrete types:
        - :class:`bool` (from various strings used in env. vars., see
          :func:`.to_bool()`)
        - :class:`datetime.datetime`, (ISO format with support for ``Z`` suffix,
          see :func:`.to_dt()`).
        - Attrs/Settings classes (see :func:`.to_attrs()`)
        - All other types use the *type* object itself as converter, this includes
          :class:`int`, :class:`float`, :class:`str`, and
          :class:`~enum.Enum`, :class:`pathlib.Path`, ….
        - ``typing.Any`` (no conversion is performed)

    Supported generic types:
        - ``typing.List[T]``, ``typing.Sequence[T]``, ``typing.MutableSequence[T]``
          (converts to :class:`list`, see :func:`.to_iterable()`)
        - ``typing.Tuple[T, ...]`` (converts to
          :class:`tuple`, see :func:`.to_iterable()`)
        - ``typing.Tuple[X, Y, Z]`` (converts to :class:`tuple`, see
          :func:`.to_tuple()`)
        - ``typing.Dict[K, V]``, ``typing.Mapping[K, V]``,
          ``typing.MutableMapping[K, V]`` (converts to :class:`dict`, see
          :func:`.to_mapping()`)
        - ``typing.Optional[T]``, ``typing.Union[X, Y, Z]`` (converts to first
          matching type, see :func:`.to_union()`)


.. function:: option(*, default=NOTHING, validator=None, repr=True, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None)

    An alias to :func:`attrs.field()`

    Additional Parameters
        **help** (str_): The help string for Click options

    .. _str: https://docs.python.org/3/library/functions.html#bool


.. function:: secret(*, default=NOTHING, validator=None, repr=***, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None)

    An alias to :func:`option()` but with a default repr that hides screts.

    When printing a settings instances, secret settings will represented with
    `***` istead of their actual value.

    Example:

    .. code-block:: python

        >>> from typed_settings import settings, secret
        >>>
        >>> @settings
        ... class Settings:
        ...     password: str = secret()
        ...
        >>> Settings(password="1234")
        Settings(password=***)

.. autofunction:: evolve


Converters
----------


.. automodule:: typed_settings.converters
   :members:


Click Options
=============

Decorators for using Typed Settings with and as :mod:`click` options.

.. currentmodule:: typed_settings
.. autofunction:: click_options
.. autofunction:: pass_settings


Utilities for generating Click options
--------------------------------------

.. automodule:: typed_settings.click_utils
   :members: TypeHandler, DEFAULT_TYPES, handle_datetime, handle_enum
