"""Refresh the intervention inventory from manifest-backed public INCINV records.

Shares the drilling refresh configuration, download, QA and provenance. Keyword
hits describe the available investigation text; they do not establish service
categories or a join to local well activity reports. Run with --help for paths.
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "drilling_hse_cli", Path(__file__).with_name("drilling_hse_patterns_analysis.py")
)
_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cli)
main = _cli.main

if __name__ == "__main__":
    main()
