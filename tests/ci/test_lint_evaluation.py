"""Literal evidence exercises the evaluation contract without installed linters."""

import copy
import hashlib
import json
import subprocess
import sys

import pytest

from scripts.ci import summarize_lint_evaluation as evaluation


@pytest.fixture
def evidence():
    files = {"src/sample.py": hashlib.sha256(b"pass\n").hexdigest()}
    source = evaluation.digest(files)
    run = {
        "seconds": 1.0,
        "returncode": 0,
        "error": None,
        "before": source,
        "after": source,
        "probe": True,
        "findings": [],
    }
    return {
        "files": files,
        "unsupported_rules": [],
        "tools": {
            tool: {
                "version": "fixture 1.0",
                "files": files,
                "runs": [copy.deepcopy(run) for _ in range(5)],
            }
            for tool in evaluation.TOOLS
        },
    }


def finding(code="F401", row=1):
    return {
        "path": "src/sample.py",
        "row": row,
        "column": 1,
        "code": code,
        "message": "fixture diagnostic",
    }


def add_findings(evidence, tool, findings):
    for run in evidence["tools"][tool]["runs"]:
        run.update(findings=copy.deepcopy(findings), returncode=1)


def test_clean_reports_and_complete_timing(evidence):
    result = evaluation.summarize(evidence)
    assert result["parity"] == "MATCH"
    assert result["timing"]["combined_seconds"] == [2.0] * 5
    assert result["timing"]["under_30_seconds"] is True
    assert result["tools"]["black"]["seconds"] == [1.0] * 5
    assert result["tools"]["black"]["median_seconds"] == 1.0
    assert result["tools"]["black"]["maximum_seconds"] == 1.0
    assert result["tools"]["black"]["file_count"] == 1


def test_equal_counts_do_not_establish_parity(evidence):
    add_findings(evidence, "flake8", [finding()])
    add_findings(evidence, "ruff-check", [finding(row=2)])
    result = evaluation.summarize(evidence)
    assert result["parity"] == "DIFFERENT"
    assert result["lint_delta"]["legacy_only"] == [finding()]
    assert result["lint_delta"]["candidate_only"] == [finding(row=2)]
    assert result["tools"]["flake8"]["rules"] == {"F401": 1}


def test_legacy_import_diagnostic_cannot_disappear(evidence):
    add_findings(evidence, "flake8", [finding("I001")])
    with pytest.raises(ValueError, match="unexpected rule"):
        evaluation.summarize(evidence)


def test_import_and_formatter_deltas_are_separate(evidence):
    add_findings(evidence, "isort", [finding("FORMAT")])
    result = evaluation.summarize(evidence)
    assert result["parity"] == "DIFFERENT"
    assert result["import_delta"]["legacy_only"] == ["src/sample.py"]
    assert result["format_delta"]["legacy_only"] == []


def test_unmapped_rules_block_parity(evidence):
    evidence["unsupported_rules"] = ["W503"]
    assert evaluation.summarize(evidence)["parity"] == "BLOCKED"


def test_same_dirty_files_cannot_prove_equal_formatted_output(evidence):
    for tool in ("black", "ruff-format"):
        add_findings(evidence, tool, [finding("FORMAT")])
    assert evaluation.summarize(evidence)["parity"] == "UNVERIFIED"


def test_limit_uses_each_combined_observation_without_rounding(evidence):
    evidence["tools"]["ruff-check"]["runs"][0]["seconds"] = 29.00001
    result = evaluation.summarize(evidence)
    assert result["timing"]["under_30_seconds"] is False
    assert result["timing"]["maximum_seconds"] > 30


