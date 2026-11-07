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
    return subprocess.run(
        [sys.executable, str(EVALS / folder / "eval.py"), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )


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


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda d: d.update(results=[]), "non-empty"),
        (lambda d: d["results"][0].update(tolerance={"abs": -1}), ">= 0"),
        (lambda d: d["report"].pop("title"), "title"),
        (lambda d: d["results"][0].update(scope="sometimes"), "scope"),
        (lambda d: d["results"].append(dict(d["results"][0])), "duplicate"),
    ],
)
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
    boundary = {"value": 100, "tolerance": {"rel_pct": 29}, "basis": "fixed"}
    assert kit.compare_one(boundary, 129)[0] == "MATCH"
    assert kit.compare_one(boundary, 129.0)[0] == "MATCH"
    assert kit.compare_one(boundary, 130)[0] == "MISMATCH"
    huge = {"value": 10**18, "tolerance": {"abs": 0}, "basis": "fixed"}
    assert kit.compare_one(huge, 10**18 + 1)[0] == "MISMATCH"
    fixed = {"value": 10, "tolerance": {"abs": 0.5}, "basis": "fixed"}
    live = {"value": 200, "tolerance": {"rel_pct": 1.0}, "basis": "live"}
    zero = {"value": 0, "tolerance": {"rel_pct": 5.0}, "basis": "fixed"}
    flag = {"value": True, "tolerance": {"abs": 0}, "basis": "fixed"}
    assert kit.compare_one(fixed, 10.5)[0] == "MATCH"  # inclusive bound
    assert kit.compare_one(fixed, 10.51)[0] == "MISMATCH"
    assert kit.compare_one(live, 202)[0] == "MATCH"  # 1 % of 200, inclusive
    assert kit.compare_one(live, 202.1)[0] == "DRIFT"
    assert kit.compare_one(zero, 0)[0] == "MATCH"  # zero reference is exact
    assert kit.compare_one(zero, 0.001)[0] == "MISMATCH"
    assert (
        kit.compare_one(zero, 5e-10)[0] == "MISMATCH"
    )  # no floating allowance at zero
    big = {"value": 1_000_000_000, "tolerance": {"abs": 0}, "basis": "fixed"}
    assert kit.compare_one(big, 1_000_000_000)[0] == "MATCH"
    assert (
        kit.compare_one(big, 1_000_000_001)[0] == "MISMATCH"
    )  # integers compare exactly
    assert kit.compare_one(fixed, True)[0] == "MISMATCH"  # boolean for a number
    assert kit.compare_one(flag, 1)[0] == "MISMATCH"  # number for a boolean
    assert kit.compare_one(fixed, float("nan"))[0] == "MISMATCH"
    assert kit.compare_one(fixed, None)[0] == "NOT_EVALUATED"
    rows = [{"status": "MATCH"}, {"status": "NOT_EVALUATED"}, {"status": "MISMATCH"}]
    assert (
        kit.grade(rows) == "FAIL"
        and kit.grade(rows[:2]) == "PARTIAL"
        and kit.grade([]) == "PARTIAL"
    )


def _reader(tmp_path, name, items):
    path = tmp_path / name
    path.write_text(json.dumps({"results": items}), encoding="utf-8")
    return str(path)


def test_compare_mode(tmp_path):
    folder = ALL[0]
    graded = [
        r for r in _manifest(folder)["results"] if r.get("scope", "both") == "both"
    ]
    full = [{"id": r["id"], "value": r["value"]} for r in graded]
    assert (
        _run(folder, "--compare", _reader(tmp_path, "full.json", full)).returncode == 0
    )
    assert (
        _run(folder, "--compare", _reader(tmp_path, "empty.json", [])).returncode == 2
    )
    assert (
        _run(folder, "--compare", _reader(tmp_path, "part.json", full[:1])).returncode
        == 2
    )
    dup = full + [full[0]]
    assert _run(folder, "--compare", _reader(tmp_path, "dup.json", dup)).returncode == 1
    extra = full + [{"id": "not_a_result", "value": 1}]
    assert (
        _run(folder, "--compare", _reader(tmp_path, "extra.json", extra)).returncode
        == 1
    )
    out = tmp_path / "odd.json"
    odd = _run(
        folder,
        "--compare",
        _reader(tmp_path, "odd-id.json", [{"id": [], "value": 1}]),
        "--out",
        str(out),
    )
    assert (
        odd.returncode == 1
        and json.loads(out.read_text(encoding="utf-8"))["grade"] == "FAIL"
    )


