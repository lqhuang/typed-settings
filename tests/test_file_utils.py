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
            ["s.toml", fu.ROOT_DIR, ["setup.py"]],
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
def test_find(args, start, expected, tmp_path, monkeypatch):
    """find() always returns a path, never raises something."""
    for p in [".git", "src/a/x", "src/a/y"]:
        tmp_path.joinpath(p).mkdir(parents=True, exist_ok=True)
    for p in ["setup.py", "s.toml", "src/stop"]:
        tmp_path.joinpath(p).touch()

    monkeypatch.chdir(tmp_path.joinpath(start))
    if len(args) > 1:
        if isinstance(args[1], str):
            args[1] = tmp_path.joinpath(args[1])
    result = fu.find(*args)
    assert result == tmp_path.joinpath(expected)
