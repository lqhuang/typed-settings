===========
Development
===========

Typed Settings uses the well-known workflow with pip_ / setuptools_ and virtualenv_.
It also uses `pre-commit`_ to lint the code you're going to commit.
Sou you don't need to learn anything too fancy. ;-)


Setting up a Development Environment
====================================

#. Clone the project and change into its directory:

   .. code-block:: console

      $ git clone git@gitlab.com:sscherfke/typed-settings.git
      $ cd typed-settings

#. Create a virtual environment in your preferred ways:

   - Using virtualenvwrapper_:

     .. code-block:: console

        $ mkvirtualenv typed-settings

   - Using virtualenv_:

     .. code-block:: console

        $ virtualenv .env
        $ source .env/bin/activate

   - Using venv_:

     .. code-block:: console

        $ python -m venv .env
        $ source .env/bin/activate

#. Install all development requirements and Typed Settings itself in development mode:

   .. code-block:: console

      (typed-settings)$ pip install -e .[dev]
      (typed-settings)$ pre-commit install --install-hooks


Linting and Testing
===================

Typed Settings uses flake8_ with a few plug-ins (e.g., bandit_) and mypy_ for linting:

.. code-block:: console

   (typed-settings)$ flake8 src tests
   (typed-settings)$ mypy src tests

Black_ and Isort_ are used for code formatting:

.. code-block:: console

   (typed-settings)$ black src tests
   (typed-settings)$ isort src tests

`Pre-commit`_ also runs all linters and formatters with all changed files every time you want to commit something.

You run the tests with pytest_.
It is configured to also run doctests in :file:`docs/` and to tests the examples in that directory,
so do not only run it on :file:`tests/`.

.. code-block:: console

   (typed-settings)$ pytest

You can also use nox_ to run tests and linters for all supported python versions at the same time.
Nox is similar to tox_ but uses python to describe all tasks:

.. code-block:: console

   (typed-settings)$ nox


Docs
====

Sphinx_ is used to build the documentation.
The documentation is formatted using reStructuredText_ (maybe we'll switch to Markdown with the MyST parser at some time).
There's a makefile that you can invoke to build the documentation:

.. code-block:: console

   (typed-settings)$ make -C docs html
   (typed-settings)$ make -C docs clean html  # Clean rebuild
   (typed-settings)$ open docs/_build/html/index  # Use "xdg-open" on Linux


Commits
=======

When you commit something, take your time to write a `precise, meaningful commit message <commit-message_>`_.
In short:

- Use the imperative: *Fix issue with XY*.
- If your change is non-trivial, describe why your change was needed and how it works.
  Separate this from the title with an empty line.
- Add references to issues, e.g. `See: #123` or `Fixes: #123`.

When any of the linters run by Pre-commit finds an issue or if a formatter changes a file, the commit is aborted.
In that case, you need to review the changes, add the files and try again:

.. code-block:: console

   (typed-settings)$ git status
   (typed-settings)$ git diff
   (typed-settings)$ git add src/typed_settings/...


Releasing New Versions
======================

Releases are created and uploaded by the CI/CD pipeline.
The release steps are only executed in tag pipelines.

To prepare a release:

#. Update the :file:`CHANGELOG.rst`.
   Use an emoji for each line.
   The changelog contains a legend at the bottom where you can look-up the proper emoji.

#. Update the version in :file:`setup.py`.

#. Commit using the message :samp:`Bump version from {a.b.c} to {x.y.z}`.

#. Create an annotated tag: :samp:`git tag -am 'Release {x.y.z}' {x.y.z}`.

#. Push everything: :samp:`git push --atomic origin main {x.y.z}`.

#. The `CI/CD pipeline <cicd-pipeline_>`_ automatically creates a release on the testing PyPI.
   Check if everything is okay.

#. Manually trigger the final release step.

.. _bandit: https://pypi.org/project/bandit/
.. _black: https://pypi.org/project/black/
.. _cicd-pipeline: https://gitlab.com/sscherfke/typed-settings/-/pipelines
.. _commit-message: https://cbea.ms/git-commit/
.. _flake8: https://pypi.org/project/flake8/
.. _isort: https://pypi.org/project/isort/
.. _mypy: https://pypi.org/project/mypy/
.. _nox: https://pypi.org/project/nox/
.. _pip: https://pypi.org/project/pip/
.. _pre-commit: https://pypi.org/project/pre-commit/
.. _pytest: https://pypi.org/project/pytest/
.. _restructuredtext: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _setuptools: https://pypi.org/project/setuptools/
.. _sphinx: https://pypi.org/project/sphinx/
.. _tox: https://pypi.org/project/tox/
.. _venv: https://docs.python.org/3/library/venv.html
.. _virtualenv: https://pypi.org/project/virtualenv/
.. _virtualenvwrapper: https://pypi.org/project/virtualenvwrapper/
