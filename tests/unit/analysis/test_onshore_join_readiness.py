"""Synthetic join arithmetic; expected counts are derived in each test."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from worldenergydata.analysis.onshore_join_readiness import audit, normalize_api


def dataset(name, state="TX", **changes):
    entry = {
        "id": name,
        "source_id": "wellbore_query",
        "source_version": "synthetic-fixture",
        "state": state,
        "domain": "wells",
        "path": f"{name}.csv",
        "status": "downloaded",
        "keys": {"api14": "api14"},
        "unique": True,
    }
    return entry | changes


def config(*entries, joins=None, artifacts=None):
    return {
        "datasets": list(entries),
        "joins": joins or [],
        "artifacts": artifacts or [],
    }


@pytest.mark.parametrize(
    "state,raw,expected",
    [
        ("TX", "42-001-00001-00-00", "42001000010000"),
        ("KS", "15-001-00001", "1500100001"),
        ("OK", "3500100001", "3500100001"),
        ("CO", "05-001-00001-00", "050010000100"),
        ("TX", "00100001", None),
        ("TX", "1500100001", None),
        ("CO", "5.001E+09", None),
        ("CO", "0500100001.0", None),
        ("KS", "API1500100001", None),
        ("OK", "", None),
        ("TX", "４２００１００００１", None),
    ],
)
def test_api_shapes(state, raw, expected):
    """Literal digit concatenation; no suffix padding or truncation is allowed."""
    assert normalize_api(raw, state) == expected


def test_audit_reports_nulls_duplicates_digest_and_no_payload(tmp_path):
    """Four rows: two equal keys, one blank, one wrong-state API.

    Valid=2; invalid=2; distinct valid keys=1; duplicate excess=2-1=1.
    """
    raw = b"api14,private_note\n42001000010000,hidden\n42001000010000,x\n,y\n15001000010000,z\n"
    (tmp_path / "wells.csv").write_bytes(raw)
    result = audit(config(dataset("wells")), tmp_path)
    observed = result["datasets"][0]
    assert observed["rows"] == 4
    assert observed["invalid_key_rows"] == 2
    assert observed["duplicate_key_rows"] == 1
    assert observed["sha256"] == hashlib.sha256(raw).hexdigest()
    assert observed["join_status"] == "FAIL"
    assert "hidden" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)


def test_many_to_one_join_counts_and_unmatched(tmp_path):
    """Left A,A,B,C versus right A,B: matched=3, unmatched=1, inner rows=3.

    Left join rows = 2*1 + 1*1 + 1*1 = 4, with no multiplication.
    """
    (tmp_path / "tests.csv").write_text(
        "api14\n42001000010000\n42001000010000\n42001000020000\n42001000030000\n"
    )
    (tmp_path / "wells.csv").write_text("api14\n42001000010000\n42001000020000\n")
    join = {"left": "tests", "right": "wells", "on": ["api14"]}
    result = audit(
        config(dataset("tests", unique=False), dataset("wells"), joins=[join]), tmp_path
    )
    assert result["joins"] == [
        {
            **join,
            "join_status": "FAIL",
            "matched_left_rows": 3,
            "unmatched_left_rows": 1,
            "inner_join_rows": 3,
            "left_join_rows": 4,
            "right_duplicate_keys": 0,
            "reason": "unmatched_left_keys",
        }
    ]


def test_duplicate_dimension_prevents_fanout(tmp_path):
    """Two left A and three right A produce 2*3=6 joined rows, not 2."""
    (tmp_path / "left.csv").write_text("id\nA\nA\n")
    (tmp_path / "right.csv").write_text("id\nA\nA\nA\n")
    entries = [
        dataset(n, keys={"well_kid": "id"}, unique=False) for n in ("left", "right")
    ]
    result = audit(
        config(
            *entries, joins=[{"left": "left", "right": "right", "on": ["well_kid"]}]
        ),
        tmp_path,
    )
    join = result["joins"][0]
    assert join["inner_join_rows"] == 6
    assert join["right_duplicate_keys"] == 1
    assert join["join_status"] == "FAIL"
    assert join["reason"] == "right_key_not_unique"


def test_kansas_kid_is_not_api_and_is_namespaced(tmp_path):
    """An exact KID match joins once within Kansas, never across states."""
    for name in ("left", "right"):
        (tmp_path / f"{name}.csv").write_text("KID\n0007\n")
    entries = [dataset(n, "KS", keys={"well_kid": "KID"}) for n in ("left", "right")]
    join = {"left": "left", "right": "right", "on": ["well_kid"]}
    assert (
        audit(config(*entries, joins=[join]), tmp_path)["joins"][0]["join_status"]
        == "PASS"
    )
    entries[1]["state"] = "TX"
    with pytest.raises(ValueError, match="same state"):
        audit(config(*entries, joins=[join]), tmp_path)


@pytest.mark.parametrize(
    "status", ["configured-only", "partial/error", "missing", "private/legacy"]
)
def test_unusable_inventory_states_do_not_open_files(tmp_path, status):
    result = audit(config(dataset("unavailable", status=status)), tmp_path)
    assert result["datasets"][0]["join_status"] == "NOT_EVALUATED"
    assert result["datasets"][0]["inventory_status"] == status


@pytest.mark.parametrize(
    "content,reason",
    [
        ("api14\n", "empty_table"),
        ("wrong\nvalue\n", "missing_key_columns"),
        ("api14,api14\na,b\n", "duplicate_columns"),
        ("api14\na,b\n", "malformed_rows"),
    ],
)
def test_bad_tables_fail_closed(tmp_path, content, reason):
    (tmp_path / "wells.csv").write_text(content)
    observed = audit(config(dataset("wells")), tmp_path)["datasets"][0]
    assert observed["join_status"] != "PASS"
    assert observed["reason"] == reason


def test_missing_file_and_missing_join_are_not_evaluated(tmp_path):
    result = audit(
        config(
            dataset("left"),
            dataset("right"),
            joins=[{"left": "left", "right": "right", "on": ["api14"]}],
        ),
        tmp_path,
    )
    assert result["datasets"][0]["inventory_status"] == "missing"
    assert result["joins"][0]["join_status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("path", ["../outside.csv", "nested/../../outside.csv"])
def test_no_path_escape(tmp_path, path):
    with pytest.raises(ValueError, match="relative path within"):
        audit(config(dataset("wells", path=path)), tmp_path)


def test_no_absolute_path_or_symlink_escape(tmp_path):
    with pytest.raises(ValueError, match="relative path within"):
        audit(config(dataset("wells", path=str(tmp_path / "x.csv"))), tmp_path)
    (tmp_path / "link.csv").symlink_to(tmp_path.parent / "outside.csv")
    with pytest.raises(ValueError, match="relative path within"):
        audit(config(dataset("wells", path="link.csv")), tmp_path)


def test_completion_error_with_zip_is_flagged_without_repair(tmp_path):
    """One valid ZIP with an error manifest is conflicting evidence, not success."""
    with zipfile.ZipFile(tmp_path / "completion.zip", "w") as archive:
        archive.writestr("sample.txt", "synthetic")
    manifest = {"source_id": "completion_data", "status": "error"}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    artifact = {
        "source_id": "completion_data",
        "path": "completion.zip",
        "manifest": "manifest.json",
    }
    observed = audit(config(artifacts=[artifact]), tmp_path)["artifacts"][0]
    assert observed["reason"] == "manifest_error_with_raw_zip"
    assert observed["join_status"] == "NOT_EVALUATED"
    assert observed["zip_present"] is True
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest


def test_parquet_has_same_key_arithmetic(tmp_path):
    """Two equal API rows in Parquet have one duplicate excess, as for CSV."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    pq.write_table(
        pa.table({"api14": ["42001000010000", "42001000010000"]}),
        tmp_path / "wells.parquet",
    )
    result = audit(config(dataset("wells", path="wells.parquet")), tmp_path)
    assert result["datasets"][0]["duplicate_key_rows"] == 1


