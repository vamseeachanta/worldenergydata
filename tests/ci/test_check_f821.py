"""Hand-checked scan fixtures: one undefined expression gives one F821 at (1, 1).

Counts below are cardinalities of explicit fixture records, independent of the
checker. CLI status conventions are documented in docs/ci/f821-scans.md.
F821 definition: https://docs.astral.sh/ruff/rules/undefined-name/ (accessed 2026).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ci import check_f821


@pytest.fixture
def scan(tmp_path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    (root / "sample.py").write_text("missing_name\n", encoding="utf-8")
    monkeypatch.chdir(root)
    output = tmp_path / "evidence"
    return root, output


def arguments(output, *extra):
    # Repetition needs two observations; the timeout is an input, not a tolerance.
    return [
        "sample.py",
        "--runs",
        "2",
        "--timeout",
        "30",
        "--output",
        str(output),
        *extra,
    ]


def fake_linter(monkeypatch, behavior=None):
    calls = []

    def run(command, **kwargs):
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "fixture-version\n", "")
        index = len(calls)
        calls.append(command)
        canary = command[-1]
        stdout = f"{canary}:1:1:F821:undefined name 'scan_canary_missing'\n"
        stdout += "sample.py:1:1:F821:undefined name 'missing_name'\n"
        result = subprocess.CompletedProcess(command, 1, stdout, "")
        return behavior(index, result, command, kwargs) if behavior else result

    monkeypatch.setattr(check_f821.subprocess, "run", run)
    return calls


def report(output):
    return json.loads((output / "report.json").read_text(encoding="utf-8"))


def test_findings_are_counted_separately_from_stderr(scan, monkeypatch):
    """One repository record + one excluded canary = one finding, not three lines."""
    _, output = scan

    def warning(index, result, command, kwargs):
        result.stderr = "environment notice\n"
        return result

    calls = fake_linter(monkeypatch, warning)
    assert check_f821.main(arguments(output)) == 1
    evidence = report(output)
    assert evidence["status"] == "STABLE"
    assert [run["count"] for run in evidence["runs"]] == [1, 1]
    assert all("--jobs=1" in command for command in calls)
    assert (output / "run-1.stderr").read_text() == "environment notice\n"


def test_stable_inventory_can_be_used_for_investigation(scan, monkeypatch):
    _, output = scan
    fake_linter(monkeypatch)
    assert check_f821.main(arguments(output, "--allow-findings")) == 0


def test_same_count_with_different_findings_is_unstable(scan, monkeypatch):
    """{sample.py:1:1} differs from {sample.py:2:1}, despite equal cardinality."""
    _, output = scan

    def move(index, result, command, kwargs):
        if index:
            result.stdout = result.stdout.replace("sample.py:1:1:", "sample.py:2:1:")
        return result

    fake_linter(monkeypatch, move)
    assert check_f821.main(arguments(output, "--allow-findings")) == 2
    assert report(output)["status"] == "UNSTABLE"


@pytest.mark.parametrize(
    "failure", ["empty", "garbage", "syntax", "duplicate", "outside"]
)
def test_incomplete_or_invalid_output_fails_closed(scan, monkeypatch, failure):
    _, output = scan

    def corrupt(index, result, command, kwargs):
        if failure == "empty":
            result.stdout = ""
            result.returncode = 0
        elif failure == "garbage":
            result.stdout += "not a finding\n"
        elif failure == "syntax":
            result.stdout += "sample.py:1:1:E999:SyntaxError\n"
        elif failure == "duplicate":
            result.stdout += "sample.py:1:1:F821:undefined name 'missing_name'\n"
        else:
            result.stdout += "unrequested.py:1:1:F821:undefined name 'missing'\n"
        return result

    fake_linter(monkeypatch, corrupt)
    assert check_f821.main(arguments(output, "--allow-findings")) == 2
    assert report(output)["status"] == "ERROR"


@pytest.mark.parametrize("returncode", [0, 2, -9])
def test_wrong_exit_status_is_never_a_valid_scan(scan, monkeypatch, returncode):
    _, output = scan

    def fail(index, result, command, kwargs):
        result.returncode = returncode
        return result

    fake_linter(monkeypatch, fail)
    assert check_f821.main(arguments(output)) == 2
    assert report(output)["runs"][0]["returncode"] == returncode


@pytest.mark.parametrize("change", ["edit", "add", "remove"])
def test_source_changes_invalidate_comparison(scan, monkeypatch, change):
    root, output = scan

    def mutate(index, result, command, kwargs):
        if change == "edit":
            (root / "sample.py").write_text("different_name\n")
        elif change == "add":
            (root / "added.py").write_text("another_name\n")
        else:
            (root / "sample.py").unlink()
        return result

    fake_linter(monkeypatch, mutate)
    args = arguments(output)
    args[0] = "."
    assert check_f821.main(args) == 2
    assert "source inventory changed" in report(output)["error"]


@pytest.mark.parametrize(
    "exception",
    [
        FileNotFoundError("tool absent"),
        subprocess.TimeoutExpired("tool", 30, b"partial", b"notice"),
    ],
)
def test_spawn_failure_or_timeout_preserves_evidence(scan, monkeypatch, exception):
    _, output = scan

    def fail(index, result, command, kwargs):
        raise exception

    fake_linter(monkeypatch, fail)
    assert check_f821.main(arguments(output)) == 2
    assert (output / "run-1.stdout").exists()
    assert report(output)["status"] == "ERROR"


def test_uv_launcher_pins_interpreter_without_sync(scan, monkeypatch):
    _, output = scan
    calls = fake_linter(monkeypatch)
    assert (
        check_f821.main(arguments(output, "--launcher", "uv", "--uv", "uv-fixture"))
        == 1
    )
    assert calls[0][:7] == [
        "uv-fixture",
        "run",
        "--no-project",
        "--no-sync",
        "--python",
        sys.executable,
        "python",
    ]


def test_overlapping_targets_are_scanned_once(scan, monkeypatch):
    _, output = scan
    calls = fake_linter(monkeypatch)
    assert check_f821.main(arguments(output, ".")) == 1
    assert calls[0].count("sample.py") == 1


@pytest.mark.parametrize("tool", ["flake8", "ruff"])
@pytest.mark.parametrize("clean", [False, True])
def test_real_tools_and_worked_example(scan, tool, clean):
    """missing_name at row 1, column 1 gives one F821; assignment gives zero.

    The excluded canary contributes one raw diagnostic in both cases, so each
    raw tool exits 1. Two identical observations have one unique inventory.
    """
    root, output = scan
    if clean:
        (root / "sample.py").write_text("missing_name = None\n")
    assert check_f821.main(arguments(output, "--tool", tool)) == (0 if clean else 1)
    evidence = report(output)
    assert evidence["status"] == "STABLE"
    assert [run["count"] for run in evidence["runs"]] == ([0, 0] if clean else [1, 1])
    assert len({run["findings_sha256"] for run in evidence["runs"]}) == 1


def test_repository_configuration_cannot_hide_findings(scan):
    root, output = scan
    (root / ".flake8").write_text("[flake8]\nignore = F821\nexclude = sample.py\n")
    assert check_f821.main(arguments(output)) == 1


def test_missing_or_empty_targets_fail_closed(scan):
    _, output = scan
    args = arguments(output)
    args[0] = "absent"
    assert check_f821.main(args) == 2
    assert report(output)["status"] == "ERROR"


def test_evidence_directory_cannot_be_inside_scan(scan):
    root, _ = scan
    output = root / "evidence"
    args = arguments(output)
    args[0] = "."
    with pytest.raises(SystemExit):
        check_f821.main(args)
    assert not output.exists()


def test_existing_evidence_is_never_overwritten(scan):
    _, output = scan
    output.mkdir()
    marker = output / "retained.txt"
    marker.write_text("original evidence\n")
    with pytest.raises(SystemExit):
        check_f821.main(arguments(output))
    assert marker.read_text() == "original evidence\n"


@pytest.mark.parametrize("tool", ["flake8", "ruff"])
def test_real_syntax_error_cannot_look_like_clean_f821_scan(scan, tool):
    root, output = scan
    (root / "sample.py").write_text("def broken(:\n")
    assert check_f821.main(arguments(output, "--tool", tool)) == 2
    assert report(output)["status"] == "ERROR"


@pytest.mark.parametrize(
    "option,value", [("--runs", "1"), ("--timeout", "0"), ("--timeout", "nan")]
)
def test_invalid_execution_inputs_create_no_evidence(scan, option, value):
    _, output = scan
    args = arguments(output)
    args[args.index(option) + 1] = value
    with pytest.raises(SystemExit):
        check_f821.main(args)
    assert not output.exists()


def test_failed_version_query_does_not_start_scans(scan, monkeypatch):
    _, output = scan

    def fail(command, **kwargs):
        assert "--version" in command
        return subprocess.CompletedProcess(command, 2, "", "version failed")

    monkeypatch.setattr(check_f821.subprocess, "run", fail)
    assert check_f821.main(arguments(output)) == 2
    assert report(output)["runs"] == []
    assert (output / "version.stderr").read_text() == "version failed"


@pytest.mark.parametrize("text", ["not json", "{}", '[{"code": "F821"}]'])
def test_malformed_ruff_json_is_rejected(scan, text):
    root, output = scan
    with pytest.raises(ValueError, match="unrecognized Ruff output"):
        check_f821.parse_findings("ruff", text, root, output / "scan_canary.py", {})


def test_workflow_adds_scan_without_replacing_existing_checks():
    """The inventory check is additive to the existing three lint commands."""
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    text = workflow.read_text()
    assert "python scripts/ci/check_f821.py" in text
    assert "uv run black --check --diff src/ tests/" in text
    assert "uv run isort --check-only --diff src/ tests/" in text
    assert "uv run flake8 src/" in text
