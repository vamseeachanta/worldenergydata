"""Contract and identity tests for the portfolio cost-map v2 surface."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
V1_MANIFEST = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")
V1_MANIFEST_SHA256 = "f5dc2fce6c0ee376d577f8dcebb70511c756bd28264744600dc018deab5fcf9e"


def test_v1_external_trust_root_and_closed_producer(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_manifest import (
        validate_v1_contract,
    )

    assert sha256((ROOT / V1_MANIFEST).read_bytes()).hexdigest() == V1_MANIFEST_SHA256
    manifest = validate_v1_contract(ROOT)
    assert manifest["producer"]["commit"] == "66ce9d6808492a01f6a7cac60415304bcc6e6ef5"
    assert {
        row["path"] for row in manifest["inputs"] if row["path"].endswith(".py")
    } == {
        "scripts/cost/build_big_foot_cost_map.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack_render.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/project_trace.py",
    }

    payload = json.loads((ROOT / V1_MANIFEST).read_text(encoding="utf-8"))
    payload["inputs"][0]["sha256"] = "0" * 64
    tampered = tmp_path / V1_MANIFEST
    tampered.parent.mkdir(parents=True)
    tampered.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="v1 manifest trust root mismatch"):
        validate_v1_contract(tmp_path)
