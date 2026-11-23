"""Reference-only per-field interests, source locators and calculation isolation."""

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from tests.unit.lower_tertiary import test_npv as npv_tests
from worldenergydata.lower_tertiary import portfolio_analytics
from worldenergydata.lower_tertiary.npv import (
    calculate_monthly_financials,
    load_field_inputs,
    summarize_field_financials,
)

FIELDS = Path(__file__).resolve().parents[3] / "config/analysis/lower_tertiary/fields"
# Literal main-branch inputs; these remain the sole calculation shares.
FLAT_PARTNERS = {
    "cascade_chinook": [
        {"name": "TotalEnergies", "working_interest": 0.60},
        {"name": "Equinor", "working_interest": 0.40},
    ],
    "jack_st_malo": [
        {"name": "Chevron", "working_interest": 0.51},
        {"name": "Equinor", "working_interest": 0.245},
        {"name": "Suncor", "working_interest": 0.245},
    ],
}
# Issue 747, first comment, discrepancy rows 3/P4 and 9/P7 only.
VERIFIED = {
    "cascade_chinook": {
        "Cascade": ("MP GOM", 1.00, "P4", 3, "FY2018"),
        "Chinook": ("MP GOM", 0.666, "P4", 3, "FY2018"),
    },
    "jack_st_malo": {
        "Jack": ("Chevron", 0.50, "P7", 9, "FY2014"),
        "St. Malo": ("Chevron", 0.51, "P7", 9, "FY2014"),
    },
}
SOURCES = {
    "P4": {
        "title": "Murphy Oil Corporation annual report",
        "url": (
            "https://www.sec.gov/Archives/edgar/data/717423/"
            "000071742319000016/mur-20181231x10k.htm"
        ),
        "date": "FY2018 (filed 2019)",
    },
    "P7": {
        "title": "Chevron Corporation annual report",
        "url": (
            "https://www.sec.gov/Archives/edgar/data/93410/"
            "000009341015000010/cvx-123114x10kdoc.htm"
        ),
        "date": "FY2014 (filed 2015)",
    },
}


