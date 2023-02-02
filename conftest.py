import os
import subprocess
from doctest import ELLIPSIS
from pathlib import Path
from textwrap import dedent
from typing import Iterator, List, Tuple

import pytest
from sybil import Example, Sybil
from sybil.evaluators.python import PythonEvaluator
from sybil.parsers.rest import CodeBlockParser, DocTestParser, SkipParser


class PythonCodeBlockParser(CodeBlockParser):
    language = "python"

    def evaluate(self, example: Example) -> None:
        raw_text = dedent(example.parsed)
        first_line, *lines = raw_text.strip().split("\n")
        comment, _, filename = first_line.partition(" ")
        if comment == "#" and filename:
            Path(filename).write_text(raw_text)
        else:
            PythonEvaluator()(example)


class TomlCodeBlockParser(CodeBlockParser):
    language = "toml"

    def evaluate(self, example: Example) -> None:
        raw_text = dedent(example.parsed)
        first_line, *lines = raw_text.strip().split("\n")
        comment, _, filename = first_line.partition(" ")
        if comment == "#" and filename:
            Path(filename).write_text(raw_text)


class ConsoleCodeBlockParser(CodeBlockParser):
    language = "console"

    def evaluate(self, example: Example) -> None:
        cmds = self._get_commands(example)

        for cmd, expected in cmds:
            result = subprocess.run(
                cmd,
                shell=True,
                # cwd=str(tmp_path),
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.stderr == ""
            assert result.stdout == expected
            assert result.returncode == 0

    def _get_commands(self, example: Example) -> List[Tuple[str, str]]:
        code_lines = dedent(example.parsed).strip().split("\n")

        cmds: List[Tuple[str, List[str]]] = []
        current_cmd: str
        for line in code_lines:
            if line.startswith("$"):
                _, _, current_cmd = line.partition(" ")
                cmds.append((current_cmd, []))
            else:
                cmds[-1][-1].append(line)

        return [(cmd, "".join(f"{x}\n" for x in lines)) for cmd, lines in cmds]


@pytest.fixture(scope="module")
def tempdir(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    tmp_path = tmp_path_factory.mktemp("doctests")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(old_cwd)


class Env:
    def __init__(self) -> None:
        self._mp = pytest.MonkeyPatch()

    def set(self, name: str, value: str) -> None:
        self._mp.setenv(name, value)

    def undo(self) -> None:
        self._mp.undo()


@pytest.fixture(scope="module")
def env() -> Iterator[Env]:
    e = Env()
    try:
        yield e
    finally:
        e.undo()


pytest_collect_file = Sybil(
    parsers=[
        SkipParser(),
        DocTestParser(optionflags=ELLIPSIS),
        PythonCodeBlockParser(),
        TomlCodeBlockParser(),
        ConsoleCodeBlockParser(),
    ],
    # patterns=["*.md", "*.rst", "*.py"],
    patterns=["docs/*.md", "docs/*.rst"],
    fixtures=["tempdir", "env"],
).pytest()
