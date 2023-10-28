```{eval-rst}
.. currentmodule:: typed_settings
```

(clis-with-argparse)=
# CLIs with Argparse

The easiest way to create a CLI for your Settings is by decorating a function with {func}`~typed_settings.cli_argparse.cli()`:

```{code-block} python
:caption: example.py

import typed_settings as ts

@ts.settings
class Settings:
    spam: int = ts.option(default=42, help="Spam count")


@ts.cli(Settings, "example")
def cli(settings: Settings) -> None:
    """Example app"""
    print(settings)


if __name__ == "__main__":
    cli()
```

The {func}`cli()` decorator does a few things:

- It creates an {class}`argparse.ArgumentParser` for you.
- It uses the docstring of the decorated function as description for it.
- It uses the default loaders (see {func}`default_loaders()`) to load settings for the app `"example"`.
- It creates an Argparse argument for each option of the provided settings and takes default values from the loaded settings.
- When the user invokes the CLI, it creates an updated settings instances from the {class}`argparse.Namespace`.
- It passes the settings instances to your function.

Let's see how the generated CLI works like:

```{code-block} console
$ export EXAMPLE_SPAM=23
$ python example.py --help
usage: example.py [-h] [--spam INT]

Example app

options:
  -h, --help  show this help message and exit

Settings:
  Settings options

  --spam INT  Spam count [default: 23]
$ python example.py --spam=3
Settings(spam=3)
```

## Tuning and Extending CLI generation

There are various ways how you can control, fine-tune and extend the default behavior of {func}`~typed_settings.cli_argparse.cli()`:

- You can customize the settings loaders and converter, see {ref}`cli-loaders-converters`.
- You can customize how individual arguments are created ({ref}`argparse-customize-options`) and
  modify or extend how certain Python types are handled (see {ref}`extending-supported-types`).
- You can also directly work with the {class}`~argparse.ArgumentParser` and the {class}`~argparse.Namespace` object, see {ref}`argparse-parser-and-namespace`.

(argparse-customize-options)=
## Customizing the Generated Arguments

Typed Settings tries to create the Argparse arguments in the most sensible way.
But you can override all keyword arguments for {meth}`~argparse.ArgumentParser.add_argument()` for each option individually via the *argparse* argument.

Lets, for example, change the generated metavar:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(
        default=42,
        help="Spam count",
        argparse={"metavar": "SPAM"},
    )


@ts.cli(Settings, "example")
def cli(settings: Settings) -> None:
    """Example app"""
    print(settings)


if __name__ == "__main__":
    cli()
```

Now compare the `--help` output with the [example above](#clis-with-argparse):

```{code-block} console
$ python example.py --help
usage: example.py [-h] [--spam SPAM]

Example app

options:
  -h, --help   show this help message and exit

Settings:
  Settings options

  --spam SPAM  Spam count [default: 42]
```

```{note}
It is not possible to retrieve an option's docstring directly within a Python program.
Thus, Typed Settings can not automatically use it as help text for a command line option.

Since setting a help string is a very common use case,
{func}`~typed_settings.cls_attrs.option()` and {func}`~typed_settings.cls_attrs.secret()` have a *help* argument as a shortcut to `argparse={"help": "..."}`.
```

## Configuring Loaders and Converters

When you just pass an application name to {func}`~typed_settings.cli_argparse.cli()` (as in the examples above),
it uses {func}`default_loaders()` to get the default loaders and {func}`default_converter()` to get the default converter.

Instead of passing an app name, you can pass your own list of loaders:

```python
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42


loaders = [ts.loaders.EnvLoader(prefix="EXAMPLE_")]

@ts.cli(Settings, loaders)
def cli(settings: Settings):
    pass
```

In a similar fashion, you can use your own converter:

```python
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42


converter = ts.default_converter()
# converter.register_structure_hook(my_type, my_converter)


@ts.cli(Settings, "example", converter=converter)
def cli(settings: Settings):
    pass
```

(argparse-parser-and-namespace)=
## Working with the ArgumentParser and Namespace

If you don't like decorators or want to manually modify/extend the generated {class}`~argparse.ArgumentParser`,
you can use the functions {func}`typed_settings.cli_argparse.make_parser()` and {func}`typed_settings.cli_argparse.namespace2settings()`.
They can also be useful for testing purposes.

Here's an example:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(default=42, help="Spam count")


def main():
    # Create an argument parser with options for all settings:
    parser, merged_settings = ts.cli_argparse.make_parser(Settings, "example")
    print(parser)
    # You could now modify/extend the ArgumentParser

    # Parse the command line args (from "sys.argv"):
    namespace = parser.parse_args()
    print(namespace)

    # Convert the Namespace to an instance of your settings class:
    settings = ts.cli_argparse.namespace2settings(
        Settings, namespace, merged_settings=merged_settings,
    )
    print(settings)


if __name__ == "__main__":
    main()
```
```{code-block} console
$ python example.py --spam=3
ArgumentParser(prog='example.py', ...)
Namespace(spam=3)
Settings(spam=3)
```


## Extending Supported Types

