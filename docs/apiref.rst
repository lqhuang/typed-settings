=============
API Reference
=============

This is the full list of all public classes and functions.

.. currentmodule:: typed_settings


Attrs Helpers
=============

Helpers for creating :mod:`attrs` classes and fields with sensible details for Typed Settings.

.. function:: settings(maybe_cls=None, *, these=None, repr=None, hash=None, init=None, slots=True, frozen=True, weakref_slot=True, str=False, auto_attribs=None, kw_only=False, cache_hash=False, auto_exc=True, eq=None, order=False, auto_detect=True, getstate_setstate=None, on_setattr=None, field_transformer=<function auto_convert>)

    An alias to :func:`attr.frozen`,
    configured with a *field_transformer* that automatically adds converters to all fields based on their annotated type.

    Supported types:

    - bool (truthy values: ``True``, ``"True"``, ``"true"``, ``"yes"``, ``"1"``, ``1``, falsy values: ``False``, ``"False"``, ``"false"``, ``"no"``, ``"0"``, ``0``)
    - int
    - float
    - str
    - datetime (see :meth:`datetime.datetime.fromisoformat()`, the ``Z`` suffix is also supported)
    - Enums
    - Nested attrs/settings classes
    - List[T] (values can be all supported types)
    - Dict[str, T] (values can be all suppported types)
    - Tuple[T, ...] (list-like tuples)
    - Tuple[T1, T2] (struct-like tuples)
    - Any
    - Optional[T]
    - Union[T1, T2]

    See :mod:`typed_settings.attrs.converters` for details.


.. function:: option(*, default=NOTHING, validator=None, repr=True, hash=None, init=True, metadata=None, converter=None, factory=None, kw_only=False, eq=None, order=None, on_setattr=None, help=None)

    An alias to :func:`attr.field()`

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

.. .. autofunction:: option
.. .. autofunction:: secret


Core Functions
==============

Core functions for loading and working with settings.

.. autofunction:: load_settings
.. autofunction:: update_settings


Click Options
=============

Decorators for using Typed Settings with and as :mod:`click` options.

.. autofunction:: click_options
.. autofunction:: pass_settings


Validators, Converters, Hooks for ``attrs``
===========================================

These functions are here to mature and may eventually end up in attrs.

Validators
----------

.. automodule:: typed_settings.attrs.validators
   :members:

Converters
----------

.. automodule:: typed_settings.attrs.converters
   :members:

Hooks
-----

.. automodule:: typed_settings.attrs.hooks
   :members:
