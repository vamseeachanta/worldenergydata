"""Frozen provenance contract and offline publication examples for issue #1633."""

import hashlib
import importlib.util
import json
import socket
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
VINTAGE = REPO / "docs/modules/bsee/analysis/production/FDAS_V30"
SIDECAR = VINTAGE / "drilling_and_completion_days.provenance.json"


def load_builder():
    path = REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network disabled for frozen metadata tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def example(tmp_path, monkeypatch):
    """Hand example: old D/C = 3/2; new D/C = 3/4, difference = 0/2.

    Counts are synthetic inputs, not a claim about a historical bore. Labels
    differ deliberately, so those differences are marked as a comparison on
    different bases. No PND measurement was supplied for the old
    side: its result must remain null, even though candidate PND is 1.
    """
    builder = load_builder()
    old = pd.DataFrame(
        {
            "API_WELL_NUMBER": [100],
            "LEASE_NAME": ["synthetic"],
            "DRILLING_DAYS": [3],
            "COMPLETION_DAYS": [2],
            "WELL_SPUD_DATE": ["2020-01-01"],
        }
    )
    workbook = tmp_path / "frozen.xlsx"
    old.to_excel(workbook, index=False, sheet_name="Sheet1")
    candidate = old.assign(
        API_WELL_NUMBER="100",
        COMPLETION_DAYS=4,
        BASIS="synthetic activity rule",
        PND_DAYS=1,
        DAYS_STATUS="war_covered",
    )
    csv = tmp_path / "candidate.csv"
    candidate.to_csv(csv, index=False)
    metadata = json.loads(SIDECAR.read_text(encoding="utf-8"))
    metadata["workbook_sha256"] = hashlib.sha256(workbook.read_bytes()).hexdigest()
    sidecar = workbook.with_suffix(".provenance.json")
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    output = tmp_path / "published.csv"
    output.write_bytes(b"previous publication\n")
    monkeypatch.setattr(builder, "FROZEN_XLSX", workbook)
    monkeypatch.setattr(builder, "CANDIDATE_CSV", csv)
    monkeypatch.setattr(builder, "OUT_CSV", output)
    return builder, workbook, sidecar, output, old, candidate


def test_repository_metadata_binds_original_bytes():
    builder = load_builder()
    workbook = VINTAGE / "drilling_and_completion_days.xlsx"
    before = workbook.read_bytes()
    labelled = builder.load_frozen(workbook)
    original = pd.read_excel(workbook, sheet_name="Sheet1")
    pd.testing.assert_frame_equal(labelled[original.columns], original)
    assert labelled["BASIS"].eq("legacy_calendar_or_war_union_post_td_remarks").all()
    assert labelled["PND_DAYS"].isna().all()
    assert labelled["DAYS_STATUS"].eq("historical_coverage_unknown").all()
    assert workbook.read_bytes() == before


def test_sidecar_load_is_additive_and_nullable(example):
    builder, workbook, sidecar, _, old, _ = example
    loaded = builder.load_frozen(workbook, sidecar)
    pd.testing.assert_frame_equal(loaded[old.columns], old)
    assert str(loaded["PND_DAYS"].dtype) == "Int64"
    assert loaded["PND_DAYS"].isna().all()


@pytest.mark.parametrize("failure", ["absent", "digest", "invalid_json"])
def test_bad_metadata_preserves_publication_and_source(example, failure):
    builder, workbook, sidecar, output, _, _ = example
    if failure == "absent":
        sidecar = sidecar.with_name("missing.json")
    elif failure == "digest":
        data = json.loads(sidecar.read_text())
        data["workbook_sha256"] = "0" * 64
        sidecar.write_text(json.dumps(data))
    else:
        sidecar.write_text("{")
    before = workbook.read_bytes(), output.read_bytes()
    with pytest.raises(ValueError, match="metadata"):
        builder.main(["--frozen-metadata", str(sidecar)])
    assert (workbook.read_bytes(), output.read_bytes()) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("basis", "calendar_spud_to_td"),
        ("pnd_days", 0),
        ("days_status", "war_covered"),
        ("reproduction_status", "verified"),
        ("sources", []),
        ("limitations", []),
        ("rule", {}),
        ("sheet", "Diagnostics"),
    ],
)
def test_unsupported_metadata_refused(example, field, value):
    builder, workbook, sidecar, _, _, _ = example
    data = json.loads(sidecar.read_text())
    data[field] = value
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="metadata"):
        builder.load_frozen(workbook, sidecar)


@pytest.mark.parametrize("field", ["sources", "rule", "limitations", "workbook_sha256"])
def test_required_evidence_cannot_be_omitted(example, field):
    builder, workbook, sidecar, _, _, _ = example
    data = json.loads(sidecar.read_text())
    del data[field]
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="metadata"):
        builder.load_frozen(workbook, sidecar)