def test_cli_worked_example(tmp_path):
    """Fixture: three observations match two unique wells; 3*1=3 inner rows."""
    example = Path("examples/onshore-joins")
    output = tmp_path / "audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.analysis.onshore_join_readiness",
            "--config",
            str(example / "input.json"),
            "--root",
            str(example),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text())
    assert result["joins"][0]["inner_join_rows"] == 3
    assert result["joins"][0]["join_status"] == "PASS"
    assert result["intended_use"] == "structural_join_audit_only"


@pytest.mark.parametrize(
    "change",
    [
        {"state": "XX"},
        {"keys": {}},
        {"unique": "false"},
        {"status": "ready"},
        {"source_version": ""},
        {"source_id": ""},
    ],
)
def test_invalid_contract_rejected(tmp_path, change):
    with pytest.raises((ValueError, TypeError)):
        audit(config(dataset("wells", **change)), tmp_path)


def test_duplicate_dataset_ids_rejected(tmp_path):
    with pytest.raises(ValueError, match="unique"):
        audit(config(dataset("wells"), dataset("wells")), tmp_path)


def test_projection_detects_duplicate_coarse_dimension(tmp_path):
    """Distinct events (A,Jan), (A,Feb) still repeat A on a well-only join.

    One left A times two right A produces two inner rows and fails cardinality.
    """
    (tmp_path / "left.csv").write_text("id\nA\n")
    (tmp_path / "right.csv").write_text("id,month\nA,Jan\nA,Feb\n")
    left = dataset("left", keys={"well_kid": "id"})
    right = dataset("right", keys={"well_kid": "id", "month": "month"})
    result = audit(
        config(
            left, right, joins=[{"left": "left", "right": "right", "on": ["well_kid"]}]
        ),
        tmp_path,
    )
    assert result["datasets"][1]["join_status"] == "PASS"
    assert result["joins"][0]["inner_join_rows"] == 2
    assert result["joins"][0]["join_status"] == "FAIL"


