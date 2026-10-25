"""Execute the offline inventory documented for issue #1337.

Expected symbols are the explicit definitions named in #1337, independently
enumerated below. Counts are hand tallies: two loaders plus one report inside;
two download implementations plus one export caller outside. Report functions
elsewhere are neither substitutes nor evidence of duplicate implementations.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)
PACKAGE = Path("packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes")
COLLECTOR = Path(
    "packages/worldenergydata-vessel_fleet/src/worldenergydata/"
    "vessel_fleet/collectors/baker_hughes_collector.py"
)
EXPORT = Path("scripts/vessel_fleet/enrich_from_government.py")
EXPECTED = {
    "worldenergydata.baker_hughes.loader.load_pivot_table": (
        PACKAGE / "loader.py",
        "inside-package",
        "implementation",
    ),
    "worldenergydata.baker_hughes.loader.load_summary": (
        PACKAGE / "loader.py",
        "inside-package",
        "implementation",
    ),
    "worldenergydata.baker_hughes.report.generate_report": (
        PACKAGE / "report.py",
        "inside-package",
        "implementation",
    ),
    "worldenergydata.vessel_fleet.collectors.baker_hughes_collector."
    "BakerHughesCollector.download_na_rig_count": (
        COLLECTOR,
        "outside-package",
        "implementation",
    ),
    "worldenergydata.vessel_fleet.collectors.baker_hughes_collector."
    "BakerHughesCollector.download_international_rig_count": (
        COLLECTOR,
        "outside-package",
        "implementation",
    ),
    "scripts.vessel_fleet.enrich_from_government.main": (
        EXPORT,
        "outside-package",
        "caller",
    ),
}


def _example():
    page = ROOT / PACKAGE / "docs/method-overlap.md"
    # The page contains one runnable Python example, not a test-only copy.
    (code,) = re.findall(
        r"```python\n(.*?)\n```", page.read_text(encoding="utf-8"), re.S
    )
    return code


def _run_example(root):
    # Isolated mode without site packages: no installed collector can be loaded.
    return subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", _example()],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _source_tree(tmp_path):
    for relative in {path for path, _, _ in EXPECTED.values()}:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


def test_documented_inventory_matches_explicit_definitions():
    result = _run_example(ROOT)
    assert result.returncode == 0, result.stderr
    inventory = json.loads(result.stdout)
    rows = inventory["definitions"]
    assert {row["symbol"] for row in rows} == set(EXPECTED)
    assert len(rows) == len(EXPECTED)
    for row in rows:
        path, boundary, role = EXPECTED[row["symbol"]]
        assert (row["path"], row["boundary"], row["role"]) == (
            path.as_posix(),
            boundary,
            role,
        )
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        source_line = lines[row["line"] - 1]  # AST line numbers are one-based.
        assert source_line.lstrip().startswith(f"def {row['symbol'].split('.')[-1]}(")
    # Independent hand tallies from the explicit #1337 list in this docstring.
    assert inventory["counts"] == {
        "inside-package": {"implementation": 3, "caller": 0},
        "outside-package": {"implementation": 2, "caller": 1},
    }


def test_unrelated_report_is_not_a_duplicate(tmp_path):
    root = _source_tree(tmp_path)
    (root / "unrelated.py").write_text(
        "def generate_report():\n    pass\n", encoding="utf-8"
    )
    result = _run_example(root)
    original = _run_example(ROOT)
    assert result.returncode == original.returncode == 0, result.stderr
    assert json.loads(result.stdout) == json.loads(original.stdout)


def test_unrelated_report_cannot_replace_missing_definition(tmp_path):
    root = _source_tree(tmp_path)
    report = root / PACKAGE / "report.py"
    report.write_text("def other_report():\n    pass\n", encoding="utf-8")
    (root / "unrelated.py").write_text(
        "def generate_report():\n    pass\n", encoding="utf-8"
    )
    result = _run_example(root)
    assert result.returncode != 0
    assert "worldenergydata.baker_hughes.report.generate_report" in result.stderr
