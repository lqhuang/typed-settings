=============
API Reference
=============

This is the full list of all public classes and functions.

.. currentmodule:: typed_settings


Attrs Helpers
=============

Helpers for creating :mod:`attrs` classes and fields with sensible details for Typed Settings.

.. autofunction:: settings
.. autofunction:: option
.. autofunction:: secret


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
