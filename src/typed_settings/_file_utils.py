from pathlib import Path
from typing import Iterable, Union


ROOT_DIR = Path().resolve().root


def find(
    filename: str,
    stop_dir: Union[str, Path] = ROOT_DIR,
    stop_files: Iterable[str] = (".git", ".hg"),
) -> Path:
    """
    Search for a file in the current directory and its parents and return its
    path.

    If the file cannot be found until *stop_dir* is reached or a directory
    contains *stop_file*, return the input *filename*.

    Args:
        filename: The name of the file to find.
        stop_dir: Stop searching if the current search dir equals this one.
        stop_files: Stop searching if the current search dir contains
         this file.

    Returns:
        The resolved path to *filename* if found, else ``Path(filename)``.

    Examples:

        Find :file:`settings.toml` until the root of the current directory
        is reached::

            find("settings.py")

        Find :file:`pyproject.toml` only in the current Git project::

            find("pyproject.toml", stop_file=".git")

    """
    start = Path.cwd().joinpath(filename)
    for path in start.parents:
        p = path.joinpath(filename)
        if p.exists():
            return p

        if path == stop_dir:
            return start

        for stop_file in stop_files:
            if path.joinpath(stop_file).exists():
                return start

    return start
