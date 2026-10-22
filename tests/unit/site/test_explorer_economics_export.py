"""Offline release-boundary tests for the Explorer economics refresh.

Synthetic worked example (USD millions): pay 100 at time zero and receive
two million barrels at a flat price p with no costs or discounting. Then
NPV(p) = -100 + 2*p, breakeven = 100/2 = 50 USD/bbl, and sensitivity
is 2 million USD per USD/bbl. At p=40, NPV=-20; at p=60, NPV=20.
These expected values are independent hand calculations, not model outputs.
The fixture's basis label describes the production contract; no discounted
cashflow is computed by the exporter.

Equation source: OpenStax, Principles of Finance (2022), section 16.2,
equation 16.1: NPV is present-value inflows minus present-value outflows.
https://openstax.org/books/principles-finance/pages/16-2-net-present-value-npv-method
"""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts/hf_export/publish_explorer_refresh_to_hf.py"
spec = importlib.util.spec_from_file_location("economics_export", SCRIPT)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

LEVELS = ("npv_mm", "breakeven_wti", "sens_mm_per_dollar")
BASIS = "life_to_date_pretax_npv_at_10pct"


def record(**changes):
    """Values from the independent worked example in the module docstring."""
    return {
        "npv_mm": -20.0,
        "breakeven_wti": 50.0,
        "sens_mm_per_dollar": 2.0,
        "economics_status": "surfaced",
        "economics_basis": BASIS,
        "eur_mmbbl": None,
        "eur_source": "synthetic worked example",
        "eur_confidence": "none",
        **changes,
    }


def inputs(tmp_path, monkeypatch, records):
    performance = tmp_path / "performance.json"
    performance.write_text(
        json.dumps({"fields": records}), encoding="utf-8", newline="\n"
    )
    monkeypatch.setattr(export, "PERFORMANCE", performance)
    live = tmp_path / "fields.parquet"
    # Deliberately stale economics in the live table must never survive refresh.
    pd.DataFrame(
        {
            "id": [*records, "absent"],
            "npv_mm": 20.0,  # Same hand example at p=60.
            "unrelated": "preserved",
        }
    ).to_parquet(live, index=False)
    return live


@pytest.mark.parametrize("npv", [-20.0, 20.0])
def test_surfaced_values_preserve_signed_ltd_npv(tmp_path, monkeypatch, npv):
    """Both signs follow the hand calculation above; negative LTD is valid."""
    live = inputs(tmp_path, monkeypatch, {"mature": record(npv_mm=npv)})
    actual = export.build_fields(live).set_index("id")
    assert actual.loc["mature", list(LEVELS)].tolist() == [npv, 50.0, 2.0]
    assert actual.loc["mature", "economics_basis"] == BASIS
    assert actual["unrelated"].eq("preserved").all()
    assert actual.loc["absent", list(LEVELS)].isna().all()


@pytest.mark.parametrize(
    "status", ["withheld", "early_life", "unavailable", None, "future"]
)
def test_non_surfaced_status_nulls_even_populated_values(tmp_path, monkeypatch, status):
    live = inputs(tmp_path, monkeypatch, {"blocked": record(economics_status=status)})
    actual = export.build_fields(live).set_index("id")
    assert actual.loc["blocked", list(LEVELS)].isna().all()
    output = tmp_path / "release.parquet"
    actual.reset_index().to_parquet(output, index=False)
    restored = pd.read_parquet(output).set_index("id")
    assert restored.loc["blocked", list(LEVELS)].isna().all()


@pytest.mark.parametrize("basis", [None, "full_cycle", ""])
def test_surfaced_values_require_known_ltd_basis(tmp_path, monkeypatch, basis):
    live = inputs(tmp_path, monkeypatch, {"mature": record(economics_basis=basis)})
    with pytest.raises(ValueError, match="economics_basis"):
        export.build_fields(live)


@pytest.mark.parametrize("key", LEVELS)
@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), "20", True])
def test_surfaced_values_require_finite_numbers(tmp_path, monkeypatch, key, bad):
    live = inputs(tmp_path, monkeypatch, {"mature": record(**{key: bad})})
    with pytest.raises(ValueError, match=key):
        export.build_fields(live)


