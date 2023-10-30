"""
Tests for "typed_settings._file_utils".
"""
from pathlib import Path
from typing import List

import pytest

from typed_settings import _file_utils as fu


@pytest.mark.parametrize(
    "args, start, expected",
    [
        # File found
        pytest.param(["s.toml"], ".", "s.toml", id="found-from-pwd"),
        pytest.param(["s.toml"], "src", "s.toml", id="found-from-subdir"),
        pytest.param(["s.toml"], "src/a/x", "s.toml", id="found-from-subdirs"),
        pytest.param(
            ["s.toml", "."],
            "src/a/x",
            "s.toml",
            id="found-from-subdirs-stop-project",
        ),
        pytest.param(
            ["s.toml", fu.ROOT_DIR, ["pyproject.toml"]],
            "src/a/x",
            "s.toml",
            id="found-from-subdirs-stop-existing-file",
        ),
        pytest.param(
            ["s.toml", fu.ROOT_DIR, ["spam"]],
            "src/a/x",
            "s.toml",
            id="found-from-subdirs-found-stop-nonexisting-file",
        ),
        pytest.param(
            ["s.toml", "x"],
            "src/a/x",
            "s.toml",
            id="found-from-subdirs-stop-nonexisting-rootdir",
        ),
        pytest.param(
            ["s.toml", "x", ["spam"]],
            "src/a/x",
            "s.toml",
            id="found-from-subdirs-stop-nonexisting-rootdir-and-file",
        ),
        # File not found
        pytest.param(
            ["s.toml", "src/a"],
            "src/a/x",
            "src/a/x/s.toml",
            id="not-found-stop-at-subdir",
        ),
        pytest.param(
            ["s.toml", fu.ROOT_DIR, ["stop"]],
            "src/a/x",
            "src/a/x/s.toml",
            id="not-found-stop-at-stop-file",
        ),
        pytest.param(["spam"], ".", "spam", id="not-found-not-exists"),
        pytest.param(
            ["spam"],
            "src",
            "src/spam",
            id="not-found-not-exists-start-from-subdir",
        ),
        pytest.param(
            ["spam", "xxx", []],
            ".",
            "spam",
            id="not-found-non-existing-rootdir-and-stopfile",
        ),
    ],
)
@pytest.mark.parametrize(
    "monkeypatch_cwd",
    [
        pytest.param(True, id="monkeypatch_cwd"),
        pytest.param(False, id="use_cwd_argument"),
    ],
)
def test_find(
    args: List[str],
    start: str,
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    monkeypatch_cwd: bool,
) -> None:
    """find() always returns a path, never raises something."""
    for p in [".git", "src/a/x", "src/a/y"]:
        tmp_path.joinpath(p).mkdir(parents=True, exist_ok=True)
    for p in ["pyproject.toml", "s.toml", "src/stop"]:
        tmp_path.joinpath(p).touch()

    # We need a deepcopy here as we modify the args below
    if len(args) > 1:
        args = list(args)
        args[1] = tmp_path.joinpath(args[1])  # type: ignore[call-overload]

    start_dir = tmp_path.joinpath(start)

    if monkeypatch_cwd:
        monkeypatch.chdir(start_dir)
        result = fu.find(*args)
    else:
        result = fu.find(*args, start_dir=start_dir)
    assert result == tmp_path.joinpath(expected)
