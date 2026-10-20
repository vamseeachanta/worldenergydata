"""Synthetic worked example; no financial assumption or production policy is set.

Hand calculation: [100,120]-[80,90]=[10,40]. A synthetic absolute limit
of 25 is crossed by that interval, so unexplained materiality is uncertain.
See docs/modules/cost/FDAS_WORKBOOK_RECONCILIATION.md for sources and scope.
"""

from decimal import Decimal

from worldenergydata.cost.workbook_reconciliation.models import (
    Basis,
    Interval,
    MaterialityPolicy,
    Observation,
)
from worldenergydata.cost.workbook_reconciliation.reconcile import reconcile


def main():
    basis = Basis(
        project_id="example-001",
        component="host",
        start="2024-01",
        end="2024-12",
        currency="USD",
        unit="USD",
        price_basis="nominal",
        basis_year="not_applicable",
        ownership="gross",
        scope="development",
        capex_basis="capex",
        assumption_vintage="synthetic",
        normalization_vintage="native",
    )
    workbook = Observation(
        basis,
        Interval(Decimal(100), Decimal(120)),
        "workbook_assumption",
        "synthetic:A1",
    )
    comparison = Observation(
        basis, Interval(Decimal(80), Decimal(90)), "mapped", "synthetic:B1"
    )
    # Fixture inputs only: not a sourced or approved production acceptance limit.
    policy = MaterialityPolicy(
        Decimal(25), Decimal(0), "synthetic worked example", True
    )
    result = reconcile(workbook, comparison, policy)
    print(f"variance=[{result.variance.low},{result.variance.high}]")
    print(f"materiality={result.materiality}; status={result.status}")


if __name__ == "__main__":
    main()
