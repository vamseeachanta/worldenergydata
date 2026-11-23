"""Shared synthetic index inputs for cost predictors and dataset adjustment."""

from contextlib import contextmanager

import pytest


@pytest.fixture
def synthetic_observations():
    from worldenergydata.cost.timeseries.schema import CostObservation

    return [
        CostObservation(
            component=component,
            year=year,
            value=value,
            unit="index_test",
            figure_type="index",
            provenance="sourced",
            source_title="Synthetic index",
            source_url="https://example.org/synthetic",
            quoted_text="Synthetic test only",
            accessed_date="2026-01-01",
            notes="Synthetic, no engineering use",
            region="global" if component == "index_ucci" else "US",
        )
        for component, end in [
            ("index_ppi_machinery", 200),
            ("index_ppi_drilling", 300),
            ("index_ucci", 900),
        ]
        for year, value in [(2019, 100), (2020, end)]
    ]


@pytest.fixture
def synthetic_escalator(synthetic_observations):
    from worldenergydata.cost.escalation import CostEscalator

    return CostEscalator(synthetic_observations)


@pytest.fixture
def data_root():
    """Restore each override before clearing the resolver's cached data root."""
    from worldenergydata.common import data_resolver

    @contextmanager
    def override(root=None):
        try:
            with pytest.MonkeyPatch.context() as patch:
                if root is None:
                    patch.delenv("WED_DATA_ROOT", raising=False)
                else:
                    patch.setenv("WED_DATA_ROOT", str(root))
                data_resolver._clear_cache()
                yield
        finally:
            # The environment has already been restored by the inner context.
            data_resolver._clear_cache()

    try:
        yield override
    finally:
        data_resolver._clear_cache()


@pytest.fixture
def write_data_root(synthetic_observations):
    """Create the synthetic curated CSV at a resolver-compatible data root."""
    from worldenergydata.cost.timeseries.dataset import write_timeseries_csv

    def write(root):
        curated = root / "modules" / "cost" / "curated"
        curated.mkdir(parents=True)
        path = curated / "cost_component_timeseries.csv"
        write_timeseries_csv(synthetic_observations, path)
        return path

    return write
