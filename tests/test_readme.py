"""
Extract examples from the README and assert they work.
"""
import pathlib
import subprocess
from typing import Dict, List, Tuple

import pytest


HERE = pathlib.Path(__file__).parent


def readme() -> str:
    """
    Returns the contents of the `README.md`.
    """
    return HERE.parent.joinpath("README.md").read_text()


def load_readme() -> List[Tuple[str, List[str]]]:
    """
    Extracts the examples and returns a dict mapping example titles to a list
    of all lines in that section.
    """
    lines = readme().splitlines()
    in_examples = False
    example_title = None
    examples: Dict[str, List[str]] = {}
    for line in lines:
        if line == "## Examples":
            in_examples = True
            continue

        if not in_examples:
            continue

        if line.startswith("## "):
            return list(examples.items())

        if line.startswith("### "):
            example_title = line[4:]
            examples[example_title] = []
            continue

        if example_title:
            examples[example_title].append(line)

    raise AssertionError("We should not have gotten here")


@pytest.fixture
def example(request, tmp_path):
    """
    Splits the example lines into code blocks.

    If a code block starts with "# filename", write the contents to that file
    in *tmp_path*.

    Else, assume that the block contains a console session.  Lines starting
    with "$" are commands, other lines are the expected output of the above
    command.
    """
    example_lines = request.param
    code_lines = None
    for line in example_lines:
        if line.startswith("```") and len(line) > 3:
            code_lines = []
            continue

        if line == "```":
            if code_lines[0].startswith("# "):
                first_line, *code_lines = code_lines
                _, _, fname = first_line.partition(" ")
                contents = "\n".join(code_lines) + "\n"
                tmp_path.joinpath(fname).write_text(contents)
            else:
                cmds = {}
                current_cmd = None
                for line in code_lines:
                    if line.startswith("$"):
                        _, _, current_cmd = line.partition(" ")
                        cmds[current_cmd] = []
                    else:
                        cmds[current_cmd].append(line)
                return cmds
        elif code_lines is not None:
            code_lines.append(line)


@pytest.mark.parametrize(
    "example",
    [pytest.param(e[1], id=e[0]) for e in load_readme()],
    indirect=True,
)
def test_readme(example, tmp_path):
    """
    All commands in the *console* block of an example produce the exact same
    results as shown in the example.
    """
    for cmd, expected in example.items():
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stderr == ""
        assert result.stdout.splitlines() == expected
        assert result.returncode == 0
