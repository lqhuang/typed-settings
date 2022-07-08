=================================
Command Line Arguments with Click
=================================

.. currentmodule:: typed_settings

You can generate Click command line options for your settings.
These let the users of your application override settings loaded from other sources (like config files).

The general algorithm for generating a Click_ CLI for your settings looks like this:

#. You decorate a Click command with :func:`click_options()`.

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
    >>> monkeypatch = getfixture("monkeypatch")
    >>> monkeypatch.setenv("EXAMPLE_SPAM", "23")
    >>>
    >>> @ts.settings
    ... class Settings:
    ...     spam: int = 42
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)

As you can see, an option is generated for each setting:

.. code-block:: python

    >>> import click.testing
    >>>
    >>> runner = click.testing.CliRunner()
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>
    >>> print(runner.invoke(cli, ["--spam=3"]).output)
    Settings(spam=3)
    <BLANKLINE>


The code above is roughly equivalent to:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = 42
    ...
    >>> defaults = ts.load(Settings, "example")
    >>>
    >>> @click.command()
    ... @click.option("--spam", type=int, default=defaults.spam, show_default=True)
    ... def cli(spam: int):
    ...     print(spam)
    ...
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>
    >>> print(runner.invoke(cli, ["--spam=3"]).output)
    3
    <BLANKLINE>

The major difference between the two is that Typed Settings passes the complete settings instances and not individual options.


Customizing the Generated Options
=================================

Typed Settings does its best to generate the Click option in the most sensible way.
However, you can override everything if you want to.

Changing the Param Decls
------------------------

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

    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      -s, --spam INTEGER  [default: 23]
      --help              Show this message and exit.
    <BLANKLINE>
    >>> print(runner.invoke(cli, ["-s", "3"]).output)
    Settings(spam=3)
    <BLANKLINE>

Tuning Boolean Flags
--------------------

Another use case is changing how binary flags for :func:`bool` typed options are generated.
By default, Typed Settings generates ``--flag/--no-flag``.

But imagine this example, where our flag is always ``False`` and we only want to allow users to enable it:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     flag: bool = False

We can achieve this by providing a custom param decl. and the *is_flag* option:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     flag: bool = ts.option(
    ...         default=False,
    ...         help='Turn "flag" on.',
    ...         click={"param_decls": ("--on", "flag"), "is_flag": True},
    ...     )
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)

    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --on    Turn "flag" on.
      --help  Show this message and exit.
    <BLANKLINE>
    >>> print(runner.invoke(cli, ["--on"]).output)
    Settings(flag=True)
    <BLANKLINE>
    >>> print(runner.invoke(cli, []).output)
    Settings(flag=False)
    <BLANKLINE>

Note, that we added the param decl. ``flag`` in addition to ``--on``.
This is required for Click to map the flag to the correct option.
We would not need that if we named our flag ``--flag``.

Option Groups
-------------

Options for nested settings classes have a common prefix,
so you can see that they belong together when you look at a command's ``--help`` output.
You can use `option groups`_ to make the distinction even clearer.

In order for this to work, Typed Settings lets you customize which decorator function is called for generating Click options.
It also allows you to specify a decorator that is called with each settings class.

This functionality is specified by the :class:`~typed_settings.click_utils.DecoratorFactory` protocol.
You can pass an implementation of that protocol to :func:`click_option()` to define the desired behavior.

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

    >>> print(runner.invoke(cli, ["--help"]).output)  # doctest: +NORMALIZE_WHITESPACE
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


Configuring Loaders and Converters
==================================

When you just pass an application name to :func:`click_options()` (as in the example above),
it uses :func:`default_loaders()` to get the default loaders and :func:`default_converter()` to get the default converter.

Instead of passing an app name, you can pass your own list of loaders to :func:`click_options()`:

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


Passing Settings to Sub-Commands
================================

One of Click's main advantages is that it makes it quite easy to create CLIs with sub commands (think of :program:`Git`).

If you want to load your settings once in the main command and make them accessible in all subcommands,
you can use the :func:`pass_settings` decorator.
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
    >>> print(runner.invoke(cli, ["--spam=3", "sub-cmd"]).output)
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
===================

Click passes the settings instance to your CLI function as positional argument by default.
If you use other decorators that behave similarly (e.g., :func:`click.pass_context`),
the order of decorators and arguments matters.

