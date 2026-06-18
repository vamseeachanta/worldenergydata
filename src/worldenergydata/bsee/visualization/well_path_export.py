"""Shared well-path export contract for 3D visualizations.

This module is the single source of truth for the JSON payload consumed by the
BSEE 3D well-path renderers (Plotly and Three.js). Both renderers import from
here so the data schema can never diverge between them.

Pipeline context
----------------
``WellAPI12.prepare_well_paths`` (``bsee/analysis/well_api12.py``) already runs
the Minimum Curvature Method over each well's directional survey and stores the
result in ``self.output_data_well_path`` as ``{api12: DataFrame}`` where each
DataFrame carries the columns ``md, inc, az, x_coor, y_coor, z_coor, dz, dls``.
This module turns that in-memory structure into a versioned, renderer-agnostic
dict / JSON file.

Coordinate convention
---------------------
Coordinates are field-relative feet, East-North-Down style as computed by the
pipeline:

* ``x`` = ``x_coor`` (cos(az) component of the minimum-curvature step)
* ``y`` = ``y_coor`` (sin(az) component)
* ``z`` = ``z_coor`` = True Vertical Depth, **positive downward**

Renderers are responsible for mapping ``z`` to a screen-down axis (Plotly
reverses the z-axis; Three.js negates z into a Y-up world). The payload never
pre-applies that flip so the numbers stay faithful to the survey.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Iterable

SCHEMA_VERSION = "1.0"

# Deterministic, colour-blind-friendly palette assigned by well index. Mirrors
# the spirit of the legacy ``wellpath_visualization.COLOR_PALETTE`` but as an
# ordered list so two renderers colour the same well identically.
COLOR_PALETTE: list[str] = [
    "#0AA0AF",
    "#E45756",
    "#F2B701",
    "#54A24B",
    "#B279A2",
    "#FF9DA6",
    "#9D755D",
    "#4C78A8",
    "#72B7B2",
    "#EECA3B",
]


def color_for_index(index: int) -> str:
    """Return a stable hex colour for the n-th well."""
    return COLOR_PALETTE[index % len(COLOR_PALETTE)]


# ---------------------------------------------------------------------------
# Reusable minimum-curvature helper (plain-Python, no pandas dependency).
# ---------------------------------------------------------------------------
def minimum_curvature(stations: Iterable[dict[str, float]]) -> list[dict[str, float]]:
    """Compute an (x, y, z) trajectory from survey stations.

    This is a dependency-light mirror of ``WellAPI12.process_survey_xyz`` used
    for demo/synthetic data and for tests that should not depend on the ~300MB
    BSEE pickle. Production payloads come from the pipeline's pandas result, but
    this guarantees the contract is exercisable standalone.

    Args:
        stations: Iterable of dicts with ``md`` (measured depth, ft),
            ``inc`` (inclination, deg) and ``az`` (azimuth, deg). Must be
            ordered by increasing ``md``.

    Returns:
        List of point dicts with ``md, inc, az, x, y, z, dls``.
    """
    stations = list(stations)
    points: list[dict[str, float]] = []
    x = y = z = 0.0
    for i, st in enumerate(stations):
        md = float(st["md"])
        inc = float(st["inc"])
        az = float(st["az"])
        dls = 0.0
        if i > 0:
            prev = stations[i - 1]
            md1, inc1, az1 = float(prev["md"]), float(prev["inc"]), float(prev["az"])
            course = md - md1
            i1, i2 = math.radians(inc1), math.radians(inc)
            a1, a2 = math.radians(az1), math.radians(az)
            dl_sq = (
                math.sin((i2 - i1) / 2) ** 2
                + math.sin(i1) * math.sin(i2) * math.sin((a2 - a1) / 2) ** 2
            )
            dog_leg = 2 * math.asin(math.sqrt(max(0.0, dl_sq)))
            dog_leg = max(dog_leg, 1e-6)
            rf = course / dog_leg * math.tan(dog_leg / 2)
            x += (math.sin(i1) * math.cos(a1) + math.sin(i2) * math.cos(a2)) * rf
            y += (math.sin(i1) * math.sin(a1) + math.sin(i2) * math.sin(a2)) * rf
            z += (math.cos(i1) + math.cos(i2)) * rf
            if course > 0:
                dls = round(math.degrees(dog_leg) * 100.0 / course, 3)
        points.append(
            {
                "md": round(md, 2),
                "inc": round(inc, 3),
                "az": round(az, 3),
                "x": round(x, 2),
                "y": round(y, 2),
                "z": round(z, 2),
                "dls": dls,
            }
        )
    return points


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------
def _points_from_dataframe(df: Any) -> list[dict[str, float]]:
    """Extract renderer point dicts from a pipeline survey DataFrame."""
    cols = {c: c for c in df.columns}
    out: list[dict[str, float]] = []
    for _, row in df.iterrows():
        out.append(
            {
                "md": round(float(row.get("md", 0.0)), 2),
                "inc": round(float(row.get("inc", 0.0)), 3),
                "az": round(float(row.get("az", 0.0)), 3),
                "x": round(float(row["x_coor"]), 2),
                "y": round(float(row["y_coor"]), 2),
                "z": round(float(row["z_coor"]), 2),
                "dls": round(float(row.get("dls", 0.0)), 3),
            }
        )
    _ = cols
    return out


def _bounds(wells: list[dict[str, Any]]) -> dict[str, list[float]]:
    xs = [p["x"] for w in wells for p in w["points"]]
    ys = [p["y"] for w in wells for p in w["points"]]
    zs = [p["z"] for w in wells for p in w["points"]]
    if not xs:
        return {"x": [0.0, 0.0], "y": [0.0, 0.0], "z": [0.0, 0.0]}
    return {
        "x": [min(xs), max(xs)],
        "y": [min(ys), max(ys)],
        "z": [min(zs), max(zs)],
    }


def build_well_paths_payload(
    output_data_well_path: dict[Any, Any],
    labels: dict[Any, str] | None = None,
    *,
    field_name: str = "",
    units: str = "ft",
) -> dict[str, Any]:
    """Build the renderer-agnostic payload from the pipeline result.

    Args:
        output_data_well_path: ``{api12: survey DataFrame}`` from
            ``WellAPI12.prepare_well_paths``. Each DataFrame must expose
            ``x_coor, y_coor, z_coor`` (and ideally ``md, inc, az, dls``).
        labels: Optional ``{api12: display label}``. Falls back to ``str(api12)``.
        field_name: Optional field name for the scene header.
        units: Coordinate units (BSEE = feet).

    Returns:
        A JSON-serialisable dict following ``SCHEMA_VERSION``.
    """
    labels = labels or {}
    wells: list[dict[str, Any]] = []
    for index, (api12, df) in enumerate(output_data_well_path.items()):
        points = _points_from_dataframe(df)
        if not points:
            continue
        surface = points[0]
        wells.append(
            {
                "api12": str(api12),
                "label": labels.get(api12, str(api12)),
                "color": color_for_index(index),
                "surface": {"x": surface["x"], "y": surface["y"], "z": surface["z"]},
                "total_md": points[-1]["md"],
                "max_tvd": max(p["z"] for p in points),
                "points": points,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "units": units,
        "coordinate_system": (
            "field-relative East-North-Down; x=x_coor, y=y_coor, " "z=TVD positive-down"
        ),
        "field": {"name": field_name},
        "well_count": len(wells),
        "bounds": _bounds(wells),
        "wells": wells,
    }


def well_paths_to_json_file(payload: dict[str, Any], output_path: str) -> str:
    """Write the payload to ``output_path`` as JSON. Returns the path."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return output_path


