import glob
import pathlib


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

import nox
from packaging.requirements import Requirement


PROJECT_DIR = pathlib.Path(__file__).parent
LINT_PATHS = [
    [
        "noxfile.py",
        "src/",
        "tests/",
    ],
    [
        "docs/conf.py",
    ],
    [
        "docs/conftest.py",
    ],
    [
        "docs/examples/",
    ],
]
# Dependencies for which to test against multiple versions
DEPS_MATRIX = {
    "attrs",
    "cattrs",
}


@nox.session
def build(session: nox.Session) -> None:
    session.install("build", "check-wheel-contents")
    session.run("rm", "-rf", "build", "dist", external=True)
    session.run("python", "-m", "build", "--sdist", "--wheel", ".")
    session.run("check-wheel-contents", *glob.glob("dist/*.whl"))


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11"])
@nox.parametrize(
    "deps_min_version",
    [True, False],
    ["min_deps_version", "latest_deps_version"],
)
@nox.parametrize("pkg_format", [".", "tar.gz", "whl"], [".", "src", "whl"])
def test(
    session: nox.Session, deps_min_version: bool, pkg_format: str
) -> None:
    if pkg_format == ".":
        src = "."
    else:
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
        pyproject = tomllib.loads(
            PROJECT_DIR.joinpath("pyproject.toml").read_text()
        )
        deps = pyproject["project"]["dependencies"]
        for dep in deps:
            req = Requirement(dep)
            if req.name not in DEPS_MATRIX:
                continue
            spec = str(req.specifier)
            assert spec.startswith(">="), spec
            spec = spec.replace(">=", "==")
            install_deps.append(f"{req.name}{spec}")

    session.install(f"{src}[test]", *install_deps)

    # We have to run the tests for the doctests in "src" separately or we'll
    # get an "ImportPathMismatchError" (the "same" file is located in the
    # cwd and in the nox venv).
    session.run("coverage", "run", "-m", "pytest", "docs", "tests")
    session.run("coverage", "run", "-m", "pytest", "src")


@nox.session(name="coverage-report")
def coverage_report(session: nox.Session) -> None:
    session.install(".[test]")
    session.run("coverage", "combine")
    # Only let the "report" command fail under 100%
    session.run("coverage", "xml", "--fail-under=0")
    session.run("coverage", "html", "--fail-under=0")
    session.run("coverage", "report")


@nox.session
def lint(session: nox.Session) -> None:
    session.install(".[lint]")
    for paths in LINT_PATHS:
        session.run("flake8", *paths)


@nox.session
def mypy(session: nox.Session) -> None:
    session.install(".[lint]")
    for paths in LINT_PATHS:
        session.run("mypy", "--show-error-codes", *paths)


@nox.session
def safety(session: nox.Session) -> None:
    session.install(".[dev]")  # Install *everything*
    session.run("safety", "check")