def test_duplicate_json_keys_refused(example):
    builder, workbook, sidecar, _, _, _ = example
    text = sidecar.read_text()
    sidecar.write_text(text[:-1] + ', "basis": "other"}')
    with pytest.raises(ValueError, match="metadata"):
        builder.load_frozen(workbook, sidecar)


def test_publication_records_both_sides_and_unknowns(example):
    builder, workbook, _, output, _, _ = example
    before = workbook.read_bytes()
    builder.main([])
    row = pd.read_csv(output).iloc[0]
    assert row["basis_v30"] == "legacy_calendar_or_war_union_post_td_remarks"
    assert row["basis_wed"] == "synthetic activity rule"
    assert row["basis"] == "mixed"
    assert pd.isna(row["pnd_days_v30"])
    assert row["pnd_days_wed"] == 1
    assert row["days_status_v30"] == "historical_coverage_unknown"
    assert row["days_status_wed"] == "war_covered"
    assert not row["same_basis"]
    assert (row["d_drill"], row["d_compl"]) == (0, 2)
    assert (row["drill_v30"], row["compl_v30"]) == (3, 2)
    assert (row["drill_wed"], row["compl_wed"]) == (3, 4)
    assert workbook.read_bytes() == before


@pytest.mark.parametrize("field", ["BASIS", "PND_DAYS", "DAYS_STATUS"])
def test_unlabelled_candidate_preserves_outputs(example, field):
    builder, workbook, _, output, _, candidate = example
    candidate.drop(columns=field).to_csv(builder.CANDIDATE_CSV, index=False)
    before = workbook.read_bytes(), output.read_bytes()
    with pytest.raises(ValueError, match="provenance"):
        builder.main([])
    assert (workbook.read_bytes(), output.read_bytes()) == before


@pytest.mark.parametrize(
    "status", ["not measured", "historical_coverage_unknown", "mixed"]
)
def test_candidate_cannot_claim_historical_unknown_coverage(example, status):
    builder, workbook, _, output, _, candidate = example
    candidate.assign(DAYS_STATUS=status).to_csv(builder.CANDIDATE_CSV, index=False)
    before = workbook.read_bytes(), output.read_bytes()
    with pytest.raises(ValueError, match="provenance"):
        builder.main([])
    assert (workbook.read_bytes(), output.read_bytes()) == before


def test_absent_side_is_not_missing_provenance(example):
    builder, _, _, output, _, candidate = example
    candidate.assign(API_WELL_NUMBER="101").to_csv(builder.CANDIDATE_CSV, index=False)
    builder.main([])
    rows = pd.read_csv(output).set_index("api12")
    assert pd.isna(rows.loc[100, "basis_wed"])
    assert pd.isna(rows.loc[101, "basis_v30"])
    assert rows.loc[100, "basis_v30"] == "legacy_calendar_or_war_union_post_td_remarks"
    assert rows.loc[101, "basis_wed"] == "synthetic activity rule"
    assert not rows["same_basis"].any()


def test_same_recorded_rule_is_explicit(example):
    """Synthetic same-rule counts: (3-3, 4-2) = (0, 2), independently by hand."""
    builder, _, _, output, _, candidate = example
    candidate.assign(BASIS="legacy_calendar_or_war_union_post_td_remarks").to_csv(
        builder.CANDIDATE_CSV, index=False
    )
    builder.main([])
    row = pd.read_csv(output).iloc[0]
    assert row["same_basis"]
    assert row["basis"] == row["basis_v30"] == row["basis_wed"]
    assert (row["d_drill"], row["d_compl"]) == (0, 2)


def test_prelabelled_workbook_is_not_overridden(example):
    builder, workbook, sidecar, output, old, _ = example
    old.assign(BASIS="another recorded rule").to_excel(workbook, index=False)
    data = json.loads(sidecar.read_text())
    data["workbook_sha256"] = hashlib.sha256(workbook.read_bytes()).hexdigest()
    sidecar.write_text(json.dumps(data))
    before = workbook.read_bytes(), output.read_bytes()
    with pytest.raises(ValueError, match="metadata conflicts"):
        builder.main([])
    assert (workbook.read_bytes(), output.read_bytes()) == before


@pytest.mark.parametrize("evidence", [None, "", [""], [None]])
@pytest.mark.parametrize("field", ["sources", "limitations"])
def test_empty_or_nontext_evidence_refused(example, field, evidence):
    builder, workbook, sidecar, _, _, _ = example
    data = json.loads(sidecar.read_text())
    data[field] = evidence
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="metadata"):
        builder.load_frozen(workbook, sidecar)
