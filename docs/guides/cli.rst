.. currentmodule:: typed_settings

============================
CLIs with Argparse and Click
============================

You can generate command line interfaces based on your settings classes.
Typed Settings generates a CLI argument for each option of your settings and passes an instanses of these settings to your CLI function.
This lets the users of your application easily override settings loaded from other sources (like config files).


Argparse or Click?
==================

:mod:`argparse` is a standard library module.
It is easy to get started with but it, but you also notice the age of the API.
More modern libraries like :mod:`click` make it easier to handle complex data types and create command line apps with sub commands.

You can use :mod:`argparse` if you just want to create a simple CLI without adding extra dependencies.

.. image:: ../_static/cli-argparse-light.png
   :align: center
   :class: only-light
   :alt: "--help" output of an "argparse" based Typed Settings CLI

.. image:: ../_static/cli-argparse-dark.png
   :align: center
   :class: only-dark
   :alt: "--help" output of an "argparse" based Typed Settings CLI

If you want to build a larger, more complex application, :mod:`click` maybe more appropriate.

.. image:: ../_static/cli-click-light.png
   :align: center
   :class: only-light
   :alt: "--help" output of a "Click" based Typed Settings CLI

.. image:: ../_static/cli-click-dark.png
   :align: center
   :class: only-dark
   :alt: "--help" output of a "Click" based Typed Settings CLI

Wich rich-click_ you can also make Click CLIs quite fancy.

.. _rich-click: https://pypi.org/project/rich-click

.. image:: ../_static/cli-rich_click-light.png
   :align: center
   :class: only-light
   :alt: "--help" output of a "Click" based Typed Settings CLI with "rich-click" styling

.. image:: ../_static/cli-rich_click-dark.png
   :align: center
   :class: only-dark
   :alt: "--help" output of a "Click" based Typed Settings CLI with "rich-click" styling

But the most important thing is: choose the framework *you* feel most comfortable with.


.. _clis-with-argparse:

CLIs with Argparse
==================

The easiest way to create a CLI for your Settings is by decorating a function with :func:`~typed_settings.argparse_utils.cli()`:

.. code-block:: python

    >>> import typed_settings as ts
    >>>
    >>> monkeypatch.setenv("EXAMPLE_SPAM", "23")
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=42, help="Spam count")
    ...
    >>> @ts.cli(Settings, "example")
    ... def cli(settings: Settings) -> None:
    ...     """Example app"""
    ...     print(settings)

In a real application, you would also add:

.. code-block:: python

    if __name__ == "main":
        cli()

Let's see what the generated CLI looks like:

.. code-block:: python

    >>> invoke(cli, "--help")
    usage: cli [-h] [--spam INT]
    <BLANKLINE>
    Example app
    <BLANKLINE>
    options:
      -h, --help  show this help message and exit
    <BLANKLINE>
    Settings:
      Settings options
    <BLANKLINE>
      --spam INT  Spam count [default: 23]
    >>>
    >>> invoke(cli, "--spam=3")
    Settings(spam=3)

The decorator does a few things:

- It creates an :class:`argparse.ArgumentParser` for you.
- It uses the docstring of the decorated function as description for it.
- It uses the default loaders (see :func:`default_loaders()`) to load settings for the app ``"example"``.
- It creates an Argparse argument for each option of the provided settings and takes default values from the loaded settings.
- When the user invokes the CLI, it creates an updated settings instances from the :class:`argparse.Namespace`.
- It passes the settings instances to your function.


Tuning and Extending CLI generation
-----------------------------------

There are various ways how you can control, fine-tune and extend the default behavior of :func:`~typed_settings.argparse_utils.cli()`:

- You can customize the settings loaders and converter, see :ref:`cli-loaders-converters`.

- You can customize how individual arguments are created (:ref:`argparse-customize-options`) and
  modify or extend how certain Python types are handled (see :ref:`extending-supported-types`).

- You can also directly work with the :class:`~argparse.ArgumentParser` and the :class:`~argparse.Namespace` object, see :ref:`argparse-parser-and-namespace`.


.. _argparse-customize-options:

Customizing the Generated Arguments
-----------------------------------

