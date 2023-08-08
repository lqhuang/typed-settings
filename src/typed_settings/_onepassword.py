"""
Helpers for invoking the 1Password CLI.
"""
import json
import subprocess
from typing import Any, Dict, Optional


__all__ = [
    "run",
    "get_item",
    "get_resource",
]


def run(*args: str) -> str:
    """
    Run ``op`` with the given arguments and return its stdout.

    Args:
        args: The command line arguments to pass to ``op``.

    Return:
        The stripped *stdout* of the ``op`` invocation.

    Raise:
        ValueError: If the CLI is not properly installed or the invocation
            failed.
    """
    cmd = ("op", *args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True  # noqa: S603
        )
    except FileNotFoundError:
        raise ValueError(
            "The 1Password CLI is not properly installed.  You can find help "
            "here: https://developer.1password.com/docs/cli/"
        ) from None
    except subprocess.CalledProcessError as e:
        _level, _date, _time, msg = e.stderr.strip().split(" ", maxsplit=3)
        raise ValueError(f'"op" error: {msg}') from None
    return result.stdout.strip()


def get_item(item: str, vault: Optional[str] = None) -> Dict[str, Any]:
    """
    Get *item* from 1Password.

    Args:
        item: The name of the item to retrieve.
        vault: Restrict search to this vault.

    Return:
        A dict mapping item labels to their values.

    Raise:
        ValueError: If the CLI is not properly installed or the invocation
            failed.
    """
    cmd = ["item", "get", "--format=json", item]
    if vault:
        cmd.append(f"--vault={vault}")
    data = json.loads(run(*cmd))
    return {
        field["label"]: field["value"] for field in data["fields"] if "value" in field
    }


def get_resource(resource: str) -> str:
    """
    Get the specified resource from 1Password using ``op read``.

    Args:
        resource: The URL (prefixed with ``op://`` for the resource.

    Return:
        The resource's value.

    Raise:
        ValueError: If the CLI is not properly installed or the invocation
            failed.
    """
    value = run("read", resource)
    return value
