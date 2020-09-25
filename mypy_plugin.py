from mypy.plugin import Plugin
from mypy.plugins.attrs import attr_attrib_makers, attr_dataclass_makers


# These work just like `attr.dataclass`.
attr_dataclass_makers.add("attr.frozen")
attr_dataclass_makers.add("typed_settings.settings")

# These are our `attr.ib` makers.
attr_attrib_makers.add("attr.field")
attr_attrib_makers.add("typed_settings.option")
attr_attrib_makers.add("typed_settings.secret")


class MyPlugin(Plugin):
    # Our plugin does nothing but it has to exist so this file gets loaded.
    pass


def plugin(version):
    return MyPlugin
