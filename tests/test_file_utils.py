import pytest

from typed_settings import _file_utils as fu


@pytest.mark.parametrize(
    "args, start, expected",
    [
        # File found
        (["s.toml"], ".", "s.toml"),
        (["s.toml"], "src", "s.toml"),
        (["s.toml"], "src/a/x", "s.toml"),
        (["s.toml", "."], "src/a/x", "s.toml"),
        (["s.toml", fu.ROOT_DIR, ["setup.py"]], "src/a/x", "s.toml"),
        (["s.toml", fu.ROOT_DIR, ["spam"]], "src/a/x", "s.toml"),
        (["s.toml", "x"], "src/a/x", "s.toml"),
        (["s.toml", "x", ["spam"]], "src/a/x", "s.toml"),
        # File not found
        (["s.toml", "src/a"], "src/a/x", "src/a/x/s.toml"),
        (["s.toml", fu.ROOT_DIR, ["stop"]], "src/a/x", "src/a/x/s.toml"),
        (["spam"], ".", "spam"),
        (["spam"], "src", "src/spam"),
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
