```{eval-rst}
.. currentmodule:: typed_settings
```

(clis-with-click)=
# CLIs with Click

You can generate Click command line options for your settings.
These let the users of your application override settings loaded from other sources (like config files).

The general algorithm for generating a [Click] CLI for your settings looks like this:

1. You decorate a Click command with {func}`~typed_settings.cli_click.click_options()`.

2. The decorator will immediately (namely, at module import time)

   - load your settings (e.g., from config files or env vars),
   - create a {func}`click.option()` for each setting and use the loaded settings value as default for that option.

3. You add a positional/keyword argument to your CLI function.

4. When you run your CLI, the decorator :

   - updates the settings with option values from the command line,
   - stores the settings instance in the Click context object (see {attr}`click.Context.obj`),
   - passes the updated settings instances as positional/keyword argument to your CLI function.

```{note}
By default, the settings instance is passed as positional argument to your CLI function.
You can optionally specify a keyword argument name if you want your settings to be passed via a keyword argument.

See [](#click-order-of-decorators) and [](#click-settings-as-keyword-arguments) for details about argument passing.
```

Here is an example:

```{code-block} python
:caption: example.py

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(default=42, help="Amount of SPAM required")


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings) -> None:
    """Example app"""
    print(settings)


if __name__ == "__main__":
    cli()
```

As you can see, an option is generated for each setting:

```{code-block} console
$ export EXAMPLE_SPAM=23
$ python example.py --help
Usage: example.py [OPTIONS]

  Example app

Options:
  --spam INTEGER  Amount of SPAM required  [default: 23]
  --help          Show this message and exit.
```

Let's invoke it with the `--spam` option:

```{code-block} console
$ python example.py --spam=3
Settings(spam=3)
```

The code above is roughly equivalent to:

```{code-block} python
:caption: example.py

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(default=42, help="Amount of SPAM required")


DEFAULTS = ts.load(Settings, "example")


@click.command()
@click.option(
    "--spam",
    type=int,
    default=DEFAULTS.spam,
    show_default=True,
    help="Amount of SPAM required",
)
def cli(spam: int):
    print(spam)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --spam INTEGER  Amount of SPAM required  [default: 42]
  --help          Show this message and exit.
$ python example.py --spam=3
3
```

The major difference between the two examples is that Typed Settings passes the complete settings instances and not individual options.


## Customizing the Generated Options

Typed Settings does its best to generate the Click option in the most sensible way.
However, you can override everything if you want to.

Lets, for example, change the generated metavar:

```{code-block} python
:caption: example.py
:emphasize-lines: 10

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(
        default=42,
        help="Amount of SPAM required",
        click={"metavar": "SPAM"},
    )


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings) -> None:
    """Example app"""
    print(settings)


if __name__ == "__main__":
    cli()
```

