"""Execute the two standalone offline worked examples in the knowledge pack.

Source: agent-pack.md, 'Offline permit search and router failure'. Hand count:
one permit example plus one router example equals two Python code blocks.
Each block carries its own independently written expected query or error.
"""

import re
import runpy
from pathlib import Path

import pytest

from worldenergydata.landman import exceptions

PACK = Path(exceptions.__file__).parent / "docs" / "agent-pack.md"
EXAMPLES = re.findall(r"```python\n(.*?)\n```", PACK.read_text(), re.DOTALL)


def test_worked_examples_are_present():
    assert len(EXAMPLES) == 2


@pytest.mark.parametrize("source", EXAMPLES, ids=["permit-dates", "router-error"])
def test_documented_example(source, tmp_path):
    example = tmp_path / "example.py"
    example.write_text(source)
    runpy.run_path(str(example))
