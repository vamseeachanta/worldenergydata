"""Independent arithmetic examples for the decline-EUR audit (#973).

All quantities below are synthetic MMbbl oil, not field estimates or acceptance
limits. Hand calculation: wells of 12, 8 and 5 total 25; excluding flagged 8
and missing-quality 5 leaves 12, so excluded volume is 13. A comparable
reference of 10 gives raw/reference = 2.5 and filtered/reference = 1.2.
No empirical fit threshold or oil-equivalent conversion is assumed.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "audit_field_eur", ROOT / "scripts/lower_tertiary/audit_field_eur.py"
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def row(api="well_a", eur="12", flag="", field="Example"):
    return {"api12": api, "field": field, "eur_mmbbl": eur, "decline_flag": flag}


def reference(**changes):
    result = {
        "eur_mmbbl": 10,
        "unit": "MMbbl_oil",
        "quantity": "recoverable",
        "scope": "full_field",
        "value_kind": "estimate",
        "source": "Synthetic hand calculation in test_eur_audit.py",
    }
    result.update(changes)
    return result


def test_filter_before_sum_and_preserve_raw_diagnostic():
    rows = [row(), row("well_b", "8", "low_fit_quality"), row("well_c", "5", None)]
    result = audit.audit_rows(rows, {"example": reference()})["example"]
    assert result["raw_decline_eur_mmbbl"] == 25
    assert result["filtered_decline_eur_mmbbl"] == 12
    assert result["excluded_decline_eur_mmbbl"] == 13
    assert result["included_wells"] == 1
    assert result["excluded_wells"] == 2
    assert result["exclusion_counts"] == {"decline_flag": 1, "missing_quality": 1}
    assert result["raw_to_reference_ratio"] == 2.5
    assert result["filtered_to_reference_ratio"] == 1.2
    assert result["trust_verdict"] == "NOT_EVALUATED"
    assert result["full_cycle_eligible"] is False
    assert "acceptance_criterion_not_supplied" in result["reasons"]
    assert "incomplete_reliable_coverage" in result["reasons"]


@pytest.mark.parametrize(
    "flag",
    ["insufficient_history", "low_fit_quality", "fit_failed: ValueError", "unknown"],
)
def test_every_nonempty_flag_is_excluded(flag):
    """One flagged synthetic well: raw = 12, reliable sum has no observation."""
    result = audit.audit_rows([row(flag=flag)], {})["example"]
    assert result["raw_decline_eur_mmbbl"] == 12
    assert result["filtered_decline_eur_mmbbl"] is None
    assert result["included_wells"] == 0
    assert result["excluded_wells"] == 1


@pytest.mark.parametrize("value", ["", None, "nan", "inf", "-inf", "-1", "bad", True])
def test_invalid_volume_does_not_become_zero_or_poison_sum(value):
    """Only the valid synthetic well contributes 12; the other is unknown."""
    result = audit.audit_rows([row(), row("well_b", value)], {})["example"]
    assert result["raw_decline_eur_mmbbl"] == 12
    assert result["filtered_decline_eur_mmbbl"] == 12
    assert result["unknown_eur_wells"] == 1
    assert result["excluded_wells"] == 1
    assert "incomplete_reliable_coverage" in result["reasons"]
    json.dumps(result, allow_nan=False)


def test_zero_is_a_known_volume():
    """Synthetic zero is valid, distinct from no valid observations."""
    result = audit.audit_rows([row(eur="0")], {})["example"]
    assert result["raw_decline_eur_mmbbl"] == 0
    assert result["filtered_decline_eur_mmbbl"] == 0
    assert result["unknown_eur_wells"] == 0


@pytest.mark.parametrize(
    "changes, reason",
    [
        ({"unit": "MMboe"}, "reference_unit_not_oil"),
        ({"unit": None}, "reference_unit_not_oil"),
        ({"quantity": "in_place"}, "reference_not_recoverable"),
        ({"scope": "phase_one"}, "reference_scope_not_full_field"),
        ({"value_kind": "lower_bound"}, "reference_not_point_estimate"),
        ({"source": ""}, "reference_source_missing"),
        ({"status": "pending"}, "reference_pending"),
        ({"eur_mmbbl": None}, "reference_value_invalid"),
        ({"eur_mmbbl": 0}, "reference_value_invalid"),
        ({"eur_mmbbl": float("nan")}, "reference_value_invalid"),
    ],
)
def test_incomparable_reference_never_produces_ratio(changes, reason):
    result = audit.audit_rows([row()], {"example": reference(**changes)})["example"]
    assert result["raw_to_reference_ratio"] is None
    assert result["filtered_to_reference_ratio"] is None
    assert reason in result["reasons"]
    assert result["trust_verdict"] == "NOT_EVALUATED"
    assert result["full_cycle_eligible"] is False
    json.dumps(result, allow_nan=False)


def test_missing_flag_column_is_not_a_quality_pass():
    item = row()
    del item["decline_flag"]
    result = audit.audit_rows([item], {})["example"]
    assert result["filtered_decline_eur_mmbbl"] is None
    assert result["exclusion_counts"] == {"missing_quality": 1}


@pytest.mark.parametrize("field", ["Example", "Other"])
def test_duplicate_well_cannot_be_counted_twice(field):
    with pytest.raises(ValueError, match="duplicate well"):
        audit.audit_rows([row(), row(field=field)], {})


@pytest.mark.parametrize("key", ["api12", "field"])
def test_missing_identity_is_rejected(key):
    item = row()
    del item[key]
    with pytest.raises(ValueError, match="identity"):
        audit.audit_rows([item], {})


def test_order_independent_and_no_input_mutation():
    rows = [row(), row("well_b", "8", field="Other")]
    refs = {"example": reference()}
    before = json.dumps([rows, refs], sort_keys=True)
    assert audit.audit_rows(rows, refs) == audit.audit_rows(reversed(rows), refs)
    assert json.dumps([rows, refs], sort_keys=True) == before


def test_reference_without_benchmark_is_explicit():
    result = audit.audit_rows([], {"example": reference()})["example"]
    assert "no_benchmark_wells" in result["reasons"]
    assert result["raw_decline_eur_mmbbl"] is None
    assert result["filtered_decline_eur_mmbbl"] is None
    assert result["full_cycle_eligible"] is False


def test_cli_writes_deterministic_report_without_changing_inputs(tmp_path):
    """Hand example: raw 12 + 8 = 20; flagged 8 excluded; reliable sum 12."""
    bench = tmp_path / "benchmark.csv"
    with bench.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row().keys())
        writer.writeheader()
        writer.writerows([row(), row("well_b", "8", "insufficient_history")])
    reserves = tmp_path / "reserves.yml"
    # JSON is a YAML subset; no external reserves values are introduced.
    reserves.write_text(json.dumps({"fields": {"example": reference()}}))
    out = tmp_path / "audit.json"
    before = (bench.read_bytes(), reserves.read_bytes())
    args = [
        "--benchmark",
        str(bench),
        "--reserves",
        str(reserves),
        "--output",
        str(out),
    ]
    assert audit.main(args) == 0
    first = out.read_bytes()
    assert audit.main(args) == 0
    assert out.read_bytes() == first
    assert (bench.read_bytes(), reserves.read_bytes()) == before
    result = json.loads(first)["fields"]["example"]
    assert result["raw_decline_eur_mmbbl"] == 20
    assert result["filtered_decline_eur_mmbbl"] == 12


@pytest.mark.parametrize("input_name", ["benchmark", "reserves"])
def test_cli_refuses_to_overwrite_inputs(tmp_path, input_name):
    bench = tmp_path / "benchmark.csv"
    bench.write_text("api12,field,eur_mmbbl,decline_flag\nwell_a,Example,12,\n")
    reserves = tmp_path / "reserves.yml"
    reserves.write_text("fields: {}\n")
    paths = {"benchmark": bench, "reserves": reserves}
    before = {key: path.read_bytes() for key, path in paths.items()}
    with pytest.raises(ValueError, match="output.*input"):
        audit.main(
            [
                "--benchmark",
                str(bench),
                "--reserves",
                str(reserves),
                "--output",
                str(paths[input_name]),
            ]
        )
    assert {key: path.read_bytes() for key, path in paths.items()} == before


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_cli_refuses_output_alias_of_input(tmp_path, link_kind):
    bench = tmp_path / "benchmark.csv"
    bench.write_text("api12,field,eur_mmbbl,decline_flag\nwell_a,Example,12,\n")
    reserves = tmp_path / "reserves.yml"
    reserves.write_text("fields: {}\n")
    out = tmp_path / "alias.json"
    if link_kind == "symlink":
        out.symlink_to(bench)
    else:
        out.hardlink_to(bench)
    before = bench.read_bytes()
    with pytest.raises(ValueError, match="output.*input"):
        audit.main(
            [
                "--benchmark",
                str(bench),
                "--reserves",
                str(reserves),
                "--output",
                str(out),
            ]
        )
    assert bench.read_bytes() == before


def test_overflow_is_reported_before_any_result_is_written():
    """Two largest representable finite volumes cannot form a finite sum."""
    import sys

    with pytest.raises(ValueError, match="volume overflow"):
        audit.audit_rows(
            [row(eur=sys.float_info.max), row("well_b", sys.float_info.max)], {}
        )


def test_display_rounding_does_not_feed_ratio_calculation():
    """Hand calculation: 12.37 / 9.9 < 1.25 -> 1.2, while volume -> 12.4.

    Dividing the rounded volume gives 12.4 / 9.9 > 1.25, rounding to 1.3;
    therefore this example distinguishes arithmetic from presentation.
    """
    result = audit.audit_rows(
        [row(eur="12.37")], {"example": reference(eur_mmbbl=9.9)}
    )["example"]
    assert result["raw_decline_eur_mmbbl"] == 12.4
    assert result["filtered_decline_eur_mmbbl"] == 12.4
    assert result["raw_to_reference_ratio"] == 1.2


def test_all_unknown_volumes_stay_unknown():
    """No valid observation is different from a synthetic observed zero."""
    result = audit.audit_rows([row(eur="")], {})["example"]
    assert result["raw_decline_eur_mmbbl"] is None
    assert result["filtered_decline_eur_mmbbl"] is None
    assert result["excluded_decline_eur_mmbbl"] is None
    assert result["unknown_eur_wells"] == 1
    assert result["exclusion_counts"] == {"invalid_eur": 1}


def test_ratio_overflow_is_unknown_and_json_remains_finite():
    """The largest finite float divided by the smallest normal float overflows.

    These are representation bounds from sys.float_info, not reserve inputs
    or empirical thresholds; an unrepresentable ratio is never emitted as inf.
    """
    import sys

    result = audit.audit_rows(
        [row(eur=sys.float_info.max)],
        {"example": reference(eur_mmbbl=sys.float_info.min)},
    )["example"]
    assert result["raw_to_reference_ratio"] is None
    assert result["filtered_to_reference_ratio"] is None
    assert "ratio_overflow" in result["reasons"]
    json.dumps(result, allow_nan=False)
