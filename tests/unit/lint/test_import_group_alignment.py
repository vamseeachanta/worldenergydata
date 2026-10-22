"""Keep both import sorters in agreement on the namespace package boundary."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = """import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe
"""
FILENAME = (
    "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py"
)


def test_import_group_alignment():
    """Both tools must preserve the explicit first-party separator.

    Expected bytes are hand-enumerated: pandas belongs to third-party imports;
    worldenergydata belongs to the configured first-party group. The existing
    tool.isort.known_first_party declaration is the classification authority.
    """
    commands = [
        [
            "ruff",
            "check",
            "--no-cache",
            "--select",
            "I",
            "--fix",
            "--stdin-filename",
            FILENAME,
            "-",
        ],
        ["isort", "--stdout", "--filename", FILENAME, "-"],
    ]
    for command in commands:
        result = subprocess.run(
            command, input=SOURCE, text=True, capture_output=True, cwd=ROOT, check=True
        )
        assert result.stdout == SOURCE, result.stderr
