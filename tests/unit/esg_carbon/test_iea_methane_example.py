"""Exercise the standalone example against the documented publication decisions.

Independent oracles: docs/data-sources/iea-methane-tracker-evaluation.md,
Findings and decision basis and Opened sources (retrieved 2026-10-19).
No emissions values or numerical models are used.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXAMPLE = _REPO_ROOT / "examples" / "esg_carbon" / "evaluate_methane_tracker.py"
_OFFLINE_RUNNER = """
import runpy
import sys

def deny_network(event, arguments):
    if event.startswith(("socket.", "subprocess.")) or event in (
        "os.system", "os.exec", "os.posix_spawn", "os.spawn"
    ):
        raise RuntimeError("Network access denied by the example test")

sys.addaudithook(deny_network)
example, *arguments = sys.argv[1:]
sys.argv = [example, *arguments]
runpy.run_path(example, run_name="__main__")
"""


def _run_example(tmp_path, *arguments):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_REPO_ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-c", _OFFLINE_RUNNER, str(_EXAMPLE), *arguments],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("intended_use", "recommendation"),
    [
        ("country_reference", "conditional_adoption"),
        ("facility_emissions", "unsuitable"),
        ("abatement_modelling", "deferred"),
    ],
)
def test_example_intended_use_decisions(tmp_path, intended_use, recommendation):
    """Document decisions apply to publications, not unopened data files."""
    result = _run_example(tmp_path, "--intended-use", intended_use)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    assessment = json.loads(result.stdout)
    assert assessment["intended_use"] == intended_use
    assert assessment["recommendation"] == recommendation
    assert assessment["evaluated_on"] == "2026-10-19"
    sources = {source["key"]: source for source in assessment["sources"]}
    assert set(sources) == {"report_2025", "documentation_2025", "product_2026"}
    for source in assessment["sources"]:
        assert source["retrieved_on"] == "2026-10-19"
        assert source["url"].startswith("https://")
        assert source["title"].strip()
        assert source["section"].strip()
    checks = {check["key"]: check for check in assessment["checks"]}
    for key in (
        "download_inspection",
        "database_licence",
        "schema_and_units",
        "historical_coverage",
    ):
        assert checks[key]["status"] == "NOT_EVALUATED"
    for check in assessment["checks"]:
        assert check["source_key"] in sources
        assert check["detail"].strip()


def test_example_rejects_unknown_use(tmp_path):
    """An unknown choice cannot silently receive a country recommendation."""
    result = _run_example(tmp_path, "--intended-use", "unknown_use")
    assert result.returncode != 0
    assert not result.stdout
    assert "invalid choice" in result.stderr
    assert "unknown_use" in result.stderr


def test_example_requires_intended_use(tmp_path):
    """The standalone interface requires an explicit intended-use decision."""
    result = _run_example(tmp_path)
    assert result.returncode != 0
    assert not result.stdout
    assert "required" in result.stderr
    assert "--intended-use" in result.stderr
