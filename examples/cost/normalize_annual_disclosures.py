"""Worked synthetic example; requires the cost package dependencies.

Run: python examples/cost/normalize_annual_disclosures.py
FX: Federal Reserve G.5A annual table (2021 revision), EUR/2020 = 1.1410
USD/EUR, https://www.federalreserve.gov/releases/g5a/20210104/ .
Hand calculation: 2 * 1,000,000 * 1.1410 = 2,282,000 USD;
2.282 * 1,000,000 USD has the same value on the same declared basis.
"""

import json
from decimal import Decimal

from worldenergydata.cost.data_collection import (
    DisclosureMoney,
    NormalizationPolicy,
    money_values_are_comparable,
    normalize_disclosure_money_rows,
)


def main() -> None:
    # The rate is an explicit scenario from the issue-336 plan (2026-04-22),
    # Scope Boundaries; it is assumed, based on previous experience, not
    # a measured inflation rate. Same-year inputs have a rebasing factor of 1.
    policy = NormalizationPolicy(
        policy_id="worked-example-v1",
        annual_escalation_rate=Decimal("0.03"),
        escalation_source=(
            "Assumed, based on previous experience; "
            "issue-336 plan (2026-04-22), Scope Boundaries"
        ),
    )
    # Amounts, year and economic basis below are synthetic example inputs.
    common = {
        "magnitude_scale": "million",
        "fiscal_year": 2020,
        "as_reported_metric_name": "Capital expenditure",
        "metric_name_normalized": "capex",
        "scope": "operator",
        "comparison_basis": "consolidated; cash capex; net interest; full year",
        "period_basis": "calendar_year_flow",
        "price_basis": "nominal",
        "provenance": {"source": "Synthetic worked example, not a filing"},
    }
    inputs = [
        DisclosureMoney(**common, amount="2", currency="EUR", unit="EUR"),
        DisclosureMoney(**common, amount="2.282", currency="USD", unit="USD"),
    ]
    results = normalize_disclosure_money_rows(inputs, policy)
    print(
        json.dumps(
            {
                "normalized_usd": [str(row.normalized_amount) for row in results],
                "comparable": money_values_are_comparable(*results),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