Typed Settings tries to create the Argparse arguments in the most sensible way.
But you can override all keyword arguments for :meth:`~argparse.ArgumentParser.add_argument()` for each option individually via the *argparse* argument.

Lets, for example, change the generated metavar:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(
    ...         default=42,
    ...         help="Spam count",
    ...         argparse={"metavar": "SPAM"},
    ...     )
    ...
    >>> @ts.cli(Settings, "example")
    ... def cli(settings: Settings) -> None:
    ...     """Example app"""
    ...     print(settings)
    ...

Now compare the ``--help`` output with the :ref:`example above <clis-with-argparse>`:

.. code-block:: python

    >>> invoke(cli, "--help")
    usage: cli [-h] [--spam SPAM]
    <BLANKLINE>
    Example app
    <BLANKLINE>
    options:
      -h, --help   show this help message and exit
    <BLANKLINE>
    Settings:
      Settings options
    <BLANKLINE>
      --spam SPAM  Spam count [default: 23]

.. note::

   It is not possible to retrieve an option's docstring directly within a Python program.
   Thus, Typed Settings can not automatically use it as help text for a command line option.

   Since this is a very common use case,
   :func:`~typed_settings.attrs.option()` and :func:`~typed_settings.attrs.secret()` have a *help* argument as a shortcut to ``argparse={"help": "..."}``.



.. _argparse-parser-and-namespace:

Working with the ArgumentParser and Namespace
---------------------------------------------

If you don't like decorators or want to manually modify/extend the generated :class:`~argparse.ArgumentParser`,
you can use the functions :func:`typed_settings.argparse_utils.make_parser()` and :func:`typed_settings.argparse_utils.namespace2settings()`.
They can also be useful for testing purposes.

Here's an example:

.. code-block:: python

    >>> import typed_settings.argparse_utils
    >>>
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=42, help="Spam count")
    ...
    >>> parser = typed_settings.argparse_utils.make_parser(Settings, "example")
    >>> parser
    ArgumentParser(prog='...', ...)
    >>> namespace = parser.parse_args(["--spam=3"])  # sys.argv[1:], without the prog. name
    >>> namespace
    Namespace(spam=3)
    >>> typed_settings.argparse_utils.namespace2settings(Settings, namespace)
    Settings(spam=3)


.. _clis-with-click:

CLIs with Click
===============

You can generate Click command line options for your settings.
These let the users of your application override settings loaded from other sources (like config files).

The general algorithm for generating a Click_ CLI for your settings looks like this:

#. You decorate a Click command with :func:`~typed_settings.click_utils.click_options()`.

#. The decorator will immediately (namely, at module import time)

   - load your settings (e.g., from config files or env vars),
   - create a :func:`click.option()` for each setting and use the loaded settings value as default for that option.

#. You add a positional/keyword argument to your CLI function.

#. When you run your CLI, the decorator :

   - updates the settings with option values from the command line,
   - stores the settings instance in the Click context object (see :attr:`click.Context.obj`),
   - passes the updated settings instances as positional/keyword argument to your CLI function.

.. _click: https://click.palletsprojects.com

.. note::

   By default, the settings are passed as positional argument.
   You can optionally specify a keyword argument name if you want your settings to be passed as keyword argument.

   See :ref:`click-order-of-decorators` and :ref:`click-settings-as-keyword-arguments` for details about argument passing.

Take this minimal example:

.. code-block:: python

    >>> import click
    >>> import typed_settings as ts
    >>>
    >>> monkeypatch.setenv("EXAMPLE_SPAM", "23")
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=42, help="Amount of SPAM required")
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings) -> None:
    ...     """Example app"""
    ...     print(settings)

In a real application, you would also add:

.. code-block:: python

    if __name__ == "main":
        cli()

As you can see, an option is generated for each setting:

.. code-block:: python

    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
      Example app
    <BLANKLINE>
    Options:
      --spam INTEGER  Amount of SPAM required  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>

Let's invoke it with the ``--spam`` option:

.. code-block:: python

    >>> invoke(cli, "--spam=3")
    Settings(spam=3)
    <BLANKLINE>


