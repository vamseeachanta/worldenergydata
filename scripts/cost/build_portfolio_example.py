"""Generate a synthetic, sourced-method cost-map example; no market cost claims.

All input values and independent hand calculations are specified in
docs/modules/cost/portfolio-cost-model.md, Worked example (2026).
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from worldenergydata.cost.portfolio.accounting import (
    Basis,
    CostItem,
    Evidence,
    Interval,
    Scenario,
    allocate,
    reconcile,
)
from worldenergydata.cost.portfolio.estimator import (
    Comparable,
    EstimateRequest,
    ValidationPolicy,
    estimate,
)
from worldenergydata.cost.portfolio.history import (
    Event,
    WorkbookValue,
    compare_workbook,
    trace,
)
from worldenergydata.cost.portfolio.report import compare_estimates, write_report


def build_example() -> dict:
    basis = Basis(
        "USD", "million", "real", "2020", "gross", "phase-a", "upstream", "capex"
    )
    source = "Synthetic example inputs; portfolio-cost-model.md, Worked example (2026)"
    observed = Evidence(source, date(2020, 1, 1), "disclosed")
    award = Evidence(source, date(2020, 1, 1), "award_derived")
    requirements = ("host", "wells", "installation", "controls")
    items = (
        CostItem(
            "a",
            ("host", "installation"),
            Interval(D(20), D(30)),
            basis,
            award,
            "included",
            "range",
        ),
        CostItem(
            "b", ("wells",), Interval(D(10), D(10)), basis, award, "included", "point"
        ),
        CostItem("c", ("controls",), None, basis, award, "included", "not_public"),
    )
    total = Interval(D(100), D(120))
    # Scenario shares are declared assumptions, never inferred market benchmarks.
    scenarios = (
        Scenario(
            "example",
            "subsea",
            {"host": D(".5"), "wells": D(".3"), "unallocated": D(".2")},
            source,
        ),
    )
    events = (
        Event(
            "e-a",
            "p-map",
            "total",
            "sanction",
            date(2020, 1, 1),
            total,
            basis,
            observed,
            "2020",
        ),
        Event(
            "e-b",
            "p-map",
            "total",
            "not_public",
            date(2021, 1, 1),
            None,
            basis,
            Evidence(source, date(2021, 1, 1), "unavailable"),
            "2021",
        ),
    )
    workbook = WorkbookValue(
        "p-map",
        "total",
        "example!B2",
        "synthetic-no-workbook-file",
        Interval(D(90), D(90)),
        basis,
        "example-vintage",
        "2020",
    )
    request = EstimateRequest(
        "p-inferred",
        "p-inferred",
        "subsea",
        "region-a",
        basis,
        "well_count",
        "well",
        D(3),
        date(2022, 1, 1),
        observed,
    )

    def comparable(key, x, y):
        # These fictional disclosures exercise the API, not production training.
        return Comparable(
            key,
            key,
            "subsea",
            "region-a",
            basis,
            "well_count",
            "well",
            D(x),
            date(2020, 1, 1),
            Interval(D(y), D(y)),
            observed,
            False,
        )

    training = tuple(comparable(f"t-{x}", x, 10 + 2 * x) for x in range(1, 6))
    calibration = (comparable("c-1", 2, 15), comparable("c-2", 4, 21))
    validation = (comparable("v-1", 2, 14), comparable("v-2", 4, 18))
    records = training + calibration + validation
    component_events = tuple(
        Event(
            f"e-award-{row.identity}",
            "p-map",
            "|".join(row.requirements),
            "not_public" if row.amount is None else "award",
            date(2020, 1, 1),
            row.amount,
            row.basis,
            row.evidence,
            "2020",
        )
        for row in items
    )
    # Every limit is an explicit demonstration input, not a deployment criterion.
    policy = ValidationPolicy(D(".5"), 3, 2, D(".01"), D(".5"), source)
    fitted = estimate(
        request,
        records,
        tuple(r.group for r in training),
        tuple(r.group for r in calibration),
        tuple(r.group for r in validation),
        policy,
    )
    return {
        "synthetic": True,
        "summary": "Synthetic arithmetic demonstration only. No real-project CAPEX estimate "
        "is qualified. Inputs, method, answer and exclusions remain explicit.",
        "revision_history": [
            {
                "revision": "initial",
                "date": "2026-10-20",
                "change": "Add an auditable example for accounting and estimation.",
            },
            {
                "revision": "correction",
                "date": "2026-10-24",
                "change": "Correct residual fractions and source sections; pin output bytes.",
            },
        ],
        "inputs": {
            "basis": basis,
            "requirements": requirements,
            "required_asset_quantities": {key: None for key in requirements},
            "items": items,
            "total": total,
            "scenarios": scenarios,
            "events": events + component_events,
            "workbook": workbook,
            "request": request,
            "comparables": records,
            "policy": policy,
        },
        "bottom_up": reconcile(total, basis, items, requirements),
        # The allocation illustrates the low target bound, not a midpoint of the range.
        "top_down": {
            "target": D(100),
            "basis": "explicit low-bound scenario",
            "allocation": allocate(D(100), "subsea", scenarios, requirements, D(".01")),
        },
        "trace": trace(events + component_events, request.as_of),
        "estimator": fitted,
        "consistency": compare_estimates(fitted.interval, None),
        "workbook": compare_workbook(events[0], workbook, "example-vintage", "2020"),
        "limits": [
            "NOT_EVALUATED: real portfolio model qualification and asset-level predictions.",
            (
                "NOT_EVALUATED: real workbook scope/vintage reconciliation beyond "
                "the frozen-cell adapter."
            ),
            (
                "Conformal coverage requires exchangeable project groups; "
                "no real-data guarantee is asserted."
            ),
            (
                "The nine fictional observations deliberately mimic disclosed records "
                "only inside this example."
            ),
            (
                "Joint allocation shares are assumed, not cost disclosures. "
                "Missing assets stay visible."
            ),
            "No FX, inflation, tax, workbook edits or stakeholder circulation.",
        ],
        "sources": [
            source,
            (
                "NIST/SEMATECH e-Handbook (2003), 4.4.3.1: "
                "https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm"
            ),
            (
                "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty "
                "Quantification (2021), section 1.1: https://arxiv.org/html/2107.07511v6"
            ),
            (
                "Cost-map program plan (2026), Shared Contract to Freeze: "
                "docs/plans/2026-07-16-issue-1038-cost-map-program.md"
            ),
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    write_report(build_example(), args.output_dir)
