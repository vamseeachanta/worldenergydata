"""Keep nightly failure evidence without changing the test result."""

import os
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/nightly.yml"


def _steps() -> list[dict]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["full-test-suite"]["steps"]


def _test_step() -> dict:
    return next(step for step in _steps() if "--cov=src" in step.get("run", ""))


def _upload_step() -> dict:
    return next(
        step
        for step in _steps()
        if step.get("with", {}).get("name") == "coverage-report"
    )


def test_reports_upload_after_test_failure() -> None:
    """A failed test must not suppress its diagnostic artifact."""
    steps = _steps()
    upload = _upload_step()
    assert upload.get("if") == "always()"
    assert steps.index(upload) > steps.index(_test_step())


def test_artifact_contains_each_requested_report() -> None:
    """Both machine-readable reports and the existing HTML are retained."""
    paths = set(_upload_step()["with"]["path"].splitlines())
    assert paths == {"coverage.xml", "coverage-report/", "test-results.xml"}
    assert "--junitxml=test-results.xml" in _test_step()["run"]


def test_full_suite_failure_is_not_masked() -> None:
    """The original test target and nonzero exit remain authoritative."""
    job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][
        "full-test-suite"
    ]
    step = _test_step()
    tokens = shlex.split(step["run"].replace("\\\n", " "))
    assert tokens[:4] == ["uv", "run", "pytest", "tests/"]
    assert "continue-on-error" not in step
    assert "continue-on-error" not in job
    assert not any(token in tokens for token in ("||", ";", "exit", "true"))


@pytest.mark.parametrize("fails", [False, True], ids=["passing", "failing"])
def test_pytest_writes_reports_before_returning(tmp_path: Path, fails: bool) -> None:
    """One synthetic test yields one case and zero or one failures by inspection.

    The fixture imports an identity function, then asserts a literal Boolean.
    Expected exits are pytest.ExitCode.OK and TESTS_FAILED, respectively; XML
    counts follow directly from that single assertion, independently of the
    workflow. No engineering coefficients or acceptance limits are used.
    """
    source = tmp_path / "src"
    source.mkdir()
    (source / "sample.py").write_text("def identity(value):\n    return value\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        f"from sample import identity\n\ndef test_sample():\n"
        f"    assert identity({not fails!r})\n"
    )
    tokens = shlex.split(_test_step()["run"].replace("\\\n", " "))
    env = dict(os.environ, PYTHONPATH=str(source), PYTEST_ADDOPTS="")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "COVERAGE_FILE"):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *tokens[3:], "-p", "no:cacheprovider"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    expected = pytest.ExitCode.TESTS_FAILED if fails else pytest.ExitCode.OK
    assert result.returncode == expected, result.stdout + result.stderr
    suite = ET.parse(tmp_path / "test-results.xml").getroot().find("testsuite")
    assert suite is not None
    assert int(suite.attrib["tests"]) == 1
    assert int(suite.attrib["failures"]) == int(fails)
    assert ET.parse(tmp_path / "coverage.xml").getroot().tag == "coverage"
    assert (tmp_path / "coverage-report" / "index.html").is_file()