The code above is roughly equivalent to:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=42, help="Amount of SPAM required")
    ...
    >>> defaults = ts.load(Settings, "example")
    >>>
    >>> @click.command()
    ... @click.option(
    ...     "--spam",
    ...     type=int,
    ...     default=defaults.spam,
    ...     show_default=True,
    ...     help="Amount of SPAM required",
    ... )
    ... def cli(spam: int):
    ...     print(spam)
    ...
    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  Amount of SPAM required  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>
    >>> invoke(cli, "--spam=3")
    3
    <BLANKLINE>

The major difference between the two is that Typed Settings passes the complete settings instances and not individual options.


Customizing the Generated Options
---------------------------------

Typed Settings does its best to generate the Click option in the most sensible way.
However, you can override everything if you want to.

Lets, for example, change the generated metavar:

.. code-block:: python

    >>> import click
    >>> import typed_settings as ts
    >>>
    >>> monkeypatch.setenv("EXAMPLE_SPAM", "23")
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(
    ...         default=42,
    ...         help="Amount of SPAM required",
    ...         click={"metavar": "SPAM"},
    ...     )
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings) -> None:
    ...     """Example app"""
    ...     print(settings)

Now compare the ``--help`` output with the :ref:`example above <clis-with-click>`:

.. code-block:: python

    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
      Example app
    <BLANKLINE>
    Options:
      --spam SPAM  Amount of SPAM required  [default: 23]
      --help       Show this message and exit.
    <BLANKLINE>

.. note::

   It is not possible to retrieve an option's docstring directly within a Python program.
   Thus, Typed Settings can not automatically use it as help text for a command line option.

   Since this is a very common use case,
   :func:`~typed_settings.attrs.option()` and :func:`~typed_settings.attrs.secret()` have a *help* argument as a shortcut to ``click={"help": "..."}``.


Changing the Param Decls
^^^^^^^^^^^^^^^^^^^^^^^^

Typed Settings generate a single param declaration for each option: :samp:`--{option-name}`.
One reason you might want to change this is to add an additional short version (e.g., ``-o``):

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=23, click={"param_decls": ("--spam", "-s")})
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)

    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      -s, --spam INTEGER  [default: 23]
      --help              Show this message and exit.
    <BLANKLINE>
    >>> invoke(cli, "-s", "3")
    Settings(spam=3)
    <BLANKLINE>

Tuning Boolean Flags
^^^^^^^^^^^^^^^^^^^^

Another use case is changing how binary flags for :class:`bool` typed options are generated.
By default, Typed Settings generates ``--flag/--no-flag``.

But imagine this example, where our flag is always ``False`` and we only want to allow users to enable it:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     flag: bool = False

We can achieve this by providing a custom param decl.:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     flag: bool = ts.option(
    ...         default=False,
    ...         help='Turn "flag" on.',
    ...         click={"param_decls": ("--on")},
    ...     )
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)

    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --on    Turn "flag" on.
      --help  Show this message and exit.
    <BLANKLINE>
    >>> invoke(cli, "--on")
    Settings(flag=True)
    <BLANKLINE>
    >>> invoke(cli, )
    Settings(flag=False)
    <BLANKLINE>

.. note::

   You do not need to add the option name to the param decls if the flag has a custom name.
   Typed Settings will always be able to map the flag to the correct option.
   You only need to take care that you don't introduce any name clashes with other options' param decls.

   It is also not needed to add ``is_flag: True`` click args.

Note, that we added the param decl. ``flag`` in addition to ``--on``.
This is required for Click to map the flag to the correct option.
We would not need that if we named our flag ``--flag``.

Option Groups
^^^^^^^^^^^^^

Options for nested settings classes have a common prefix,
so you can see that they belong together when you look at a command's ``--help`` output.
You can use `option groups`_ to make the distinction even clearer.

In order for this to work, Typed Settings lets you customize which decorator function is called for generating Click options.
It also allows you to specify a decorator that is called with each settings class.

This functionality is specified by the :class:`~typed_settings.click_utils.DecoratorFactory` protocol.
You can pass an implementation of that protocol to :func:`~typed_settings.click_utils.click_options()` to define the desired behavior.

