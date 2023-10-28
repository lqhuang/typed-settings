```{currentmodule} typed_settings
```

# Settings Classes

On this page, you'll learn everything about writing settings classes.

## Writing Settings Classes

Settings classes are normal [attrs], [dataclasses], or [Pydantic] classes with type hints:

[attrs]: https://www.attrs.org/en/stable/
[dataclasses]: https://docs.python.org/3/library/dataclasses.html
[pydantic]: https://pydantic-docs.helpmanual.io/

```python
>>> import attrs
>>> import dataclasses
>>> import pydantic
>>>
>>> @attrs.define
... class Settings1:
...     username: str
...     password: str
...
>>> # or
>>> @dataclasses.dataclass
... class Settings2:
...     username: str
...     password: str
...
>>> # or
>>> class Settings3(pydantic.BaseModel):
...     username: str
...     password: str
```

Typed Settings also provides some convenience aliases for `attrs` classes:

```python
>>> import typed_settings as ts
>>>
>>> @ts.settings
... class Settings:
...      username: str = ts.option(help="The username")
...      password: str = ts.secret(help="The password")
```

{func}`settings()` is just an alias for {func}`attrs.define`.
{func}`option()` and {func}`secret()` are wrappers for {func}`attrs.field()`.
They make it easier to add extra metadata for {doc}`CLI options <clis-argparse-or-click>`.
{func}`secret()` also adds basic protection against {ref}`leaking secrets <secrets>`.

```{hint}
Using {func}`settings()` may keep your code a bit cleaner,
but using {func}`attrs.define()` causes fewer problems with type checkers (see {ref}`sec-mypy`).

You *should* use {func}`attrs.define` (or even {func}`attrs.frozen`) if possible.

However, for the sake of brevity we will use {func}`settings()` in many examples.
```

(secrets)=

## Secrets

Secrets, even when stored in an encrypted vault, most of the time end up as plain strings in your app.
And plain strings tend to get printed.
This can be log messages, debug {func}`print()`s, tracebacks, you name it:

```python
>>> import typed_settings as ts
>>>
>>> @ts.settings
... class Settings:
...      username: str
...      password: str
...
>>> settings = Settings("spam", "eggs")
>>> print(f"Settings loaded: {settings}")
Settings loaded: Settings(username='spam', password='eggs')
```

Oops!

```{danger}
Never use environment variables to pass secrets to your application!

It's far easier for environment variables to leak outside than for config files.
You may, for example, accidentally leak your env via your CI/CD pipeline,
or you may be affected by a [security incident] for which you can't do anything.

The most secure thing is to use an encrypted vault to store your secrets.
If that is not possible, store them in a config file.

If you *have* to use environment variables, write the secret to a file and use the env var to point to that file,
e.g., {code}`MYAPP_API_TOKEN_FILE=/private/token` (instead of just {code}`MYAPP_API_TOKEN="3KX93ad..."`).
[GitLab CI/CD] supports this, for example.

[security incident]: https://thehackernews.com/2021/09/travis-ci-flaw-exposes-secrets-of.html
[gitlab ci/cd]: https://docs.gitlab.com/ee/ci/variables/#cicd-variable-types
```

You can add basic leaking prevention by using {func}`secret()` for creating an option field:

```python
>>> import typed_settings as ts
>>>
>>> @ts.settings
... class Settings:
...      username: str
...      password: str = ts.secret()
...
>>> settings = Settings("spam", "eggs")
>>> print(f"Settings loaded: {settings}")
Settings loaded: Settings(username='spam', password='*******')
```

However, we would still leak the secret if we print the field directly:

```python
>>> print(f"{settings.username=}, {settings.password=}")
settings.username='spam', settings.password='eggs'
```

You can use {class}`~typed_settings.types.SecretStr` instead of {class}`str` to protect against this:

```python
>>> import typed_settings as ts
>>> from typed_settings.types import SecretStr
>>>
>>> @ts.settings
... class Settings:
...      username: str
...      password: SecretStr = ts.secret()
...
>>> settings = Settings("spam", SecretStr("eggs"))
>>> print(f"Settings loaded: {settings}")
Settings loaded: Settings(username='spam', password='*******')
>>> print(f"{settings.username=}, {settings.password=}")
settings.username='spam', settings.password='*******'
```

The good thing about {class}`~typed_settings.types.SecretStr` that it is a drop-in replacement for normal strings.
That bad thing is, that is still not a 100% safe (and maybe, that it only works for strings):

```python
>>> print(settings.password)
eggs
>>> print(f"Le secret: {settings.password}")
Le secret: eggs
```

The generic class {class}`~typed_settings.types.Secret` makes accidental secrets leakage nearly impossible,
since it also protects an object's string representation.
However, it is no longer a drop-in replacement for strings
as you have to call its {meth}`typed_settings.types.Secret.get_secret_value()` method to retrieve the actual value:

```python
>>> import typed_settings as ts
>>> from typed_settings.types import Secret
>>>
>>> @ts.settings
... class Settings:
...      username: str
...      password: SecretStr
...
>>> settings = Settings("spam", Secret("eggs"))
>>> print(f"Settings loaded: {settings}")
Settings loaded: Settings(username='spam', password=Secret('*******'))
>>> print(settings.password)
*******
>>> print(f"Le secret: {settings.password}")
Le secret: *******
>>> settings.password.get_secret_value()
'eggs'
```

{class}`~typed_settings.types.SecretStr()` and `~typed_settings.secret()` usually form the best compromise between usability and safety.

But now matter what you use, you should explicitly test the (log) output of your code to make sure, secrets are not contained at all or are masked at least.

## Dynamic Options

The benefit of class based settings is that you can use properties to create "dynamic" or "aggregated" settings.

Imagine, you want to configure the URL for a REST API but the only part that usually changes with every deployment is the hostname.

For these cases, you can make each part of the URL configurable and create a property that returns the full URL:

```python
>>> from pathlib import Path
>>> import typed_settings as ts
>>>
>>> @ts.settings
... class ServiceConfig:
...     scheme: str = "https"
...     host: str = "example.com"
...     port: int = 443
...     path: Path() = Path("api")
...
...     @property
...     def url(self) -> str:
...         return f"{self.scheme}://{self.host}:{self.port}/{self.path}"
...
>>> print(ServiceConfig().url)
https://example.com:443/api
```

Another use case is loading data from files, e.g., secrets like SSH keys:

```python
>>> from functools import cache
>>> from pathlib import Path
>>> import typed_settings as ts
>>>
>>> @ts.settings(frozen=True)
... class SSH:
...     key_file: Path
...
...     @property
...     @cache
...     def key(self) -> str:
...         return self.key_file.read_text()
...
>>> key_file = tmp_path.joinpath("id_1337")
>>> key_file.write_text("le key")
6
>>> print(SSH(key_file=key_file).key)
le key
```

(sec-mypy)=

## Mypy

Unfortunately, [mypy] still gets confused when you alias {func}`attrs.define` (or even import it from any module other than {mod}`attr` or {mod}`attrs`).

Accessing your settings class' attributes does work without any problems,
but when you manually instantiate your class, mypy will issue a `call-arg` error.

The [suggested workaround] is to create a simple mypy plugin,
so Typed Settings ships with a simple mypy plugin in {mod}`typed_settings.mypy`.

You can activate the plugin via your {file}`pyproject.toml` or {file}`mypy.ini`:

[mypy]: http://mypy-lang.org/
[suggested workaround]: https://www.attrs.org/en/stable/extending.html?highlight=mypy#wrapping-the-decorator

```{code-block} toml
:caption: pyproject.toml

 [tool.mypy]
 plugins = ["typed_settings.mypy"]
```

```{code-block} ini
:caption: mypy.ini

 [mypy]
 plugins=typed_settings.mypy
```