# ---------------------------------------------------------------------------
# Synthetic demo data — lets both renderers run with zero external data.
# ---------------------------------------------------------------------------
def _synthetic_well(
    api12: str,
    label: str,
    *,
    kop: float,
    azimuth: float,
    max_inc: float,
    total_md: float,
    surf_x: float,
    surf_y: float,
    index: int,
) -> dict[str, Any]:
    """Build one synthetic deviated well (build-and-hold profile)."""
    stations = []
    md = 0.0
    step = 500.0
    while md <= total_md + 1e-9:
        if md <= kop:
            inc = 0.0
        else:
            inc = min(max_inc, (md - kop) / 1500.0 * max_inc)
        stations.append({"md": md, "inc": inc, "az": azimuth})
        md += step
    points = minimum_curvature(stations)
    for p in points:  # shift to the surface wellhead location
        p["x"] = round(p["x"] + surf_x, 2)
        p["y"] = round(p["y"] + surf_y, 2)
    return {
        "api12": api12,
        "label": label,
        "color": color_for_index(index),
        "surface": {"x": surf_x, "y": surf_y, "z": 0.0},
        "total_md": points[-1]["md"],
        "max_tvd": max(p["z"] for p in points),
        "points": points,
    }


def demo_payload() -> dict[str, Any]:
    """Return a small, realistic multi-well payload for demos and tests.

    Three deviated wells off a shared platform in a Gulf-of-Mexico-style field.
    Geometry is produced by the real minimum-curvature helper above, so the
    shapes are physically plausible, not random.
    """
    specs = [
        dict(
            api12="608124000401",
            label="DEMO A-001-ST00",
            kop=3000,
            azimuth=45,
            max_inc=55,
            total_md=15000,
            surf_x=0.0,
            surf_y=0.0,
        ),
        dict(
            api12="608124000402",
            label="DEMO A-002-ST00",
            kop=3500,
            azimuth=135,
            max_inc=42,
            total_md=14000,
            surf_x=60.0,
            surf_y=-40.0,
        ),
        dict(
            api12="608124000403",
            label="DEMO A-003-ST00",
            kop=2800,
            azimuth=255,
            max_inc=68,
            total_md=16500,
            surf_x=-50.0,
            surf_y=50.0,
        ),
    ]
    wells = [_synthetic_well(index=i, **s) for i, s in enumerate(specs)]
    return {
        "schema_version": SCHEMA_VERSION,
        "units": "ft",
        "coordinate_system": (
            "field-relative East-North-Down; x=x_coor, y=y_coor, " "z=TVD positive-down"
        ),
        "field": {"name": "DEMO FIELD"},
        "well_count": len(wells),
        "bounds": _bounds(wells),
        "wells": wells,
    }