The type specific keyword arguments for {meth}`argparse.ArgumentParser.add_argument()` are generated by a thing called {class}`~typed_settings.cli_utils.TypeArgsMaker`.
It is framework agnostic and uses a {class}`~typed_settings.cli_utils.TypeHandler`
that actually generates the framework specific arguments for each type.

For argparse, this is the {class}`typed_settings.cli_argparse.ArgparseHandler`.
The easiest way to extend its capabilities is by passing a dict to it that maps types to specialized handler functions.  The {data}`typed_settings.cli_argparse.DEFAULT_TYPES` contain handlers for datetimes and enums.

```{note}
The {class}`~typed_settings.cli_argparse.ArgparseHandler` supports so many common types
that it was quite hard to come up with an example that makes at least *some* sense …;-)).

The following example is split into several smaller parts to make it easier
to describe what's going on.
At the end, you'll find the complete example in a single box.
```

Let's assume you want to add support for a special *dataclass* that represents an RGB color and
that you want to use a single command line option for it (like {samp}`--color {R G B}`).

```python
import attrs
import dataclasses

@dataclasses.dataclass
class RGB:
    r: int = 0
    g: int = 0
    b: int = 0


@ts.settings
class Settings:
    color: RGB = RGB(0, 0, 0)
```

```{note}
If we used `attrs` instead of {mod}`dataclasses` here, Typed Settings would automatically generate three options `--color-r`, `--color-g`, and `--color-b`.
```

Since we want to create an instance of `RGB` from a tuple,
we need to register a custom converter for it:

```python
converter = ts.default_converter()
converter.register_structure_hook(
    RGB, lambda val, cls: val if isinstance(val, RGB) else cls(*val)
)
```

Next, we need to create a type handler function (see the {class}`~typed_settings.cli_utils.TypeHandlerFunc` protocol) for our dataclass.
It must take a type, a default value and a flag that indicates whether the type was originally wrapped with {class}`typing.Optional`.
It must return a dictionary with keyword arguments for {meth}`argparse.ArgumentParser.add_argument()`.

For our use case, we need an {code}`int` option that takes exactly three arguments and has the metavar {code}`R G B`.
If (and only if) there is a default value for our option, we want to use it.

```python
from typed_settings.cli_utils import Default, StrDict

def handle_rgb(_type: type, default: Default, is_optional: bool) -> StrDict:
    type_info = {
        "type": int,
        "nargs": 3,
        "metavar": ("R", "G", "B"),
    }
    if default:
        type_info["default"] = dataclasses.astuple(default)
    elif is_optional:
        type_info["default"] = None
    return type_info
```

We can now create a {class}`~typed_settings.cli_argparse.ArgparseHandler` and configure it with a dict of our type handlers.

```python
type_dict = {
    **ts.cli_argparse.DEFAULT_TYPES,
    RGB: handle_rgb,
}
type_handler = ts.cli_argparse.ArgparseHandler(type_dict)
```

Finally, we pass that handler to {class}`~typed_settings.cli_utils.TypeArgsMaker` and this in turn to {func}`~typed_settings.cli_argparse.cli()`:

```python
@ts.cli(
    Settings,
    "example",
    converter=converter,
    type_args_maker=ts.cli_utils.TypeArgsMaker(type_handler),
)
def cli(settings: Settings):
    print(settings)
```

Full example

```{code-block} python
:caption: example.py

import dataclasses

import attrs
import typed_settings as ts
from typed_settings.cli_utils import Default, StrDict


@dataclasses.dataclass
class RGB:
    r: int = 0
    g: int = 0
    b: int = 0


@ts.settings
class Settings:
    color: RGB = RGB(0, 0, 0)


converter = ts.default_converter()
converter.register_structure_hook(
    RGB, lambda val, cls: val if isinstance(val, RGB) else cls(*val)
)

def handle_rgb(_type: type, default: Default, is_optional: bool) -> StrDict:
    type_info = {
        "type": int,
        "nargs": 3,
        "metavar": ("R", "G", "B"),
    }
    if default:
        type_info["default"] = dataclasses.astuple(default)
    elif is_optional:
        type_info["default"] = None
    return type_info


type_dict = {
    **ts.cli_argparse.DEFAULT_TYPES,
    RGB: handle_rgb,
}
type_handler = ts.cli_argparse.ArgparseHandler(type_dict)


@ts.cli(
    Settings,
    "example",
    converter=converter,
    type_args_maker=ts.cli_utils.TypeArgsMaker(type_handler),
)
def cli(settings: Settings):
    print(settings)


if __name__ == "__main__":
    cli()
```
```{code-block} console
$ # Check if our metavar and default value is used:
$ python example.py --help
usage: example.py [-h] [--color R G B]

options:
  -h, --help     show this help message and exit

Settings:
  Settings options

  --color R G B  [default: (0, 0, 0)]
$ # Try passing our own color:
$ python example.py --color 23 42 7
Settings(color=RGB(r=23, g=42, b=7))
```

This sounds a bit involved and it *is* in fact a bit involved,
but this mechanism gives you the freedom to modify all behavior to your needs.

If adding a simple type handler is not enough, you can extend the {class}`~typed_settings.cli_argparse.ArgparseHandler` (or create a new one)
and – if that is not enough – event the {class}`~typed_settings.cli_utils.TypeArgsMaker`.
