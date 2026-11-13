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

def deny_external_operations(event, arguments):
    if event.startswith("socket."):
        raise RuntimeError("Network access denied by the example test")
    if event.startswith("subprocess.") or event in (
        "os.system", "os.exec", "os.posix_spawn", "os.spawn",
        "os.fork", "os.forkpty", "os.startfile", "_winapi.CreateProcess"
    ):
        raise RuntimeError("Process creation denied by the example test")

sys.addaudithook(deny_external_operations)
example, *arguments = sys.argv[1:]
sys.argv = [example, *arguments]
runpy.run_path(example, run_name="__main__")
"""


def _run_example(tmp_path, *arguments):
    env = os.environ.copy()
    env.pop("PYTHONWARNINGS", None)
    env["PYTHONPATH"] = str(_REPO_ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-c", _OFFLINE_RUNNER, str(_EXAMPLE), *arguments],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )


@pytest.mark.parametrize(
    ("intended_use", "recommendation", "intended_use_status"),
    [
        ("country_reference", "conditional_adoption", None),
        ("facility_emissions", "unsuitable", "UNSUITABLE"),
        ("abatement_modelling", "deferred", "NOT_EVALUATED"),
    ],
)
def test_example_intended_use_decisions(
    tmp_path, intended_use, recommendation, intended_use_status
):
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
    if intended_use_status is None:
        assert "intended_use" not in checks
    else:
        assert checks["intended_use"]["status"] == intended_use_status
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


@pytest.fixture
def example_probe(tmp_path, monkeypatch):
    probe = tmp_path / "probe.py"
    monkeypatch.setattr(sys.modules[__name__], "_EXAMPLE", probe)
    return probe


@pytest.mark.parametrize(
    ("event", "message"),
    [
        ("socket.connect", "Network access denied by the example test"),
        ("subprocess.Popen", "Process creation denied by the example test"),
        ("os.system", "Process creation denied by the example test"),
        ("os.exec", "Process creation denied by the example test"),
        ("os.posix_spawn", "Process creation denied by the example test"),
        ("os.spawn", "Process creation denied by the example test"),
        ("os.fork", "Process creation denied by the example test"),
        ("os.forkpty", "Process creation denied by the example test"),
        ("os.startfile", "Process creation denied by the example test"),
        ("_winapi.CreateProcess", "Process creation denied by the example test"),
    ],
)
def test_offline_runner_denial_messages(tmp_path, example_probe, event, message):
    """Audit probes exercise denials without making network or process calls."""
    example_probe.write_text(
        "import sys\nsys.audit(sys.argv[1])\n",
        encoding="utf-8",
        newline="\n",
    )
    result = _run_example(tmp_path, event)
    assert result.returncode != 0
    assert message in result.stderr


def test_child_does_not_inherit_warning_options(tmp_path, example_probe, monkeypatch):
    """Caller warning policies cannot change the child interpreter's decisions."""
    monkeypatch.setenv("PYTHONWARNINGS", "error")
    example_probe.write_text(
        "import json\nimport os\nprint(json.dumps(os.environ.get('PYTHONWARNINGS')))\n",
        encoding="utf-8",
        newline="\n",
    )
    result = _run_example(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) is None
