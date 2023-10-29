"""
Tests for "typed_settings.onepasword".
"""
import os
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple

import pytest
from packaging.version import Version

from typed_settings import _onepassword as op


HERE = Path(__file__).parent


@pytest.fixture(autouse=True, params=[False, True])
def mock_op_cli(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Generate two test runs for each test: One with the real "op" ClI and one with a
    mock.
    """
    if request.param:
        request.getfixturevalue("mock_op")
    else:
        try:  # pragma: no cover
            has_op = op.run("account", "list") != ""
        except ValueError:  # pragma: no cover
            has_op = False

        in_ci = "CI" in os.environ
        on_feature_branch = os.getenv("CI_COMMIT_BRANCH", "") not in {"main", ""}

        if (not has_op) or (in_ci and on_feature_branch):  # pragma: no cover
            pytest.skip(reason="OP not installed or credentials not accessible")


def test_op_run() -> None:
    """
    "run()" invokes the CLI with the provided arguments and returns its stdout.
    """
    result = op.run("--version")
    assert Version(result)


def test_op_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    A helpful error is raised if op is not installed.
    """
    orig_run = subprocess.run

    def fake_run(cmd: Tuple[str, ...], **kwargs: Any):
        cmd = ("xyz",) + cmd[1:]
        return orig_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    msg = (
        "The 1Password CLI is not properly installed.*"
        "https://developer.1password.com/docs/cli"
    )
    with pytest.raises(ValueError, match=msg):
        op.run("--version")


def test_op_error() -> None:
    """
    An error is raised if the "op" invocation fails.
    """
    msg = '"op" error:.*(unknown command)|(No such command).*'
    with pytest.raises(ValueError, match=msg):
        op.run("spam", "eggs")


@pytest.mark.parametrize("vault", ["Test", None])
def test_get_item(vault: Optional[str]) -> None:
    """
    An item can be retrieved from 1Password.  Item labels are converted to
    dict keys.
    """
    result = op.get_item("Test", vault)
    assert result == {"username": "spam", "password": "eggs"}


def test_get_item_not_exists() -> None:
    """
    A ValueError with the "op" output is raised if an item does not exist.
    """
    msg = '"op" error: "xyz" isn\'t an item.*'
    with pytest.raises(ValueError, match=msg):
        op.get_item("xyz")


def test_get_resource() -> None:
    """
    A resource canbe retrieved from 1Password.
    """
    result = op.get_resource("op://Test/Test/password")
    assert result == "eggs"


def test_get_resource_not_exists() -> None:
    """
    A ValueError with the "op" output is raised if a resource does not exist.
    """
    msg = '"op" error: could not read secret xyz: invalid secret reference.*'
    with pytest.raises(ValueError, match=msg):
        op.get_resource("xyz")
