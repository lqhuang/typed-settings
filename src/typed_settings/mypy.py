"""
A simple mypy plugin that makes the Typed Settings attrs aliases and wrappers
recognized by it.

You can activate the plugin via your :file:`pyproject.toml` or
:file:`mypy.ini`:

.. code-block:: toml

    # pyproject.toml
    [tool.mypy]
    plugins = ["typed_settings.mypy"]

.. code-block:: ini

    # mypy.ini
    [mypy]
    plugins=typed_settings.mypy
"""

try:  # pragma: no cover
    from typing import Type

    from mypy.plugin import Plugin
    from mypy.plugins.attrs import attr_attrib_makers, attr_dataclass_makers
except ImportError:
    pass
else:  # pragma: no cover
    # These work just like `attr.dataclass`.
    attr_dataclass_makers.add("attr.frozen")
    attr_dataclass_makers.add("typed_settings.attrs.settings")
    attr_dataclass_makers.add("tests.test_hooks.auto_converter")

    # These are our `attr.ib` makers.
    attr_attrib_makers.add("attr.field")
    attr_attrib_makers.add("typed_settings.attrs.option")
    attr_attrib_makers.add("typed_settings.attrs.secret")

    class MyPlugin(Plugin):
        # Our plugin does nothing but it has to exist so this file gets loaded.
        pass

    def plugin(version: str) -> Type[Plugin]:
        return MyPlugin
