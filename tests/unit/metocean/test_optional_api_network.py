"""Opt-in cached samples; excluded from ordinary runs, never a unit-test fixture."""

import os
from pathlib import Path

import pytest

from worldenergydata.metocean.clients.metocean_api_adapter import MetoceanAPIAdapter

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        os.environ.get("METOCEAN_API_NETWORK") != "1",
        reason="Explicit METOCEAN_API_NETWORK=1 and a persistent cache are required",
    ),
]


@pytest.mark.parametrize(
    "dataset,variables", [("NORA3", ["hs"]), ("NorKyst800", ["zeta"])]
)
def test_small_cached_sample(dataset, variables):
    """Sample inputs are supplied by the caller, not guessed archive coverage.

    Set a short provider-supported window, a point inside the dataset domain,
    and a persistent cache directory. Numeric environmental values have no
    independent oracle here and remain NOT_EVALUATED. The second request must
    use the completed digest-checked sample without another backend call.
    """
    cache = Path(os.environ["METOCEAN_API_SAMPLE_CACHE"])
    adapter = MetoceanAPIAdapter(cache)
    query = {
        "dataset": dataset,
        "variables": variables,
        "lon": float(os.environ["METOCEAN_API_SAMPLE_LON"]),
        "lat": float(os.environ["METOCEAN_API_SAMPLE_LAT"]),
        "start_time": os.environ["METOCEAN_API_SAMPLE_START"],
        "end_time": os.environ["METOCEAN_API_SAMPLE_END"],
    }
    first = adapter.fetch(**query)
    assert not first.empty
    adapter._download = lambda *args: pytest.fail(
        "A completed sample was downloaded again"
    )
    assert first.equals(adapter.fetch(**query))