def read_config(field_id):
    return yaml.safe_load((FIELDS / f"{field_id}.yml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("field_id", VERIFIED)
def test_verified_reference_block_loads_unchanged(field_id):
    config = read_config(field_id)
    block = config["partners_by_field"]
    loaded = load_field_inputs(FIELDS, {"fields": {}})[field_id]
    assert loaded["partners_by_field"] == block
    assert loaded["raw"] == config["field"]
    assert set(block) == set(VERIFIED[field_id])
    for field_name, (name, share, key, row, period) in VERIFIED[field_id].items():
        assert block[field_name] == [
            {
                "name": name,
                "share": share,
                "source": {"key": key, **SOURCES[key], "research_note_row": row},
                "source_class": "primary",
                "as_of": period,
            }
        ]


@pytest.mark.parametrize("field_id", FLAT_PARTNERS)
def test_flat_partners_remain_main_literals(field_id):
    config = read_config(field_id)
    assert config["field"]["partners"] == FLAT_PARTNERS[field_id]
    assert (
        load_field_inputs(FIELDS, {"fields": {}})[field_id]["raw"]["partners"]
        == FLAT_PARTNERS[field_id]
    )


def test_file_without_reference_block_preserves_legacy_profile():
    config = read_config("julia")
    assert "partners_by_field" not in config
    loaded = load_field_inputs(FIELDS, {"fields": {}})["julia"]
    assert loaded == {
        "field_id": "julia",
        "display_name": config["field"]["display_name"],
        "status": config["field"]["status"],
        "first_oil": pd.Timestamp(config["field"]["first_oil"]),
        "data_through": pd.Timestamp(config["field"]["data_through"]),
        "capex": config["field"]["capex"],
        "leases": [],
        "opex_per_boe": config["field"]["opex_per_boe"],
        "raw": config["field"],
    }


@pytest.mark.parametrize("share", [-0.01, 1.01, "0.5", True, float("nan")])
def test_validator_rejects_invalid_share(share):
    from worldenergydata.lower_tertiary.partner_reference import (
        validate_partners_by_field,
    )

    block = copy.deepcopy(read_config("cascade_chinook")["partners_by_field"])
    block["Cascade"][0]["share"] = share
    with pytest.raises(ValueError, match="share"):
        validate_partners_by_field("cascade_chinook", block)


@pytest.mark.parametrize("field_id", VERIFIED)
def test_validator_rejects_foreign_field_name(field_id):
    from worldenergydata.lower_tertiary.partner_reference import (
        validate_partners_by_field,
    )

    other_id = next(key for key in VERIFIED if key != field_id)
    block = copy.deepcopy(read_config(other_id)["partners_by_field"])
    with pytest.raises(ValueError, match="field name"):
        validate_partners_by_field(field_id, block)


@pytest.mark.parametrize("source", [None, "", "  ", {}, True, 1, {"title": " "}])
def test_validator_rejects_empty_source(source):
    from worldenergydata.lower_tertiary.partner_reference import (
        validate_partners_by_field,
    )

    block = copy.deepcopy(read_config("cascade_chinook")["partners_by_field"])
    if source is None:
        del block["Cascade"][0]["source"]
    else:
        block["Cascade"][0]["source"] = source
    with pytest.raises(ValueError, match="source"):
        validate_partners_by_field("cascade_chinook", block)


def test_loader_rejects_invalid_reference_block(tmp_path):
    config = read_config("cascade_chinook")
    config["partners_by_field"]["Cascade"][0]["share"] = -0.01
    (tmp_path / "cascade_chinook.yml").write_text(
        yaml.safe_dump(config), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="share"):
        load_field_inputs(tmp_path, {"fields": {}})


def test_partial_shares_and_empty_block_are_valid():
    from worldenergydata.lower_tertiary.partner_reference import (
        validate_partners_by_field,
    )

    for field_id in VERIFIED:
        block = read_config(field_id)["partners_by_field"]
        validate_partners_by_field(field_id, block)
        validate_partners_by_field(field_id, {})
        validate_partners_by_field(field_id, None)


@pytest.mark.parametrize("field_id", VERIFIED)
def test_loader_preserves_explicit_empty_block(tmp_path, field_id):
    config = read_config(field_id)
    config["partners_by_field"] = {}
    (tmp_path / f"{field_id}.yml").write_text(yaml.safe_dump(config), encoding="utf-8")
    assert (
        load_field_inputs(tmp_path, {"fields": {}})[field_id]["partners_by_field"] == {}
    )


def test_concentration_bytes_ignore_reference_block(monkeypatch, tmp_path):
    # Real paired configurations; no production-data files or invented economics.
    loaded = load_field_inputs(FIELDS, {"fields": {}})
    configs = {field_id: read_config(field_id) for field_id in VERIFIED}
    for field_id, config in configs.items():
        assert loaded[field_id]["partners_by_field"] == config["partners_by_field"]
        (tmp_path / f"{field_id}.yml").write_text(
            yaml.safe_dump(config), encoding="utf-8"
        )
    monkeypatch.setattr(portfolio_analytics, "fields_config_dir", lambda: tmp_path)
    before = portfolio_analytics.analyze_operator_concentration(tuple(VERIFIED))
    for field_id, config in configs.items():
        del config["partners_by_field"]
        (tmp_path / f"{field_id}.yml").write_text(
            yaml.safe_dump(config), encoding="utf-8"
        )
    after = portfolio_analytics.analyze_operator_concentration(tuple(VERIFIED))
    assert json.dumps(before.to_dict(orient="records"), sort_keys=True) == json.dumps(
        after.to_dict(orient="records"), sort_keys=True
    )


def financial_outputs(profile):
    """Reuse the synthetic production and economics helpers from test_npv."""
    summary_tests = npv_tests.TestSummarizeFieldFinancials()
    economics = npv_tests.TestCalculateMonthlyFinancials()._make_econ_config()
    economics.update(summary_tests._make_econ_config())
    monthly = calculate_monthly_financials(
        summary_tests._make_monthly(), economics, profile["opex_per_boe"]
    )
    return monthly, summarize_field_financials(monthly, profile, economics)


@pytest.mark.parametrize("field_id", VERIFIED)
def test_npv_outputs_ignore_reference_block(tmp_path, field_id):
    """Pin: partner reference data changes no monthly or summary output on main."""
    with_reference = load_field_inputs(FIELDS, {"fields": {}})[field_id]
    config = read_config(field_id)
    del config["partners_by_field"]
    (tmp_path / f"{field_id}.yml").write_text(yaml.safe_dump(config), encoding="utf-8")
    without_reference = load_field_inputs(tmp_path, {"fields": {}})[field_id]

    assert "partners_by_field" in with_reference
    assert "partners_by_field" not in without_reference
    assert {
        key: value
        for key, value in with_reference.items()
        if key != "partners_by_field"
    } == without_reference

    before_monthly, before_summary = financial_outputs(with_reference)
    after_monthly, after_summary = financial_outputs(without_reference)
    pd.testing.assert_frame_equal(before_monthly, after_monthly, check_exact=True)
    assert before_summary == after_summary


def test_shared_production_monthly_outputs_equal_but_summaries_differ():
    """Pin: shared production/economics and equal opex give equal monthly outputs."""
    profiles = load_field_inputs(FIELDS, {"fields": {}})
    cascade = profiles["cascade_chinook"]
    julia = profiles["julia"]
    assert cascade["opex_per_boe"] == julia["opex_per_boe"]
    cascade_monthly, cascade_summary = financial_outputs(cascade)
    julia_monthly, julia_summary = financial_outputs(julia)

    pd.testing.assert_frame_equal(cascade_monthly, julia_monthly, check_exact=True)
    assert cascade["first_oil"] != julia["first_oil"]
    assert cascade_summary != julia_summary
    for key in ("CAPEX ($MM)", "NPV Operations ($MM)", "NPV Project ($MM)"):
        assert cascade_summary[key] != julia_summary[key]
