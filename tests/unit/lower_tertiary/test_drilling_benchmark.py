"""Independent arithmetic examples for the descriptive days-versus-depth badge.

Synthetic inputs are test quantities, not measured engineering data. OLS follows
NIST/SEMATECH e-Handbook, section 4.4.3.1, straight-line model
(web edition retrieved 2026-10-19):
https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))

from lower_tertiary.drilling_benchmark import benchmark_well, load_benchmark_rows


def _row(api, depth, days):
    return {
        "api_well_number": api,
        "max_well_bore_tvd_ft": depth,
        "drilling_days": days,
    }


def _well(**updates):
    # Invented identifier and quantities for the hand calculation below.
    return dict(api="100000000001", max_tvd_ft=20000, drilling_rig_days=60, **updates)


def _rows():
    return [
        _row("100000000001.0", 20000, 60),
        _row("100000000002.0", 10000, 20),
        _row("100000000003.0", 30000, 40),
    ]


def _builder():
    spec = importlib.util.spec_from_file_location(
        "timeline_benchmark_test",
        REPO / "scripts/lower_tertiary/build_well_timelines.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_leave_one_out_ratio_from_independent_hand_calculation():
    """Peers: xbar=20000, ybar=30; Sxy=200000, Sxx=200000000.

    b=0.001 day/ft; a=10 days. At 20000 ft, fitted=30 days;
    observed/fitted=60/30=2. The target's 60 days are excluded from the fit.
    """
    result = benchmark_well(_well(), _rows())
    assert result["status"] == "EVALUATED"
    assert result["peer_count"] == 2
    assert result["fitted_days"] == pytest.approx(30)
    assert result["observed_to_fitted"] == pytest.approx(2)
    assert "acceptance" in result["limitation"]


@pytest.mark.parametrize(
    "value", [None, "", "bad", 0, -1, float("nan"), float("inf"), True]
)
@pytest.mark.parametrize("key", ["max_tvd_ft", "drilling_rig_days"])
def test_invalid_target_is_not_evaluated(key, value):
    well = _well()
    well[key] = value
    assert benchmark_well(well, _rows())["status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("rows", [[], [_row("100000000002", 10000, 20)]])
def test_missing_target_key_is_not_evaluated(rows):
    assert benchmark_well(_well(), rows)["status"] == "NOT_EVALUATED"


def test_missing_api_does_not_join_anonymous_rows():
    well = _well()
    well["api"] = None
    assert benchmark_well(well, [_row("", 20000, 60)])["status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("index", [0, 1])
def test_duplicate_target_or_peer_key_is_not_evaluated(index):
    rows = _rows()
    rows.append(dict(rows[index]))
    result = benchmark_well(_well(), rows)
    assert result["status"] == "NOT_EVALUATED"
    assert "duplicate" in result["reason"].lower()


def test_mixed_source_duration_is_not_compared():
    well = _well()
    well["drilling_rig_days"] = 61
    result = benchmark_well(well, _rows())
    assert result["status"] == "NOT_EVALUATED"
    assert "disagree" in result["reason"]


@pytest.mark.parametrize("depths", [(10000, 10000), (10000, 15000)])
def test_extrapolation_is_not_evaluated(depths):
    rows = _rows()
    for row, depth in zip(rows[1:], depths):
        row["max_well_bore_tvd_ft"] = depth
    result = benchmark_well(_well(), rows)
    assert result["status"] == "NOT_EVALUATED"
    assert result["reason"] == "Target TVD lies outside the peer depth range"


def test_constant_depth_is_not_evaluated():
    well = _well()
    rows = _rows()
    for row in rows:
        row["max_well_bore_tvd_ft"] = well["max_tvd_ft"]
    result = benchmark_well(well, rows)
    assert result["status"] == "NOT_EVALUATED"
    assert result["peer_count"] == 2
    assert result["reason"] == "Peer TVDs are constant; slope cannot be calculated"


def test_invalid_peers_do_not_count_towards_fit():
    rows = _rows()
    rows[1]["drilling_days"] = "NaN"
    result = benchmark_well(_well(), rows)
    assert result["status"] == "NOT_EVALUATED"
    assert result["peer_count"] == 1


def test_csv_loader_preserves_api_and_missing_file_is_explicit(tmp_path):
    path = tmp_path / "cohort.csv"
    path.write_text(
        "api_well_number,max_well_bore_tvd_ft,drilling_days\n"
        "100000000001.0,20000,60\n"
    )
    assert load_benchmark_rows(path) == [_row("100000000001.0", "20000", "60")]
    assert load_benchmark_rows(tmp_path / "absent.csv") == []
    path.write_text("unrelated\nvalue\n")
    with pytest.raises(ValueError, match="columns"):
        load_benchmark_rows(path)


def test_drill_card_badge_uses_same_benchmark_result():
    builder = _builder()
    well = dict(
        _well(),
        first_oil="2020-01-01",
        spud_date="2019-01-01",
        field_id="example",
        slot="A",
        completion_rig_days=10,
    )
    field = {"display_name": "Example"}
    result = builder.facts_to_well(well, field, drilling_rows=_rows())
    card = result["cards"][0]
    assert card["badge"] == "Days vs depth · 2.0× fitted"
    assert "descriptive" in " ".join(card["li"])
    assert result["drilling_benchmark"]["fitted_days"] == pytest.approx(30)
    page = builder.render(result)
    assert 'class="benchmark-badge"' in page
    assert "2.0× fitted" in page
    json.dumps(result, allow_nan=False)


def test_missing_benchmark_shows_reason_in_card():
    builder = _builder()
    well = dict(
        _well(),
        first_oil="2020-01-01",
        spud_date="2019-01-01",
        field_id="example",
        slot="A",
    )
    result = builder.facts_to_well(well, {"display_name": "Example"})
    card = result["cards"][0]
    assert "NOT_EVALUATED" in card["badge"]
    assert result["drilling_benchmark"]["reason"] in card["li"]


def test_three_peer_fit_from_independent_hand_calculation():
    """x=(10000,20000,30000), y=(20,50,40): xbar=20000, ybar=110/3.

    Sxy=200000, Sxx=200000000, b=0.001. At mean x, yhat=110/3;
    ratio=60/(110/3)=18/11. No output of the implementation is reused.
    """
    rows = _rows() + [_row("100000000004", 20000, 50)]
    result = benchmark_well(_well(), list(reversed(rows)))
    assert result["peer_count"] == 3
    assert result["fitted_days"] == pytest.approx(110 / 3)
    assert result["observed_to_fitted"] == pytest.approx(18 / 11)


def test_generator_reads_saved_cohort_and_writes_badge(tmp_path, monkeypatch):
    """The same 60/30=2 hand example shall reach a generated timeline page."""
    from types import SimpleNamespace

    builder = _builder()
    facts = tmp_path / "facts.json"
    cohort = tmp_path / "cohort.csv"
    well = dict(
        _well(),
        first_oil="2020-01-01",
        spud_date="2019-01-01",
        field_id="example",
        slot="A",
        completion_rig_days=10,
    )
    facts.write_text(
        json.dumps(
            {
                "fields": {"example": {"display_name": "Example"}},
                "wells": [well],
            }
        )
    )
    cohort.write_text(
        "api_well_number,max_well_bore_tvd_ft,drilling_days\n"
        "100000000001.0,20000,60\n"
        "100000000002.0,10000,20\n"
        "100000000003.0,30000,40\n"
    )
    we = SimpleNamespace(
        compute_well_economics=lambda *a, **k: SimpleNamespace(to_json=dict),
        norms_comparison=lambda *a: {},
    )
    monkeypatch.setattr(builder, "FACTS", facts)
    monkeypatch.setattr(builder, "DRILLING_CSV", cohort)
    monkeypatch.setattr(builder, "HERE", tmp_path)
    monkeypatch.setattr(builder.site_nav, "inject_for", lambda page, *a: page)
    monkeypatch.setattr(
        builder,
        "_economics_context",
        lambda: (
            we,
            {"display": {}},
            None,
            None,
            {},
            {},
            None,
        ),
    )
    builder.main()
    page = (tmp_path / "example_A_well.html").read_text()
    assert "Days vs depth · 2.0× fitted" in page
    assert '"peer_count": 2' in page
    assert '"fitted_days": 30.0' in page
    assert (tmp_path / "index.html").is_file()


@pytest.mark.parametrize(
    "depths,days", [([1e308, 1e308], [20, 40]), ([10000, 30000], [1e-308, 1e-308])]
)
def test_finite_extreme_inputs_cannot_emit_nonfinite_results(depths, days):
    """Finite inputs can overflow sums or the ratio; no usable value is implied."""
    rows = _rows()
    well = _well()
    well["drilling_rig_days"] = rows[0]["drilling_days"] = 1e308
    if depths[0] == depths[1]:
        well["max_tvd_ft"] = rows[0]["max_well_bore_tvd_ft"] = depths[0]
    for row, x, y in zip(rows[1:], depths, days):
        row["max_well_bore_tvd_ft"] = x
        row["drilling_days"] = y
    result = benchmark_well(well, rows)
    assert result["status"] == "NOT_EVALUATED"
    json.dumps(result, allow_nan=False)
