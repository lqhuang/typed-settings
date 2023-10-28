```{currentmodule} typed_settings
```

# Post-processing Settings

Processors are applied after all settings have been loaded but before the loaded settings are converted to your settings class.

```{note}
This approach allows you to, e.g., use template strings where an `int` is expected –
as long as the template results in a valid `int`.
```

As with loaders, you can configure a list of processors that are applied one after another.

## Interpolation

*Interpolation* is basically a simple form of templating.
The stdlib's [configparser] uses old-school string formatting for this.
Typed Settings uses new style format strings:

[configparser]: https://docs.python.org/3/library/configparser.html#interpolation-of-values

```{code-block} python
:caption: example.py
:emphasize-lines: 7,13

import typed_settings as ts


@ts.settings
class Settings:
    a: str
    b: str = "{a}{a}"


settings = ts.load_settings(
    cls=Settings,
    loaders=ts.default_loaders("example", ["example.toml"]),
    processors=[ts.processors.FormatProcessor()],
)
print(settings)
```

```{code-block} toml
:caption: example.toml

[example]
a = "spam"
```

```{code-block} console
$ python example.py
Settings(a='spam', b='spamspam')
```

You can access nested settings like dictionary items but you have to leave out the quotes.
It is also okay to refer to values that are themselves format strings:

```{code-block} python
:caption: example.py
:emphasize-lines: 6,11-13,19

import typed_settings as ts


@ts.settings
class Nested:
    x: str = "{b}"


@ts.settings
class Settings:
    a: str = "{nested[x]}"
    b: str = "spam"
    nested: Nested = Nested()


settings = ts.load_settings(
    cls=Settings,
    loaders=[],
    processors=[ts.processors.FormatProcessor()],
)
print(settings)
```
```{code-block} console
$ python example.py
Settings(a='spam', b='spam', nested=Nested(x='spam'))
```

## Templating

If interpolation via format strings is not expressive enough,
you can also use templating via [Jinja].
This works very similarly to how [Ansible] templates its variables.

[ansible]: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html#simple-variables
[jinja]: http://jinja.pocoo.org/

The package {program}`jinja2` is required for this feature:

```bash
$ pip install -U jinja2
```

You can now use Jinja variables inside your settings:

```{code-block} python
:caption: example.py
:emphasize-lines: 6-7,13

import typed_settings as ts


@ts.settings
class Settings:
    a: str = "spam"
    b: str = "{{ a }}{{ a }}"


settings = ts.load_settings(
    cls=Settings,
    loaders=[],
    processors=[ts.processors.JinjaProcessor()],
)
print(settings)
```
```{code-block} console
$ python example.py
Settings(a='spam', b='spamspam')
```

In contrast to format strings, you can access nested settings like attributes via `.`.
It is also okay to refer to values that are themselves templates:

```{code-block} python
:caption: example.py
:emphasize-lines: 6,11-13,19

import typed_settings as ts


@ts.settings
class Nested:
    x: str = "{% if b == 'spam'%}True{% else %}False{% endif %}"


@ts.settings
class Settings:
    a: bool = "{{ nested.x }}"
    b: str = "spam"
    nested: Nested = Nested()


settings = ts.load_settings(
    cls=Settings,
    loaders=[],
    processors=[ts.processors.JinjaProcessor()],
)
print(settings)
```
```{code-block} console
$ python example.py
Settings(a=True, b='spam', nested=Nested(x='True'))
```

## Loading Secrets via Helper Scripts

The {class}`~typed_settings.processors.UrlProcessor` allows you to reference and query external resources,
e.g., scripts or secrets in a given location.

You pass a mapping of URL schemas and handlers to it.
If a settings value starts with one of the configured schemas,
the corresponding handler is invoked and the original settings value is replaced with the handler's result.

```{hint}
The URL processor is not very strict in what "schemas" it accepts.
You can pass any string to it as the following example shows.
```

Let's create a settings class and define some exemplary default values,
and a corresponding {class}`~typed_settings.processors.UrlProcessor`:

```{code-block} python
:caption: example.py

import typed_settings as ts


@ts.settings
class Settings:
    a: str = "script://echo password"
    b: str = "helper: echo password"
    c: str = "raw://script://echo password"


# UrlProcessor takes a dict mapping schemas/prefixes to handler funcs:
url_processor = ts.processors.UrlProcessor({
    "raw://": ts.processors.handle_raw,
    "script://": ts.processors.handle_script,
    "helper: ": ts.processors.handle_script,
})
settings = ts.load_settings(
    cls=Settings,
    loaders=[],
    processors=[url_processor],
)
print(settings)
```

The first two values indicate that the script {code}`echo password` should be run and its output (`"password"`) be used as new settings value.

The `raw://` schema for the setting `c` works like an escape sequence if the literal value should be `script://echo password`.

Let's take a look at the resulting settings:

```{code-block} console
$ python example.py
Settings(a='password', b='password', c='script://echo password')
```
