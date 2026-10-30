"""Offline synthetic API replay; writes only to an explicitly supplied directory.

Inputs: synthetic cumulative oil 3, 6, 0 MMbbl and one unavailable value.
Hand calculation: maximum = 6, hence normalized bar widths 0.5, 1.0, 0.0.
No values, release approvals or revision identifiers describe a real dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(output: Path):
    spec = importlib.util.spec_from_file_location(
        "explorer_visualization", ROOT / "scripts/hf_export/explorer_visualization.py"
    )
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    bundle = {
        "schema_version": "1.0.0",
        "projection": "field_explorer_results",
        "hf_dataset": "worldenergydata",
        "fields": {
            "alpha": {"name": "Synthetic alpha", "performance": {"cum_oil_mmbbl": 3}},
            "beta": {"name": "Synthetic beta", "performance": {"cum_oil_mmbbl": 6}},
            "zero": {"name": "Synthetic zero", "performance": {"cum_oil_mmbbl": 0}},
            "unknown": {
                "name": "Synthetic unknown",
                "performance": {"cum_oil_mmbbl": None},
            },
        },
        # Synthetic source digest and Git hashes exercise the production formats.
        "sources": [{"role": "field_detail", "sha256": "d" * 64}],
    }
    raw = json.dumps(bundle, sort_keys=True, allow_nan=False).encode()
    manifest = {
        "renderer_revision": "c" * 40,
        # Demonstration resource limits are operational inputs, not criteria.
        "limits": {"request_bytes": 4096, "bundle_bytes": 10000, "timeout_seconds": 5},
        "releases": [
            {
                "dataset_id": "public-example/explorer",
                "dataset_revision": "a" * 40,
                "source_revision": "b" * 40,
                "bundle_path": "explorer_results_bundle.json",
                "bundle_sha256": hashlib.sha256(raw).hexdigest(),
                "public_data_approved": True,
            }
        ],
    }
    request = json.dumps({"dataset_revision": "a" * 40, "field_id": "alpha"}).encode()
    app = renderer.create_app(manifest, fetch=lambda url, **kwargs: raw)
    status = []
    body = b"".join(
        app(
            {
                "PATH_INFO": "/render",
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(request)),
                "wsgi.input": io.BytesIO(request),
            },
            lambda code, headers: status.append(code),
        )
    )
    if status != ["200 OK"]:
        raise RuntimeError("Synthetic API replay failed")
    response = json.loads(body)
    output.mkdir(parents=True, exist_ok=True)
    (output / "input_bundle.json").write_bytes(raw)
    (output / "synthetic_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    (output / "render_response.json").write_bytes(body)
    (output / "chart.svg").write_text(response["svg"], encoding="utf-8")
    print("Synthetic replay: 3/6 = 0.5; 6/6 = 1.0; zero = 0.0; missing = unavailable.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
