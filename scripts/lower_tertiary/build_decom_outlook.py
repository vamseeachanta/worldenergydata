"""Build an input-traceable, wells-only decommissioning outlook sidecar.

Repository cost factors are uncalibrated assumptions, not engineering inputs.
No removal cost, regulatory compliance verdict or BSEE band is inferred.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for source in (ROOT / "src", *sorted((ROOT / "packages").glob("*/src"))):
    sys.path.insert(0, str(source))

import yaml
from worldenergydata.decommissioning.cost_model import (
    DecommissioningCostEstimator,
)
from worldenergydata.decommissioning.regulations import get_regulations

HERE = ROOT / "reports/lower_tertiary/lifecycle"
REGISTRY = "config/ong_field_development/fields_registry.yml"
MODEL = "packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py"
REGULATIONS = "packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py"
# NIST SP 811 (2008), Appendix B.8, foot: exact international foot conversion.
# https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf
METRES_PER_FOOT = 0.3048
BASIS = (
    "Uncalibrated parametric model estimate, not BSEE; wells only. "
    "Cost factors assumed, based on previous experience; independent calibration "
    "is NOT_EVALUATED. Not a field-specific budget or engineering design basis."
)


def source_digests() -> dict:
    paths = (
        REGISTRY,
        MODEL,
        REGULATIONS,
        "reports/lower_tertiary/lifecycle/_facts.json",
    )
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths
    }


def valid_depth(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def build_record(
    fact: dict, registered: dict, *, digests=None, bsee_reason=None, generated_on=None
) -> dict:
    """Echo available inputs; retain nulls for unavailable or invalid inputs."""
    depth = valid_depth(fact.get("water_depth_ft"))
    count = (registered.get("validated_economics") or {}).get("wellbores")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        count = None
    depth_m = depth * METRES_PER_FOOT if depth is not None else None
    per_well = None
    reference_year = None
    if depth_m is not None:
        # cost_model.py: _COST_FACTORS['well_p_and_a'], _REGION_MULTIPLIERS['gom'].
        # Existing repository coefficients are assumptions, not calibrated data.
        estimate = DecommissioningCostEstimator().estimate(
            "well_p_and_a", water_depth_m=depth_m, region="gom"
        )
        per_well = estimate.estimated_cost_musd
        reference_year = estimate.year
    reasons = []
    if depth_m is None:
        reasons.append("Valid field water depth unavailable")
    if count is None:
        reasons.append("Validated wellbore count unavailable")
    return {
        "projected_cop_year": fact.get("gates", {}).get("projected_cop_year"),
        "wellbores": count,
        "water_depth_ft": depth,
        "water_depth_m": depth_m,
        "pa_per_well_musd": per_well,
        "pa_estimate_musd": (
            per_well * count if per_well is not None and count is not None else None
        ),
        "pa_reason": "; ".join(reasons) or None,
        "basis": BASIS,
        "bsee_decom_band": None,
        "bsee_reason": bsee_reason or "BSEE source and field attribution NOT_EVALUATED",
        "regulations": [
            {
                "name": reg.requirement_type.replace("_", " "),
                "reference": reg.reference_doc,
            }
            for reg in get_regulations("gom")
            if reg.requirement_type
            in {"well_plugging", "structure_removal", "pipeline_decommission"}
        ],
        "regulatory_status": "NOT_EVALUATED: reference index only; applicability and current requirements need review",
        "provenance": {
            "generated_on": generated_on or date.today().isoformat(),
            "model": MODEL,
            "region": "gom",
            "cost_reference_year": reference_year,
            "wellbore_source": REGISTRY,
            "source_digests": source_digests() if digests is None else digests,
        },
    }


def build_outlook(facts: list, registry: dict, *, generated_on=None) -> dict:
    from worldenergydata.bsee.analysis.field_decom import load_decom_totals

    totals = load_decom_totals()
    reason = (
        "BSEE decom totals unavailable or unreadable; no liability band established"
        if totals.empty
        else "BSEE totals present; canonical field attribution NOT_EVALUATED"
    )
    digests = source_digests()
    return {
        "fields": {
            fact["id"]: build_record(
                fact,
                registry.get(fact["id"], {}),
                digests=digests,
                bsee_reason=reason,
                generated_on=generated_on,
            )
            for fact in facts
        }
    }


def main():
    facts = json.loads((HERE / "_facts.json").read_text())
    registry = yaml.safe_load((ROOT / REGISTRY).read_text())["fields"]
    output = build_outlook(facts, registry)
    path = HERE / "_decommissioning.json"
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    assert json.loads(path.read_text()) == output
    print(f"Wrote {path.name}: {len(output['fields'])} fields")


if __name__ == "__main__":
    main()
