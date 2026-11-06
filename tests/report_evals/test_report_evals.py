"""Report evals: contract, comparison rules, run records and script identity.

The full well-permit eval needs network access for the BSEE files; the
scheduled report-eval job runs it.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

EVALS = Path(__file__).resolve().parents[2] / "examples" / "report-evals"
ALL = sorted(p.name for p in EVALS.iterdir() if (p / "results.json").exists())


def _kit():
    sys.path.insert(0, str(EVALS))
    import evalkit
    return evalkit


def _schema() -> dict:
    return json.loads((EVALS / "results.schema.json").read_text(encoding="utf-8"))


def _manifest(folder: str) -> dict:
    return json.loads((EVALS / folder / "results.json").read_text(encoding="utf-8"))


def _run(folder: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(EVALS / folder / "eval.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=600)


@pytest.mark.parametrize("folder", ALL)
def test_results_json_meets_contract(folder):
    """--validate-only checks the full schema with the standard library."""
    out = _run(folder, "--validate-only")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "valid against results.schema.json" in out.stdout


@pytest.mark.parametrize("folder", ALL)
def test_results_json_passes_jsonschema(folder):
    """Cross-check with the reference validator where it is installed."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(_schema())
    errors = [e.message for e in validator.iter_errors(_manifest(folder))]
    assert not errors, errors


@pytest.mark.parametrize("folder", ALL)
def test_last_run_is_bound_to_current_files(folder):
    records = sorted((EVALS / folder).glob("last-run*.json"))
    assert records, "no run record committed"
    for record in records:
        out = _run(folder, "--check-record", str(record))
        assert out.returncode == 0, (record.name, out.stdout)


@pytest.mark.parametrize("mutate, expected", [
    (lambda d: d.update(results=[]), "non-empty"),
    (lambda d: d["results"][0].update(tolerance={"abs": -1}), ">= 0"),
    (lambda d: d["report"].pop("title"), "title"),
    (lambda d: d["results"][0].update(scope="sometimes"), "scope"),
    (lambda d: d["results"].append(dict(d["results"][0])), "duplicate"),
])
def test_invalid_manifests_are_rejected(mutate, expected):
    kit = _kit()
    doc = copy.deepcopy(_manifest(ALL[0]))
    mutate(doc)
    errors = kit.validate(doc, _schema())
    assert errors and any(expected in e for e in errors), errors
    try:
        jsonschema = __import__("jsonschema")
    except ImportError:
        return
    if expected != "duplicate":  # JSON Schema cannot express unique ids
        assert list(jsonschema.Draft202012Validator(_schema()).iter_errors(doc))


def test_comparison_contract():
    kit = _kit()
    fixed = {"value": 10, "tolerance": {"abs": 0.5}, "basis": "fixed"}
    live = {"value": 200, "tolerance": {"rel_pct": 1.0}, "basis": "live"}
    zero = {"value": 0, "tolerance": {"rel_pct": 5.0}, "basis": "fixed"}
    flag = {"value": True, "tolerance": {"abs": 0}, "basis": "fixed"}
    assert kit.compare_one(fixed, 10.5)[0] == "MATCH"        # inclusive bound
    assert kit.compare_one(fixed, 10.51)[0] == "MISMATCH"
    assert kit.compare_one(live, 202)[0] == "MATCH"          # 1 % of 200, inclusive
    assert kit.compare_one(live, 202.1)[0] == "DRIFT"
    assert kit.compare_one(zero, 0)[0] == "MATCH"            # zero reference is exact
    assert kit.compare_one(zero, 0.001)[0] == "MISMATCH"
    assert kit.compare_one(zero, 5e-10)[0] == "MISMATCH"     # no floating allowance at zero
    big = {"value": 1_000_000_000, "tolerance": {"abs": 0}, "basis": "fixed"}
    assert kit.compare_one(big, 1_000_000_000)[0] == "MATCH"
    assert kit.compare_one(big, 1_000_000_001)[0] == "MISMATCH"  # integers compare exactly
    assert kit.compare_one(fixed, True)[0] == "MISMATCH"     # boolean for a number
    assert kit.compare_one(flag, 1)[0] == "MISMATCH"         # number for a boolean
    assert kit.compare_one(fixed, float("nan"))[0] == "MISMATCH"
    assert kit.compare_one(fixed, None)[0] == "NOT_EVALUATED"
    rows = [{"status": "MATCH"}, {"status": "NOT_EVALUATED"}, {"status": "MISMATCH"}]
    assert kit.grade(rows) == "FAIL" and kit.grade(rows[:2]) == "PARTIAL" and kit.grade([]) == "PARTIAL"


def _reader(tmp_path, name, items):
    path = tmp_path / name
    path.write_text(json.dumps({"results": items}), encoding="utf-8")
    return str(path)


