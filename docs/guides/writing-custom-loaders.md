# Writing Custom Loaders

When you want to load settings from a completely new source, you can implement your own {class}`~typed_settings.loaders.Loader`:

- It has to be a callable (i.e., a function, or a class with a {meth}`~object.__call__()` method).
- It has to accept the user's settings class and a list of {class}`typed_settings.types.OptionInfo` instances.
- It has to return a dictionary with the loaded settings.

~~~{admonition} Why return a {code}`dict` and not a settings instance?
:class: hint

Loaders return a dictionary with loaded settings instead of instances of the user's settings class.

There are two reasons for this:
- The a config file might not contain values for all options, so it might not be possible to instantiate the settings class.
- Dicts can easier be created (most libs for TOML, JSON, or YAML return dicts) an merged than class instances.

Typed Settings validates and cleans the loaded settings from all loaders automatically and
converts them to instances of your settings class.
~~~

In the following example, we'll write a class that loads settings from an instance of the settings class.
This can be useful to useful for application specific defaults for the settings of another library.

Since our loader needs some configuration -- the default instance --,
we'll create a class with an `__init__()` and a `__call__()` method.

The `__init__()` method stores our default instances.
It also creates an instance of {class}`~typed_settings.types.LoaderMeta`
which stores some metadata about the current loader.
It is used for resolving relative paths and for better error messages.

The `__call__()` method is invoked when our loader is called.
It converts the instances to a dictionary with settings and returns it:

```{code-block} python
:emphasize-lines: 7-8,18-19

import attrs
import typed_settings as ts


class InstanceLoader:
    def __init__(self, instance: attrs.AttrsInstance) -> None :
        self.meta = ts.types.LoaderMeta(self)
        self.instance = instance

    def __call__(
        self, settings_cls: type, options: ts.types.OptionList
    ) -> ts.types.LoadedSettings:
        if not isinstance(self.instance, settings_cls):
            raise ValueError(
                f'"self.instance" is not an instance of {settings_cls}: '
                f"{type(self.instance)}"
            )
        settings = attrs.asdict(self.instance)
        return ts.types.LoadedSettings(settings, self.meta)
```

Using the new loader works the same way as we've seen before:

```{code-block} python
:caption: example.py
:emphasize-lines: 6-20, 29

import attrs
import typed_settings as ts


class InstanceLoader:
    def __init__(self, instance: attrs.AttrsInstance) -> None :
        self.meta = ts.types.LoaderMeta(self)
        self.instance = instance

    def __call__(
        self, settings_cls: type, options: ts.types.OptionList
    ) -> ts.types.LoadedSettings:
        if not isinstance(self.instance, settings_cls):
            raise ValueError(
                f'"self.instance" is not an instance of {settings_cls}: '
                f"{type(self.instance)}"
            )
        settings = attrs.asdict(self.instance)
        return ts.types.LoadedSettings(settings, self.meta)


@attrs.frozen
class Settings:
    option1: str
    option2: str


inst_loader = InstanceLoader(Settings("a", "b"))
settings = ts.load_settings(Settings, loaders=[inst_loader])
print(settings)
```
```{code-block} console
$ python example.py
Settings(option1='a', option2='b')
```

The built-in {mod}`~typed_settings.loaders` can serve you as additional examples.
Some are simpler, other a bit more complex.
But all are documented and commented.

````{tip}
Classes with just an {code}`__init__()` and a single method can also be implemented as {func}`~functools.partial()` functions:

```{code-block} python
:emphasize-lines: 1,8,9,29

from functools import partial

import attrs
import typed_settings as ts


def load_from_instance(
    instance: attrs.AttrsInstance,
    settings_cls: type,
    options: ts.types.OptionList,
) -> ts.types.LoadedSettings:
    if not isinstance(instance, settings_cls):
        raise ValueError(
            f'"instance" is not an instance of {settings_cls}: '
            f"{type(instance)}"
        )
    settings = attrs.asdict(instance)
    meta = ts.types.LoaderMeta("InstanceLoader")
    return ts.types.LoadedSettings(settings, meta)


@attrs.frozen
class Settings:
    option1: str
    option2: str


inst_loader = partial(load_from_instance, Settings("a", "b"))
ts.load_settings(Settings, loaders=[inst_loader])
```
````

```{note}
The {class}`~typed_settings.loaders.InstanceLoader` was added to Typed Settings in version 1.0.0 but we'll keep this example.
```
