"""Offline worked example with synthetic inputs, not measured observations.

Run with ``python -m worldenergydata.metocean.unified.example OUTPUT_DIR``.
The two locations reuse the repository's Gulf of Mexico and North Sea examples.
Each source supplies Hs of 2, 4, 6 m at the three explicitly supplied times.
The independent hand calculation is mean Hs = (2 + 4 + 6) / 3 = 4 m.
No engineering constants, thresholds, downloads or credentials are used.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from worldenergydata.metocean.unified import (
    MetoceanDashboard,
    MetoceanQuery,
    UnifiedMetoceanClient,
)
from worldenergydata.metocean.unified.unified_query import SOURCES


def run_example(output_dir: Path) -> dict:
    """Save attributed CSV/Plotly outputs and return a per-location summary."""
    output_dir.mkdir(parents=True, exist_ok=True)

    def fetch(q):
        return pd.DataFrame(
            {
                "timestamp": [
                    "2023-01-01T00:00Z",
                    "2023-01-01T00:30Z",
                    "2023-01-02T00:00Z",
                ],
                "parameter": ["Hs"] * 3,
                "value": [2.0, 4.0, 6.0],
                "source": ["synthetic"] * 3,
                "unit": ["m"] * 3,
            }
        )

    client = UnifiedMetoceanClient(
        source_fetchers={source: fetch for source in SOURCES}
    )
    summary = {}
    for name, lat, lon in [("gulf", 28.5, -88.5), ("north_sea", 57.0, 3.5)]:
        result = client.query(
            MetoceanQuery(
                lat,
                lon,
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
                parameters=("Hs",),
            )
        )
        result.data.to_csv(output_dir / f"{name}.csv", index=False)
        MetoceanDashboard().save(result, str(output_dir / f"{name}.html"))
        summary[name] = {
            "rows": len(result.data),
            "mean_Hs_m": result.data.value.mean(),
        }
    return summary


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    print(json.dumps(run_example(parser.parse_args().output_dir), indent=2))
