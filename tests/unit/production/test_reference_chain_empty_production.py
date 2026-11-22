"""Shared empty-production contract from issue #1289, not an economic model."""

from datetime import datetime
from importlib import import_module
from unittest.mock import Mock

import pandas as pd
import pytest


@pytest.fixture(
    params=[
        ("spain", "run_spain_reference_chain", "build_spain_field_concept"),
        ("brazil_anp", "run_brazil_reference_chain", "build_brazil_field_concept"),
        ("sodir", "run_norway_reference_chain", "build_norway_field_concept"),
    ],
    ids=["spain", "brazil_anp", "sodir"],
)
def chain(request):
    domain, runner_name, builder_name = request.param
    module = import_module(f"worldenergydata.{domain}.reference_chain")
    return module, getattr(module, runner_name), builder_name


@pytest.mark.parametrize("with_schema", [False, True], ids=["bare", "schema"])
def test_empty_production_raises_before_screening_or_cashflow(
    chain, with_schema, monkeypatch
):
    """Issue #1289 requires an error for no observations, including no matches.

    Both frames contain no rows, so there is no observed first month and no
    defensible revenue metric. This is a set-emptiness check with no numeric
    acceptance limit or engineering constant.
    """
    from worldenergydata.production.unified.query import STANDARD_COLUMNS

    module, run_chain, builder_name = chain
    adapter = Mock()
    adapter.fetch.return_value = pd.DataFrame(
        columns=STANDARD_COLUMNS if with_schema else None
    )
    downstream = [Mock(), Mock(), Mock()]
    downstream[-1].return_value.generate_monthly_cashflow.return_value = []
    for name, stub in zip((builder_name, "recommend", "CashflowEngine"), downstream):
        monkeypatch.setattr(module, name, stub)

    with pytest.raises(ValueError, match="production is empty"):
        run_chain(
            adapter=adapter,
            field_meta={},
            field_name="synthetic-field",
        )

    adapter.fetch.assert_called_once()
    for stub in downstream:
        stub.assert_not_called()


def test_first_month_comes_from_earliest_observation(chain):
    """Independent ordering: January precedes February in the same year.

    Synthetic months reuse the dates in the existing country-chain fixtures
    (tests/unit/spain/test_reference_chain.py::FixtureCoresLoader). Reversing
    them must still select January; no production magnitude is required.
    """
    module, _, _ = chain
    production = pd.DataFrame({"YEAR_MONTH": ["2024-02", "2024-01"]})

    # Calendar ordering above gives the first day of January, independently.
    assert module._first_oil_date(production) == datetime(2024, 1, 1)
