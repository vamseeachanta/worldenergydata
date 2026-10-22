#!/usr/bin/env python3
"""Adapt the reusable domain workflow's selector interface to the core tier.

Issue #466 (2026 update) assigns broad integration/performance suites to
auxiliary CI; the unchanged full tier remains available through the selector.
"""

import sys

from select_test_targets import main

if __name__ == "__main__":
    raise SystemExit(main([*sys.argv[1:], "--tier", "core"]))
