# ABOUTME: Generate an example Field Development Plan HTML for the Julia LT field.
# ABOUTME: Issue #567 — first worked example (Lower Tertiary, lease G20351).
"""
Build ``reports/lower_tertiary/julia_fdp.html`` — a worked field-development-plan
example for **Julia** (Walker Ridge, lease G20351), a Lower Tertiary subsea
tieback. Parameters come from ``config/analysis/lower_tertiary/fields/julia.yml``
+ the field-economics report; ``actuals`` show the as-built figures next to the
engine's recommendation.

Run:
    .venv/bin/python scripts/field_development/build_julia_fdp.py
"""

from __future__ import annotations

from pathlib import Path

from worldenergydata.field_development import build_fdp_html
from worldenergydata.field_development.enums import (
    ConceptType,
    FluidType,
    MetoceanRegime,
    ReservoirDistribution,
)
from worldenergydata.field_development.models import FieldConcept

OUT = Path(__file__).parents[2] / "reports" / "lower_tertiary" / "julia_fdp.html"

# Julia: Lower Tertiary subsea tieback to the Jack/St. Malo hub (Walker Ridge).
JULIA = FieldConcept(
    name="Julia (Lower Tertiary)",
    operator="ExxonMobil (Equinor 50%)",
    region="US Gulf of Mexico — Walker Ridge",
    water_depth_m=2160.0,  # ~7,100 ft
    fluid_type=FluidType.OIL,
    api_gravity=27.0,  # heavy Lower Tertiary crude
    gor_scf_stb=1000.0,
    recoverable_reserves_mmboe=80.0,
    num_wells=5,
    num_manifolds=2,
    plateau_rate_boed=34000.0,
    field_life_years=20.0,
    concept_type=ConceptType.SUBSEA_TIEBACK,
    tieback_distance_km=30.0,  # to Jack/St. Malo host
    distance_to_host_km=30.0,
    host_spare_capacity=True,
    metocean_regime=MetoceanRegime.HURRICANE_CYCLONE,
    reservoir_distribution=ReservoirDistribution.DISTRIBUTED,
    year_fid=2013,
    year_first_oil=2016,
    discount_rate=0.10,
    data_source="config/analysis/lower_tertiary/fields/julia.yml + BSEE OGOR-A",
)

ACTUALS = {
    "CAPEX (as built)": "$4,700 MM",
    "Producing wells": "4 (9 wellbores)",
    "Oil produced": "77.5 MMbbl",
    "First oil": "2016-03",
    "Host": "Jack/St. Malo (tieback)",
    "Lease": "G20351",
}


def main() -> None:
    html = build_fdp_html(
        JULIA,
        top_n=5,
        actuals=ACTUALS,
        title="Field Development Plan — Julia (Lower Tertiary)",
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
