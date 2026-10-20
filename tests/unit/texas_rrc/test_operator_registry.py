"""Synthetic hand calculations for the operator registry, never live operators."""

import hashlib
import json
from dataclasses import replace

import pandas as pd
import pytest

from worldenergydata.texas_rrc.operators.io import (
    load_operator_inputs,
    write_operator_registry,
)
from worldenergydata.texas_rrc.operators.registry import (
    RegistryPolicy,
    build_operator_registry,
)


@pytest.fixture
def policy():
    # Policy inputs are synthetic, not regulatory size or stripper limits.
    return RegistryPolicy(
        as_of="2025-12", size_bands=((2, "small"), (4, "medium")), stripper_bopd=2
    )


@pytest.fixture
def inputs():
    """One oil lease, two oil wells, and a single-well gas lease.

    Hand calculation: 12 * (150 + 0) = 1800 bbl oil;
    12 * (10 + 20) = 360 Mcf gas; water = 12 * (100 + 150) = 3000 bbl.
    Water cut = 3000 / (1800 + 3000) = 0.625.
    Field well shares 2/3 and 1/3: HHI = (2/3)^2 + (1/3)^2 = 5/9.
    Gas-well gas rate = 12 * 20 / 365 = 240/365 Mcf/calendar day.
    Oil lease volume is never duplicated onto its two wells.
    """
    production = pd.DataFrame(
        [
            {
                "operator_no": "001",
                "operator_name": name,
                "district": "08",
                "lease_no": lease,
                "oil_gas_code": kind,
                "field_no": field,
                "production_month": f"2025-{month:02d}",
                "oil_bbl": oil,
                "gas_mcf": gas,
                "water_bbl": water,
            }
            for month in range(1, 13)
            for lease, kind, field, oil, gas, water, name in [
                ("L1", "O", "F1", 150, 10, 100, "EXAMPLE ENERGY, LLC"),
                ("L2", "G", "F2", 0, 20, 150, "Example Energy Inc."),
            ]
        ]
    )
    wells = pd.DataFrame(
        [
            {
                "operator_no": "001",
                "operator_name": "Example Energy Co.",
                "district": "08",
                "county": "101",
                "lease_no": lease,
                "oil_gas_code": kind,
                "field_no": field,
                "well_id": well,
                "well_status": status,
            }
            for lease, kind, field, well, status in [
                ("L1", "O", "F1", "W1", "producing"),
                ("L1", "O", "F1", "W2", "inactive"),
                ("L2", "G", "F2", "W3", "producing"),
            ]
        ]
    )
    return production, wells


def test_rollup_and_honest_allocation(inputs, policy):
    production, wells = inputs
    result = build_operator_registry(production, wells, policy)
    row = result.registry.iloc[0]
    assert row.operator_no == "001"
    assert row.well_count_total == 3
    assert row.well_count_producing == 2
    assert row.well_count_inactive == 1
    assert row.oil_bbl_last12 == 1800
    assert row.gas_mcf_last12 == 360
    assert row.water_bbl_last12 == 3000
    assert row.water_cut_est == pytest.approx(0.625)
    assert row.field_concentration == pytest.approx(5 / 9)
    assert row.field_count == 2
    assert pd.isna(row.bopd_per_well_median)
    assert row.gas_mcfd_per_well_median == pytest.approx(240 / 365)
    assert pd.isna(row.stripper_share)
    assert row.gas_rate_eligible_well_count == 1
    assert row.per_well_metrics_status == "NOT_EVALUATED"
    assert row.gas_per_well_metrics_status == "PARTIAL"
    assert row.operator_size_band == "medium"
    assert row.first_production == "2025-01"
    assert row.last_production == "2025-12"
    assert row.ownership_basis == "operator_of_record_only"
    assert result.quality["production_rows_by_basis"] == {
        "oil_lease": 12,
        "gas_well": 12,
    }
    assert result.quality["operators_usable_last12"] == 1
    assert result.quality["operators_by_district"] == {"08": 1}


