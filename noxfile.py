import glob

import nox


LOCATIONS = [
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


@nox.session(python=["3.7", "3.8", "3.9", "3.10.0b1"])
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

    args = session.posargs or ["tests"]
    # session.run("pytest", *args)
    session.run("coverage", "run", "-m", "pytest", *args)


@nox.session(name="coverage-report")
def coverage_report(session):
    session.install(".[test]")
    session.run("coverage", "combine")
    session.run("coverage", "xml")
    session.run("coverage", "report")


@nox.session
def lint(session):
    session.install(".[lint]")

    args = session.posargs or LOCATIONS
    session.run("flake8", *args)


@nox.session
def mypy(session):
    session.install(".[lint]")

    args = session.posargs or LOCATIONS
    session.run("mypy", *args)


@nox.session
def safety(session):
    session.install(".[dev]")  # Install *everything*
    session.run("safety", "check")