The innermost decorator (the one closest to the :code:`def`) will be passed as first argument,
The second-innermost as second argument and so forth:

.. code-block:: python

    >>> @click.command()
    ... @ts.click_options(Settings, loaders)
    ... @click.pass_context
    ... def cli(ctx: click.Context, settings: Settings):
    ...     print(ctx, settings)
    ...
    >>> print(runner.invoke(cli, []).stdout)
    <click.core.Context object at 0x...> Settings(spam=23)
    <BLANKLINE>


.. _click-settings-as-keyword-arguments:

Settings as Keyword Arguments
=============================

If a command wants to load multiple types of settings or
if you use command groups where both, the parent group and its sub commands, want to load settings,
then the "store a single settings instance ans pass it as positional argument" approach no longer works.

Instead, you need to specify an *argname* for :func:`click_options()` and :func:`pass_settings()`.
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
    >>> print(runner.invoke(cli, ["--spam=42", "cmd", "--eggs=many"]).stdout)
    True
    Settings(spam=42)
    CmdSettings(eggs='many')
    <BLANKLINE>


Help!
=====

As you may have noticed in the examples above, the generated options were lacking a proper help string.
You can add one via :func:`ts.option()` and :func:`ts.secret()`:

.. code-block:: python

    >>> @ts.settings
    ... class Settings:
    ...     spam: int = ts.option(default=23, help="Amount of SPAM required")
    ...
    >>> @click.command()
    ... @ts.click_options(Settings, "example")
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --spam INTEGER  Amount of SPAM required  [default: 23]
      --help          Show this message and exit.
    <BLANKLINE>


Extending supported types
=========================

Typed Settings and it's Click utilities support the data types for the most common use cases out-of-the-box
(in fact, it was quite hard to come up with an example that makes at least *some* sense …;-)).

But let's assume you have a dataclass class that represents an RGB color and
you want to use a single command line option for it (like :samp:`--color {R G B}`).

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

Typed Settings uses a :class:`~typed_settings.click_utils.TypeHandler` to generate type specific arguments for :func:`click.option()`.
The :class:`~typed_settings.click_utils.TypeHandler` takes a dictionary that maps Python types to handler functions.
These functions receive that type and the default value for the option.
They return a dictionary with keyword arguments for :func:`click.option()`.

For our use case, we need an :code:`int` options that takes exactly three arguments and has the metavar :code:`R G B`.
If (and only if) there is a default value for our option, we want to use it.

.. code-block:: python

    >>> from typed_settings.click_utils import DEFAULT_TYPES, StrDict, TypeHandler
    >>>
    >>> def handle_rgb(_type: type, default: object) -> StrDict:
    ...     type_info = {
    ...         "type": int,
    ...         "nargs": 3,
    ...         "metavar": "R G B",
    ...     }
    ...     if default is not attrs.NOTHING:
    ...         type_info["default"] = dataclasses.astuple(default)
    ...     return type_info

We now update the dict with built-in type handlers with our own and
create a new :class:`~typed_settings.click_utils.TypeHandler` instance with it:

.. code-block:: python

    >>> type_dict = {
    ...     **DEFAULT_TYPES,
    ...     RGB: handle_rgb,
    ... }
    >>> type_handler = TypeHandler(type_dict)

Finally, we need to pass the type handler as well as our updated converter to :func:`click_options()` and we are ready to go:

.. code-block:: python

    >>> @click.command()
    ... @ts.click_options(Settings, "example", converter, type_handler=type_handler)
    ... def cli(settings: Settings):
    ...     print(settings)
    ...
    >>> # Check if our metavar and default value is used:
    >>> print(runner.invoke(cli, ["--help"]).output)
    Usage: cli [OPTIONS]
    <BLANKLINE>
    Options:
      --color R G B  [default: 0, 0, 0]
      --help         Show this message and exit.
    <BLANKLINE>
    >>> # Try passing our own color:
    >>> print(runner.invoke(cli, "--color 23 42 7".split()).output)
    Settings(color=RGB(r=23, g=42, b=7))
    <BLANKLINE>

The way described above should be sufficient for most extensions.
However, if you need to achieve something more complicated, like adding support for new kinds of container types, you can also sub-class :class:`~typed_settings.click_utils.TypeHandler()`.