def test_names_collisions_do_not_merge_transfers(inputs, policy):
    production, wells = inputs
    other = wells.iloc[[0]].assign(operator_no="002", well_id="W4")
    result = build_operator_registry(production, pd.concat([wells, other]), policy)
    assert list(result.registry.operator_no) == ["001", "002"]
    assert result.quality["name_collision_count"] == 1
    assert result.quality["name_ambiguity_count"] == 0
    assert result.quality["name_variant_operator_count"] == 1
    assert result.registry.iloc[0].normalized_name == "EXAMPLE ENERGY"
    assert "002" in result.registry.iloc[0].name_collision_operator_nos
    # A different core under the same number is an ambiguity, not a rename guess.
    wells.loc[0, "operator_name"] = "OTHER ENERGY"
    result = build_operator_registry(production, wells, policy)
    assert result.quality["name_ambiguity_count"] == 1


def test_missing_is_not_zero_and_policy_is_required(inputs, policy):
    production, wells = inputs
    production.loc[0, "water_bbl"] = None
    result = build_operator_registry(
        production, wells, replace(policy, size_bands=(), stripper_bopd=None)
    )
    row = result.registry.iloc[0]
    assert pd.isna(row.water_bbl_last12)
    assert pd.isna(row.water_cut_est)
    assert pd.isna(row.stripper_share)
    assert row.operator_size_band == "NOT_EVALUATED"
    assert "stripper_threshold_missing" in row.quality_flags


def test_missing_month_partial_sum_is_flagged(inputs, policy):
    production, wells = inputs
    # One gas-lease month absent: 11*20 + 12*10 = 340 observed Mcf.
    production = production.drop(index=1)
    result = build_operator_registry(production, wells, policy)
    row = result.registry.iloc[0]
    assert row.oil_bbl_last12 == 1800
    assert row.gas_mcf_last12 == 340
    assert pd.isna(row.gas_mcfd_per_well_median)
    assert not row.usable_last12
    assert pd.isna(row.bopd_per_well_median)
    assert result.quality["operators_usable_last12"] == 0


def test_duplicate_rows_collapse_but_revisions_fail(inputs, policy):
    production, wells = inputs
    result = build_operator_registry(
        pd.concat([production, production.iloc[[0]]]),
        pd.concat([wells, wells.iloc[[0]]]),
        policy,
    )
    assert result.registry.iloc[0].oil_bbl_last12 == 1800
    assert result.registry.iloc[0].well_count_total == 3
    changed = production.iloc[[0]].assign(oil_bbl=999)
    with pytest.raises(ValueError, match="Conflicting production"):
        build_operator_registry(pd.concat([production, changed]), wells, policy)
    with pytest.raises(ValueError, match="Conflicting well"):
        build_operator_registry(
            production,
            pd.concat([wells, wells.iloc[[0]].assign(operator_no="002")]),
            policy,
        )


@pytest.mark.parametrize("bad", [-1, float("inf"), "not numeric"])
def test_invalid_volumes_rejected(inputs, policy, bad):
    production, wells = inputs
    production["oil_bbl"] = production.oil_bbl.astype(object)
    production.loc[0, "oil_bbl"] = bad
    with pytest.raises(ValueError, match="oil_bbl"):
        build_operator_registry(production, wells, policy)


def test_lease_keys_include_type_and_district(inputs, policy):
    production, wells = inputs
    # Same lease number in another district remains separate: +12*150 bbl.
    extra = production[production.oil_gas_code == "O"].assign(district="01")
    result = build_operator_registry(pd.concat([production, extra]), wells, policy)
    assert result.registry.iloc[0].oil_bbl_last12 == 3600
    with pytest.raises(ValueError, match="oil_gas_code"):
        build_operator_registry(production.drop(columns="oil_gas_code"), wells, policy)


def test_no_well_inventory_is_unknown(inputs, policy):
    production, wells = inputs
    result = build_operator_registry(production, wells.iloc[:0], policy)
    row = result.registry.iloc[0]
    assert pd.isna(row.well_count_total)
    assert pd.isna(row.field_concentration)
    assert row.operator_size_band == "NOT_EVALUATED"
    assert result.quality["unmatched_production_units"] == 2


