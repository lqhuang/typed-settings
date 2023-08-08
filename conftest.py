"""
Fixtures for the documentation tests and examples.
"""
import os
import re
import subprocess
from doctest import ELLIPSIS
from itertools import chain
from pathlib import Path
from textwrap import dedent
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import pytest
from sybil import Document, Example, Region, Sybil
from sybil.evaluators.python import PythonEvaluator, pad
from sybil.parsers.abstract.lexers import BlockLexer
from sybil.parsers.rest import DocTestParser, SkipParser
from sybil.parsers.rest.lexers import DirectiveInCommentLexer
from sybil.region import LexedRegion
from sybil.typing import Evaluator, Lexer


START_PATTERN_TEMPLATE = (
    r"^(?P<prefix>[ \t]*)\.\.\s*(?P<directive>{directive})"
    r"{delimiter}\s*"
    r"(?P<arguments>[\w-]+\b)?"
    r"(?P<options>(?:\s*\:[\w-]+\:.*\n)*)"
    r"(?:\s*\n)*\n"
)

END_PATTERN_TEMPLATE = "(\n\\Z|\n[ \t]{{0,{len_prefix}}}(?=\\S))"


class DirectiveLexer(BlockLexer):
    """
    A lexer for ReST directives.
    Both ``directive`` and ``arguments`` are regex patterns.

    Copied and adjusted from Sybil.
    """

    delimiter = "::"

    def __init__(
        self,
        directive: str,
        arguments: str = "",
        mapping: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            start_pattern=re.compile(
                START_PATTERN_TEMPLATE.format(
                    directive=directive,
                    delimiter=self.delimiter,
                    arguments=arguments,
                ),
                re.MULTILINE,
            ),
            end_pattern_template=END_PATTERN_TEMPLATE,
            mapping=mapping,
        )

    def __call__(self, document: Document) -> Iterable[LexedRegion]:
        for region in super().__call__(document):
            if isinstance(region, LexedRegion):
                option_strs = region.lexemes.get("options", "").splitlines()
                options: Dict[str, str] = {}
                for option_str in option_strs:
                    optname, _, optval = option_str.strip().partition(" ")
                    optname = optname[1:-1]
                    options[optname] = optval
                region.lexemes["options"] = options
            yield region


class AbstractCodeBlockParser:
    """
    Abstract base class for code block parsers.

    Copied and adjusted from Sybil.
    """

    language: str

    def __init__(
        self,
        lexers: Sequence[Lexer],
        language: Optional[str] = None,
        evaluator: Evaluator = None,
    ):
        self.lexers = lexers
        if language is not None:
            self.language = language
        assert self.language, "language must be specified!"
        if evaluator is not None:
            self.evaluate = evaluator  # type: ignore[assignment]

    def evaluate(self, example: Example) -> Optional[str]:
        raise NotImplementedError

    def __call__(self, document: Document) -> Iterable[Region]:
        for lexed in chain(*(lexer(document) for lexer in self.lexers)):
            if lexed.lexemes["arguments"] == self.language:
                r = Region(
                    lexed.start,
                    lexed.end,
                    lexed.lexemes["source"],
                    self.evaluate,
                )
                r.options = lexed.lexemes.get("options", {})
                yield r


class CodeBlockParser(AbstractCodeBlockParser):
    """
    Parser for "code-block" directives.
    """

    def __init__(
        self,
        language: Optional[str] = None,
        evaluator: Optional[Evaluator] = None,
    ):
        super().__init__(
            [
                DirectiveLexer(directive=r"code-block"),
                DirectiveInCommentLexer(directive=r"(invisible-)?code(-block)?"),
            ],
            language,
            evaluator,
        )

    pad = staticmethod(pad)


class CodeFileParser(CodeBlockParser):
    """
    Parser for included/referenced files.
    """

    ext: str

    def __init__(
        self,
        language: Optional[str] = None,
        *,
        ext: Optional[str] = None,
        fallback_evaluator: Evaluator = None,
    ) -> None:
        super().__init__(language=language)  # type: ignore[arg-type]
        if ext is not None:
            self.ext = ext
        if self.ext is None:
            raise ValueError('"ext" must be specified!')
        self.evaluator = fallback_evaluator

    def evaluate(self, example: Example) -> None:
        caption = example.region.options.get("caption")
        if caption and caption.endswith(self.ext):
            raw_text = dedent(example.parsed)
            Path(caption).write_text(raw_text)
        elif self.evaluator is not None:
            self.evaluator(example)


class ConsoleCodeBlockParser(CodeBlockParser):
    """
    Code block parser for Console sessions.

    Parses the command as well as the expected output.
    """

    language = "console"

    def evaluate(self, example: Example) -> None:
        cmds = self._get_commands(example)

        for cmd, expected in cmds:
            result = subprocess.run(
                cmd,
                shell=True,  # noqa: S602
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
    """
    Create a a "doctests" diretory in "tmp_path" and make that dir the CWD.
    """
    tmp_path = tmp_path_factory.mktemp("doctests")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
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


pytest_collect_file = Sybil(
    parsers=[
        SkipParser(),
        DocTestParser(optionflags=ELLIPSIS),
        CodeFileParser("python", ext=".py", fallback_evaluator=PythonEvaluator()),
        CodeFileParser("toml", ext=".toml"),
        ConsoleCodeBlockParser(),
    ],
    # patterns=["*.md", "*.rst", "*.py"],
    patterns=["docs/*.md", "docs/*.rst"],
    fixtures=["tempdir", "env"],
).pytest()
