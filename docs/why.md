# Why Typed Settings?

This page introduces you to similar libraries and shows why Typed Settings might be the better choice for you.

(list-of-features)=
## Comprehensive List of Features

- Your app defines the structure of your settings as typed classes with defaults.
- Typed settings loads settings from a number of defined sources.
  Each source may override parts of the settings loaded by previous sources.
- The loaded settings can optionally be post-processed.
- The loaded and processed values are converted to an instance of your settings class.
- Additionally, CLI options can be generated for all options and
  the loaded settings serve as default values.
- The user invokes the CLI and an updated instance of the settings instance is passed to your CLI function.


### Settings Layout and Structure

- Settings are defined as [attrs], [dataclasses], or [Pydantic] classes with type hints and, optionally, validators.

  - Options can be marked/typed as secrets and are hidden when a settings instance is printed.

- Settings classes can be nested if you want to group your settings.

- If it is installed, [cattrs] is used for converting the loaded values to the proper types.
  Typed Settings has a built-in converter that is used as a fallback.
  You can extend the existing converters or drop in your own.

  - By default, all basic data types (bool, int, float, str) are supported, as well as enums, paths and datetimes.
    Most built-in collection types are supported, as well as optional values.
  - You can extend the converter to support additional types.


### Loading Settings

- You define a list of settings loaders that are run one after another.
  Each loader merges its results with the previously loaded settings.
  The last loader in the list has the highest precedence.

- There are built-in loaders for:

  - Config files:

    - Multiple files can be loaded and their results are merged
    - File paths can be statically set,
      searched in the current project or file system,
      or loaded from an environment variable (similarly to `$PATH`)..
      There are no implicit default search paths.
    - Settings files can be optional or mandatory.
    - Config files are allowed to contain settings for multiple apps (like {file}`pyproject.toml`)
    - Extra options in config files (that do not map to an attribute in the settings class) are errors.
    - Supported formats: Toml, Python.
      Support for additional files can be added with a few lines of code.

  - Environment variables.
    Their prefix (e.g., `MYAPP_`) can be customized.

  - Existing settings instances and plain dicts.

  - [1Password].


### Post Processing

- Settings can be post-processed and updated.

- Like loaders, processors can be chained and extended.

- Included processors:

  - Interpolation with format strings (similarly to [configparser])
  - [Jinja]-Templating (similarly to [Ansible variables])
  - Replace URLs with the value they return, e.g., {samp}`helper://{script}` is replaced by the output of {samp}`{script}` or {samp}`op://{resource}` is replaced by the corresponding 1Password resource.


### CLIs

- Typed Settings can generate CLI options for your settings.
  The loaded (and processed) settings serve as default values for these options.

- The generated options can be adjusted to your needs.

- Supported libraries:

  - [argparse]
  - [Click] (including [click-option-group] and [rich-click])


### API and Misc.

- Typed Settings provides convenience APIs with reasonable defaults but limited customizability
  and APIs that let you configure everything in detail.

- Logging via the `typed_settings` logger:

  - Config files that are being loaded or that cannot be found
  - Looked up env vars

- Most aspects of Typed Settings can be customized or extended.

- All dependencies (except for [tomli] for Python <= 3.10) are optional.  We work towards having no mandatory dependencies.

- Extensive documentation

- Continued development.
  Typed Settings is used in production in commercial products,
  so the probability that it's getting abandoned is relatively low.


## What about Dynaconf?

[Dynaconf] seems quite similar to {program}`TS` on a first glance, but follows a different philosophy.

Settings can be loaded from multiple config files and overridden by environment variables,
but you don't predefine the structure of your settings in advance.
This makes defining defaults and validators for options a bit more tedious, but it is possible nonetheless.

Environment variables use the prefix {code}`DYNACONF_` by default which may lead to conflicts with other apps.

{program}`Dynaconf` supports a lot more file formats than {program}`TS` and can read secrets from {program}`HashiCorp Vault` and {program}`Redis`.
{program}`TS` may add support for these, though.

Settings can contain template vars (for Python format strings or [Jinja]) which are replaced with the values of loaded settings.
Supported for this in {program}`TS` is [planned].

{program}`Dynaconf` allows you to place the settings for all deployment environments (e.g., *production* and *testing)* into a single config file.
I like to put these into different files since your configuration may consist of additional files (like SSH keys) that also differ between environments.

It seems like it is also not intended to share config files with other applications, e.g. in {file}`pyproject.toml`.

{program}`Dynaconf` can easily integrate with {program}`Flask` and {program}`Django`, but not with {program}`click`.


## What about environ-config?

[Environ-config] stems from the author of {program}`attrs` and uses {program}`attrs` classes to define the structure of your settings.

Settings can only be loaded from environment variables.
Secrets can also be read from {program}`HashiCorp Vault`, {program}`envconsul` and `ini` files.

Additional config files are not supported which [may lead to problems] if your app needs more complex configuration.

{program}`Click` is not supported.

It provides helpful debug logging and built-in dynamic docstring generation for the settings class.


## What about Pydantic?

[Pydantic] is more comparable to {program}`attrs` but also offers integrated settings loading (amongst many other features).

Settings classes are, as in {program}`TS` and {program}`environ-config`, predefined.
Option values are automatically converted and can easily be validated.

Settings can only be loaded from environment variables (and {file}`.env` files), though.


[1password]: https://developer.1password.com/docs/cli/
[ansible variables]: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html#referencing-simple-variables
[argparse]: https://docs.python.org/3/library/argparse.html
[attrs]: https://attrs.readthedocs.io
[cattrs]: https://cattrs.readthedocs.io
[click-option-group]: https://click-option-group.readthedocs.io
[click]: https://click.palletsprojects.com
[configparser]: https://docs.python.org/3/library/configparser.html#interpolation-of-values
[dataclasses]: https://docs.python.org/3/library/dataclasses.html
[dynaconf]: https://www.dynaconf.com
[environ-config]: https://github.com/hynek/environ-config
[jinja]: https://jinja.palletsprojects.com
[may lead to problems]: https://hitchdev.com/strictyaml/why-not/environment-variables-as-config/
[planned]: https://gitlab.com/sscherfke/typed-settings/-/issues/2
[pydantic]: https://pydantic-docs.helpmanual.io/
[rich-click]: https://github.com/ewels/rich-click
[tomli]: https://github.com/hukkin/tomli
