"""Synthetic index arithmetic only; no observed cost or calibration claim."""

from hashlib import sha256

import pytest

from tests.unit.cost.test_escalation import observation
from worldenergydata.cost.escalation import CostEscalator
from worldenergydata.cost.timeseries.dataset import write_timeseries_csv


def synthetic_escalator():
    return CostEscalator(synthetic_observations())


def synthetic_observations():
    return [
        observation(component, year, value)
        for component, end in [
            ("index_ppi_machinery", 200),
            ("index_ppi_drilling", 300),
            ("index_ucci", 900),
        ]
        for year, value in [(2019, 100), (2020, end)]
    ]


def test_forward_factor_trace_cache_and_exact_inverse():
    """Mean(200/100, 300/100)=2.5; inverse=0.4, not mean(1/2, 1/3)."""
    from worldenergydata.cost.calibration.index_adjustment import IndexAdjustment

    adjustment = IndexAdjustment(escalator=synthetic_escalator())
    forward = adjustment.factor(2019, 2020)
    assert forward.factor == 2.5
    assert 250 / forward.factor == 100
    assert adjustment.factor(2019, 2020) is forward
    assert adjustment.factor(2020, 2020).factor == 1
    assert "public series only" in forward.note
    assert forward.trace and "index_ucci" not in forward.index_used
    assert adjustment.csv_sha256 is None


@pytest.mark.parametrize("year", [1990, 2035, 2020.5, True, "bad", None])
def test_invalid_or_uncovered_year_raises(year):
    from worldenergydata.cost.calibration.index_adjustment import IndexAdjustment

    adjustment = IndexAdjustment(escalator=synthetic_escalator())
    with pytest.raises(ValueError):
        adjustment.factor(year, 2020)
    with pytest.raises(ValueError):
        adjustment.factor(2020, year)


def test_explicit_csv_snapshot_and_missing_default(tmp_path, monkeypatch):
    from worldenergydata.cost.calibration.index_adjustment import IndexAdjustment

    path = tmp_path / "indices.csv"
    write_timeseries_csv(synthetic_observations(), path)
    adjustment = IndexAdjustment(index_path=path)
    assert adjustment.csv_sha256 == sha256(path.read_bytes()).hexdigest()
    monkeypatch.chdir(tmp_path)
    assert adjustment.factor(2019, 2020).factor == 2.5
    with pytest.raises(FileNotFoundError, match="index"):
        IndexAdjustment()
