"""Offline database example with invented volumes and an existing decline fit.

Run with --output-dir pointing to disposable output storage. The example retains
its synthetic raw input, a manifest and a SQLite database, and never downloads
data. Input arithmetic: 100 + 80 + 64 = 244 bbl; consecutive monthly ratios are
0.8. With the existing fitter's t=1,2,3 convention, qi=125 bbl/month and
Di=ln(1.25)/month give exactly 100, 80, 64 bbl/month. These are demonstration
inputs, not regulator observations or engineering acceptance limits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from worldenergydata.production.database import (
    CANONICAL_UNITS,
    ProductionDatabase,
    SourceSnapshot,
)
from worldenergydata.production.forecast import ArpsDeclineCurve


def run_example(output_dir: Path) -> dict:
    """Retain the source bytes and verify stored evidence through a fresh reader."""
    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "production.sqlite"
    if database_path.exists():
        raise FileExistsError("use a new output directory to preserve prior evidence")
    rows = [
        {
            "region": "synthetic-region",
            "field_name": "external-example",
            "year": 2024,
            "month": month,
            "oil_bbl": oil,
            "gas_mcf": None,
            "water_bbl": 0.0,
            "condensate_bbl": None,
            "source": "synthetic-example",
        }
        # Invented exact geometric sequence; the independent arithmetic is above.
        for month, oil in ((1, 100.0), (2, 80.0), (3, 64.0))
    ]
    raw = json.dumps(rows, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    raw_path = output_dir / "raw-production.json"
    with raw_path.open("xb") as stream:
        stream.write(raw)
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    with ProductionDatabase(database_path) as db:
        db.add_asset("example-field", "Synthetic example field", "field")
        db.add_asset("example-facility", "Synthetic example facility", "facility")
        db.link_asset("example-field", "example-facility")
        db.add_snapshot(
            SourceSnapshot(
                snapshot_id="example-v1",
                source_id="bsee-data-center",
                version="synthetic-example-v1",
                locator="https://example.org/synthetic-production",
                retrieved_at="2026-10-20T00:00:00Z",
                sha256=digest,
                data_kind="synthetic",
            )
        )
        db.map_field("bsee-data-center", "external-example", "example-field")
        db.ingest("example-v1", rows, units=CANONICAL_UNITS)
        history = db.decline_history(
            "example-v1", "example-field", allow_synthetic=True
        )
        frame = pd.DataFrame(history.points, columns=["month", "rate_bbl"])
        # Demonstration choices, not economic assumptions: a 20 bbl/month cutoff
        # and six output months. EUR from this fit is not used or qualified.
        fit = ArpsDeclineCurve().fit(
            frame, model="exponential", economic_limit=20.0, months=6
        )
        db.save_decline(
            "example-curve",
            history,
            model=fit.model,
            qi=fit.qi,
            di=fit.Di,
            b=fit.b,
            method_ref="Existing monthly fitter; EIA Production Decline Curve Analysis (2023).",
        )
    with ProductionDatabase(database_path) as db:
        curve = db.decline_curve("example-curve")
        result = {
            "dataset_id": "production-database-worked-example",
            "data_kind": curve["data_kind"],
            "raw_file": raw_path.name,
            "raw_sha256": digest,
            "history_sha256": curve["history_sha256"],
            "qualification": curve["qualification"],
            "oil_total_bbl": sum(
                row["oil_bbl"] for row in db.production("example-v1", "example-field")
            ),
            "fitted_qi_bbl_per_month": round(curve["qi"], 1),
        }
        if db.source_snapshot("example-v1")["sha256"] != digest:
            raise ValueError("retained source digest mismatch")
    manifest = output_dir / "manifest.json"
    with manifest.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if json.loads(manifest.read_text(encoding="utf-8")) != result:
        raise ValueError("manifest readback mismatch")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    print(json.dumps(run_example(parser.parse_args().output_dir), indent=2))