Now compare the `--help` output with the [example above](#clis-with-click):

```{code-block} console
$ export EXAMPLE_SPAM=23
$ python example.py --help
Usage: example.py [OPTIONS]

  Example app

Options:
  --spam SPAM  Amount of SPAM required  [default: 23]
  --help       Show this message and exit.
```

```{note}
It is not possible to retrieve an option's docstring directly within a Python program.
Thus, Typed Settings can not automatically use it as help text for a command line option.

Since this is a very common use case,
{func}`~typed_settings.cls_attrs.option()` and {func}`~typed_settings.cls_attrs.secret()` have a *help* argument as a shortcut to `click={"help": "..."}`.
```

### Changing the Param Decls

Typed Settings generate a single param declaration for each option: {samp}`--{option-name}`.
One reason you might want to change this is to add an additional short version (e.g., `-o`):

```{code-block} python
:caption: example.py
:emphasize-lines: 9

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(
        default=23,
        click={"param_decls": ("--spam", "-s")},
    )


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings):
    print(settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  -s, --spam INTEGER  [default: 23]
  --help              Show this message and exit.
$ python example.py -s 3
Settings(spam=3)
```

### Tuning Boolean Flags

Another use case is changing how binary flags for {class}`bool` typed options are generated.
By default, Typed Settings generates `--flag/--no-flag`.

But imagine this example, where our flag is always `False` and we only want to allow users to enable it:

```python
import typed_settings as ts

@ts.settings
class Settings:
    flag: bool = False
```

We can achieve this by providing a custom param decl.:

```{code-block} python
:caption: example.py
:emphasize-lines: 10

import click
import typed_settings as ts


@ts.settings
class Settings:
    flag: bool = ts.option(
        default=False,
        help='Turn "flag" on.',
        click={"param_decls": ("--on",)},
    )


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings):
    print(settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --on    Turn "flag" on.
  --help  Show this message and exit.
$ python example.py --on
Settings(flag=True)
$ python example.py
Settings(flag=False)
```

```{note}
You do not need to add the option name to the param decls if the flag has a custom name.
Typed Settings will always be able to map the flag to the correct option.
You only need to take care that you don't introduce any name clashes with other options' param decls.

It is also not needed to add `is_flag: True` to the click args.
```


### Option Groups

Options for nested settings classes have a common prefix,
so you can see that they belong together when you look at a command's `--help` output.
You can use [option groups] to make the distinction even clearer.

In order for this to work, Typed Settings lets you customize which decorator function is called for generating Click options.
It also allows you to specify a decorator that is called with each settings class.

This functionality is specified by the {class}`~typed_settings.cli_click.DecoratorFactory` protocol.
You can pass an implementation of that protocol to {func}`~typed_settings.cli_click.click_options()` to define the desired behavior.

The default is to use {class}`~typed_settings.cli_click.ClickOptionFactory`.
With an instance of {class}`~typed_settings.cli_click.OptionGroupFactory`, you can generate option groups:

```{code-block} python
:caption: example.py
:emphasize-lines: 30-31,38

import click
import typed_settings as ts


@ts.settings
class SpamSettings:
    """
    Settings for spam
    """
    a: str = ""
    b: str = ""


@ts.settings
class EggsSettings:
    """
    Settings for eggs
    """
    a: str = ""
    c: str = ""


@ts.settings
class Main:
    """
    Main settings
    """
    a: int = 0
    b: int = 0
    spam: SpamSettings = SpamSettings()
    eggs: EggsSettings = EggsSettings()


@click.command()
@ts.click_options(
    Main,
    "myapp",
    decorator_factory=ts.cli_click.OptionGroupFactory(),
)
def cli(settings: Main):
    print(settings)


if __name__ == "__main__":
    cli()
```

When we now run our program with `--help`, we can see the option groups.
The first line of the settings class' docstring is used as group name:

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  Main settings:
    --a INTEGER        [default: 0]
    --b INTEGER        [default: 0]
  Settings for spam:
    --spam-a TEXT
    --spam-b TEXT
  Settings for eggs:
    --eggs-a TEXT
    --eggs-c TEXT
  --help               Show this message and exit.
```

### Derived attributes

Typed Settings supports [attrs derived attributes][attrs_derived_attributes].
The values of these attributes are dynamically set in `__attrs_post_init__()`.
They are created with `ts.option(init=False)`.

These attributes are excluded from `click_options`:

```{code-block} python
:caption: example.py

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = ts.option(default=23)
    computed_spam: int = ts.option(init=False)

    def __attrs_post_init__(self):
            self.computed_spam = self.spam + 19


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings):
    print(settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --spam INTEGER  [default: 23]
  --help          Show this message and exit.
$ python example.py
Settings(spam=23, computed_spam=42)
```

## Passing Settings to Sub-Commands

One of Click's main advantages is that it makes it quite easy to create CLIs with sub commands (think of {program}`Git`).

If you want to load your settings once in the main command and make them accessible in all subcommands,
you can use the {func}`~typed_settings.cli_click.pass_settings` decorator.
It searches all *context* objects from the current one via all parent context until it finds a settings instances and passes it to the decorated command:

```{code-block} python
:caption: example.py
:emphasize-lines: 16-17

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42

@click.group()
@ts.click_options(Settings, "example")
def cli(settings: Settings):
    pass


@cli.command()
@ts.pass_settings
def sub_cmd(settings: Settings):
    click.echo(settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --spam=3 sub-cmd
Settings(spam=3)
```

```{important}
The example above only works well if either:

- Only the parent group loads settings
- Only concrete commands load settings

This is because the settings instance is stored in the {attr}`click.Context.obj` with a fixed key.

If you want your sub-commands to *additonally* load their own settings,
please continue to read the next two setions.
```

(click-order-of-decorators)=
## Order of Decorators

Click passes the settings instance to your CLI function as positional argument by default.
If you use other decorators that behave similarly (e.g., {func}`click.pass_context`),
the order of decorators and arguments matters.

The innermost decorator (the one closest to the {code}`def`) will be passed as first argument,
The second-innermost as second argument and so forth:

```{code-block} python
:caption: example.py
:emphasize-lines: 11-13

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42


@click.command()
@ts.click_options(Settings, "example")
@click.pass_context
def cli(ctx: click.Context, settings: Settings):
    print(ctx, settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py
<click.core.Context object at 0x...> Settings(spam=42)
```

(click-settings-as-keyword-arguments)=
## Settings as Keyword Arguments

If a command wants to load multiple types of settings or
if you use command groups where both, the parent group and its sub commands, want to load settings,
then the "store a single settings instance and pass it as positional argument" approach no longer works.

Instead, you need to specify an *argname* for {func}`~typed_settings.cli_click.click_options()` and {func}`~typed_settings.cli_click.pass_settings()`.
The settings instance is then stored under that key in the {attr}`click.Context.obj` and passed as keyword argument to the decorated function:

```{code-block} python
:caption: example.py
:emphasize-lines: 16-18,21,27-29

import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42


@ts.settings
class CmdSettings:
    eggs: str = ""


@click.group()
@ts.click_options(Settings, "example", argname="main_settings")
@click.pass_obj
def cli(ctx_obj: dict, *, main_settings: Settings):
    # "main_settings" is now a keyword argument
    # It is stored in the ctx object under the same key
    print(main_settings is ctx_obj["main_settings"])


# Require the parent group's settings as "main_settings"
# Define command specific settings as "cmd_settings"
@cli.command()
@ts.pass_settings(argname="main_settings")
@ts.click_options(CmdSettings, "example-cmd", argname="cmd_settings")
def cmd(*, main_settings: Settings, cmd_settings: CmdSettings):
    print(main_settings)
    print(cmd_settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --spam=42 cmd --eggs=many
True
Settings(spam=42)
CmdSettings(eggs='many')
```

(cli-loaders-converters)=
## Configuring Loaders and Converters

When you just pass an application name to {func}`~typed_settings.cli_click.click_options()` (as in the examples above),
it uses {func}`default_loaders()` to get the default loaders and {func}`default_converter()` to get the default converter.

Instead of passing an app name, you can pass your own list of loaders:

```python
import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42


loaders = [ts.loaders.EnvLoader(prefix="EXAMPLE_")]

@click.command()
@ts.click_options(Settings, loaders)
def cli(settings: Settings):
    pass
```

In a similar fashion, you can use your own converter:

```python
import click
import typed_settings as ts


@ts.settings
class Settings:
    spam: int = 42


converter = ts.default_converter()
# converter.register_structure_hook(my_type, my_converter)


@click.command()
@ts.click_options(Settings, "example", converter=converter)
def cli(settings: Settings):
    pass
```


## Optional and Union Types

Using optional options (with type {samp}`Optional[{T}]` or {samp}`{T} | None`) is generelly supported for scalar types and containers:

```{code-block} python
:caption: example.py

import click
import typed_settings as ts


@ts.settings
class Settings:
    a: int | None
    b: list[int] | None


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings):
    print(settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --a INTEGER
  --b INTEGER
  --help       Show this message and exit.
$ python example.py
Settings(a=None, b=[])
```

```{note}
Click will always give us an empty list, even if the default for an optional list is `None`.
```

However, optional nested settings do not work:

```{code-block} python
:caption: example.py

import click
import typed_settings as ts


@ts.settings
class Nested:
   a: int
   b: int | None


@ts.settings
class Settings:
    n: Nested
    o: Nested | None


@click.command()
@ts.click_options(Settings, "example")
def cli(settings: Settings):
    print(settings)


if __name__ == "__main__":
    cli()
```

```{code-block} console
$ python example.py --help
Usage: example.py [OPTIONS]

Options:
  --n-a INTEGER  [required]
  --n-b INTEGER
  --o NESTED
  --help         Show this message and exit.
```

Unions other than {code}`Optional` are also not supported.

(extending-supported-types)=
## Extending Supported Types

The type specific keyword arguments for {func}`click.option()` are generated by a thing called {class}`~typed_settings.cli_utils.TypeArgsMaker`.
It is framework agnostic and uses a {class}`~typed_settings.cli_utils.TypeHandler`
that actually generates the framework specific arguments for each type.

For Click, this is the {class}`typed_settings.cli_click.ClickHandler`.
The easiest way to extend its capabilities is by passing a dict to it that maps types to specialized handler functions.  The {data}`typed_settings.cli_click.DEFAULT_TYPES` contain handlers for datetimes and enums.

```{note}
The {class}`~typed_settings.cli_click.ClickHandler` supports so many common types
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
It must return a dictionary with keyword arguments for {func}`click.option()`.

For our use case, we need an {code}`int` option that takes exactly three arguments and has the metavar {code}`R G B`.
If (and only if) there is a default value for our option, we want to use it.

```python
from typed_settings.cli_utils import Default, StrDict

def handle_rgb(_type: type, default: Default, is_optional: bool) -> StrDict:
    type_info = {
        "type": int,
        "nargs": 3,
        "metavar": "R G B",
    }
    if default:
        type_info["default"] = dataclasses.astuple(default)
    elif is_optional:
        type_info["default"] = None
    return type_info
```

We can now create a {class}`~typed_settings.cli_click.ClickHandler` and configure it with a dict of our type handlers.

```python
type_dict = {
    **ts.cli_click.DEFAULT_TYPES,
    RGB: handle_rgb,
}
type_handler = ts.cli_click.ClickHandler(type_dict)
```

Finally, we pass that handler to {class}`~typed_settings.cli_utils.TypeArgsMaker` and this in turn to {func}`~typed_settings.cli_click.click_options()`:

```python
@click.command()
@ts.click_options(
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
import click
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
        "metavar": "R G B",
    }
    if default:
        type_info["default"] = dataclasses.astuple(default)
    elif is_optional:
        type_info["default"] = None
    return type_info


type_dict = {
    **ts.cli_click.DEFAULT_TYPES,
    RGB: handle_rgb,
}
type_handler = ts.cli_click.ClickHandler(type_dict)


@click.command()
@ts.click_options(
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
Usage: example.py [OPTIONS]

Options:
  --color R G B  [default: 0, 0, 0]
  --help         Show this message and exit.
$ # Try passing our own color:
$ python example.py --color 23 42 7
Settings(color=RGB(r=23, g=42, b=7))
```

This sounds a bit involved and it *is* in fact a bit involved,
but this mechanism gives you the freedom to modify all behavior to your needs.

If adding a simple type handler is not enough, you can extend the {class}`~typed_settings.cli_click.ClickHandler` (or create a new one)
and – if that is not enough – event the {class}`~typed_settings.cli_utils.TypeArgsMaker`.

[attrs_derived_attributes]: https://www.attrs.org/en/stable/init.html#derived-attributes
[click]: https://click.palletsprojects.com
[option groups]: https://click-option-group.readthedocs.io