def test_composite_join_uses_names_not_column_order(tmp_path):
    """The tuple (district=01,field=007) matches once despite reversed maps."""
    (tmp_path / "left.csv").write_text("d,f\n01,007\n")
    (tmp_path / "right.csv").write_text("f,d\n007,01\n")
    left = dataset("left", keys={"district": "d", "field": "f"})
    right = dataset("right", keys={"field": "f", "district": "d"})
    result = audit(
        config(
            left,
            right,
            joins=[{"left": "left", "right": "right", "on": ["district", "field"]}],
        ),
        tmp_path,
    )
    assert result["joins"][0]["matched_left_rows"] == 1
    assert result["joins"][0]["join_status"] == "PASS"


def test_api_grain_is_never_inferred(tmp_path):
    """A complete API10 cannot satisfy an API14 declaration by invented zeros."""
    (tmp_path / "wells.csv").write_text("api14\n4200100001\n")
    assert (
        audit(config(dataset("wells")), tmp_path)["datasets"][0]["invalid_key_rows"]
        == 1
    )


def test_parquet_numeric_keys_are_rejected(tmp_path):
    """Numeric identifiers lack the string identity contract, even if integral."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    pq.write_table(pa.table({"id": [7]}), tmp_path / "wells.parquet")
    result = audit(
        config(dataset("wells", path="wells.parquet", keys={"well_kid": "id"})),
        tmp_path,
    )
    assert result["datasets"][0]["invalid_key_rows"] == 1
    assert result["datasets"][0]["join_status"] == "FAIL"


@pytest.mark.parametrize(
    "content,reason",
    [
        ("not-json", "manifest_unavailable"),
        ("[]", "manifest_source_mismatch"),
        ('{"source_id":"other"}', "manifest_source_mismatch"),
        (
            '{"source_id":"completion_data","status":"success"}',
            "raw_zip_missing_or_invalid",
        ),
    ],
)
def test_artifact_cannot_promote_missing_or_mismatched_evidence(
    tmp_path, content, reason
):
    (tmp_path / "manifest.json").write_text(content)
    artifact = {
        "source_id": "completion_data",
        "path": "missing.zip",
        "manifest": "manifest.json",
    }
    result = audit(config(artifacts=[artifact]), tmp_path)["artifacts"][0]
    assert result["reason"] == reason
    assert result["join_status"] == "NOT_EVALUATED"


def test_existing_report_cannot_be_overwritten(tmp_path):
    """The selected report already contains evidence; it must remain intact."""
    output = tmp_path / "existing.json"
    output.write_text("preserved")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.analysis.onshore_join_readiness",
            "--config",
            "examples/onshore-joins/input.json",
            "--root",
            "examples/onshore-joins",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert output.read_text() == "preserved"


@pytest.mark.parametrize("extension", ["csv", "parquet"])
def test_mixed_state_rows_are_not_relabelled(tmp_path, extension):
    """Two equal KIDs have different state evidence: only the Kansas row is valid."""
    path = tmp_path / f"wells.{extension}"
    if extension == "csv":
        path.write_text("id,state\n0007,KS\n0007,TX\n")
    else:
        import pyarrow as pa
        import pyarrow.parquet as pq

        pq.write_table(pa.table({"id": ["0007", "0007"], "state": ["KS", "TX"]}), path)
    entry = dataset("wells", "KS", path=path.name, keys={"well_kid": "id"})
    result = audit(config(entry), tmp_path)["datasets"][0]
    assert result["invalid_key_rows"] == 1
    assert result["distinct_keys"] == 1
    assert result["join_status"] == "FAIL"