def test_compare_mode(tmp_path):
    folder = ALL[0]
    graded = [r for r in _manifest(folder)["results"] if r.get("scope", "both") == "both"]
    full = [{"id": r["id"], "value": r["value"]} for r in graded]
    assert _run(folder, "--compare", _reader(tmp_path, "full.json", full)).returncode == 0
    assert _run(folder, "--compare", _reader(tmp_path, "empty.json", [])).returncode == 2
    assert _run(folder, "--compare", _reader(tmp_path, "part.json", full[:1])).returncode == 2
    dup = full + [full[0]]
    assert _run(folder, "--compare", _reader(tmp_path, "dup.json", dup)).returncode == 1
    extra = full + [{"id": "not_a_result", "value": 1}]
    assert _run(folder, "--compare", _reader(tmp_path, "extra.json", extra)).returncode == 1
    out = tmp_path / "odd.json"
    odd = _run(folder, "--compare", _reader(tmp_path, "odd-id.json", [{"id": [], "value": 1}]), "--out", str(out))
    assert odd.returncode == 1 and json.loads(out.read_text(encoding="utf-8"))["grade"] == "FAIL"


def _demo_folder(tmp_path):
    work = tmp_path / "evals" / "demo"
    work.mkdir(parents=True)
    (tmp_path / "evals" / "results.schema.json").write_text(json.dumps(_schema()), encoding="utf-8")
    (tmp_path / "evals" / "evalkit.py").write_text((EVALS / "evalkit.py").read_text(encoding="utf-8"),
                                                   encoding="utf-8")
    (work / "results.json").write_text(json.dumps(_manifest(ALL[0])), encoding="utf-8")
    (work / "eval.py").write_text("# demo\n", encoding="utf-8")
    (work / "PROMPT.md").write_text("demo\n", encoding="utf-8")
    return work


def test_failure_after_final_value_fails_the_run(tmp_path):
    """compute() that fills every value and then raises must not grade PASS."""
    kit = _kit()
    work = _demo_folder(tmp_path)
    results = _manifest(ALL[0])["results"]

    def compute(args, values, notes, context):
        for r in results:
            values[r["id"]] = r["value"]
        raise ValueError("failure after final value")

    out = tmp_path / "run.json"
    assert kit.main(work / "results.json", compute, argv=["--out", str(out)]) == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["grade"] == "FAIL" and any("failure after final value" in e for e in record["errors"])
    assert {r["status"] for r in record["results"]} == {"MATCH"}


def test_record_written_without_out(tmp_path):
    kit = _kit()
    work = _demo_folder(tmp_path)
    runs = Path(tempfile.gettempdir()) / "report-evals-runs"
    before = set(runs.glob("*.json")) if runs.exists() else set()
    kit.main(work / "results.json", lambda args, values, notes, context: None, argv=[])
    assert set(runs.glob("*.json")) - before


@pytest.mark.parametrize("mode, removed", [("rebuild", "eval.py"), ("prompt-level", "PROMPT.md"),
                                          ("rebuild", "../evalkit.py")])
def test_missing_bound_file_makes_record_stale(tmp_path, mode, removed):
    kit = _kit()
    work = _demo_folder(tmp_path)
    names = kit.PROMPT_ARTIFACTS if mode == "prompt-level" else kit.REBUILD_ARTIFACTS
    record = tmp_path / "record.json"
    record.write_text(json.dumps({"mode": mode, "artifacts": kit.artifacts(work, names)}), encoding="utf-8")
    assert kit.check_record(work, record) == []
    (work / removed).unlink()
    assert any("missing" in p for p in kit.check_record(work, record))


def test_failed_compute_still_writes_record(tmp_path):
    """An exception in compute() grades its results ERROR and the record is written."""
    kit = _kit()
    work = tmp_path / "evals" / "demo"
    work.mkdir(parents=True)
    (tmp_path / "evals" / "results.schema.json").write_text(json.dumps(_schema()), encoding="utf-8")
    (work / "results.json").write_text(json.dumps(_manifest(ALL[0])), encoding="utf-8")

    def compute(args, values, notes, context):
        values[_manifest(ALL[0])["results"][0]["id"]] = _manifest(ALL[0])["results"][0]["value"]
        raise OSError("network down")

    out = tmp_path / "run.json"
    assert kit.main(work / "results.json", compute, argv=["--out", str(out)]) == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["grade"] == "FAIL" and "network down" in record["context"]["compute_error"]
    assert record["results"][0]["status"] == "MATCH"
    assert {r["status"] for r in record["results"][1:]} == {"ERROR"}


def _wells_module():
    spec = importlib.util.spec_from_file_location("_wells_eval", EVALS / "issue-002-gom-well-permits" / "eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("revision", ["pinned", "candidate"])
def test_script_identity_by_revision(tmp_path, revision):
    """pinned: a changed copy is graded False. candidate: identity is not graded."""
    module = _wells_module()
    pin = _manifest("issue-002-gom-well-permits")["code"]["commit"]
    blob = module.evalkit.git_blob(EVALS.parents[1], pin, module.SCRIPT)
    if blob is None:
        pytest.skip("pinned commit not readable in this clone")
    changed = tmp_path / "count_rawdata.py"
    changed.write_bytes(blob + b"\n# changed\n")
    args = type("Args", (), {"repo_root": EVALS.parents[1], "script": changed, "cache": tmp_path,
                             "revision": revision})()
    values, notes, context = {}, {}, {}
    module.resolve_script(args, pin, values, notes, context)
    if revision == "pinned":
        assert values["script_matches_pinned_commit"] is False
    else:
        assert "script_matches_pinned_commit" not in values
        assert context["code_mode"] == "candidate"
