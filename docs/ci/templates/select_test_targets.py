#!/usr/bin/env python3
"""Copy to scripts/ci beside domain_matrix.py; replace sample with the package.

Keep a real tests/contracts smoke suite for docs-only changes. Add shared code
to core_prefixes and register exact non-module contract routes as needed.
See docs/ci/domain-matrix.md for the workflow interface and adoption checks.
"""

from pathlib import Path

from domain_matrix import SelectionRules, main

RULES = SelectionRules(
    always_xdist=("tests/contracts",),
    core_exact=frozenset(
        {
            "pyproject.toml",
            "uv.lock",
            "tests/conftest.py",
            ".github/workflows/ci.yml",
        }
    ),
    core_prefixes=("scripts/ci/", "tests/ci/", "src/sample/common/"),
    module_patterns=(r"^(?:src/sample|tests/unit)/([^/]+)/",),
    integration_patterns=(r"^tests/integration/modules/([^/]+)/",),
    contract_routes={"config/schema.json": "tests/contracts"},
)

if __name__ == "__main__":
    raise SystemExit(main(RULES, Path(__file__).resolve().parents[2]))
