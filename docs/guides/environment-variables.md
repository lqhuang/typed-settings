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
    attrib1: int = 0
    attrib2: bool = True


@ts.settings
class Settings:
    nested: Nested = Nested()
    attrib: str = ""


print(ts.load(Settings, "myapp"))
```
```{code-block} console
$ export MYAPP_ATTRIB=spam
$ export MYAPP_NESTED_ATTRIB1=42
$ export MYAPP_NESTED_ATTRIB2=0
$ python example.py
Settings(nested=Nested(attrib1=42, attrib2=False), attrib='spam')
```

```{warning}
{code}`Settings` should not define an attribute {code}`nested_attrib1` as it would conflict with {code}`nested.attrib1`.
If you added this attribute to the example above, the value `42` would be assigned to both options.
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