def test_file_loader_preserves_identifiers_and_manifest(inputs, policy, tmp_path):
    production, wells = inputs
    p, w = tmp_path / "production.csv", tmp_path / "wells.csv"
    production.rename(
        columns={
            "operator_no": "OPERATOR_NO",
            "lease_no": "LEASE_NO",
            "oil_bbl": "LEASE_OIL_PROD_VOL",
        }
    ).to_csv(p, index=False)
    wells.to_csv(w, index=False)
    loaded = load_operator_inputs(p, w)
    result = build_operator_registry(loaded.production, loaded.wells, policy)
    manifest = write_operator_registry(
        result,
        tmp_path / "output",
        policy,
        inputs=loaded.provenance,
        code_revision="test",
        allow_non_catalog_root=True,
    )
    payload = json.loads(manifest.read_text())
    output = pd.read_parquet(manifest.parent / "operator_registry.parquet")
    assert output.operator_no.iloc[0] == "001"
    assert payload["row_count"] == 1
    assert payload["inputs"][0]["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    parquet = manifest.parent / "operator_registry.parquet"
    assert (
        payload["outputs"][parquet.name]["sha256"]
        == hashlib.sha256(parquet.read_bytes()).hexdigest()
    )
    assert payload["policy"]["as_of"] == "2025-12"
    assert (manifest.parent / "quality.json").is_file()
    with pytest.raises(FileExistsError):
        write_operator_registry(
            result, tmp_path / "output", policy, allow_non_catalog_root=True
        )


def test_deterministic_and_empty(inputs, policy):
    production, wells = inputs
    a = build_operator_registry(production, wells, policy)
    b = build_operator_registry(
        production.sample(frac=1, random_state=7), wells.iloc[::-1], policy
    )
    pd.testing.assert_frame_equal(a.registry, b.registry)
    assert a.quality == b.quality
    empty = build_operator_registry(production.iloc[:0], wells.iloc[:0], policy)
    assert empty.registry.empty
    assert "operator_no" in empty.registry


def test_future_rows_and_history_do_not_move_to_successor(inputs, policy):
    production, wells = inputs
    # Future oil volume is excluded; historic production stays with the filer.
    future = production.iloc[[0]].assign(production_month="2026-01", oil_bbl=999)
    old = production.iloc[[0]].assign(operator_no="009", production_month="2024-01")
    result = build_operator_registry(
        pd.concat([production, future, old]), wells, policy
    )
    current = result.registry.set_index("operator_no").loc["001"]
    previous = result.registry.set_index("operator_no").loc["009"]
    assert current.oil_bbl_last12 == 1800
    assert previous.first_production == "2024-01"
    assert pd.isna(previous.oil_bbl_last12)
    assert not previous.usable_last12


def test_zero_production_and_unclassified_status(inputs, policy):
    production, wells = inputs
    production.loc[:, ["oil_bbl", "gas_mcf", "water_bbl"]] = 0
    wells["well_status"] = "active"
    row = build_operator_registry(production, wells, policy).registry.iloc[0]
    assert row.oil_bbl_last12 == 0
    assert pd.isna(row.water_cut_est)
    assert pd.isna(row.first_production)
    assert row.well_count_producing == 0
    assert row.well_count_other == 3
    assert pd.isna(row.bopd_per_well_median)


def test_ambiguous_gas_lease_is_not_allocated(inputs, policy):
    production, wells = inputs
    extra = wells.iloc[[-1]].assign(well_id="W4")
    row = build_operator_registry(
        production, pd.concat([wells, extra]), policy
    ).registry.iloc[0]
    assert pd.isna(row.bopd_per_well_median)
    assert row.gas_rate_eligible_well_count == 0
    assert pd.isna(row.gas_mcfd_per_well_median)


def test_partial_field_inventory_is_unknown(inputs, policy):
    production, wells = inputs
    wells.loc[0, "field_no"] = ""
    row = build_operator_registry(production, wells, policy).registry.iloc[0]
    assert pd.isna(row.field_concentration)
    assert "field_concentration_unavailable" in row.quality_flags


@pytest.mark.parametrize(
    "settings",
    [
        {"as_of": "2025-13"},
        {"as_of": "2025-1"},
        {"as_of": "2025-12", "size_bands": ((4, "large"), (2, "small"))},
        {"as_of": "2025-12", "stripper_bopd": -1},
    ],
)
def test_invalid_policy(settings):
    with pytest.raises(ValueError):
        RegistryPolicy(**settings)


def test_native_pdq_zip_and_total_gas(inputs, tmp_path):
    """Synthetic native volume arithmetic: gas 20 + casinghead 5 = 25 Mcf.

    A district summary of 999 must not be added to the lease-level input.
    """
    import zipfile

    from worldenergydata.texas_rrc.operators.io import normalize_input_columns

    production, wells = inputs
    native = (
        production.iloc[[1]]
        .rename(
            columns={
                "production_month": "CYCLE_YEAR_MONTH",
                "gas_mcf": "LEASE_GAS_PROD_VOL",
            }
        )
        .assign(LEASE_CSGD_PROD_VOL=5)
    )
    native["CYCLE_YEAR_MONTH"] = "202501"
    archive = tmp_path / "pdq.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "OG_LEASE_CYCLE_DATA_TABLE.dsv", native.to_csv(index=False, sep="}")
        )
        handle.writestr("OG_DISTRICT_CYCLE_DATA_TABLE.dsv", "oil_bbl\n999\n")
    w = tmp_path / "wells.csv"
    wells.to_csv(w, index=False)
    loaded = load_operator_inputs(archive, w)
    assert len(loaded.production) == 1
    assert loaded.production.gas_mcf.iloc[0] == 25
    assert loaded.production.production_month.iloc[0] == "2025-01"
    with pytest.raises(ValueError, match="aliases"):
        normalize_input_columns(
            pd.DataFrame({"operator_no": ["1"], "OPERATOR_NO": ["2"]})
        )


