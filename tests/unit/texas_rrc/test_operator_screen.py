"""Independent synthetic arithmetic for the operator screen; no field calibration.

Fixture rates: A=(62/31,28/28)=(2,1), B=(248/31,224/28)=(8,8),
C=(62/31,0/28)=(2,0) bbl/day per two-well lease. February peer medians
excluding the subject operator: A=(8+0)/2=4, C=(1+8)/2=4.5.
A's deficit=(4-1)/4=0.75. C's decline=1, peer decline median=(0.5+0)/2
=0.25, excess=0.75. Population CV for C is 1/1=1. A totals 90 bbl.
These are hand calculations, not estimates of recoverable production.
"""

import copy
import json
from pathlib import Path

import pytest

from worldenergydata.texas_rrc.operator_screen import (
    Policy,
    build_screen,
    load_bundle,
    render_onepager,
    write_outputs,
)
from worldenergydata.texas_rrc.operator_screen.__main__ import main

FIXTURE = Path(__file__).parent / "fixtures" / "operator_screen.json"


@pytest.fixture
def bundle():
    return load_bundle(FIXTURE)


def run(bundle, **overrides):
    config = {**bundle["policy"], **overrides}
    return build_screen(bundle, Policy(**config), as_of="2025-02")


def test_registry_preserves_ids_and_counts_lease_once(bundle):
    result = run(bundle)
    a = result["operators"][0]
    assert a["operator_no"] == "000001"
    assert a["well_count_total"] == 2
    assert a["oil_bbl_window"] == 90
    assert a["gas_mcf_window"] == 0
    assert a["water_cut_est"] is None
    assert a["stripper_share"] is None  # lease volume cannot classify either well
    assert a["field_concentration"] == 1  # (2/2)^2
    assert a["name_collision_count"] == 1
    assert a["name_variant_count"] == 2
    assert len(result["operators"]) == 3  # shared normalized names never merge IDs
    assert result["coverage"]["production_rows_by_granularity"] == {"lease": 6}
    assert result["coverage"]["operators_with_complete_window"] == 3


def test_peer_arithmetic_reasons_and_deterministic_rank(bundle):
    result = run(bundle)
    a = next(x for x in result["candidates"] if x["operator_no"] == "000001")
    c = result["candidates"][0]
    assert a["rate_bopd"] == 1
    assert a["peer_median_bopd"] == 4
    assert a["deficit_fraction"] == 0.75
    assert a["signals"] == ["below_peer_median"]
    assert c["operator_no"] == "000003"
    assert c["decline_excess_fraction"] == 0.75
    assert c["rate_cv"] == 1
    assert c["signal_count"] == 4
    assert c["granularity"] == "lease"
    assert c["mechanism"] == "NOT_EVALUATED"
    assert result["ranked_operators"][0]["operator_no"] == "000003"
    shuffled = copy.deepcopy(bundle)
    shuffled["wells"].reverse()
    shuffled["production"].reverse()
    assert run(shuffled) == result


def test_no_peers_from_same_operator_and_sensitivity(bundle):
    result = run(bundle, min_peers=3)
    assert all(x["peer_status"] == "NOT_EVALUATED" for x in result["candidates"])
    assert all(x["deficit_fraction"] is None for x in result["candidates"])
    assert result["sensitivity"]["peer_eligible_candidates"] == 0
    assert run(bundle)["sensitivity"]["peer_eligible_candidates"] == 3


def test_missing_month_is_unknown_not_zero(bundle):
    bundle["production"] = [
        r
        for r in bundle["production"]
        if not (r["operator_no"] == "000001" and r["month"] == "2025-02")
    ]
    result = run(bundle)
    assert result["operators"][0]["oil_bbl_window"] is None
    a = next(x for x in result["candidates"] if x["operator_no"] == "000001")
    assert a["rate_bopd"] is None
    assert a["signals"] == []
    assert a["history_status"] == "NOT_EVALUATED"


def test_partial_water_never_becomes_zero(bundle):
    bundle["production"][0]["water_bbl"] = 100
    assert run(bundle)["operators"][0]["water_cut_est"] is None


