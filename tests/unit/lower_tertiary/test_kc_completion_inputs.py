"""KC report inputs and arithmetic, without raw-data or solver dependencies.

Synthetic examples below are hand calculations, not field measurements.
Lease identities come from the committed leases_v21_kc.csv and issue 842.
"""

import pandas as pd
import pytest

from scripts.completion import build_completion_report as report
from worldenergydata.lower_tertiary import v30_reproducer as inputs


def test_kc_report_loads_committed_candidate():
    """The candidate's Buckskin API set must survive the report input adapter."""
    source = pd.read_csv(inputs.V50_KC_DRILLING_PATH)
    expected = source.loc[source.LEASE_NAME == "Buckskin", "API_WELL_NUMBER"]
    rows = report.load_report_data("v50_kc")
    actual = {str(r["API_WELL_NUMBER"]) for r in rows if r["LEASE_NAME"] == "Buckskin"}
    assert actual == set(expected.astype(str))
    assert all(isinstance(r["DRILLING_DAYS"], (int, float)) for r in rows)


def test_frozen_report_input_remains_default():
    assert report.load_report_data() == report._load()


def test_unknown_report_input_is_rejected():
    with pytest.raises(ValueError, match="input set"):
        report.load_report_data("unknown")


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), "unknown"])
def test_kc_loader_rejects_invalid_days(tmp_path, monkeypatch, bad):
    """Days are finite nonnegative counts; missing is not a true zero."""
    frame = pd.read_csv(inputs.V50_KC_DRILLING_PATH)
    frame["DRILLING_DAYS"] = frame["DRILLING_DAYS"].astype(object)
    frame.loc[0, "DRILLING_DAYS"] = bad
    path = tmp_path / "days.csv"
    frame.to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_DRILLING_PATH", path)
    with pytest.raises(ValueError, match="DRILLING_DAYS"):
        inputs.load_v50_kc_drilling()


def test_kc_loader_rejects_duplicate_apis(tmp_path, monkeypatch):
    frame = pd.read_csv(inputs.V50_KC_DRILLING_PATH)
    path = tmp_path / "days.csv"
    pd.concat([frame, frame.iloc[:1]]).to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_DRILLING_PATH", path)
    with pytest.raises(ValueError, match="API_WELL_NUMBER"):
        inputs.load_v50_kc_drilling()


def test_kc_loader_rejects_unmapped_lease(tmp_path, monkeypatch):
    frame = pd.read_csv(inputs.V50_KC_DRILLING_PATH)
    frame.loc[0, "SURF_LEASE_NUM"] = "UNMAPPED"
    path = tmp_path / "days.csv"
    frame.to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_DRILLING_PATH", path)
    with pytest.raises(ValueError, match="lease"):
        inputs.load_v50_kc_drilling()


@pytest.mark.parametrize(
    "defect", ["empty", "blank_api", "missing_column", "wrong_name"]
)
def test_kc_loader_rejects_incomplete_identity(tmp_path, monkeypatch, defect):
    frame = pd.read_csv(inputs.V50_KC_DRILLING_PATH, dtype={"API_WELL_NUMBER": str})
    if defect == "empty":
        frame = frame.iloc[:0]
    elif defect == "blank_api":
        frame.loc[0, "API_WELL_NUMBER"] = " "
    elif defect == "missing_column":
        frame = frame.drop(columns="COMPLETION_DAYS")
    else:
        frame.loc[0, "LEASE_NAME"] = "Unknown"
    path = tmp_path / "days.csv"
    frame.to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_DRILLING_PATH", path)
    with pytest.raises(ValueError):
        inputs.load_v50_kc_drilling()


def test_financial_consumer_receives_same_validated_candidate():
    from worldenergydata.lower_tertiary.v30_financial_reproducer import (
        _input_set_tables,
    )

    _, leases, days = _input_set_tables("v50_kc")
    report_apis = {r["API_WELL_NUMBER"] for r in report.load_report_data("v50_kc")}
    assert set(days.API_WELL_NUMBER) == report_apis
    assert set(days.SURF_LEASE_NUM) <= set(leases.LEASE_NUM)


