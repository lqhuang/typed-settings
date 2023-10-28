# 1Password

Typed Settings allows you to load settings from your 1Password vault.

There is a {class}`~typed_settings.loaders.OnePasswordLoader` that can load complete items from your vault,
and the {class}`~typed_settings.processors.UrlProcessor` handler {class}`~typed_settings.processors.handle_op` that queries 1Password via resource URLs (e.g., {samp}`op://{vault}/{item}/{field}`).

In order for this to work, you need to install and setup the [1Password CLI](https://developer.1password.com/docs/cli/).
When you are done, you can verify that it works by running `op item list` in your terminal.

We'll assume that there is a vault named *Test* that contains an item *api-a*.
That item has the fields *username* and *credential*, and *hostname*.

```{image} ../_static/1password-test-light.png
:align: center
:alt: A screenshot of 1Password showing the *Test* item from the *Test* vault.
:class: only-light
```

```{image} ../_static/1password-test-dark.png
:align: center
:alt: A screenshot of 1Password showing the *Test* item from the *Test* vault.
:class: only-dark
```

## 1Password Loader

The {class}`~typed_settings.loaders.OnePasswordLoader` needs to be configured with the item name to load and, optionally, the vault name.

You can define this statically or via another settings class,
which we'll do in the following example.

Let's assume we work on an API client that can be configured with several different instances of that API.
The config file might look like this:

```{code-block} toml
:caption: myapi.toml

[global]
vault = "Test"
default_item = "api-a"

# Loaded from 1password
# [api-a]
# hostname = ...
# username = ...
# credential = ...

[api-b]
hostname = "https://api-b.example.com"
username = "bot"
credential = "1234"
```

```{important}
The field name of the 1Password item *must* match the settings names in order for this to work!
```

Let's start by defining and loading the global settings:

```{code-block} python
:caption: myapi.py

import typed_settings as ts


@ts.settings
class GlobalSettings:
    vault: str
    default_item: str
    verify_ssl: bool = True


global_settings = ts.load(
    GlobalSettings, "myapi", ["myapi.toml"], config_file_section="global"
)
```

We can now add the API settings and load them:

```{code-block} python
:caption: myapi.py
:emphasize-lines: 11-15,23,29

import typed_settings as ts


@ts.settings
class GlobalSettings:
    vault: str
    default_item: str
    verify_ssl: bool = True


@ts.settings
class ApiSettings:
    hostname: str
    username: str
    credential: ts.types.SecretStr


global_settings = ts.load(
    GlobalSettings, "myapi", ["myapi.toml"], config_file_section="global"
)
print(global_settings)

item = global_settings.default_item  # Or ask the user instead :)

api_settings = ts.load_settings(
    ApiSettings,
    loaders=[
        *ts.default_loaders(item, ["myapi.toml"]),
        ts.loaders.OnePasswordLoader(item=item, vault=global_settings.vault),
    ],
)
print(api_settings)
```
```{code-block} console
$ python myapi.py
GlobalSettings(vault='Test', default_item='api-a', verify_ssl=True)
ApiSettings(hostname='https://api-a.example.com', username='user', credential='*******')

```

## URL Processor with 1Password handler

The URL processor may be easier to use if you just want to get a single secret from a vault:

- You can specify the vault and item name in the URL and don't need to use another setting for this.
- The name of your option and the item's field name don't need to match.

We can change the example from above by removing the 1Password loader and adding processors instead.
We can also remove the *vault* option from the global settings:

```{code-block} toml
:caption: myapi.toml
:emphasize-lines: 7,12

[global]
default_item = "api-a"

[api-a]
hostname = "https://api-a.example.com"
username = "user"
api-token = "op://Test/api-a/credential"

[api-b]
hostname = "https://api-b.example.com"
username = "bot"
credential = "op://Test/api-b/credential"
```

```{code-block} python
:caption: myapi.py
:emphasize-lines: 12-15,19

import typed_settings as ts

# We'll skip loading the global settings for the sake of simplicity:
item = "api-a"

@ts.settings
class ApiSettings:
    hostname: str
    username: str
    api_token: ts.types.SecretStr

url_processor = ts.processors.UrlProcessor({
    "op://": ts.processors.handle_op,
    # You can add additional handlers to support more password managers
})
api_settings = ts.load_settings(
    ApiSettings,
    loaders=ts.default_loaders(item, ["myapi.toml"]),
    processors=[url_processor],
)
print(api_settings)
```
```{code-block} console
$ python myapi.py
ApiSettings(hostname='https://api-a.example.com', username='user', api_token='*******')
```