@pytest.mark.parametrize(
    "kind", ["duplicate", "negative", "nonfinite", "unknown", "mixed"]
)
def test_rejects_ambiguous_or_invalid_production(bundle, kind):
    row = copy.deepcopy(bundle["production"][0])
    if kind == "duplicate":
        bundle["production"].append(row)
    elif kind == "negative":
        row["oil_bbl"] = -1
        bundle["production"][0] = row
    elif kind == "nonfinite":
        row["oil_bbl"] = float("nan")
        bundle["production"][0] = row
    elif kind == "unknown":
        row["operator_no"] = "missing"
        bundle["production"][0] = row
    else:
        row.update(granularity="well", api_number=bundle["wells"][0]["api_number"])
        bundle["production"].append(row)
    with pytest.raises(ValueError):
        run(bundle)


def test_rejects_duplicate_well_inventory_and_future_snapshot(bundle):
    bundle["wells"].append(copy.deepcopy(bundle["wells"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        run(bundle)


def test_transfer_history_is_not_assigned_to_current_inventory(bundle):
    bundle["production"][0]["operator_no"] = "000002"
    with pytest.raises(ValueError, match="operator"):
        run(bundle)


def test_unknown_vintage_cannot_enter_peer_group(bundle):
    bundle["wells"][0]["completion_year"] = None
    a = next(x for x in run(bundle)["candidates"] if x["operator_no"] == "000001")
    assert a["peer_status"] == "NOT_EVALUATED"


def test_well_grain_supports_stripper_classification(bundle):
    """A's verified well rates are 1 and 1 bbl/day, so 2/2 qualify at 2."""
    a_rows = bundle["production"][:2]
    bundle["production"] = bundle["production"][2:]
    for well in bundle["wells"][:2]:
        for row in a_rows:
            bundle["production"].append(
                {
                    **row,
                    "granularity": "well",
                    "api_number": well["api_number"],
                    "oil_bbl": 31 if row["month"] == "2025-01" else 28,
                }
            )
    a = run(bundle)["operators"][0]
    assert a["stripper_share"] == 1
    assert a["bopd_per_well_median"] == 1
    assert a["selection_status"] == "SELECTED"


@pytest.mark.parametrize(
    "overrides",
    [
        {"min_peers": 0},
        {"min_wells": 4, "max_wells": 2},
        {"min_stripper_share": 1.1},
        {"deficit_fraction": float("nan")},
        {"window_months": 1},
        {"vintage_years": 0},
        {"top_candidates": 0},
    ],
)
def test_policy_requires_explicit_valid_thresholds(bundle, overrides):
    with pytest.raises(ValueError):
        run(bundle, **overrides)


def test_onepager_golden_and_non_suppressible_limits(bundle):
    html = render_onepager(run(bundle), "000001")
    golden = FIXTURE.with_name("operator_screen_onepager.html").read_text()
    assert html == golden
    assert "What this data cannot tell you" in html
    assert "NOT_EVALUATED" in html
    assert "lease" in html
    assert "<svg" in html
    with pytest.raises(KeyError):
        render_onepager(run(bundle), "absent")


def test_html_escapes_input_names(bundle):
    for well in bundle["wells"][:2]:
        well["operator_name"] = "<script>alert('x')</script>"
    html = render_onepager(run(bundle), "000001")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_write_outputs_parquet_and_provenance(bundle, tmp_path):
    import pyarrow.parquet as pq

    result = run(bundle)
    write_outputs(result, tmp_path)
    assert len(pq.read_table(tmp_path / "operator_registry.parquet")) == 3
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["source"] == bundle["source"]
    assert manifest["validation_gate"] == "NOT_EVALUATED"
    assert len(manifest["input_sha256"]) == 64
    assert (tmp_path / "operators" / "000001.html").read_text() == render_onepager(
        result, "000001"
    )
    for path in tmp_path.rglob("*"):
        if path.is_file():
            before = path.read_bytes()
            write_outputs(result, tmp_path)
            assert path.read_bytes() == before


def test_cli_build_target(bundle, tmp_path):
    assert (
        main(
            [
                "--input",
                str(FIXTURE),
                "--as-of",
                "2025-02",
                "--output",
                str(tmp_path),
                "--operator",
                "000002",
            ]
        )
        == 0
    )
    assert (tmp_path / "operators" / "000002.html").is_file()
    assert not (tmp_path / "operators" / "000001.html").exists()


def test_provenance_and_nonempty_input_required(bundle):
    del bundle["source"]["snapshot_date"]
    with pytest.raises(ValueError, match="source"):
        run(bundle)


def test_gas_units_do_not_pass_an_oil_stripper_screen(bundle):
    for row in bundle["wells"]:
        row["oil_gas_code"] = "G"
    for row in bundle["production"]:
        row["oil_gas_code"] = "G"
    result = run(bundle)
    assert all(o["selection_status"] == "NOT_EVALUATED" for o in result["operators"])
    assert all(c["signals"] == [] for c in result["candidates"])


def test_future_production_does_not_create_prior_oil_signal(bundle):
    for row in bundle["production"][4:]:
        row["oil_bbl"] = 0
    future = {**bundle["production"][-1], "month": "2025-03", "oil_bbl": 100}
    bundle["production"].append(future)
    c = next(c for c in run(bundle)["candidates"] if c["operator_no"] == "000003")
    assert "idle_with_prior_oil" not in c["signals"]


def test_zero_peer_median_does_not_divide_or_imply_deficit(bundle):
    for row in bundle["production"]:
        row["oil_bbl"] = 0
    result = run(bundle)
    assert all(c["deficit_fraction"] is None for c in result["candidates"])
    assert all(c["signals"] == [] for c in result["candidates"])


def test_same_operator_units_are_excluded_from_peers(bundle):
    for well in bundle["wells"][2:]:
        well["operator_no"] = "000001"
    for row in bundle["production"][2:]:
        row["operator_no"] = "000001"
    assert all(c["peer_count"] == 0 for c in run(bundle)["candidates"])


def test_inventory_without_production_has_explicit_gaps(bundle):
    bundle["production"] = []
    result = run(bundle)
    assert result["candidates"] == []
    assert result["operators"][0]["oil_bbl_window"] is None
    assert "NOT_EVALUATED" in render_onepager(result, "000001")


def test_unequal_lease_sizes_are_not_peers(bundle):
    bundle["wells"].pop()
    c = next(c for c in run(bundle)["candidates"] if c["operator_no"] == "000003")
    assert c["peer_count"] == 0


def test_vintage_policy_sensitivity_is_explicit(bundle):
    for well in bundle["wells"][4:]:
        well["completion_year"] = 2001
    assert run(bundle)["sensitivity"]["peer_eligible_candidates"] == 3
    assert run(bundle, vintage_years=1)["sensitivity"]["peer_eligible_candidates"] == 0


def test_water_cut_and_field_concentration_hand_calculation(bundle):
    """A: water=45+45=90, oil=90, cut=90/180=0.5; two fields: HHI=0.5."""
    bundle["production"][0]["water_bbl"] = 45
    bundle["production"][1]["water_bbl"] = 45
    bundle["wells"][1]["field_no"] = "00000002"
    a = run(bundle)["operators"][0]
    assert a["water_cut_est"] == 0.5
    assert a["field_concentration"] == 0.5
    assert a["field_count"] == 2


def test_calendar_window_crosses_year_and_leap_day(bundle):
    """Leap February rate is 29/29=1; December is retained in a 3-month window."""
    bundle["source"].update(snapshot_date="2024-03-01", inventory_date="2024-02-29")
    for row in bundle["production"]:
        row["month"] = row["month"].replace("2025", "2024")
        if row["month"] == "2024-02":
            row["oil_bbl"] = 29
    result = build_screen(bundle, Policy(**bundle["policy"]), as_of="2024-02")
    assert all(c["rate_bopd"] == 1 for c in result["candidates"])
    policy = Policy(**{**bundle["policy"], "window_months": 3})
    assert build_screen(bundle, policy, as_of="2024-02")["window"][0] == "2023-12"


def test_pdq_adapter_preserves_regulator_grain(bundle):
    """PDQ gas=10 gas-well Mcf + 5 casinghead Mcf=15; identifiers stay strings."""
    from worldenergydata.texas_rrc.operator_screen import normalize_pdq_rows

    raw = {
        "DISTRICT_NO": "01",
        "OIL_GAS_CODE": "O",
        "LEASE_NO": "000001",
        "OPERATOR_NO": "000001",
        "CYCLE_YEAR_MONTH": "202502",
        "LEASE_OIL_PROD_VOL": "28",
        "LEASE_GAS_PROD_VOL": "10",
        "LEASE_CSGD_PROD_VOL": "5",
        "PROD_REPORT_FILED_FLAG": "Y",
    }
    rows = normalize_pdq_rows([raw])
    assert rows[0]["gas_mcf"] == 15
    assert rows[0]["oil_bbl"] == 28
    assert rows[0]["granularity"] == "lease"
    assert rows[0]["water_bbl"] is None
    raw["PROD_REPORT_FILED_FLAG"] = "N"
    assert normalize_pdq_rows([raw]) == []


def test_pdq_adapter_refuses_missing_volume_or_numeric_ids():
    from worldenergydata.texas_rrc.operator_screen import normalize_pdq_rows

    with pytest.raises(ValueError):
        normalize_pdq_rows([{"OPERATOR_NO": 1}])


def test_cli_yaml_policy_is_explicit_override(bundle, tmp_path):
    config = tmp_path / "policy.yml"
    config.write_text(
        json.dumps({"operator_screen": {**bundle["policy"], "min_peers": 3}})
    )
    main(
        [
            "--input",
            str(FIXTURE),
            "--as-of",
            "2025-02",
            "--output",
            str(tmp_path / "out"),
            "--config",
            str(config),
        ]
    )
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert manifest["policy"]["min_peers"] == 3
    assert manifest["sensitivity"]["peer_eligible_candidates"] == 0


def test_make_onepager_target(tmp_path):
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    subprocess.run(
        [
            "make",
            "onepager",
            f"INPUT={FIXTURE.resolve()}",
            "AS_OF=2025-02",
            f"OUTPUT={tmp_path}",
            "OPERATOR=000001",
            f"PYTHON={sys.executable}",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    assert (tmp_path / "operators" / "000001.html").is_file()


def test_default_policy_template_cannot_silently_select_thresholds():
    import yaml

    root = Path(__file__).resolve().parents[3]
    config = yaml.safe_load((root / "config" / "texas_rrc.yml").read_text())
    with pytest.raises(ValueError):
        Policy(**config["operator_screen"])


def test_idle_evidence_reports_prior_rate_and_elapsed_months(bundle):
    """C last produced 62/31=2 in January; February minus January is one month."""
    c = next(c for c in run(bundle)["candidates"] if c["operator_no"] == "000003")
    assert c["last_positive_oil_month"] == "2025-01"
    assert c["last_positive_oil_bopd"] == 2
    assert c["months_since_positive_oil"] == 1
    assert c["observed_window_months"] == 2


def test_numeric_volume_types_are_not_coerced(bundle):
    bundle["production"][0]["oil_bbl"] = "62"
    with pytest.raises(TypeError, match="numeric"):
        run(bundle)


def test_source_dates_cannot_describe_an_unmatched_inventory(bundle):
    bundle["source"]["inventory_date"] = "2025-03-01"
    with pytest.raises(ValueError, match="inventory"):
        run(bundle)


def test_snapshot_cannot_predate_analysis_month(bundle):
    bundle["source"]["snapshot_date"] = "2025-01-31"
    with pytest.raises(ValueError, match="snapshot"):
        run(bundle)


def test_report_values_match_independent_worked_example(bundle):
    """A: 90 bbl total; 1 observed versus 4 peer bbl/day; deficit is 75.0 %."""
    html = render_onepager(run(bundle), "000001")
    assert "<dd>90.0</dd>" in html
    assert "<td>1.0</td><td>4.0</td>" in html
    assert "<td>75.0 %</td>" in html
    gas = copy.deepcopy(bundle)
    for row in gas["wells"] + gas["production"]:
        row["oil_gas_code"] = "G"
    assert (
        "Gas-unit oil signals and gas stripper classification: NOT_EVALUATED"
        in render_onepager(run(gas), "000001")
    )