def test_leap_year_calendar_rate(inputs, policy):
    """Hand calculation: 240 Mcf / 366 days in calendar year 2024."""
    production, wells = inputs
    production["production_month"] = production.production_month.str.replace(
        "2025", "2024"
    )
    row = build_operator_registry(
        production, wells, replace(policy, as_of="2024-12")
    ).registry.iloc[0]
    assert row.gas_mcfd_per_well_median == pytest.approx(240 / 366)


def test_cli_uses_config(inputs, tmp_path, capsys):
    from worldenergydata.texas_rrc.operators.__main__ import main

    production, wells = inputs
    p, w = tmp_path / "production.csv", tmp_path / "wells.csv"
    production.to_csv(p, index=False)
    wells.to_csv(w, index=False)
    main(
        [
            "--production",
            str(p),
            "--wells",
            str(w),
            "--as-of",
            "2025-12",
            "--output-root",
            str(tmp_path / "build"),
            "--allow-non-catalog-root",
        ]
    )
    assert "Registry operators: 1" in capsys.readouterr().out
    manifest = tmp_path / "build/curated/operators/operator_registry/manifest.json"
    assert json.loads(manifest.read_text())["policy"]["stripper_bopd"] is None


def test_gas_rate_does_not_require_crude_or_infer_oil(inputs, policy):
    """Gas-well hand calculation: 12*20 / 365 Mcf/calendar day.

    RRC PDQ FAQ distinguishes crude oil from gas-well condensate. Missing
    crude oil cannot invalidate a known gas volume or establish oil BOPD.
    """
    production, wells = inputs
    production.loc[production.oil_gas_code == "G", "oil_bbl"] = None
    row = build_operator_registry(production, wells, policy).registry.iloc[0]
    assert row.gas_mcfd_per_well_median == pytest.approx(240 / 365)
    assert pd.isna(row.bopd_per_well_median)
    assert pd.isna(row.stripper_share)
    assert not row.usable_last12


def test_unreported_current_inventory_unit_is_a_gap(inputs, policy):
    production, wells = inputs
    extra = wells.iloc[[0]].assign(well_id="W4", lease_no="MISSING")
    result = build_operator_registry(production, pd.concat([wells, extra]), policy)
    assert not result.registry.iloc[0].usable_last12
    assert result.quality["unmatched_well_units"] == 1