@pytest.mark.parametrize(
    "failure",
    [
        "exit",
        "timeout",
        "version",
        "digest",
        "inventory",
        "runs",
        "unstable",
        "nan",
        "negative",
        "boolean",
        "probe",
        "outside",
        "duplicate",
        "syntax",
        "exit-findings",
        "missing-tool",
        "absolute",
        "bad-hash",
        "bad-row",
        "missing-field",
        "bad-message",
        "wrong-family",
        "unsupported-shape",
    ],
)
def test_invalid_evidence_cannot_make_claims(evidence, failure):
    tool = evidence["tools"]["ruff-check"]
    run = tool["runs"][0]
    if failure == "exit":
        run["returncode"] = 2
    elif failure == "timeout":
        run["error"] = "command timed out"
    elif failure == "version":
        tool["version"] = " "
    elif failure == "digest":
        run["after"] = "0" * 64
    elif failure == "inventory":
        tool["files"] = {"tests/other.py": "0" * 64}
    elif failure == "runs":
        tool["runs"].pop()
    elif failure == "unstable":
        run.update(returncode=1, findings=[finding()])
    elif failure in ("nan", "negative", "boolean"):
        run["seconds"] = {"nan": float("nan"), "negative": -1, "boolean": True}[failure]
    elif failure == "probe":
        run["probe"] = False
    elif failure in (
        "outside",
        "duplicate",
        "syntax",
        "bad-row",
        "bad-message",
        "wrong-family",
    ):
        item = finding()
        if failure == "outside":
            item["path"] = "unrequested.py"
        elif failure == "syntax":
            item["code"] = "E999"
        elif failure == "bad-row":
            item["row"] = True
        elif failure == "bad-message":
            item["message"] = None
        elif failure == "wrong-family":
            item["code"] = "B001"
        run.update(returncode=1, findings=[item] * (2 if failure == "duplicate" else 1))
    elif failure == "exit-findings":
        run["returncode"] = 1
    elif failure == "missing-tool":
        del evidence["tools"]["black"]
    elif failure == "absolute":
        evidence["files"] = {"/sample.py": "0" * 64}
    elif failure == "bad-hash":
        evidence["files"]["src/sample.py"] = "unknown"
    elif failure == "missing-field":
        del run["findings"]
    else:
        evidence["unsupported_rules"] = "W503"
    with pytest.raises(ValueError):
        evaluation.summarize(evidence)


@pytest.mark.parametrize("raw", ["not JSON", "{}", "[]", "null"])
def test_cli_invalid_json_writes_error_without_passing_claims(tmp_path, raw):
    source, output = tmp_path / "input.json", tmp_path / "summary.json"
    source.write_text(raw)
    assert evaluation.main([str(source), str(output)]) == 2
    result = json.loads(output.read_text())
    assert result["status"] == "ERROR"
    assert result["parity"] == "UNVERIFIED"
    assert result["timing"] is None


def test_cli_retains_valid_deltas(tmp_path, evidence):
    source, output = tmp_path / "input.json", tmp_path / "summary.json"
    source.write_text(json.dumps(evidence))
    assert evaluation.main([str(source), str(output)]) == 0
    assert json.loads(output.read_text())["parity"] == "MATCH"


@pytest.mark.parametrize("scope", ["top", "inventory", "tool", "run", "finding"])
def test_cli_duplicate_json_keys_cannot_make_claims(tmp_path, evidence, scope):
    raw = json.dumps(evidence)
    if scope == "top":
        entry = '"unsupported_rules": []'
        raw = raw.replace(entry, entry + ", " + entry, 1)
    elif scope == "inventory":
        entry = (
            json.dumps("src/sample.py")
            + ": "
            + json.dumps(evidence["files"]["src/sample.py"])
        )
        raw = raw.replace(entry, entry + ", " + entry, 1)
    elif scope == "tool":
        raw = raw.replace(
            '"version": "fixture 1.0"',
            '"version": "old", "version": "fixture 1.0"',
            1,
        )
    elif scope == "run":
        # A last-value-wins decoder would erase all five legacy findings.
        raw = raw.replace('"returncode": 0', '"returncode": 1, "returncode": 0', 5)
        raw = raw.replace(
            '"findings": []',
            '"findings": ' + json.dumps([finding()]) + ', "findings": []',
            5,
        )
    else:
        add_findings(evidence, "flake8", [finding()])
        raw = json.dumps(evidence).replace('"row": 1', '"row": 2, "row": 1', 1)
    source, output = tmp_path / "input.json", tmp_path / "summary.json"
    source.write_text(raw)
    assert evaluation.main([str(source), str(output)]) == 2
    result = json.loads(output.read_text())
    assert result["status"] == "ERROR"
    assert result["parity"] == "UNVERIFIED"
    assert result["timing"] is None


