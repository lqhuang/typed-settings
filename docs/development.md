# Development

% skip: start

Typed Settings uses [Hatch] as build tool.
However, you can set-up your local development environment in whichever way you like.

It uses [nox] as task manager, e.g. to run the linters and
tests against a matrix of different dependency and Python versions.
Nox is similar to [tox] but uses Python to describe all tasks.

It also uses [pre-commit] to lint the code you're going to commit.


## Setting up a Development Environment

1. Clone the project and change into its directory:

   ```console
   $ git clone git@gitlab.com:sscherfke/typed-settings.git
   $ cd typed-settings
   ```

2. Create a virtual environment in your preferred ways, for example:

   - Using [Hatch]:

     ```console
     $ hatch shell
     ```

     This not only creates and activates an environment but also installs/updates all development dependencies and pre-commit.

   - Using [uv]:

     ```console
     $ uv venv
     $ source .venv/bin/activate
     ```

   - Using [venv]:

     ```console
     $ python -m venv .venv
     $ source .venv/bin/activate
     ```

3. If you did not use Hatch,
   install all development requirements and Typed Settings itself in development mode:

   ```console
   (typed-settings)$ uv pip install -e .[dev]
   (typed-settings)$ # or, if you don't use "uv":
   (typed-settings)$ pip install -e .[dev]
   (typed-settings)$
   (typed-settings)$ pre-commit install --install-hooks
   ```

## Linting

Typed Settings uses [ruff] and [mypy] for linting.
You can run these tools directly but it's easier to use {program}`nox`:

```console
(typed-settings)$ nox -e lint mypy
```

[Ruff] is also used for code formatting and auto-fixing linting issues.
You should use {program}`nox` to run it:

```console
(typed-settings)$ nox -e fix
```

[Pre-commit] also runs all linters and formatters with all changed files every time you want to commit something.


## Testing

You run the tests with [pytest].
It is configured to also run doctests in {file}`src/` and {file}`docs/` and
to test the examples in that directory,
so do not only run it on {file}`tests/`.

```console
(typed-settings)$ pytest
```

You can also use [nox] to run tests for all supported Python versions at the same time.
This will also calculate the combined test coverage and run the linters.

```console
(typed-settings)$ nox
```

## Docs

[Sphinx] is used to build the documentation.
The documentation is formatted with Markdown using [MyST]
(with the exception of the API docs, which are formatted with [ReStructuredText]).
There's a {file}`Makefile` that you can invoke to build the documentation:

```console
(typed-settings)$ make -C docs html
(typed-settings)$ make -C docs clean html  # Clean rebuild
(typed-settings)$ open docs/_build/html/index.html  # Use "xdg-open" on Linux
```

## Commits

When you commit something, take your time to write a [precise, meaningful commit message][commit-message].
In short:

- Use the imperative: *Fix issue with XY*.
- If your change is non-trivial, describe why your change was needed and how it works.
  Separate this from the title with an empty line.
- Add references to issues, e.g. `See: #123` or `Fixes: #123`.

When any of the linters run by Pre-commit finds an issue or if a formatter changes a file, the commit is aborted.
In that case, you need to review the changes, add the files and try again:

```console
(typed-settings)$ git status
(typed-settings)$ git diff
(typed-settings)$ git add src/typed_settings/...
```

## Releasing New Versions

Releases are created and uploaded by the CI/CD pipeline.
The release steps are only executed in tag pipelines.

To prepare a release:

1. Update the {file}`CHANGELOG.md`.
   Use an emoji for each line.
   The changelog contains a legend at the bottom where you can look-up the proper emoji.
2. Update the version in {file}`pyproject.toml`.
3. Commit using the message {samp}`Bump version from {a.b.c} to {x.y.z}`.
4. Create an annotated tag: {samp}`git tag -am 'Release {x.y.z}' {x.y.z}`.
5. Push everything: {samp}`git push --atomic origin main {x.y.z}`.
6. The [CI/CD pipeline][cicd-pipeline] automatically creates a release on the testing PyPI.
   Check if everything is okay.
7. Manually trigger the final release step.

[cicd-pipeline]: https://gitlab.com/sscherfke/typed-settings/-/pipelines
[commit-message]: https://cbea.ms/git-commit/
[hatch]: https://hatch.pypa.io/latest/
[mypy]: https://pypi.org/project/mypy/
[myst]: https://myst-parser.readthedocs.io/en/latest/
[nox]: https://pypi.org/project/nox/
[pre-commit]: https://pypi.org/project/pre-commit/
[pytest]: https://pypi.org/project/pytest/
[restructuredtext]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
[ruff]: https://pypi.org/project/ruff/
[sphinx]: https://pypi.org/project/sphinx/
[tox]: https://pypi.org/project/tox/
[uv]: https://pypi.org/project/uv/
[venv]: https://docs.python.org/3/library/venv.html