def grid_input(tmp_path, monkeypatch, status="surfaced"):
    """The grid's values also use the module's independent hand example."""
    path = tmp_path / "grid.json"
    path.write_text(
        json.dumps(
            {
                "fields": {
                    "mature": {
                        "economics_status": status,
                        "grid": [
                            {
                                "wti_price_multiplier": 1.0,
                                "discount_rate": 0.0,
                                "npv_musd": -20.0,
                                "economics_status": "surfaced",
                            }
                        ],
                        # Reference price is 40: 50/40 = 1.25 at breakeven.
                        "breakeven_multiplier_by_rate": {"0": 1.25},
                    }
                }
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(export, "PARAMETRIC_JSON", path)


@pytest.mark.parametrize("status", ["withheld", "early_life", "unavailable", None])
def test_grid_cannot_override_current_withholding(tmp_path, monkeypatch, status):
    inputs(tmp_path, monkeypatch, {"mature": record(economics_status=status)})
    grid_input(tmp_path, monkeypatch)
    actual = export.build_parametric()
    assert actual.empty
    assert "field" in actual.columns  # Empty releases still have a stable schema.


def test_grid_requires_both_snapshots_to_allow_release(tmp_path, monkeypatch):
    inputs(tmp_path, monkeypatch, {"mature": record()})
    grid_input(tmp_path, monkeypatch, status="withheld")
    assert export.build_parametric().empty
    grid_input(tmp_path, monkeypatch)
    actual = export.build_parametric()
    assert actual["field"].tolist() == ["mature"]
    assert actual["npv_musd"].tolist() == [-20.0]
    assert actual["breakeven_multiplier"].tolist() == [1.25]
    assert actual["economics_basis"].tolist() == ["life_to_date_pretax_npv"]


def test_grid_excludes_fields_missing_from_current_contract(tmp_path, monkeypatch):
    inputs(tmp_path, monkeypatch, {})
    grid_input(tmp_path, monkeypatch)
    assert export.build_parametric().empty


@pytest.mark.parametrize("status", ["withheld", None])
def test_grid_row_status_cannot_override_withholding(tmp_path, monkeypatch, status):
    inputs(tmp_path, monkeypatch, {"mature": record()})
    grid_input(tmp_path, monkeypatch)
    grid = json.loads(export.PARAMETRIC_JSON.read_text(encoding="utf-8"))
    grid["fields"]["mature"]["grid"][0]["economics_status"] = status
    export.PARAMETRIC_JSON.write_text(json.dumps(grid), encoding="utf-8", newline="\n")
    assert export.build_parametric().empty


def test_card_explains_release_policy_without_promising_full_cycle():
    card = export.build_readme(0, [])
    assert "economics_status = surfaced" in card
    assert "stale grid cannot" in card
    assert "Negative life-to-date NPV" in card
    assert "Full-cycle economics remain" in card
    assert f"`fields.economics_basis = {BASIS}`" in card
    assert "`parametric_economics.economics_basis = life_to_date_pretax_npv`" in card
    assert "each row's `discount_rate`" in card


def test_committed_economics_propagate_without_reinterpreting_npv(tmp_path):
    """Expected values are the reviewed, committed source snapshots (#976).

    This is a propagation check, not an independent financial-model validation.
    It compares every economics level and the sensitivity-grid baseline with
    the performance contract, and the contract with the Explorer bundle.
    """
    perf = json.loads(export.PERFORMANCE.read_text(encoding="utf-8"))["fields"]
    bundle = json.loads(export.BUNDLE.read_text(encoding="utf-8"))["fields"]
    live = tmp_path / "fields.parquet"
    pd.DataFrame({"id": list(bundle)}).to_parquet(live, index=False)
    actual = export.build_fields(live).set_index("id")
    for field, row in actual.iterrows():
        source = perf.get(field, {})
        expected = bundle[field].get("performance") or {}
        for key in (*LEVELS, "economics_status", "economics_basis"):
            assert source.get(key) == expected.get(key)
        for key in LEVELS:
            value = source.get(key)
            if source.get("economics_status") == "surfaced":
                assert row[key] == value
            else:
                assert pd.isna(row[key])

    grid = json.loads(export.PARAMETRIC_JSON.read_text(encoding="utf-8"))
    published = export.build_parametric()
    surfaced = {k for k, v in perf.items() if v["economics_status"] == "surfaced"}
    assert set(published["field"]) == surfaced
    for match in grid["baseline_match"]:
        if match["field"] in surfaced:
            assert match["parametric_npv_mm_at_1x_r0"] == perf[match["field"]]["npv_mm"]
    for field in surfaced:
        # Unity means the unchanged price deck; rate is an explicit source input.
        baseline = published[
            (published["field"] == field)
            & (published["wti_price_multiplier"] == 1.0)
            & (
                published["discount_rate"]
                == grid["fields"][field]["discount_rate_base"]
            )
        ]
        assert baseline["npv_musd"].tolist() == [perf[field]["npv_mm"]]
