"""
Configuration and tasks for **Nox**.
"""

import glob
import os
import pathlib


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

import nox
from packaging.requirements import Requirement


PROJECT_DIR = pathlib.Path(__file__).parent
MYPY_PATHS = [
    [
        "./noxfile.py",
        "src/",
        "tests/",
    ],
    [
        "docs/conf.py",
        "docs/conftest.py",
    ],
    [
        "docs/examples/",
    ],
]
LINT_PATHS = [p for paths in MYPY_PATHS for p in paths]
# Dependencies for which to test against multiple versions
PYTHON_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12"]
LATEST_STABLE_PYTHON = PYTHON_VERSIONS[-1]
DEPS_MATRIX = {
    "attrs",
    "cattrs",
}

IN_CI = "CI" in os.environ
OMMIT_IN_REPORT = [
    "src/typed_settings/argparse_utils.py",
    "src/typed_settings/attrs.py",
    "src/typed_settings/click_utils.py",
    "src/typed_settings/mypy.py",
]
if IN_CI:
    OMMIT_IN_REPORT += [
        "src/typed_settings/_onepassword.py",
        "tests/test_onepassword.py",
    ]


@nox.session
def build(session: nox.Session) -> None:
    """
    Build an sdist and a wheel for TS.
    """
    session.install("hatch", "check-wheel-contents")
    session.run("rm", "-rf", "build", "dist", external=True)
    session.run("hatch", "build")  # , external=True)
    session.run("check-wheel-contents", *glob.glob("dist/*.whl"))


@nox.session(python=PYTHON_VERSIONS, tags=["test"])
@nox.parametrize(
    "deps_min_version",
    [True, False],
    ["min_deps_version", "latest_deps_version"],
)
@nox.parametrize("pkg_format", ["tar.gz", "whl"], ["src", "whl"])
def test(session: nox.Session, deps_min_version: bool, pkg_format: str) -> None:
    """
    Run all tests for various configurations (Python and dependency versions).

    Run the full matrix (all combinations of latest/min dependencies and packakge
    formats) only for the latest stable Python version to save some CI/CD minutes.
    """
    if session.python != LATEST_STABLE_PYTHON:
        # We need to save GitLab CI minutes so we skip running the tests for some
        # configurations if this is not the latest stable Python version.
        if pkg_format != "whl" or deps_min_version:
            session.skip(f"Skipping this session for Python {session.python}")

    pkgs = glob.glob(f"dist/*.{pkg_format}")
    if len(pkgs) == 0:
        session.log('Package not found, running "build" ...')
        build(session)
        pkgs = glob.glob(f"dist/*.{pkg_format}")
    if len(pkgs) != 1:
        session.error(f"Expected exactly 1 file: {', '.join(pkgs)}")
    src = pkgs[0]

    # If testing against the minium versions of our dependencies,
    # extract their minium version from pyproject.toml and pin
    # these versions.
    install_deps = []
    if deps_min_version:
        pyproject = tomllib.loads(PROJECT_DIR.joinpath("pyproject.toml").read_text())
        deps = pyproject["project"]["dependencies"]
        for dep in deps:
            req = Requirement(dep)
            if req.name not in DEPS_MATRIX:
                continue
            spec = str(req.specifier)
            assert spec.startswith(">="), spec
            spec = spec.replace(">=", "==")
            install_deps.append(f"{req.name}{spec}")

    session.install(f"typed-settings[test] @ {src}", *install_deps)

    # We have to run the tests for the doctests in "src" separately or we'll
    # get an "ImportPathMismatchError" (the "same" file is located in the
    # cwd and in the nox venv).
    if tuple(map(int, session.python.split("."))) < (3, 10):  # type: ignore
        # Skip doctests on older Python versions
        # The output of arparse's "--help" has changed in 3.10
        session.run("coverage", "run", "-m", "pytest", "tests", "-k", "not test_readme")
    else:
        session.run("coverage", "run", "-m", "pytest", "docs", "tests")
    session.run("coverage", "run", "-m", "pytest", "src")


@nox.session(tags=["test"])
def test_no_optionals(session: nox.Session) -> None:
    """
    Run tests with no optional dependencies installed.
    """
    pkgs = glob.glob("dist/*.whl")
    session.install(f"typed-settings @ {pkgs[0]}", "coverage", "pytest", "sybil")
    session.run("coverage", "run", "-m", "pytest", "tests/test_no_optionals.py")


@nox.session(name="coverage-report", tags=["test"])
def coverage_report(session: nox.Session) -> None:
    """
    Create a coverate report from the results of the test sessions.
    """
    args = []
    if OMMIT_IN_REPORT:
        args.append(f"--omit={','.join(OMMIT_IN_REPORT)}")

    session.install("typed-settings[test] @ .")
    session.run("coverage", "combine")
    # Only let the "report" command fail under 100%
    session.run("coverage", "xml", "--fail-under=0")
    session.run("coverage", "html", "--fail-under=0")
    session.run("coverage", "report", *args)


@nox.session(python=False, tags=["lint"])
def fix(session: nox.Session) -> None:
    """
    Run code fixers.
    """
    session.run("ruff", "check", "--fix-only", *LINT_PATHS)
    session.run("ruff", "format", *LINT_PATHS)


@nox.session(tags=["lint"])
def lint(session: nox.Session) -> None:
    """
    Run the linters.
    """
    session.install("typed-settings[lint] @ .")
    session.run("ruff", "check", *LINT_PATHS)


@nox.session(tags=["lint"])
def mypy(session: nox.Session) -> None:
    """
    Run type checking with MyPy.
    """
    session.install("typed-settings[dev] @ .")
    for paths in MYPY_PATHS:
        session.run("mypy", "--show-error-codes", *paths)


@nox.session(name="sec-check", tags=["lint"])
def sec_check(session: nox.Session) -> None:
    """
    Run a security check with pip-audit.
    """
    session.install("typed-settings[dev] @ .")  # Install *everything*
    session.run("pip-audit")