def test_normalized_api_duplicates_are_rejected(tmp_path, monkeypatch):
    frame = pd.read_csv(inputs.V50_KC_DRILLING_PATH, dtype={"API_WELL_NUMBER": str})
    frame.loc[1, "API_WELL_NUMBER"] = " " + frame.loc[0, "API_WELL_NUMBER"] + " "
    path = tmp_path / "days.csv"
    frame.to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_DRILLING_PATH", path)
    with pytest.raises(ValueError, match="API_WELL_NUMBER"):
        inputs.load_v50_kc_drilling()


def test_kc_loader_preserves_zero_and_normalizes_leases(tmp_path, monkeypatch):
    """A supplied true zero remains zero; spacing cannot break a known lease join."""
    frame = pd.read_csv(inputs.V50_KC_DRILLING_PATH)
    frame.loc[0, "DRILLING_DAYS"] = 0
    frame.loc[0, "SURF_LEASE_NUM"] = ' "g 31752" '
    path = tmp_path / "days.csv"
    frame.to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_DRILLING_PATH", path)
    result = inputs.load_v50_kc_drilling()
    assert result.loc[0, "DRILLING_DAYS"] == 0
    assert result.loc[0, "SURF_LEASE_NUM"] == "G31752"


def test_kc_loader_rejects_duplicate_lease_mapping(tmp_path, monkeypatch):
    frame = pd.read_csv(inputs.V50_KC_LEASES_PATH)
    path = tmp_path / "leases.csv"
    pd.concat([frame, frame.iloc[:1]]).to_csv(path, index=False)
    monkeypatch.setattr(inputs, "V50_KC_LEASES_PATH", path)
    with pytest.raises(ValueError, match="duplicate lease"):
        inputs.load_v50_kc_drilling()


def test_kc_reconciliation_hand_calculation():
    """Two synthetic bores: (2+3)+(5+7)=17 days; no external benchmark used.

    Common totals: 17 days, 2 bores. Benchmark: 16 days, 1 bore.
    Differences: 17-16=+1 day and 2-1=+1 bore, requiring investigation.
    """
    rows = [
        {"LEASE_NAME": "Buckskin", "DRILLING_DAYS": 2, "COMPLETION_DAYS": 3},
        {"LEASE_NAME": "Buckskin", "DRILLING_DAYS": 5, "COMPLETION_DAYS": 7},
    ]
    benchmark = {"Buckskin": {"fo": "", "bores": 1, "d_and_c": 16}}
    result = report.compute_reconciliation(rows, benchmark=benchmark)
    assert result["wed_common"] == {"bores": 2, "dc": 17}
    assert result["common_delta_dc"] == 1
    row = result["rows"][0]
    assert row["status"] == "investigate"
    assert row["delta_bores"] == 1
    assert "Same wellbore count" not in report._recon_note(row)
    assert "Not yet in" not in report._recon_note(row)


def test_kc_cli_writes_candidate_separately(tmp_path):
    report.main(["--input-set", "v50_kc", "--output-dir", str(tmp_path)])
    page = (tmp_path / "verification.html").read_text()
    assert "v50_kc" in page
    assert "NOT_EVALUATED" in page
    assert "not yet ingested" not in page
    assert "at/below the" not in page
    assert "version-independent" not in page
    assert "Revision history" in page
    assert (tmp_path / "index.html").is_file()


def test_kc_cli_requires_explicit_output_dir():
    """An opt-in candidate must not overwrite the frozen published reports."""
    with pytest.raises(SystemExit):
        report.main(["--input-set", "v50_kc"])


def test_kc_cli_rejects_frozen_output_directory():
    with pytest.raises(SystemExit):
        report.main(["--input-set", "v50_kc", "--output-dir", str(report._OUT.parent)])


def test_day_match_note_handles_additional_bores():
    """A +1 bore delta describes an additional bore, not minus-one fewer."""
    row = {"dev": "Example", "status": "days_match", "delta_bores": 1}
    note = report._recon_note(row)
    assert "1 additional" in note
    assert "-1" not in note


def test_empty_comparison_does_not_invent_percentage_agreement():
    result = report.compute_reconciliation([], benchmark={})
    page = report.render_verification(result, [])
    assert "Percentage difference NOT_EVALUATED" in page
