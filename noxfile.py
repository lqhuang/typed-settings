import glob

import nox


LINT_PATHS = [
    # "docs/conf.py",
    "noxfile.py",
    "setup.py",
    "src/",
    "tests/",
]


@nox.session
def build(session):
    session.install("build", "check-wheel-contents")
    session.run("rm", "-rf", "build", "dist", external=True)
    session.run("python", "-m", "build", "--sdist", "--wheel", ".")
    session.run("check-wheel-contents", *glob.glob("dist/*.whl"))


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11.0b1"])
@nox.parametrize("pkg_format", [".", "tar.gz", "whl"], [".", "src", "whl"])
def test(session, pkg_format):
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

    session.install(f"{src}[test]")

    # We have to run the tests for the doctests in "src" separately or we'll
    # get an "ImportPathMismatchError" (the "same" file is located in the
    # cwd and in the nox venv).
    session.run("coverage", "run", "-m", "pytest", "docs", "tests")
    session.run("coverage", "run", "-m", "pytest", "src")


@nox.session(name="coverage-report")
def coverage_report(session):
    session.install(".[test]")
    session.run("coverage", "combine")
    session.run("coverage", "xml")
    session.run("coverage", "html")
    session.run("coverage", "report")


@nox.session
def lint(session):
    session.install(".[lint]")
    session.run("flake8", *LINT_PATHS)


@nox.session
def mypy(session):
    session.install(".[lint]")
    session.run("mypy", "--show-error-codes", *LINT_PATHS)


@nox.session
def safety(session):
    session.install(".[dev]")  # Install *everything*
    session.run("safety", "check")