The default is to use :class:`~typed_settings.click_utils.ClickOptionFactory`.
With an instance of :class:`~typed_settings.click_utils.OptionGroupFactory`, you can generate option groups:


.. code-block:: python

    >>> from typed_settings.click_utils import OptionGroupFactory
    >>>
    >>>
    >>> @ts.settings
    ... class SpamSettings:
    ...     """
    ...     Settings for spam
    ...     """
    ...     a: str = ""
    ...     b: str = ""
    >>>
    >>> @ts.settings
    ... class EggsSettings:
    ...     """
    ...     Settings for eggs
    ...     """
    ...     a: str = ""
    ...     c: str = ""
    ...
    >>> @ts.settings
    ... class Main:
    ...     """
    ...     Main settings
    ...     """
    ...     a: int = 0
    ...     b: int = 0
    ...     spam: SpamSettings = SpamSettings()
    ...     eggs: EggsSettings = EggsSettings()
    >>>
    >>> @click.command()
    ... @ts.click_options(Main, "myapp", decorator_factory=OptionGroupFactory())
    ... def cli(settings: Main):
    ...     print(settings)

When we now run our program with ``--help``, we can see the option groups.
The first line of the settings class' docstring is used as group name:

.. code-block:: python

    >>> invoke(cli, "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: cli [OPTIONS]
    <BLANKLINE>
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
    <BLANKLINE>


.. _option groups: https://click-option-group.readthedocs.io

Derived attributes
^^^^^^^^^^^^^^^^^^

Typed Settings supports `attrs derived attributes <attrs_derived_attributes_>`_.
The values of these attributes are dynamically set in ``__attrs_post_init__()``.
They are created with ``ts.option(init=False)``.

These attributes are excluded from ``click_options``:

.. _attrs_derived_attributes: https://www.attrs.org/en/stable/init.html#derived-attributes

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=23)
    ...     computed_spam: int = ts.option(init=False)
    ...
    ...     def __attrs_post_init__(self):
    ...             self.computed_spam = self.spam + 19
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)

    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>
    >>> invoke(cli)
    Settings(spam=23, computed_spam=42)
    <BLANKLINE>


Passing Settings to Sub-Commands
--------------------------------

One of Click's main advantages is that it makes it quite easy to create CLIs with sub commands (think of :program:`Git`).

If you want to load your settings once in the main command and make them accessible in all subcommands,
you can use the :func:`~typed_settings.click_utils.pass_settings` decorator.
It searches all *context* objects from the current one via all parent context until it finds a settings instances and passes it to the decorated command:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = 42
    ...
    >>> @click.group()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     pass
    >>>
    >>> @cli.command()
    ... @ts.pass_settings
    ... def sub_cmd(settings: Settings):
    ...     click.echo(settings)
    >>> invoke(cli, "--spam=3", "sub-cmd")
    Settings(spam=3)
    <BLANKLINE>

.. note::

   The example above only works well if either:

   - Only the parent group loads settings
   - Only concrete commands load settings

   This is because the settings instance is stored in the :attr:`click.Context.obj` with a fixed key.

   If you want your sub-commands to *additonally* load their own settings,
   please continue to read the next two setions.


.. _click-order-of-decorators:

Order of Decorators
-------------------

Click passes the settings instance to your CLI function as positional argument by default.
If you use other decorators that behave similarly (e.g., :func:`click.pass_context`),
the order of decorators and arguments matters.

The innermost decorator (the one closest to the :code:`def`) will be passed as first argument,
The second-innermost as second argument and so forth:

.. code-block:: python

    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... @click.pass_context
    ... def cli(ctx: click.Context, settings: Settings):
    ...     print(ctx, settings)
    ...
    >>> invoke(cli)
    <click.core.Context object at 0x...> Settings(spam=23)
    <BLANKLINE>


.. _click-settings-as-keyword-arguments:

Settings as Keyword Arguments
-----------------------------

If a command wants to load multiple types of settings or
if you use command groups where both, the parent group and its sub commands, want to load settings,
then the "store a single settings instance ans pass it as positional argument" approach no longer works.