def _demo_folder(tmp_path):
    work = tmp_path / "evals" / "demo"
    work.mkdir(parents=True)
    (tmp_path / "evals" / "results.schema.json").write_text(
        json.dumps(_schema()), encoding="utf-8"
    )
    (tmp_path / "evals" / "evalkit.py").write_text(
        (EVALS / "evalkit.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
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
    assert record["grade"] == "FAIL" and any(
        "failure after final value" in e for e in record["errors"]
    )
    assert {r["status"] for r in record["results"]} == {"MATCH"}


def test_record_written_without_out(tmp_path, monkeypatch):
    kit = _kit()
    monkeypatch.setattr(kit.tempfile, "gettempdir", lambda: str(tmp_path))
    work = _demo_folder(tmp_path)
    runs = Path(tempfile.gettempdir()) / "report-evals-runs"
    before = set(runs.glob("*.json")) if runs.exists() else set()
    kit.main(work / "results.json", lambda args, values, notes, context: None, argv=[])
    assert set(runs.glob("*.json")) - before


@pytest.mark.parametrize(
    "mode, removed",
    [
        ("rebuild", "eval.py"),
        ("prompt-level", "PROMPT.md"),
        ("rebuild", "../evalkit.py"),
    ],
)
def test_missing_bound_file_makes_record_stale(tmp_path, mode, removed):
    kit = _kit()
    work = _demo_folder(tmp_path)
    names = kit.PROMPT_ARTIFACTS if mode == "prompt-level" else kit.REBUILD_ARTIFACTS
    record = tmp_path / "record.json"
    record.write_text(
        json.dumps({"mode": mode, "artifacts": kit.artifacts(work, names)}),
        encoding="utf-8",
    )
    assert kit.check_record(work, record) == []
    (work / removed).unlink()
    assert any("missing" in p for p in kit.check_record(work, record))


def test_failed_compute_still_writes_record(tmp_path):
    """An exception in compute() grades its results ERROR and the record is written."""
    kit = _kit()
    work = tmp_path / "evals" / "demo"
    work.mkdir(parents=True)
    (tmp_path / "evals" / "results.schema.json").write_text(
        json.dumps(_schema()), encoding="utf-8"
    )
    (work / "results.json").write_text(json.dumps(_manifest(ALL[0])), encoding="utf-8")

    def compute(args, values, notes, context):
        values[_manifest(ALL[0])["results"][0]["id"]] = _manifest(ALL[0])["results"][0][
            "value"
        ]
        raise OSError("network down")

    out = tmp_path / "run.json"
    assert kit.main(work / "results.json", compute, argv=["--out", str(out)]) == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert (
        record["grade"] == "FAIL"
        and "network down" in record["context"]["compute_error"]
    )
    assert record["results"][0]["status"] == "MATCH"
    assert {r["status"] for r in record["results"][1:]} == {"ERROR"}


def test_same_second_runs_keep_both_records(tmp_path, monkeypatch):
    """Two runs started in the same second write two records; neither replaces the other."""
    kit = _kit()
    work = _demo_folder(tmp_path)
    monkeypatch.setattr(kit.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(kit, "utc_now", lambda: "2026-11-06T12:00:00Z")
    results = _manifest(ALL[0])["results"]

    def failing(args, values, notes, context):
        raise ValueError("first run fails")

    def passing(args, values, notes, context):
        for r in results:
            values[r["id"]] = r["value"]

    runs = Path(tempfile.gettempdir()) / "report-evals-runs"
    before = set(runs.glob("*.json")) if runs.exists() else set()
    assert kit.main(work / "results.json", failing, argv=[]) == 1
    kit.main(work / "results.json", passing, argv=[])
    new = set(runs.glob("*.json")) - before
    grades = sorted(json.loads(p.read_text(encoding="utf-8"))["grade"] for p in new)
    assert len(new) == 2 and grades[0] == "FAIL", grades


def test_offline_blob_lookup_never_fetches(tmp_path, monkeypatch):
    """A pinned blob missing from the clone is unavailable offline; git fetch is not run."""
    kit = _kit()
    calls = []
    real_run = kit.subprocess.run

    def recording_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(kit.subprocess, "run", recording_run)
    assert kit.git_blob(EVALS.parents[1], "0" * 40, "README.md", fetch=False) is None
    assert calls and not any("fetch" in c for c in calls)
    args = type(
        "Args",
        (),
        {
            "repo_root": EVALS.parents[1],
            "pinned_commit": "0" * 40,
            "revision": "pinned",
            "offline": True,
        },
    )()
    with pytest.raises(FileNotFoundError):
        kit.repo_file(args, "README.md")
    assert not any("fetch" in c for c in calls)


def _wells_module():
    spec = importlib.util.spec_from_file_location(
        "_wells_eval", EVALS / "issue-002-gom-well-permits" / "eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("revision", ["pinned", "candidate"])
def test_script_identity_by_revision(tmp_path, revision):
    """pinned: a changed copy is graded False. candidate: identity is not graded."""
    module = _wells_module()
    # A local fixture repository supplies committed bytes without fetching a remote pin.
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "fetch", "-q", str(EVALS.parents[1]), "HEAD"],
        check=True,
    )
    pin = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "FETCH_HEAD"], text=True
    ).strip()
    # Identity checking is independent of the script's filename or executable behavior.
    module.SCRIPT = "examples/report-evals/issue-002-gom-well-permits/eval.py"
    blob = module.evalkit.git_blob(repo, pin, module.SCRIPT, fetch=False)
    assert blob is not None
    changed = tmp_path / "count_rawdata.py"
    changed.write_bytes(blob + b"\n# changed\n")
    args = type(
        "Args",
        (),
        {
            "repo_root": repo,
            "script": changed,
            "cache": tmp_path,
            "revision": revision,
        },
    )()
    values, notes, context = {}, {}, {}
    module.resolve_script(args, pin, values, notes, context)
    if revision == "pinned":
        assert values["script_matches_pinned_commit"] is False
    else:
        assert "script_matches_pinned_commit" not in values
        assert context["code_mode"] == "candidate"


