"""Field selection and request isolation at the report generation boundary."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from scripts.lower_tertiary import generate_field_economics_report as gen
from scripts.lower_tertiary import regenerate_all_field_reports as batch
from worldenergydata.lower_tertiary import v30_financial_reproducer as fin

FIELDS = [
    "Jack St Malo",
    "Stones",
    "Julia",
    "Big Foot",
    "Cascade Chinook",
    "Anchor",
    "Shenandoah",
]


@pytest.fixture
def report_inputs(monkeypatch):
    # Isolate disk-heavy financial and operations inputs; assemble real Markdown.
    rows = {
        name: {
            "npv_usd": (index - 3) * 100_000_000.0,
            "total_oil_bbl": 1_000_000,
            "revenue_usd": 80_000_000,
            "royalty_usd": 15_000_000,
            "variable_opex_usd": 4_000_000,
            "fixed_opex_usd": 20_000_000,
            "dnc_total_usd": 100_000_000,
            "facilities_cost_usd": 200_000_000,
            "net_cashflow_usd": -259_000_000,
            "producers": 1,
            "injectors": 0,
            "wellbores": 1,
        }
        for index, name in enumerate(FIELDS)
    }

    def timeline(name, **kwargs):
        npv = rows[name]["npv_usd"]
        return {
            "timeline": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2025-04-01", "2025-05-01"]),
                    "cumulative_npv_usd": [-500_000_000, npv],
                    "net_cashflow_usd": [-500_000_000, npv + 500_000_000],
                }
            ),
            "terminal_npv_usd": npv,
            "dev_system": "subsea15",
            "first_oil": pd.Timestamp("2025-04-01"),
            "discount_rate_annual": 0.10,
        }

    def stackup(name, **kwargs):
        npv = rows[name]["npv_usd"]
        return {
            "field_terminal_npv_usd": npv,
            "sum_well_npv_usd": npv,
            "residual_usd": 0,
            "wells": [],
            "blocks": [],
            "blocks_note": "Synthetic generation inputs",
        }

    monkeypatch.setattr(gen, "_ensure_ogor_loader", lambda: "synthetic inputs")
    monkeypatch.setattr(gen, "leases_for_dev", lambda name: ["G12345"])
    monkeypatch.setattr(
        gen, "build_operations_timeline", lambda *a, **kw: pd.DataFrame()
    )
    monkeypatch.setattr(fin, "reproduce_v30_financials", lambda **kw: rows)
    monkeypatch.setattr(fin, "build_field_npv_timeline", timeline)
    monkeypatch.setattr(fin, "build_well_npv_stackup", stackup)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Jack St Malo", "$-300.0 M"),
        ("Stones", "$-200.0 M"),
        ("Julia", "$-100.0 M"),
        ("Big Foot", "$0.0 M"),
        ("Cascade Chinook", "$100.0 M"),
        ("Anchor", "$200.0 M"),
        ("Shenandoah", "$300.0 M"),
    ],
)
def test_generated_header_uses_selected_field_npv(name, expected, report_inputs):
    md = gen.build_report(name)
    header = md.splitlines()[4]
    body = next(line for line in md.splitlines() if line.startswith("| **NPV @"))
    assert f"**{expected}**" in header
    assert f"**{expected}**" in body
    assert "## Revision history" in md
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", md)


@pytest.mark.parametrize(
    "changed, expected",
    [
        ({"end_date": "2026-04-30"}, 100),
        ({"first_oil_overrides": {"Cascade Chinook": "2012-09-01"}}, 10),
        ({"input_set": "v50_kc"}, 1),
    ],
)
def test_batch_financial_cache_distinguishes_requests(monkeypatch, changed, expected):
    calls = []

    def financials(end_date=None, first_oil_overrides=None, input_set="v30"):
        calls.append((end_date, first_oil_overrides, input_set))
        return {
            "npv_usd": 100 * bool(end_date)
            + 10 * bool(first_oil_overrides)
            + (input_set == "v50_kc")
        }

    monkeypatch.setattr(fin, "reproduce_v30_financials", financials)
    # The batch cache installer patches module globals; let monkeypatch restore them.
    from worldenergydata.lower_tertiary import v30_reproducer as rep
    from worldenergydata.lower_tertiary import wti_prices as wti

    for module in (fin, rep, wti):
        for key, value in vars(module).copy().items():
            if key.startswith("load_") or key == "reproduce_v30_production":
                monkeypatch.setattr(module, key, value)
    batch._install_batch_caches()

    base = {"end_date": None, "first_oil_overrides": None, "input_set": "v30"}
    assert fin.reproduce_v30_financials(**base)["npv_usd"] == 0
    assert fin.reproduce_v30_financials(**base)["npv_usd"] == 0
    assert fin.reproduce_v30_financials(**(base | changed))["npv_usd"] == expected
    assert fin.reproduce_v30_financials(**base)["npv_usd"] == 0
    assert len(calls) == 2