Instead, you need to specify an *argname* for :func:`~typed_settings.click_utils.click_options()` and :func:`~typed_settings.click_utils.pass_settings()`.
The settings instance is then stored under that key in the :attr:`click.Context.obj` and passed as keyword argument to the decorated function:

.. code-block:: python

    >>> @ts.settings
    ... class CmdSettings:
    ...     eggs: str = ""
    >>>
    >>> @click.group()
    ... @ts.click_options(Settings, "example", argname="main_settings")
    ... @click.pass_obj
    ... def cli(ctx_obj: dict, *, main_settings: Settings):
    ...     # "main_settings" is now a keyword argument
    ...     # It is stored in the ctx object under the same key
    ...     print(main_settings is ctx_obj["main_settings"])
    >>>
    >>> @cli.command()
    ... # Require the parent group's settings as "main_settings"
    ... @ts.pass_settings(argname="main_settings")
    ... # Define command specific settings as "cmd_settings"
    ... @ts.click_options(CmdSettings, "example-cmd", argname="cmd_settings")
    ... def cmd(*, main_settings: Settings, cmd_settings: CmdSettings):
    ...     print(main_settings)
    ...     print(cmd_settings)
    >>>
    >>> invoke(cli, "--spam=42", "cmd", "--eggs=many")
    True
    Settings(spam=42)
    CmdSettings(eggs='many')
    <BLANKLINE>


.. _cli-loaders-converters:

Configuring Loaders and Converters
==================================

When you just pass an application name to :func:`~typed_settings.argparse_utils.cli()` or :func:`~typed_settings.click_utils.click_options()` (as in the examples above),
it uses :func:`default_loaders()` to get the default loaders and :func:`default_converter()` to get the default converter.

Instead of passing an app name, you can pass your own list of loaders to :func:`~typed_settings.click_utils.click_options()`:

.. code-block:: python

    >>> # Only load envs vars, no config files
    >>> loaders = ts.default_loaders(
    ...     appname="example",
    ...     config_files=(),
    ...     config_files_var=None,
    ... )
    >>> @click.command()
    ... @ts.click_options(Settings, loaders)
    ... def cli(settings: Settings):
    ...     pass

In a similar fashion, you can use your own converter:

.. code-block:: python

    >>> converter = ts.default_converter()
    >>> # converter.register_structure_hook(my_type, my_converter)
    >>>
    >>> @click.command()
    ... @ts.click_options(Settings, "example", converter=converter)
    ... def cli(settings: Settings):
    ...     pass

The :func:`typed_settings.argparse_utils.cli()` decorator can be configured in the same way.


Optional and Union Types
========================

Using optional options (with type :samp:`Optional[{T}]`) is generelly supported for scalar types and containers.

.. code-block:: python

    >>> from typing import List, Optional
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     a: Optional[int]
    ...     b: Optional[List[int]]
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --a INTEGER
      --b INTEGER
      --help       Show this message and exit.
    <BLANKLINE>
    >>> invoke(cli, )
    Settings(a=None, b=[])
    <BLANKLINE>

.. note::

   Click will always give us an empty list, even if the default for an optional list is ``None``.

However, optional nested settings do not work:

.. code-block:: python

    >>> @ts.settings
    ... class Nested:
    ...    a: int
    ...    b: Optional[int]
    ...
    >>> @ts.settings
    ... class Settings:
    ...     n: Nested
    ...     o: Optional[Nested]
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --n-a INTEGER  [required]
      --n-b INTEGER
      --o NESTED
      --help         Show this message and exit.
    <BLANKLINE>

Unions other than :code:`Optional` are also not supported.


.. _extending-supported-types:

Extending Supported Types
=========================

The type specific keyword arguments for :func:`click.option()` or :meth:`argparse.ArgumentParser.add_argument()` are generated by a thing called :class:`~typed_settings.cli_utils.TypeArgsMaker`.
It is framework agnostic and uses a :class:`~typed_settings.cli_utils.TypeHandler`
that actually generates the framework specific arguments for each type.

For Click, this is the :class:`typed_settings.click_utils.ClickHandler`.
The easiest way to extend its capabilities is by passing a dict to it that maps types to specialized handler functions.  The :data:`typed_settings.click_utils.DEFAULT_TYPES` contain handlers for datetimes and enums.