@pytest.mark.parametrize("revision, code", [("candidate", 0), ("pinned", 2)])
def test_identity_is_graded_only_when_pinned(tmp_path, revision, code):
    """With every count matching, a candidate run can PASS; a pinned run also needs the identity result."""
    module = _wells_module()
    results = _manifest("issue-002-gom-well-permits")["results"]

    def counts_only(args, values, notes, context):
        for r in results:
            if r["id"] != "script_matches_pinned_commit":
                values[r["id"]] = r["value"]

    out = tmp_path / "run.json"
    got = module.evalkit.main(
        EVALS / "issue-002-gom-well-permits" / "results.json",
        counts_only,
        module.add_args,
        argv=["--revision", revision, "--out", str(out)],
    )
    assert got == code
    ids = {r["id"] for r in json.loads(out.read_text(encoding="utf-8"))["results"]}
    assert ("script_matches_pinned_commit" in ids) == (revision == "pinned")


@pytest.mark.parametrize("entry", [None, 3, "invalid", []])
def test_non_object_result_is_rejected(entry):
    doc = copy.deepcopy(_manifest(ALL[0]))
    doc["results"][0] = entry
    assert _kit().validate(doc, _schema())


def test_unreadable_pin_is_candidate(tmp_path, monkeypatch):
    module = _wells_module()
    monkeypatch.setattr(module.evalkit, "git_blob", lambda *args, **kwargs: None)
    script = tmp_path / "count_rawdata.py"
    script.write_text("# fixture\n", encoding="utf-8")
    args = type(
        "Args",
        (),
        {
            "revision": "pinned",
            "repo_root": tmp_path,
            "script": script,
            "cache": tmp_path,
        },
    )()
    values, notes, context = {}, {}, {}
    assert module.resolve_script(args, "0" * 40, values, notes, context) == script
    assert context["code_mode"] == "candidate"
    assert "script_matches_pinned_commit" not in values


@pytest.mark.parametrize(
    "failure",
    ["RemoteDisconnected", "IncompleteRead", "ConnectionResetError", "SSLError"],
)
def test_download_failures_are_unavailable(failure):
    module = _wells_module()
    cmd = [
        sys.executable,
        "-c",
        f"import sys; sys.stderr.write('{failure}'); sys.exit(1)",
    ]
    with pytest.raises(OSError, match="BSEE download failed"):
        module._run(cmd, timeout=10)


def test_pinned_files_are_isolated(tmp_path, monkeypatch):
    kit = _kit()
    monkeypatch.setattr(kit.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(kit, "git_blob", lambda *args, **kwargs: b"# fixture\n")

    def args():
        return type(
            "Args",
            (),
            {"revision": "pinned", "repo_root": tmp_path, "pinned_commit": "0" * 40},
        )()

    first, second = args(), args()
    path = kit.repo_file(first, "code/script.py")
    neighbor = kit.repo_file(first, "code/data.json")
    other = kit.repo_file(second, "code/script.py")
    assert path.parent == neighbor.parent
    assert path != other


def test_resolved_scripts_are_isolated(tmp_path, monkeypatch):
    module = _wells_module()
    monkeypatch.setattr(
        module.evalkit, "git_blob", lambda *args, **kwargs: b"# fixture\n"
    )
    args = type(
        "Args",
        (),
        {
            "revision": "pinned",
            "repo_root": tmp_path,
            "script": None,
            "cache": tmp_path,
        },
    )()
    first = module.resolve_script(args, "0" * 40, {}, {}, {})
    second = module.resolve_script(args, "0" * 40, {}, {}, {})
    assert first != second
    assert first.read_bytes() == second.read_bytes() == b"# fixture\n"


def test_record_reports_dirty_artifacts(tmp_path):
    kit = _kit()
    work = _demo_folder(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    out = tmp_path / "record.json"
    kit.main(work / "results.json", lambda *args: None, argv=["--out", str(out)])
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["context"]["artifacts_dirty"] is True
