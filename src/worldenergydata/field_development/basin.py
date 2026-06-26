# ABOUTME: Sourced basin → concept-family affinity prior (calibration v2).
# ABOUTME: Issue #567 — regional development culture as a scoring criterion.
"""
worldenergydata.field_development.basin
=======================================

A **basin/region prior** for the recommendation engine.

Water depth gates *which* concepts are feasible, but in the same depth band the
choice between, say, an FPSO and a semisub or a spar is driven heavily by
**regional development practice** — a real, documented signal the depth-only
engine was blind to (it never predicted FPSO; see :mod:`calibration`). Examples
that any offshore engineer would state as fact:

* **Brazil** (Campos/Santos pre-salt) is FPSO country — standalone floaters with
  storage, rarely fixed platforms or spars.
* **West Africa deepwater** (Angola, Nigeria, Congo, Gabon, Equatorial Guinea,
  Ghana) is overwhelmingly FPSO.
* The **US Gulf of Mexico** historically did *not* use FPSOs (the first, BW
  Pioneer, came only in 2012); its deepwater is spars, semisubs, TLPs and subsea
  tiebacks. So GoM should *suppress* FPSO and favour the moored-floater family.
* The **North Sea** (UK, Norway, Denmark, Netherlands) is fixed jackets on the
  shelf plus FPSOs and subsea tiebacks in deeper/marginal areas; spars/TLPs are
  essentially absent.

This is **sourced domain knowledge**, encoded as a coarse affinity table — the
same kind of prior as the per-concept depth envelopes in :mod:`sanity`. It is
deliberately *not* a frequency fitted to the calibration labels: the basin
archetypes are few and the affinities are favour/neutral/disfavour levels chosen
from development practice, so the prior generalizes to unseen fields in a basin
rather than memorizing the back-test.
"""

from __future__ import annotations

from worldenergydata.field_development.enums import ConceptType

# Affinity levels (a concept's fit to a basin's development culture).
FAVOURED = 1.0
NEUTRAL = 0.5
DISFAVOURED = 0.15

# Region (the SubseaIQ ``COUNTRY`` value) → basin archetype. Lower-cased keys;
# unmapped regions fall through to a neutral prior.
_REGION_TO_BASIN: dict[str, str] = {
    "us": "gom",
    "gulf of mexico": "gom",
    "mexico": "gom_shelf",
    "brazil": "brazil",
    "angola": "w_africa",
    "nigeria": "w_africa",
    "congo": "w_africa",
    "congo, the demo. rep. of the": "w_africa",
    "gabon": "w_africa",
    "equatorial guinea": "w_africa",
    "ghana": "w_africa",
    "ivory coast": "w_africa",
    "cote d'ivoire": "w_africa",
    "uk": "north_sea",
    "norway": "north_sea",
    "denmark": "north_sea",
    "netherlands": "north_sea",
    "australia": "aus_sea_asia",
    "indonesia": "aus_sea_asia",
    "malaysia": "aus_sea_asia",
    "thailand": "aus_sea_asia",
    "viet nam": "aus_sea_asia",
    "vietnam": "aus_sea_asia",
    "china": "aus_sea_asia",
    "india": "aus_sea_asia",
}

# Basin archetype → per-concept affinity. Concepts omitted from a basin's map are
# scored NEUTRAL. Encodes documented regional development practice (see module
# docstring), not fitted label frequencies.
BASIN_AFFINITY: dict[str, dict[ConceptType, float]] = {
    # Brazil pre-salt/Campos: FPSO standalone floaters; no fixed/spar.
    "brazil": {
        ConceptType.FPSO: FAVOURED,
        ConceptType.SEMISUB_FPS: NEUTRAL,
        ConceptType.SUBSEA_TIEBACK: NEUTRAL,
        ConceptType.FIXED_JACKET: DISFAVOURED,
        ConceptType.SPAR: DISFAVOURED,
        ConceptType.TLP: DISFAVOURED,
        ConceptType.COMPLIANT_TOWER: DISFAVOURED,
    },
    # West Africa deepwater: FPSO-dominant.
    "w_africa": {
        ConceptType.FPSO: FAVOURED,
        ConceptType.SUBSEA_TIEBACK: NEUTRAL,
        ConceptType.COMPLIANT_TOWER: NEUTRAL,
        ConceptType.FIXED_JACKET: DISFAVOURED,
        ConceptType.SPAR: DISFAVOURED,
        ConceptType.TLP: DISFAVOURED,
        ConceptType.SEMISUB_FPS: DISFAVOURED,
    },
    # US Gulf of Mexico deepwater: moored-floater family + subsea; FPSO rare.
    "gom": {
        ConceptType.SPAR: FAVOURED,
        ConceptType.SEMISUB_FPS: FAVOURED,
        ConceptType.TLP: FAVOURED,
        ConceptType.SUBSEA_TIEBACK: FAVOURED,
        ConceptType.FIXED_JACKET: NEUTRAL,
        ConceptType.COMPLIANT_TOWER: NEUTRAL,
        ConceptType.FPSO: DISFAVOURED,
        ConceptType.FLNG: DISFAVOURED,
    },
    # GoM/Mexico shelf: shallow fixed platforms.
    "gom_shelf": {
        ConceptType.FIXED_JACKET: FAVOURED,
        ConceptType.NUI: FAVOURED,
        ConceptType.FPSO: DISFAVOURED,
        ConceptType.SPAR: DISFAVOURED,
    },
    # North Sea: fixed jackets + FPSO + subsea; spars/TLPs absent.
    "north_sea": {
        ConceptType.FIXED_JACKET: FAVOURED,
        ConceptType.FPSO: FAVOURED,
        ConceptType.SUBSEA_TIEBACK: FAVOURED,
        ConceptType.SEMISUB_FPS: NEUTRAL,
        ConceptType.SPAR: DISFAVOURED,
        ConceptType.TLP: DISFAVOURED,
        ConceptType.COMPLIANT_TOWER: DISFAVOURED,
    },
    # Australia / SE Asia: FPSO + fixed + subsea + FLNG (NW Shelf gas).
    "aus_sea_asia": {
        ConceptType.FPSO: FAVOURED,
        ConceptType.FIXED_JACKET: FAVOURED,
        ConceptType.SUBSEA_TIEBACK: FAVOURED,
        ConceptType.FLNG: NEUTRAL,
        ConceptType.SPAR: DISFAVOURED,
        ConceptType.TLP: DISFAVOURED,
    },
}


def region_to_basin(region: str | None) -> str | None:
    """Map a SubseaIQ region/country to a basin archetype, or None if unmapped."""
    if not region:
        return None
    return _REGION_TO_BASIN.get(region.strip().lower())


def region_fit(concept: ConceptType, region: str | None) -> float:
    """Affinity in [0, 1] of a concept to the region's basin development culture.

    Returns the neutral mid-score when the region is unknown or unmapped, so the
    prior only ever *adds* signal where the basin is recognized — it never
    penalizes a field merely for lacking a region.
    """
    basin = region_to_basin(region)
    if basin is None:
        return NEUTRAL
    return BASIN_AFFINITY.get(basin, {}).get(concept, NEUTRAL)
