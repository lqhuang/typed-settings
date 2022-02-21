"""
This plugin collects and runs the examples in :file:`doc/examples/`.

Examples need to have a :file:`test.console` file that contains shell commands
and their output similarly to Python doctests.
"""
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Union

import pytest
from _pytest._code.code import TerminalRepr
from _pytest.assertion.util import _diff_text


if TYPE_CHECKING:
    from _pytest._code.code import ExceptionInfo, _TracebackStyle
    from _pytest._io import TerminalWriter
    from _pytest.config import Config
    from _pytest.main import Session


EXAMPLES_DIR = Path(__file__).parent.joinpath("examples")


# Part of pathlib only from py39
def is_relative_to(path: Path, other: Path) -> bool:
    """Return True if the path is relative to another path or False."""
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def pytest_ignore_collect(collection_path: Path, config: "Config") -> bool:
    """Do not collect Python files from the examples."""
    return (
        is_relative_to(collection_path, EXAMPLES_DIR)
        and collection_path.suffix == ".py"
    )


def pytest_collect_file(
    file_path: Path, parent: "Session"
) -> Optional["ExampleFile"]:
    """Checks if the file is a rst file and creates an
    :class:`ExampleFile` instance."""
    if (
        is_relative_to(file_path, EXAMPLES_DIR)
        and file_path.name == "test.console"
    ):
        return ExampleFile.from_parent(parent, path=file_path)
    return None


class ExampleFile(pytest.File):
    """Represents an example ``.py`` and its output ``.out``."""

    def collect(self) -> Generator["ExampleItem", None, None]:
        name = f"Example.{self.path.parent.name}"
        name = "console_session"
        yield ExampleItem.from_parent(self, name=name)


class ExampleItem(pytest.Item):
    """Executes an example found in a rst-file."""

    def runtest(self) -> None:
        # Read expected output.
        # The last line is an empty line, skip it.
        lines = self.path.read_text().splitlines()
        cmds: Dict[str, List[str]] = {}
        last_cmd = ""
        for line in lines:
            if line.startswith("$ "):
                last_cmd = line[2:]
                cmds[last_cmd] = []
            else:
                cmds[last_cmd].append(line)

        for cmd, output_lines in cmds.items():
            expected = "\n".join(output_lines)
            output = subprocess.run(
                cmd,
                shell=True,
                cwd=self.path.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                check=True,
            ).stdout.strip()
            if output != expected:
                raise ValueError(cmd, output, expected)

    def repr_failure(
        self,
        excinfo: "ExceptionInfo[BaseException]",
        style: "Optional[_TracebackStyle]" = None,
    ) -> Union[TerminalRepr, str]:
        if excinfo.errisinstance(ValueError):
            # Output is mismatching. Create a nice diff as failure description.
            cmd, output, expected = excinfo.value.args
            diff_text = _diff_text(output, expected, 2)
            return ReprFailExample(self, cmd, diff_text)

        elif excinfo.errisinstance(subprocess.CalledProcessError):
            # Something went wrong while executing the example.
            return ReprErrorExample(self, excinfo)  # type: ignore

        # Something went terribly wrong :(
        return pytest.Item.repr_failure(self, excinfo)


class ReprFailExample(TerminalRepr):
    """Reports output mismatches in a nice and informative representation."""

    markup = {
        "+": dict(green=True),
        "-": dict(red=True),
        "?": dict(bold=True),
    }
    """Colorization codes for the diff markup."""

    def __init__(
        self, item: ExampleItem, cmd: str, diff_text: List[str]
    ) -> None:
        self.item = item
        self.cmd = cmd
        self.diff_text = diff_text

    def toterminal(self, tw: "TerminalWriter") -> None:
        tw.line()
        tw.line("Got unexpected output while running the console session:")
        tw.line()
        tw.line(f"$ {self.cmd}", bold=True)
        for line in self.diff_text:
            markup = self.markup.get(line[0], {})
            tw.line(line, **markup)
        tw.line()


class ReprErrorExample(TerminalRepr):
    """Reports failures in the execution of an example."""

    def __init__(
        self,
        item: ExampleItem,
        exc_info: "ExceptionInfo[subprocess.CalledProcessError]",
    ) -> None:
        self.item = item
        self.exc_info = exc_info

    def toterminal(self, tw: "TerminalWriter") -> None:
        exc = self.exc_info.value
        tw.line()
        tw.line("An error occurred while running the console session:")
        tw.line()
        tw.line(f"$ {exc.cmd}", bold=True)
        tw.line(self.exc_info.value.output)
