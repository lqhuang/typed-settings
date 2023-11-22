"""
Fixtures for the documentation tests and examples.
"""
import os
import re
import subprocess
from doctest import ELLIPSIS
from pathlib import Path
from textwrap import dedent
from typing import Iterable, Iterator, Optional, Tuple, Union

import pytest
import sybil
import sybil.evaluators.doctest
import sybil.evaluators.python
import sybil.parsers.abstract
import sybil.parsers.abstract.lexers
import sybil.parsers.myst
import sybil.parsers.myst.lexers
import sybil.parsers.rest
import sybil.parsers.rest.lexers
import sybil.region
import sybil.typing


class CodeFileParser(sybil.parsers.myst.CodeBlockParser):
    """
    Parser for included/referenced files.
    """

    ext: str

    def __init__(
        self,
        language: Optional[str] = None,
        *,
        ext: Optional[str] = None,
        fallback_evaluator: Optional[sybil.typing.Evaluator] = None,
        doctest_optionflags: int = 0,
    ) -> None:
        super().__init__(language=language)  # type: ignore[arg-type]
        if ext is not None:
            self.ext = ext
        if self.ext is None:
            raise ValueError('"ext" must be specified!')

        self.evaluator = fallback_evaluator

        # Allow doctests in normal "```python" blocks
        self.doctest_parser: Optional[sybil.parsers.abstract.DocTestStringParser] = None
        if language == "python":
            self.doctest_parser = sybil.parsers.abstract.DocTestStringParser(
                sybil.evaluators.doctest.DocTestEvaluator(doctest_optionflags)
            )

    def __call__(self, document: sybil.Document) -> Iterable[sybil.Region]:
        for region in super().__call__(document):
            # Doctests in a normal "```python" block
            source = region.parsed
            if self.language == "python" and source.startswith(">>>"):
                for doctest_region in self.doctest_parser(source, document.path):  # type: ignore
                    doctest_region.adjust(region, source)
                    yield doctest_region
            else:
                yield region

    def evaluate(self, example: sybil.Example) -> None:
        caption = example.region.lexemes.get("options", {}).get("caption")
        if caption and caption.endswith(self.ext):
            raw_text = dedent(example.parsed)
            Path(caption).write_text(raw_text)
        elif self.evaluator is not None:
            self.evaluator(example)


class ConsoleCodeBlockParser(sybil.parsers.myst.CodeBlockParser):
    """
    Code block parser for Console sessions.

    Parses the command as well as the expected output.
    """

    language = "console"

    def evaluate(self, example: sybil.Example) -> None:
        cmds, output = self._get_commands(example)

        expected: Union[str, re.Pattern]
        if "..." in output:
            output = re.escape(output).replace("\\.\\.\\.", ".*")
            expected = re.compile(f"^{output}$", flags=re.DOTALL)
        else:
            expected = output
        proc = subprocess.Popen(
            ["bash"],  # noqa: S603, S607
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _stderr = proc.communicate(cmds)
        # Remove trailing spaces in output:
        stdout = "".join(f"{line.rstrip()}\n" for line in stdout.splitlines())
        if isinstance(expected, str):
            assert stdout == expected
        else:
            assert expected.match(stdout)

    def _get_commands(self, example: sybil.Example) -> Tuple[str, str]:
        """
        Return commands and outputs.
        """
        # Until version 23.0.1 this function returned a list of (cmd, output) tuples and
        # each cmd was invoked individually.
        # This prevented the use of "export VAR=val" because the env was not carried
        # over to the next command.
        #
        # Now we just concatenate all commands and run them as a single script and
        # compare the output of all commands at once.  It's not very easy to simulate an
        # interactive Bash session in Python and this is good enough for the doctests.
        code_lines = dedent(example.parsed).strip().splitlines()

        cmds, output = [], []
        for line in code_lines:
            if line.startswith("$"):
                _, _, current_cmd = line.partition(" ")
                cmds.append(current_cmd)
            else:
                output.append(line)

        cmds.append("exit")

        return "".join(f"{c}\n" for c in cmds), "".join(f"{o}\n" for o in output)


@pytest.fixture(scope="module")
def tempdir(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """
    Create a a "doctests" diretory in "tmp_path" and make that dir the CWD.
    """
    tests_dir = Path(__file__).parent.joinpath("tests")
    assert tests_dir.is_dir()
    path = os.getenv("PATH")
    path = f"{tests_dir}:{path}"

    tmp_path = tmp_path_factory.mktemp("doctests")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setitem(os.environ, "PATH", path)
            yield tmp_path
    finally:
        os.chdir(old_cwd)


class Env:
    """
    This object is returned by the :func:`env()` fixture and allows setting environment
    variables that are only visible for the current code block.
    """

    def __init__(self) -> None:
        self._mp = pytest.MonkeyPatch()

    def set(self, name: str, value: str) -> None:
        self._mp.setenv(name, value)

    def undo(self) -> None:
        self._mp.undo()


@pytest.fixture(scope="module")
def env() -> Iterator[Env]:
    """
    Return an :class:`Env` object that allows setting env vars for the current code
    block.

    All vars are deleted afterwards.
    """
    e = Env()
    try:
        yield e
    finally:
        e.undo()


markdown_examples = sybil.Sybil(
    parsers=[
        CodeFileParser(
            "python",
            ext=".py",
            fallback_evaluator=sybil.evaluators.python.PythonEvaluator(),
        ),
        CodeFileParser("json", ext=".json"),
        CodeFileParser("toml", ext=".toml"),
        ConsoleCodeBlockParser(),
        sybil.parsers.myst.DocTestDirectiveParser(optionflags=ELLIPSIS),
        sybil.parsers.myst.SkipParser(),
    ],
    patterns=["*.md"],
    fixtures=["tempdir", "env", "tmp_path"],
)
rest_examples = sybil.Sybil(
    parsers=[
        sybil.parsers.rest.SkipParser(),
        sybil.parsers.rest.DocTestParser(optionflags=ELLIPSIS),
    ],
    patterns=["*.py"],
)
pytest_collect_file = (markdown_examples + rest_examples).pytest()
