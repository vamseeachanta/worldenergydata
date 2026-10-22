"""P&A screen expectations use independent arithmetic on synthetic inputs.

Status meanings: BSEE Data Center, Borehole Status Code enumeration, retrieved
2026-10-20; https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields.
Synthetic prices below are arithmetic fixtures, not engineering cost estimates.
"""

from copy import deepcopy

import pytest

from worldenergydata.field_development.well_pa_risk import build_well_pa_signals


def snapshot():
    """Six attributed rows: TA, TA, COM, COM, COM, PA; one unmatched row."""
    return {
        "basis": "Synthetic registered-bottom-lease attribution",
        "source_boreholes": 7,
        "joined_boreholes": 6,
        "unmatched_counts": {"lease_not_in_registry": 1},
        "source_sha256": "a" * 64,
        "registry_sha256": "b" * 64,
        "source_retrieved_at_utc": "2026-10-20T00:00:00+00:00",
        "status_definitions_url": (
            "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields"
        ),
        "fields": [
            {
                "field_id": "sample_field",
                "registered_leases": ["G00001"],
                "borehole_count": 6,
                "status_counts": {"TA": 2, "COM": 3, "PA": 1},
            },
            {
                "field_id": "empty_field",
                "registered_leases": ["G00002"],
                "borehole_count": 0,
                "status_counts": {},
            },
        ],
    }


def prices():
    """Hypothetical inputs: TA costs 10 USD/borehole; COM costs 20 USD/borehole."""
    return {
        "sample_field": {
            "unit_cost_usd": {"TA": "10", "COM": "20"},
            "source": "Synthetic hand calculation in test_well_pa_risk.py",
            "price_basis": "Hypothetical constant USD; arithmetic only",
        }
    }


def test_counts_and_provenance_without_cost_basis():
    """2 TA + 3 COM = 5 candidates; PA is excluded; 6 + 1 = 7 source rows."""
    data = snapshot()
    before = deepcopy(data)
    signals = build_well_pa_signals(data)
    signal = signals["sample_field"]
    assert signal["ta_count"] == 2
    assert signal["com_count"] == 3
    assert signal["candidate_boreholes"] == 5
    assert signal["other_status_counts"] == {"PA": 1}
    assert signal["cost"] == {
        "status": "NOT_EVALUATED",
        "reason": "missing_unit_cost_basis",
        "total_usd": None,
    }
    assert signal["provenance"]["source_sha256"] == data["source_sha256"]
    assert signal["provenance"]["unmatched_counts"] == data["unmatched_counts"]
    assert "TA 2 / COM 3" in signal["label"]
    assert data == before


def test_scenario_cost_hand_calculation():
    """C = (2 boreholes * 10 USD) + (3 boreholes * 20 USD) = 80 USD."""
    cost = build_well_pa_signals(snapshot(), prices())["sample_field"]["cost"]
    assert cost["status"] == "SCENARIO"
    assert cost["total_usd"] == "80"
    assert cost["by_status_usd"] == {"TA": "20", "COM": "60"}
    assert cost["source"] == prices()["sample_field"]["source"]
    assert cost["price_basis"] == prices()["sample_field"]["price_basis"]


def test_decimal_costs_are_exact():
    """2 * 0.1 + 3 * 0.2 = 0.8 USD exactly, without binary float residue."""
    inputs = prices()
    inputs["sample_field"]["unit_cost_usd"] = {"TA": "0.1", "COM": "0.2"}
    cost = build_well_pa_signals(snapshot(), inputs)["sample_field"]["cost"]
    assert cost["total_usd"] == "0.8"


def test_empty_field_has_no_inferred_zero_liability():
    """No observed boreholes gives no cost, even with explicit prices."""
    inputs = {"empty_field": prices()["sample_field"]}
    signals = build_well_pa_signals(snapshot(), inputs)
    signal = signals["empty_field"]
    assert signal["availability"] == "no_boreholes_on_registered_leases"
    assert signal["cost"]["status"] == "NOT_EVALUATED"
    assert signal["cost"]["reason"] == "no_boreholes_on_registered_leases"
    assert signal["cost"]["total_usd"] is None


def test_unknown_and_missing_statuses_are_explicit_and_excluded():
    """Two unknown + three missing + one PA gives zero TA/COM candidates."""
    data = snapshot()
    data["fields"][0]["status_counts"] = {"NEW": 2, "MISSING": 3, "PA": 1}
    signal = build_well_pa_signals(data, prices())["sample_field"]
    assert signal["candidate_boreholes"] == 0
    assert signal["other_status_counts"] == {"NEW": 2, "MISSING": 3, "PA": 1}
    assert signal["cost"]["reason"] == "no_ta_com_boreholes"
    assert signal["cost"]["total_usd"] is None


@pytest.mark.parametrize("missing", ["TA", "COM", "source", "price_basis"])
def test_partial_cost_basis_is_not_evaluated(missing):
    inputs = prices()
    basis = inputs["sample_field"]
    if missing in ("TA", "COM"):
        del basis["unit_cost_usd"][missing]
    else:
        del basis[missing]
    cost = build_well_pa_signals(snapshot(), inputs)["sample_field"]["cost"]
    assert cost["status"] == "NOT_EVALUATED"
    assert cost["total_usd"] is None


@pytest.mark.parametrize("invalid", ["-1", "NaN", "Infinity", "bad", True, None])
def test_invalid_unit_cost_is_rejected(invalid):
    inputs = prices()
    inputs["sample_field"]["unit_cost_usd"]["TA"] = invalid
    with pytest.raises(ValueError, match="unit cost"):
        build_well_pa_signals(snapshot(), inputs)


@pytest.mark.parametrize("invalid", [-1, 1.5, True, "2"])
def test_invalid_counts_are_rejected(invalid):
    data = snapshot()
    data["fields"][0]["status_counts"]["TA"] = invalid
    with pytest.raises(ValueError, match="count"):
        build_well_pa_signals(data)


def test_duplicate_fields_and_inconsistent_totals_are_rejected():
    data = snapshot()
    data["fields"].append(deepcopy(data["fields"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        build_well_pa_signals(data)
    data = snapshot()
    data["fields"][0]["borehole_count"] += 1
    with pytest.raises(ValueError, match="count"):
        build_well_pa_signals(data)
    data = snapshot()
    data["source_boreholes"] += 1
    with pytest.raises(ValueError, match="count"):
        build_well_pa_signals(data)


def test_unknown_cost_field_is_rejected():
    with pytest.raises(ValueError, match="Unknown cost field"):
        build_well_pa_signals(snapshot(), {"typo": prices()["sample_field"]})