For Argparse this is analogous the :class:`typed_settings.argparse_utils.ArgparseHandler` and :data:`typed_settings.argparse_utils.DEFAULT_TYPES`.

.. note::

   The :class:`~typed_settings.click_utils.ClickHandler` (and :class:`~typed_settings.argparse_utils.ArgparseHandler`) support so many common types
   that it was quite hard to come up with an example that makes at least *some* sense …;-)).

   The example uses Click but it works the same way for Argparse.

Let's assume you want to add support for a special *dataclass* that represents an RGB color and
that you want to use a single command line option for it (like :samp:`--color {R G B}`).

.. code-block:: python

    >>> import attrs
    >>> import dataclasses
    >>>
    >>> @dataclasses.dataclass
    ... class RGB:
    ...     r: int = 0
    ...     g: int = 0
    ...     b: int = 0
    ...
    >>> @ts.settings
    ... class Settings:
    ...     color: RGB = RGB(0, 0, 0)

.. note::

   If we used ``attrs`` instead of :mod:`dataclasses` here, Typed Settings would automatically generate three options ``--color-r``, ``--color-g``, and ``--color-b``.

Since Cattrs has no built-in support for dataclasses, we need to register a converter for it:

.. code-block:: python

    >>> converter = ts.default_converter()
    >>> converter.register_structure_hook(
    ...     RGB, lambda val, cls: val if isinstance(val, RGB) else cls(*val)
    ... )

Next, we need to create a type handler function (see the :class:`~typed_settings.cli_utils.TypeHandlerFunc` protocol) for out dataclass.
It must take a type, a default value and a flag that indicates whether the type was originally wrapped with :class:`typing.Optional`.
It must return a dictionary with keyword arguments for :func:`click.option()`.

For our use case, we need an :code:`int` options that takes exactly three arguments and has the metavar :code:`R G B`.
If (and only if) there is a default value for our option, we want to use it.

.. code-block:: python

    >>> from typed_settings.cli_utils import Default, StrDict
    >>>
    >>> def handle_rgb(_type: type, default: Default, is_optional: bool) -> StrDict:
    ...     type_info = {
    ...         "type": int,
    ...         "nargs": 3,
    ...         "metavar": "R G B",
    ...     }
    ...     if default:
    ...         type_info["default"] = dataclasses.astuple(default)
    ...     elif is_optional:
    ...         type_info["default"] = None
    ...     return type_info

We can now create a :class:`~typed_settings.click_utils.ClickHandler` and configure it with a dict of our type handlers.

.. code-block:: python

    >>> from typed_settings.cli_utils import TypeArgsMaker
    >>> from typed_settings.click_utils import DEFAULT_TYPES, ClickHandler
    >>>
    >>> type_dict = {
    ...     **DEFAULT_TYPES,
    ...     RGB: handle_rgb,
    ... }
    >>> type_handler = ClickHandler(type_dict)

Finally, we pass that handler to :class:`~typed_settings.cli_utils.TypeArgsMaker` and this in turn to :func:`~typed_settings.click_utils.click_options()`:

.. code-block:: python

    >>> @click.command()
    ... @ts.click_options(
    ...     Settings,
    ...     "example",
    ...     converter=converter,
    ...     type_args_maker=TypeArgsMaker(type_handler),
    ... )
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> # Check if our metavar and default value is used:
    >>> invoke(cli, "--help")
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --color R G B  [default: 0, 0, 0]
      --help         Show this message and exit.
    <BLANKLINE>
    >>> # Try passing our own color:
    >>> invoke(cli, "--color", "23", "42", "7")
    Settings(color=RGB(r=23, g=42, b=7))
    <BLANKLINE>

This sounds a bit involved and it *is* in fact a bit involved,
but this mechanism gives you the freedom to modify all behavior to your needs.

If adding a simple type handler is not enough, you can extend the :class:`~typed_settings.click_utils.ClickHandler` (or create a new one)
and – if that is not enough – event the :class:`~typed_settings.cli_utils.TypeArgsMaker`.
