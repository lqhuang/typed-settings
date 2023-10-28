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
from typing import Dict, Iterable, Iterator, Optional, Sequence, Tuple, Union

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


REST_START_PATTERN = (
    r"^(?P<prefix>[ \t]*)\.\.\s*(?P<directive>code-block::\s*)"
    r"(?P<language>[\w-]+\b)?"
    r"(?P<options>(?:\s*\:[\w-]+\:.*\n)*)"
    r"(?:\s*\n)*\n"
)

MYST_START_PATTERN = (
    r"^(?P<prefix>[ \t]*)"
    r"```\{(?P<directive>code-block)}\s*"
    r"(?P<arguments>[\w-]+\b)$\n"
    r"(?P<options>(?:\s*\:[\w-]+\:.*\n)*)?"
)


class ParametrizedCodeBlockLexer(sybil.parsers.abstract.lexers.BlockLexer):
    """
    Base class for configurable code-block lexers.
    """

    def __init__(self, start_pattern_template: str, end_pattern_template: str) -> None:
        super().__init__(
            start_pattern=re.compile(start_pattern_template, re.MULTILINE),
            end_pattern_template=end_pattern_template,
        )

    def __call__(self, document: sybil.Document) -> Iterable[sybil.region.LexedRegion]:
        for region in super().__call__(document):
            if isinstance(region, sybil.region.LexedRegion):
                # 'or ""' also handles "get()" returning None:
                options_str = region.lexemes.get("options", "") or ""
                option_lines = options_str.splitlines()
                options: Dict[str, str] = {}
                for option_str in option_lines:
                    optname, _, optval = option_str.strip().partition(" ")
                    optname = optname[1:-1]
                    options[optname] = optval.strip()
                region.lexemes["options"] = options
            yield region


class MystCodeBlockLexer(ParametrizedCodeBlockLexer):
    """
    A lexer for MyST code-block directives.
    Both ``directive`` and ``arguments`` are regex patterns.

    Copied and adjusted from Sybil.

    .. code-block:: markdown

        ```{code-block} language
        :key1: val1
        :key2: val2

        This is
        directive content
    """

    def __init__(self) -> None:
        super().__init__(
            start_pattern_template=MYST_START_PATTERN,
            end_pattern_template=sybil.parsers.myst.lexers.CODEBLOCK_END_TEMPLATE,
        )


class RestCodeBlockLexer(ParametrizedCodeBlockLexer):
    """
    A lexer for ReST code-block directives.

    Copied and adjusted from Sybil.
    """

    def __init__(self):
        super().__init__(
            start_pattern_template=REST_START_PATTERN,
            end_pattern_template=sybil.parsers.rest.lexers.END_PATTERN_TEMPLATE,
        )


class AbstractCodeBlockParser:
    """
    Abstract base class for code block parsers.

    Copied from Sybil and adjusted to extract directive options, too.
    """

    language: str

    def __init__(
        self,
        lexers: Sequence[sybil.typing.Lexer],
        language: Optional[str] = None,
        evaluator: sybil.typing.Evaluator = None,
    ):
        self.lexers = lexers
        if language is not None:
            self.language = language
        assert self.language, "language must be specified!"
        if evaluator is not None:
            self.evaluate = evaluator  # type: ignore[assignment]

    def evaluate(self, example: sybil.Example) -> Optional[str]:
        raise NotImplementedError

    def __call__(self, document: sybil.Document) -> Iterable[sybil.Region]:
        for lexed in chain(*(lexer(document) for lexer in self.lexers)):
            if lexed.lexemes["arguments"] == self.language:
                r = sybil.Region(
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
        evaluator: Optional[sybil.typing.Evaluator] = None,
    ):
        super().__init__(
            [
                sybil.parsers.myst.lexers.FencedCodeBlockLexer(
                    language=r".+",
                    mapping={"language": "arguments", "source": "source"},
                ),
                MystCodeBlockLexer(),
                RestCodeBlockLexer(),
                sybil.parsers.rest.lexers.DirectiveInCommentLexer(
                    directive=r"(invisible-)?code(-block)?"
                ),
                # sybil.parser.myst.lexers.DirectiveInPercentCommentLexer(directive=...)
            ],
            language,
            evaluator,
        )

    pad = staticmethod(sybil.evaluators.python.pad)


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
        fallback_evaluator: sybil.typing.Evaluator = None,
        doctest_optionflags: int = 0,
    ) -> None:
        super().__init__(language=language)  # type: ignore[arg-type]
        if ext is not None:
            self.ext = ext
        if self.ext is None:
            raise ValueError('"ext" must be specified!')
        if language == "python":
            self.doctest_parser = sybil.parsers.abstract.DocTestStringParser(
                sybil.evaluators.doctest.DocTestEvaluator(doctest_optionflags)
            )
        else:
            self.doctest_parser = None
        self.evaluator = fallback_evaluator

    def __call__(self, document: sybil.Document) -> Iterable[sybil.Region]:
        for region in super().__call__(document):
            source = region.parsed
            if region.parsed.startswith(">>>"):
                for doctest_region in self.doctest_parser(source, document.path):
                    doctest_region.adjust(region, source)
                    yield doctest_region
            else:
                yield region

    def evaluate(self, example: sybil.Example) -> None:
        caption = example.region.options.get("caption")
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
        # sybil.parsers.myst.PythonCodeBlockParser(doctest_optionflags=ELLIPSIS),
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
    patterns=["*.rst", "*.py"],
    fixtures=["tempdir", "env", "tmp_path"],
)
pytest_collect_file = (markdown_examples + rest_examples).pytest()
