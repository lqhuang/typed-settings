import os
import subprocess
from typing import Any, Optional, Tuple

import pytest
from packaging.version import Version

from typed_settings import _onepassword as op


try:
    HAS_OP = op.run("account", "list") != ""
except ValueError:
    HAS_OP = False
IN_CI = "CI" in os.environ
ON_FEATURE_BRANCH = os.getenv("CI_COMMIT_BRANCH", "") not in {"main", ""}

pytestmark = pytest.mark.skipif(
    (not HAS_OP) or (IN_CI and ON_FEATURE_BRANCH),
    reason="OP not installed or credentials not accessible",
)


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
    msg = '"op" error:.*unknown command.*'
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
