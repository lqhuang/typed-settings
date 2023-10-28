```{eval-rst}
.. currentmodule:: typed_settings
```

# CLIs with Argparse or Click

You can generate command line interfaces based on your settings classes.

Typed Settings generates a CLI argument for each option of your settings and passes an instances of these settings to your CLI function.
This lets the users of your application override settings loaded from other sources (like config files).


## Argparse or Click?

[Argparse] is a standard library module.
It is easy to get started with it, but you also notice the age of the API.
More modern libraries like [Click] make it easier to handle complex data types and create command line apps with sub commands.

You can use [argparse] if you just want to create a simple CLI without adding extra dependencies.

```{image} ../_static/cli-argparse-light.png
:align: center
:alt: '"--help" output of an "argparse" based Typed Settings CLI'
:class: only-light
```

```{image} ../_static/cli-argparse-dark.png
:align: center
:alt: '"--help" output of an "argparse" based Typed Settings CLI'
:class: only-dark
```

If you want to build a larger, more complex application, [Click] maybe more appropriate.

```{image} ../_static/cli-click-light.png
:align: center
:alt: '"--help" output of a "Click" based Typed Settings CLI'
:class: only-light
```

```{image} ../_static/cli-click-dark.png
:align: center
:alt: '"--help" output of a "Click" based Typed Settings CLI'
:class: only-dark
```

Wich [rich-click] you can also make Click CLIs quite fancy.

```{image} ../_static/cli-rich_click-light.png
:align: center
:alt: '"--help" output of a "Click" based Typed Settings CLI with "rich-click" styling'
:class: only-light
```

```{image} ../_static/cli-rich_click-dark.png
:align: center
:alt: '"--help" output of a "Click" based Typed Settings CLI with "rich-click" styling'
:class: only-dark
```

But the most important thing is: choose the framework *you* feel most comfortable with.

[argparse]: https://docs.python.org/3/library/argparse.html
[click]: https://click.palletsprojects.com
[rich-click]: https://pypi.org/project/rich-click
