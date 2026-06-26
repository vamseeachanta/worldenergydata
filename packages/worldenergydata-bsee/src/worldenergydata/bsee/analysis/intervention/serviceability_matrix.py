# ABOUTME: Depth-band x intervention-scope -> serviceable-by capability matrix (worldenergydata #586).
# ABOUTME: Encodes the "requires a MODU" determination — riser-need (not water depth) picks the asset class.

"""Serviceability matrix — the "requires a MODU" determination (epic #582, #586).

The subsea-intervention/maintenance database (#582) needs a decision layer that
turns a well's *water-depth band* (from #583) and the *intervention scope* into
the set of asset classes that can actually service it, and whether a riser is
required. The central engineering rule encoded here:

    Depth does **not** pick the asset; **riser-need** picks the asset.

A 9,000 ft riserless wireline job and a 2,000 ft riserless wireline job both use
the same light intervention asset class — the band only changes *availability*
(how many such units are rated/working in that band), not *capability*. What
forces a heavy, riser-based asset (a MODU or a Helix Q-class heavy-intervention
semi) is the scope of work: anything that opens the production envelope and needs
a workover riser + subsea BOP (tubing pull, recompletion, ESP change-out, P&A).

Three intervention scopes are modelled:

* ``light_live_well`` — riserless light well intervention (RLWI). Wireline /
  slickline run through a subsea lubricator from an RLWI monohull or an MPSV.
  Live well, no riser.
* ``through_tubing_ct`` — coiled-tubing through-tubing work (stimulation, scale
  removal, perforating). Needs an intervention riser; a heavy-intervention semi
  or a MODU.
* ``heavy_dead_well`` — tubing pull / recompletion / ESP change-out / P&A. Full
  workover riser + subsea BOP. A MODU or a Helix Q-class heavy-intervention semi.

Two engineering modifiers:

* **Horizontal subsea tree (HXT)** — on a horizontal tree the tubing hanger lands
  in the tree, so the tubing cannot be pulled without going through the tree.
  An HXT tubing pull therefore forces a riser-based asset *even for what would
  otherwise be light scope*. (Vertical trees keep the riserless option.)
* **5,000–10,000 ft availability constraint** — light riserless work is fully
  *capable* in the ultra-deepwater band, but the pool of RLWI/MPSV units rated
  and contracted for that depth is thin. That band is therefore flagged
  ``availability_constrained`` for light work — an availability limit, not a
  capability limit.

Numbers/rules are externalised to a reviewable YAML so downstream consumers
(the #588 brief, digitalmodel #891 demand model) read data, not hard-coded logic.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Optional

# Reuse the band scheme from #583 — DO NOT redefine bands here.
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    MODU_SERVICING_BANDS,
    classify_modu_band,  # noqa: F401  (re-exported for callers that band a depth)
)

# Asset classes are referenced conceptually from the vessel-fleet taxonomy (#592).
# Import is best-effort so this module's *logic* stays self-contained and CI-safe
# even when the vessel_fleet package is not on the path.
try:  # pragma: no cover - import shim
    from worldenergydata.vessel_fleet.constants import VesselType

    _RLWI_MONOHULL = VesselType.RLWI_MONOHULL.value
    _MPSV = VesselType.MPSV.value
    _HEAVY_INTERVENTION_SEMI = VesselType.HEAVY_INTERVENTION_SEMI.value
except Exception:  # pragma: no cover - fallback to literal asset-class keys
    _RLWI_MONOHULL = "rlwi_monohull"
    _MPSV = "mpsv"
    _HEAVY_INTERVENTION_SEMI = "heavy_intervention_semi"

# A MODU (mobile offshore drilling unit — drillship / drilling semi) is a drilling
# asset, not a construction/service VesselType, so it carries its own key here.
_MODU = "modu"

# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------
# Intervention scopes in increasing intervention weight. Each scope's *base*
# eligibility and riser-need are properties of the WORK, not the water depth —
# that is the whole point of the matrix.
SCOPE_LABELS: "OrderedDict[str, str]" = OrderedDict(
    [
        ("light_live_well", "Light live-well (riserless wireline)"),
        ("through_tubing_ct", "Through-tubing coiled tubing"),
        ("heavy_dead_well", "Heavy dead-well (tubing pull / recompletion / P&A)"),
    ]
)

_SCOPE_RULES: dict[str, dict] = {
    "light_live_well": {
        "description": (
            "Riserless light well intervention: wireline/slickline through a "
            "subsea lubricator from an RLWI monohull or MPSV. Live well, no riser."
        ),
        "eligible_asset_classes": [_RLWI_MONOHULL, _MPSV],
        "riser_required": False,
    },
    "through_tubing_ct": {
        "description": (
            "Through-tubing coiled-tubing work (stimulation, scale, perforating). "
            "Needs an intervention riser — heavy-intervention semi or MODU."
        ),
        "eligible_asset_classes": [_HEAVY_INTERVENTION_SEMI, _MODU],
        "riser_required": True,
    },
    "heavy_dead_well": {
        "description": (
            "Tubing pull / recompletion / ESP change-out / P&A. Full workover "
            "riser + subsea BOP — a MODU or a Helix Q-class heavy-intervention semi."
        ),
        "eligible_asset_classes": [_MODU, _HEAVY_INTERVENTION_SEMI],
        "riser_required": True,
    },
}

# The asset classes that a horizontal-tree-forced or otherwise riser-based job
# falls back to (drop the riserless light units).
_RISER_BASED_ASSETS: list[str] = [_MODU, _HEAVY_INTERVENTION_SEMI]

# The band where light riserless work is capable but supply-thin.
_AVAILABILITY_CONSTRAINED_BAND = "band_5000_10000"

_RISER_RULE = "Depth does not pick the asset; riser-need picks the asset."

SCOPES: tuple[str, ...] = tuple(SCOPE_LABELS.keys())


# ---------------------------------------------------------------------------
# Core pure function
# ---------------------------------------------------------------------------
def serviceable_assets(band: str, scope: str, horizontal_tree: bool = False) -> dict:
    """Return the serviceability record for one (band, scope) cell.

    Parameters
    ----------
    band:
        A band key from ``BAND_LABELS`` (#583 scheme).
    scope:
        A scope key from ``SCOPES``.
    horizontal_tree:
        If ``True``, the well has a horizontal subsea tree (HXT). An HXT tubing
        pull cannot be done riserless, so a light scope is forced riser-based.

    Returns
    -------
    dict
        ``eligible_asset_classes``, ``riser_required`` and the band/scope flags
        that explain the determination.
    """
    if band not in BAND_LABELS:
        raise KeyError(f"unknown band {band!r}; expected one of {list(BAND_LABELS)}")
    if scope not in _SCOPE_RULES:
        raise KeyError(f"unknown scope {scope!r}; expected one of {list(SCOPES)}")

    rule = _SCOPE_RULES[scope]
    eligible = list(rule["eligible_asset_classes"])
    riser_required = bool(rule["riser_required"])
    notes: list[str] = []

    # --- Horizontal-tree (HXT) modifier ---
    # On a horizontal tree the tubing hanger lands in the tree, so pulling tubing
    # forces a riser-based asset even for a scope that is riserless on a vertical
    # tree. Only the light (riserless) scope can change; the CT/heavy scopes are
    # already riser-based.
    hxt_modifier_applied = False
    if horizontal_tree and not riser_required:
        eligible = list(_RISER_BASED_ASSETS)
        riser_required = True
        hxt_modifier_applied = True
        notes.append(
            "HXT tubing pull forces riser-based access — riserless light units "
            "cannot pull tubing through a horizontal tree."
        )

    # --- 5,000-10,000 ft availability constraint (light work only) ---
    # Capability is unchanged; only the supply of rated/working light units is
    # thin in the ultra-deepwater band.
    availability_constrained = (
        band == _AVAILABILITY_CONSTRAINED_BAND
        and scope == "light_live_well"
        and not hxt_modifier_applied
    )
    if availability_constrained:
        notes.append(
            "Light riserless work is fully capable here, but the pool of "
            "RLWI/MPSV units rated for 5,000-10,000 ft is thin — an availability "
            "limit, not a capability limit."
        )

    modu_servicing_band = band in MODU_SERVICING_BANDS
    if not modu_servicing_band:
        notes.append(
            "Shelf band (< 500 ft): jack-up / platform serviceable — not a "
            "MODU-required water depth."
        )

    return {
        "band": band,
        "band_label": BAND_LABELS[band],
        "scope": scope,
        "scope_label": SCOPE_LABELS[scope],
        "scope_description": rule["description"],
        "eligible_asset_classes": eligible,
        "riser_required": riser_required,
        "riser_rule": _RISER_RULE,
        "modu_servicing_band": modu_servicing_band,
        "availability_constrained": availability_constrained,
        "horizontal_tree": bool(horizontal_tree),
        "hxt_modifier_applied": hxt_modifier_applied,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Matrix assembly (pure)
# ---------------------------------------------------------------------------
def build_matrix(
    horizontal_tree: bool = False,
) -> "OrderedDict[str, OrderedDict[str, dict]]":
    """Build the full band x scope serviceability matrix (nested dict).

    By default this is the vertical-tree (VXT) base case. Pass
    ``horizontal_tree=True`` for the HXT variant, where light tubing-access
    scope is forced riser-based.
    """
    matrix: "OrderedDict[str, OrderedDict[str, dict]]" = OrderedDict()
    for band in BAND_LABELS:
        row: "OrderedDict[str, dict]" = OrderedDict()
        for scope in SCOPES:
            row[scope] = serviceable_assets(
                band, scope, horizontal_tree=horizontal_tree
            )
        matrix[band] = row
    return matrix


def _as_plain(matrix: "OrderedDict[str, OrderedDict[str, dict]]") -> dict:
    """Convert the nested OrderedDict matrix to plain dicts for YAML dumping."""
    return {
        band: {scope: dict(cell) for scope, cell in row.items()}
        for band, row in matrix.items()
    }


# ---------------------------------------------------------------------------
# Build / serialise
# ---------------------------------------------------------------------------
def build_serviceability(out_path: Optional[Path] = None) -> dict:
    """Assemble the serviceability matrix result; optionally write YAML.

    Returns a dict with the vertical-tree ``matrix``, the ``horizontal_tree``
    variant, the ``scopes`` legend, ``asset_classes`` legend, a ``confidence``
    note and ``provenance``.
    """
    result = {
        "matrix": _as_plain(build_matrix(horizontal_tree=False)),
        "horizontal_tree_variant": _as_plain(build_matrix(horizontal_tree=True)),
        "scopes": dict(SCOPE_LABELS),
        "bands": dict(BAND_LABELS),
        "asset_classes": {
            _RLWI_MONOHULL: "Riserless light well intervention monohull (vessel_fleet #592)",
            _MPSV: "Multipurpose support vessel (vessel_fleet #592)",
            _HEAVY_INTERVENTION_SEMI: "Heavy-intervention semi, e.g. Helix Q-class (vessel_fleet #592)",
            _MODU: "Mobile offshore drilling unit (drillship / drilling semi)",
        },
        "rules": {
            "riser_rule": _RISER_RULE,
            "hxt_modifier": (
                "A horizontal subsea tree (HXT) tubing pull forces a riser-based "
                "asset even for otherwise-light scope."
            ),
            "availability_constraint": (
                "Light riserless work in 5,000-10,000 ft is availability_constrained "
                "(thin supply of rated units), not capability-limited."
            ),
        },
        "provenance": {
            "band_scheme": "worldenergydata#583 (well_inventory_by_band)",
            "asset_taxonomy": "worldenergydata#592 (vessel_fleet.constants.VesselType)",
            "issue": "worldenergydata#586 (epic #582)",
        },
        "confidence": (
            "Capability/riser-need rules are [engineering judgement] from standard "
            "subsea-intervention practice (RLWI vs CT vs full workover), not a "
            "measured BSEE dataset. Band-level *availability* (unit supply) is "
            "indicative and should be calibrated against the vessel fleet (#592)."
        ),
    }

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result


if __name__ == "__main__":  # pragma: no cover
    _here = Path(__file__).resolve().parent
    out = _here / "data" / "serviceability_matrix.yml"
    build_serviceability(out_path=out)
    print(f"wrote {out}")
