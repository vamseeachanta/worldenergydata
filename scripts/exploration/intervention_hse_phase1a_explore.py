"""Refresh the intervention inventory from manifest-backed public INCINV records.

Shares the drilling refresh configuration, download, QA and provenance. Keyword
hits describe the available investigation text; they do not establish service
categories or a join to local well activity reports. Run with --help for paths.
"""

import importlib.util
from pathlib import Path


def main(argv=None):
    """Load the adjacent entry point even when isolated Python omits sys.path."""
    path = Path(__file__).with_name("drilling_hse_patterns_analysis.py")
    spec = importlib.util.spec_from_file_location("hse_drilling_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main(argv)


if __name__ == "__main__":
    main()
