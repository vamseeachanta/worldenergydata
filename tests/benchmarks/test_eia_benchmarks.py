"""Performance benchmarks for EIA state and basin production loaders.

Exercises the pure-pandas transform path with synthetic record sets.
Run with:
    cd worldenergydata && PYTHONPATH=src uv run python -m pytest \
        tests/benchmarks/test_eia_benchmarks.py --benchmark-only -q
"""

import random

import pytest

from worldenergydata.eia_us.production.basin_production import BasinProductionLoader
from worldenergydata.eia_us.production.state_production import StateProductionLoader

_STATES = ["TX", "ND", "NM", "OK", "CO", "WY", "LA", "AK", "CA", "OH", "WV", "PA"]
_BASINS = ["Permian", "Bakken", "Eagle Ford", "DJ Basin", "Appalachian",
           "Haynesville", "Anadarko"]

random.seed(42)


def _state_records(n: int) -> list:
    """Generate n synthetic EIA state production API records."""
    return [
        {
            "period": f"{2010 + (i // 12)}-{(i % 12) + 1:02d}",
            "value": str(round(random.uniform(100, 50000), 1)),
            "unit": "MBBLS",
        }
        for i in range(n)
    ]


def _basin_records(n: int) -> list:
    """Generate n synthetic DPR basin production records."""
    return [
        {
            "period": f"{2015 + (i // 12)}-{(i % 12) + 1:02d}",
            "basin": _BASINS[i % len(_BASINS)],
            "rig_count": str(random.randint(10, 300)),
            "new_well_ip_bopd": str(round(random.uniform(500, 2000), 1)),
            "legacy_decline_bopd": str(round(random.uniform(-5000, -100), 1)),
            "total_production_bopd": str(round(random.uniform(100000, 2000000), 1)),
        }
        for i in range(n)
    ]


_STATE_RECORDS_1000 = _state_records(1000)
_BASIN_RECORDS_500 = _basin_records(500)


def test_bench_state_production_loader(benchmark):
    """Benchmark StateProductionLoader.load with 1000 synthetic EIA records."""
    loader = StateProductionLoader()
    result = benchmark(loader.load, _STATE_RECORDS_1000, "TX")
    assert len(result) == 1000
    assert "crude_bbl" in result.columns


def test_bench_basin_production_loader(benchmark):
    """Benchmark BasinProductionLoader.load with 500 synthetic DPR records."""
    loader = BasinProductionLoader()
    result = benchmark(loader.load, _BASIN_RECORDS_500)
    assert len(result) == 500
    assert "total_production_bopd" in result.columns
