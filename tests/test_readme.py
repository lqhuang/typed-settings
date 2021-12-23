"""
Extract examples from the README and assert they work.
"""
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import attr
import docutils.frontend
import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import pytest


HERE = Path(__file__).parent


@attr.frozen
class CodeFile:
    filename: str
    contents: str

    @classmethod
    def from_lines(cls, lines: List[str]) -> "CodeFile":
        """
        Create "CodeFile" instances from literal blocks showing file contents.
        """
        filename, *lines = lines
        _, _, filename = filename.partition(" ")
        joined = "\n".join(lines)
        return cls(filename, f"{joined}\n")


@attr.frozen
class ExampleCommand:
    command: str
    output: str

    @classmethod
    def cmds_from_lines(cls, lines: List[str]) -> Tuple["ExampleCommand", ...]:
        """
        Create a list of "ExampleCommand" instances from the literal blocks
        showing "ineractive" shell sessions.
        """
        cmds: Dict[str, List[str]] = {}
        for line in lines:
            if line.startswith("$"):
                _, _, current_cmd = line.partition(" ")
                cmds[current_cmd] = []
            else:
                cmds[current_cmd].append(f"{line}\n")
        return tuple(cls(cmd, "".join(out)) for cmd, out in cmds.items())


@attr.frozen
class Example:
    title: str
    files: Tuple[CodeFile, ...]
    commands: Tuple[ExampleCommand, ...]


def readme() -> str:
    """
    Returns the contents of the `README.rst`.
    """
    return HERE.parent.joinpath("README.rst").read_text()


def parse_rst(text: str) -> docutils.nodes.document:
    """
    Parse an ReST file and return a document.
    """
    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(
        components=components
    ).get_default_values()
    document = docutils.utils.new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


class ExamplesVisitor(docutils.nodes.NodeVisitor):
    """
    Visit all nodes of the README and extract all "example" sections.
    """

    def __init__(self, doc: docutils.nodes.document):
        super().__init__(doc)
        self.examples: List[Example] = []

    def visit_section(self, node: docutils.nodes.section) -> None:
        if node.parent.children[0].astext() == "Examples":
            title = node.children[0].astext()
            lbv = LiteralBlockVisitor(self.document)
            node.walk(lbv)
            example = Example(title, tuple(lbv.files), lbv.commands)
            self.examples.append(example)

    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        pass


class LiteralBlockVisitor(docutils.nodes.NodeVisitor):
    """
    Visit all literal blocks of an example node and extract all code files
    and the example commands.
    """

    def __init__(self, doc: docutils.nodes.document):
        super().__init__(doc)
        self.files: List[CodeFile] = []
        self.commands: Tuple[ExampleCommand, ...]

    def visit_literal_block(self, node: docutils.nodes.literal_block) -> None:
        classes = node.attributes["classes"]
        lines = node.astext().splitlines()
        if "console" in classes:
            self.commands = ExampleCommand.cmds_from_lines(lines)
        else:
            self.files.append(CodeFile.from_lines(lines))

    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        pass


def load_readme() -> List[Example]:
    """
    Extract examples from the README file and return them.
    """
    doc = parse_rst(readme())
    visitor = ExamplesVisitor(doc)
    doc.walk(visitor)
    return visitor.examples


@pytest.mark.parametrize(
    "example",
    [pytest.param(e, id=e.title) for e in load_readme()],
    # indirect=True,
)
def test_readme(example: Example, tmp_path: Path):
    """
    All commands in the *console* block of an example produce the exact same
    results as shown in the example.
    """
    for code_file in example.files:
        tmp_path.joinpath(code_file.filename).write_text(code_file.contents)

    # for cmd, expected in example.items():
    for cmd in example.commands:
        result = subprocess.run(
            cmd.command,
            shell=True,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stderr == ""
        assert result.stdout == cmd.output
        assert result.returncode == 0