@pytest.mark.parametrize("tool", ["black", "isort", "ruff-format"])
@pytest.mark.parametrize("coordinate", ["row", "column"])
def test_formatter_requires_whole_file_location(evidence, tool, coordinate):
    item = finding("FORMAT")
    item[coordinate] = 2
    add_findings(evidence, tool, [item])
    with pytest.raises(ValueError, match="formatter location"):
        evaluation.summarize(evidence)


@pytest.mark.parametrize("tool", ["black", "isort", "ruff-format"])
def test_formatter_path_cannot_count_twice(evidence, tool):
    first = finding("FORMAT")
    second = dict(first, message="another notice for the same file")
    add_findings(evidence, tool, [first, second])
    with pytest.raises(ValueError, match="duplicate formatter path"):
        evaluation.summarize(evidence)


@pytest.mark.parametrize("tool", ["black", "isort", "ruff-format"])
def test_formatter_distinct_paths_remain_valid_across_runs(evidence, tool):
    evidence["files"]["tests/other.py"] = hashlib.sha256(b"pass\n").hexdigest()
    source = evaluation.digest(evidence["files"])
    for record in evidence["tools"].values():
        for run in record["runs"]:
            run.update(before=source, after=source)
    first = finding("FORMAT")
    second = dict(first, path="tests/other.py")
    add_findings(evidence, tool, [first, second])
    result = evaluation.summarize(evidence)
    assert result["tools"][tool]["rules"] == {"FORMAT": 2}
    assert len(result["tools"][tool]["findings"]) == 2


@pytest.mark.parametrize("seconds", [10**400, 1e308], ids=["huge-int", "sum-overflow"])
def test_unrepresentable_timing_rejected(evidence, seconds):
    for name in ("ruff-check", "ruff-format"):
        for run in evidence["tools"][name]["runs"]:
            run["seconds"] = seconds
    with pytest.raises(ValueError, match="duration|combined"):
        evaluation.summarize(evidence)


@pytest.mark.parametrize("seconds", [10**400, 1e308], ids=["huge-int", "sum-overflow"])
def test_cli_timing_overflow_writes_error_report(tmp_path, evidence, seconds):
    for name in ("ruff-check", "ruff-format"):
        for run in evidence["tools"][name]["runs"]:
            run["seconds"] = seconds
    source, output = tmp_path / "input.json", tmp_path / "summary.json"
    source.write_text(json.dumps(evidence))
    assert evaluation.main([str(source), str(output)]) == 2
    result = json.loads(output.read_text())
    assert result["status"] == "ERROR"
    assert result["parity"] == "UNVERIFIED"
    assert result["timing"] is None


@pytest.mark.parametrize(
    "alias",
    ["same", "relative", "parent", "input-symlink", "output-symlink", "hardlink"],
)
@pytest.mark.parametrize("valid", [True, False], ids=["valid", "malformed"])
def test_cli_rejects_input_alias_without_changing_evidence(
    tmp_path, evidence, alias, valid
):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(evidence) if valid else "not JSON", encoding="utf-8")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    original = source
    output = source
    if alias == "relative":
        output = source.relative_to(tmp_path)
    elif alias == "parent":
        (tmp_path / "nested").mkdir()
        output = tmp_path / "nested" / ".." / source.name
    elif alias == "input-symlink":
        source = tmp_path / "input-link.json"
        source.symlink_to(original.name)
    elif alias == "output-symlink":
        output = tmp_path / "output-link.json"
        output.symlink_to(source.name)
    elif alias == "hardlink":
        output = tmp_path / "output-link.json"
        output.hardlink_to(source)
    result = subprocess.run(
        [sys.executable, str(evaluation.__file__), str(source), str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "output must not overwrite evidence" in result.stderr
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert hashlib.sha256((tmp_path / output).read_bytes()).hexdigest() == before
    if alias == "input-symlink":
        assert source.is_symlink()
    elif alias == "output-symlink":
        assert output.is_symlink()
