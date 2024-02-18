```{currentmodule} typed_settings
```

(guide-settings-from-env-vars)=
# Environment Variables

This pages explains how to load settings from environment variables.

## Basics

Typed Settings loads environment variables that match `{PREFIX}{OPTION_NAME}`.

{samp}`{PREFIX}` is an option for the {class}`~typed_settings.loaders.EnvLoader`.
It should be UPPER_CASE and end with an `_`, but this is not enforced.
The prefix can also be an empty string.

If you use {func}`load()` (or {func}`default_loaders()`), {samp}`{PREFIX}` is derived from the *appname* argument.
For example, {code}`"appname"` becomes {code}`"APPNAME_"`.
You can override it with the *env_prefix* argument.
You can also completely disable environment variable loading by setting *env_prefix* to {code}`None`.

Values loaded from environment variables are strings.
They are converted to the type specified in the settings class by the converter at the end of the settings loading process.
The {func}`~typed_settings.converters.default_converter()` supports the most common types like booleans, dates, enums and paths.

```{danger}
Never pass secrets via environment variables!

See {ref}`secrets` for details.
```

## Nested settings

Settings classes can be nested but environment variables have a flat namespace.
So Typed Settings builds a flat list of all options and uses the "dotted path" to an attribute (e.g., {code}`attrib.nested_attrib.nested_nested_attrib`) for mapping flat names to nested attributes.

Here's an example:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Nested:
    attrib: int = 0


@ts.settings
class Settings:
    nested: Nested = Nested()
    attrib: str = ""
    flag: bool = True


print(ts.load(Settings, "myapp"))
```
```{code-block} console
$ export MYAPP_ATTRIB=spam
$ export MYAPP_FLAG=0
$ export MYAPP_NESTED_ATTRIB=42
$ python example.py
Settings(nested=Nested(attrib=42), attrib='spam', flag=False)
```

### Delimiter for nested settings

If the {code}`Settings` from above defined an attribute {code}`nested_attrib`},
this would lead to a conflict with the env-var name {code}`MYAPP_NESTED_ATTRIB`.

To avoid this problem, you can define a *nested delimiter* when you load the settings:

```{code-block} python
:caption: example.py
:emphasize-lines: 18

import typed_settings as ts


@ts.settings
class Nested:
    attrib: str


@ts.settings
class Settings:
    nested: Nested
    nested_attrib: str


settings = ts.load(
    Settings,
    "myapp",
    env_nested_delimiter="__",
)
print(settings)
```
```{code-block} console
$ export MYAPP_NESTED_ATTRIB=spam
$ export MYAPP_NESTED__ATTRIB=eggs
$ python example.py
Settings(nested=Nested(attrib='eggs'), nested_attrib='spam')
```

## Overriding the var name for a single option

Sometimes, you may want to read an option from another variable than Typed Settings would normally do.
For example, your company's convention might be to use {code}`SSH_PRIVATE_KEY_FILE`, but your app would look for {code}`MYAPP_SSH_KEY_FILE`:

```{code-block} python
import typed_settings as ts


@ts.settings
class Settings:
    ssh_key_file: str = ""


print(ts.load(Settings, "myapp"))
```

In order to read from the desired env var, you can use {func}`os.getenv()` and assign its result as default for your option:

```{code-block} python
:caption: example.py

import os
import typed_settings as ts


@ts.settings
class Settings:
    ssh_key_file: str = os.getenv("SSH_PRIVATE_KEY_FILE", "")


print(ts.load(Settings, "myapp"))
```
```{code-block} console
$ export SSH_PRIVATE_KEY_FILE='/run/private/id_ed25519'
$ python example.py
Settings(ssh_key_file='/run/private/id_ed25519')
```
