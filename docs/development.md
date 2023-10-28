# Development

% skip: start

Typed Settings uses [Hatch] for environment management, building and publishing.
However, you can also use [pip]  and [virtualenv], if you like.

It uses [nox] to run the linters and tests against a matrix of different dependency and Python versions.
Nox is similar to [tox] but uses Python to describe all tasks.

It also uses [pre-commit] to lint the code you're going to commit.

## Setting up a Development Environment

1. Clone the project and change into its directory:

   ```console
   $ git clone git@gitlab.com:sscherfke/typed-settings.git
   $ cd typed-settings
   ```

2. Create a virtual environment in your preferred ways:

   - Using [Hatch]:

     ```console
     $ hatch shell
     ```

     This not only creates and activates an environment but also installs/updates all development dependencies and pre-commit.

   - Using [virtualenvwrapper]:

     ```console
     $ mkvirtualenv typed-settings
     ```

   - Using [virtualenv]:

     ```console
     $ virtualenv .env
     $ source .env/bin/activate
     ```

   - Using [venv]:

     ```console
     $ python -m venv .env
     $ source .env/bin/activate
     ```

3. If you did not use Hatch,
   install all development requirements and Typed Settings itself in development mode:

   ```console
   (typed-settings)$ pip install -e .[dev]  # Not needed with hatch
   (typed-settings)$ pre-commit install --install-hooks
   ```

## Linting

Typed Settings uses [flake8] with a few plug-ins (e.g., [bandit]) and [mypy] for linting:

```console
(typed-settings)$ flake8 PATH...
(typed-settings)$ mypy PATH...
(typed-settings)$ # or
(typed-settings)$ hatch run lint
```

[Black] and [Isort] are used for code formatting:

```console
(typed-settings)$ black PATH...
(typed-settings)$ isort PATH...
(typed-settings)$ # or
(typed-settings)$ hatch run fix [PATH...]
```

[Pre-commit] also runs all linters and formatters with all changed files every time you want to commit something.

## Testing

You run the tests with [pytest].
It is configured to also run doctests in {file}`src/` and {file}`docs/` and to test the examples in that directory,
so do not only run it on {file}`tests/`.

```console
(typed-settings)$ pytest
(typed-settings)$ # or
(typed-settings)$ hatch run test
```

Hatch provides a shortcut for quickly running the tests and measure the coverage:

```console
(typed-settings)$ hatch run cov
```

You will not get to 100% with this though, since some compatibilty code will not be executed.

You can also use [nox] to run tests for all supported Python versions at the same time.
This should get you to 100% coverage.

Just run `nox` to build a package, test it, and lint it:

```console
(typed-settings)$ nox
```

## Docs

[Sphinx] is used to build the documentation.
The documentation is formatted using [reStructuredText] (maybe we'll switch to Markdown with the MyST parser at some time).
There's a makefile that you can invoke to build the documentation:

```console
(typed-settings)$ make -C docs html
(typed-settings)$ # or
(typed-settings)$ hatch run docs
(typed-settings)$
(typed-settings)$ make -C docs clean html  # Clean rebuild
(typed-settings)$ # or
(typed-settings)$ hatch run clean-docs
(typed-settings)$
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

1. Update the {file}`CHANGELOG.rst`.
   Use an emoji for each line.
   The changelog contains a legend at the bottom where you can look-up the proper emoji.
2. Update the version in {file}`pyproject.toml`.
3. Commit using the message {samp}`Bump version from {a.b.c} to {x.y.z}`.
4. Create an annotated tag: {samp}`git tag -am 'Release {x.y.z}' {x.y.z}`.
5. Push everything: {samp}`git push --atomic origin main {x.y.z}`.
6. The [CI/CD pipeline][cicd-pipeline] automatically creates a release on the testing PyPI.
   Check if everything is okay.
7. Manually trigger the final release step.

[bandit]: https://pypi.org/project/bandit/
[black]: https://pypi.org/project/black/
[cicd-pipeline]: https://gitlab.com/sscherfke/typed-settings/-/pipelines
[commit-message]: https://cbea.ms/git-commit/
[flake8]: https://pypi.org/project/flake8/
[hatch]: https://hatch.pypa.io/latest/
[isort]: https://pypi.org/project/isort/
[mypy]: https://pypi.org/project/mypy/
[nox]: https://pypi.org/project/nox/
[pip]: https://pypi.org/project/pip/
[pre-commit]: https://pypi.org/project/pre-commit/
[pytest]: https://pypi.org/project/pytest/
[restructuredtext]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
[sphinx]: https://pypi.org/project/sphinx/
[tox]: https://pypi.org/project/tox/
[venv]: https://docs.python.org/3/library/venv.html
[virtualenv]: https://pypi.org/project/virtualenv/
[virtualenvwrapper]: https://pypi.org/project/virtualenvwrapper/
