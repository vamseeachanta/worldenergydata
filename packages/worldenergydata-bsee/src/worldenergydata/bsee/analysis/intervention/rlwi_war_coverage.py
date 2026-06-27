# ABOUTME: Probes whether the dedicated subsea-intervention / RLWI fleet appears in the BSEE WAR record at all (worldenergydata #628).
# ABOUTME: Name/aka-matches the #593 roster + #598 seed vessels against WAR RIG_NAME, bands the hits, and emits a per-vessel + overall absent-vs-shelf-only-vs-coverage-gap verdict.

"""Does the dedicated-intervention fleet show up in BSEE WAR at all?

Epic #591's review claims **0 light-intervention (RLWI) assets are recorded in
the 5,000-10,000 ft band**. This module validates that from first principles:
it takes the named dedicated-intervention/OSV vessels (#593
``intervention_osv_roster.yml`` + #598 ``intervention_vessels_seed.yml``),
searches WAR ``RIG_NAME`` for each vessel + its alternate names, bands the
matched records by MODU water-depth band, and decides *why* a vessel is missing
from the deepwater bands.

FLOOR caveat: ``WATER_DEPTH`` is populated on only ~6% of WAR rows; every
band-resolved figure is a hard lower bound over the depth-stamped subset, never
a total. Depth-null rows are reported, never silently bucketed.

Per-vessel verdict (the absences mean very different things):

* ``not_in_war``               -- no WAR record matches; in GoM-only WAR this is
  genuine absence from the recorded population (mostly North Sea/Brazil units).
* ``in_war_depth_unknown``     -- in WAR but no record carries a depth, so it
  cannot be banded: a coverage gap, NOT evidence of scarcity.
* ``shelf_or_transition_only`` -- depth-stamped records exist but all below the
  deepwater bands.
* ``present_deepwater``        -- has a depth-stamped record in a deepwater band.

Name matching uses :func:`vessel_fleet.identity_resolver.canonicalize_name`
(reused). A WAR name matches when it equals a vessel/aka canonical name, or
contains its tokens as a contiguous subsequence (absorbing operator/class
prefixes, e.g. ``"OCEANEERING MSV OCEAN EVOLUTION"`` -> ``"OCEAN EVOLUTION"``,
``"CALDIVE Q4000"`` -> ``"Q4000"``). To avoid generic-word false positives, a
*contains* match requires the needle to be a hull token (carrying a digit) or a
multi-token name with a token rare in the WAR vocabulary (df <= ``max_token_df``);
a bare single alpha token (e.g. ``"Intervention"``) matches by exact equality
only. Aggregation is pure; I/O is confined to ``load_*`` and :func:`build_coverage`.
"""

from __future__ import annotations

import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

# Reuse the demand-axis band scheme (#583) verbatim -- never redefine bands.
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    classify_modu_band,
)

# Reuse the WAR loader (#597) so the binary read lives in exactly one place.
from worldenergydata.bsee.analysis.intervention.war_vessel_crossref import (
    DATE_COL,
    DEPTH_COL,
    RIG_COL,
    load_war,
)

# Canonical name normalisation (#599) -- shared with the identity resolver.
from worldenergydata.vessel_fleet.identity_resolver import canonicalize_name

# Deepwater bands = the MODU-servicing bands at/above 3,000 ft. The review's
# specific claim is about the 5,000-10,000 ft band.
DEEPWATER_BANDS: tuple[str, ...] = (
    "band_3000_5000",
    "band_5000_10000",
    "band_gt_10000",
)
REVIEW_BAND = "band_5000_10000"

# vessel_type values that denote a LIGHT (riser-based) well-intervention unit.
LIGHT_INTERVENTION_TYPES: frozenset[str] = frozenset({"rlwi_monohull"})

# A WAR-vocabulary token appearing in <= this many distinct rig names is treated
# as distinctive enough to anchor a (non-exact) contains match.
DEFAULT_MAX_TOKEN_DF = 5

_ROSTER_REL = Path("intervention_osv_roster.yml")
_SEED_REL = Path("intervention_vessels_seed.yml")
_WAR_REL = Path("bin") / "war" / "mv_war_main.bin"


def _resolve_vessel_data_dir(vessel_data_dir: Optional[Path]) -> Path:
    if vessel_data_dir is not None:
        return Path(vessel_data_dir)
    # Default: the committed vessel_fleet data dir next to this package.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = (
            parent
            / "worldenergydata-vessel_fleet"
            / "src"
            / "worldenergydata"
            / "vessel_fleet"
            / "data"
        )
        if candidate.exists():
            return candidate
    raise RuntimeError(
        "Could not locate vessel_fleet/data; pass vessel_data_dir explicitly."
    )


def _vessel_key(name: str, imo: object) -> str:
    """Merge key: IMO when present (strongest), else the canonical name."""
    if imo not in (None, ""):
        return f"imo:{str(imo).strip()}"
    return f"name:{canonicalize_name(name)}"


def load_intervention_vessels(
    roster_path: Optional[Path] = None,
    seed_path: Optional[Path] = None,
    vessel_data_dir: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Load + merge the dedicated-intervention vessels from roster (#593) + seed (#598).

    Records that share an IMO (or, lacking IMO, a canonical name) are merged so
    a vessel present in both files is probed once. Returns one dict per distinct
    vessel with: ``name``, ``aka`` (sorted unique alternate names, incl. the
    primary names from each file), ``vessel_types``, ``intervention_classes``,
    ``gom_resident``, ``imo``, ``source_files``.
    """
    import yaml

    data_dir = _resolve_vessel_data_dir(vessel_data_dir)
    roster_path = Path(roster_path) if roster_path else data_dir / _ROSTER_REL
    seed_path = Path(seed_path) if seed_path else data_dir / _SEED_REL

    merged: "OrderedDict[str, dict[str, Any]]" = OrderedDict()

    def _ingest(name, aka, vessel_type, intervention_class, gom, imo, source_file):
        if not name:
            return
        key = _vessel_key(name, imo)
        entry = merged.get(key)
        if entry is None:
            entry = {
                "name": name,
                "_aka": set(),
                "vessel_types": set(),
                "intervention_classes": set(),
                "gom_resident": gom,
                "imo": str(imo).strip() if imo not in (None, "") else None,
                "source_files": set(),
            }
            merged[key] = entry
        entry["_aka"].add(name)
        for alt in aka or []:
            if alt:
                entry["_aka"].add(str(alt))
        if vessel_type:
            entry["vessel_types"].add(vessel_type)
        if intervention_class:
            entry["intervention_classes"].add(intervention_class)
        if entry["gom_resident"] is None and gom is not None:
            entry["gom_resident"] = gom
        entry["source_files"].add(source_file)

    roster_doc = yaml.safe_load(roster_path.read_text()) or {}
    for v in roster_doc.get("vessels", []) or []:
        _ingest(
            v.get("vessel_name"),
            v.get("aka"),
            v.get("vessel_type"),
            None,
            v.get("gom_resident"),
            v.get("imo"),
            "intervention_osv_roster.yml",
        )
    seed_doc = yaml.safe_load(seed_path.read_text()) or {}
    for v in seed_doc.get("vessels", []) or []:
        _ingest(
            v.get("name"),
            v.get("aka"),
            v.get("vessel_type"),
            v.get("intervention_class"),
            v.get("gom_resident"),
            v.get("imo"),
            "intervention_vessels_seed.yml",
        )

    out: list[dict[str, Any]] = []
    for entry in merged.values():
        out.append(
            {
                "name": entry["name"],
                "aka": sorted(entry["_aka"]),
                "vessel_types": sorted(entry["vessel_types"]),
                "intervention_classes": sorted(entry["intervention_classes"]),
                "gom_resident": entry["gom_resident"],
                "imo": entry["imo"],
                "source_files": sorted(entry["source_files"]),
            }
        )
    return out


def _tokens(canon: str) -> tuple[str, ...]:
    return tuple(t for t in canon.split(" ") if t)


def build_token_df(war_canon_names: Iterable[str]) -> dict[str, int]:
    """Document frequency of each token across the distinct WAR canonical names.

    ``df[token]`` = number of distinct WAR rig names containing the token.
    """
    df: Counter = Counter()
    for name in set(war_canon_names):
        for tok in set(_tokens(name)):
            df[tok] += 1
    return dict(df)


def _is_distinctive_token(tok: str, token_df: dict[str, int], max_df: int) -> bool:
    if any(ch.isdigit() for ch in tok):
        return True
    return token_df.get(tok, 0) <= max_df


def _needle_is_distinctive(
    needle_tokens: tuple[str, ...], token_df: dict[str, int], max_df: int
) -> bool:
    return any(_is_distinctive_token(t, token_df, max_df) for t in needle_tokens)


def _is_subsequence(needle: tuple[str, ...], hay: tuple[str, ...]) -> bool:
    n, h = len(needle), len(hay)
    if n == 0 or n > h:
        return False
    return any(hay[i : i + n] == needle for i in range(h - n + 1))


def match_war_names(
    needle_canons: Iterable[str],
    war_canon_uniques: Iterable[str],
    token_df: dict[str, int],
    max_df: int = DEFAULT_MAX_TOKEN_DF,
) -> list[str]:
    """Return the WAR canonical rig names that match any vessel needle.

    A WAR name matches when it equals a needle (always), or contains the
    needle's tokens as a contiguous subsequence AND the needle carries a
    distinctive token (a digit/hull token or a rare WAR-vocabulary token).
    """
    needles = [c for c in {canonicalize_name(c) for c in needle_canons} if c]
    uniques = list(dict.fromkeys(war_canon_uniques))
    hay_tokens = {u: _tokens(u) for u in uniques}
    matched: set[str] = set()
    for needle in needles:
        ntoks = _tokens(needle)
        has_hull_token = any(any(ch.isdigit() for ch in t) for t in ntoks)
        # A bare single alpha token (e.g. "INTERVENTION") is too generic to
        # anchor a contains match -- it would absorb unrelated multi-word rigs
        # like "OLYMPIC INTERVENTION IV". Single-token needles match by exact
        # canonical equality only, unless the token is a hull number ("Q4000").
        contains_ok = has_hull_token or (
            len(ntoks) >= 2 and _needle_is_distinctive(ntoks, token_df, max_df)
        )
        for u in uniques:
            if u == needle:
                matched.add(u)
            elif contains_ok and _is_subsequence(ntoks, hay_tokens[u]):
                matched.add(u)
    return sorted(matched)


def _parse_year(value: object) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    year = int(match.group(0))
    return year if 1947 <= year <= 2100 else None


def _vessel_verdict(total: int, depth_stamped: int, deepwater: int) -> str:
    if total == 0:
        return "not_in_war"
    if depth_stamped == 0:
        return "in_war_depth_unknown"
    if deepwater == 0:
        return "shelf_or_transition_only"
    return "present_deepwater"


def _is_light(vessel: dict[str, Any]) -> bool:
    if any(t in LIGHT_INTERVENTION_TYPES for t in vessel.get("vessel_types", [])):
        return True
    return "light" in vessel.get("intervention_classes", [])


def _empty_band_map() -> "OrderedDict[str, int]":
    return OrderedDict((k, 0) for k in BAND_LABELS)


def probe_vessel(
    vessel: dict[str, Any],
    war: pd.DataFrame,
    war_canon: pd.Series,
    war_canon_uniques: list[str],
    token_df: dict[str, int],
    max_df: int = DEFAULT_MAX_TOKEN_DF,
) -> dict[str, Any]:
    """Probe one vessel against WAR; return its hit/band/verdict record (FLOOR)."""
    needles = [vessel.get("name", "")] + list(vessel.get("aka", []))
    matched = match_war_names(needles, war_canon_uniques, token_df, max_df)

    mask = war_canon.isin(matched)
    sub = war[mask]
    total = int(len(sub))

    depths = pd.to_numeric(sub.get(DEPTH_COL), errors="coerce")
    bands = depths.map(classify_modu_band)
    band_counts = _empty_band_map()
    for key in bands.dropna():
        if key in band_counts:
            band_counts[key] += 1
    depth_stamped = int(depths.notna().sum())
    deepwater = sum(band_counts[b] for b in DEEPWATER_BANDS)
    review_band = int(band_counts.get(REVIEW_BAND, 0))

    years = [y for y in (_parse_year(v) for v in sub.get(DATE_COL, [])) if y]
    date_range = {
        "first_year": min(years) if years else None,
        "last_year": max(years) if years else None,
    }

    example_raw: list[str] = []
    if total and RIG_COL in sub.columns:
        example_raw = [str(n) for n in sub[RIG_COL].value_counts().head(5).index]

    return {
        "vessel_name": vessel.get("name"),
        "imo": vessel.get("imo"),
        "vessel_types": vessel.get("vessel_types", []),
        "intervention_classes": vessel.get("intervention_classes", []),
        "is_light_intervention": _is_light(vessel),
        "gom_resident": vessel.get("gom_resident"),
        "aka": vessel.get("aka", []),
        "source_files": vessel.get("source_files", []),
        "matched_war_rig_names": matched,
        "example_raw_rig_names": example_raw,
        "war_records": total,
        "records_with_water_depth": depth_stamped,
        "bands_depth_stamped": dict(band_counts),
        "deepwater_records": int(deepwater),
        "review_band_records": review_band,
        "date_range": date_range,
        "verdict": _vessel_verdict(total, depth_stamped, int(deepwater)),
        "is_floor": True,
    }


def _overall_verdict(per_vessel: list[dict[str, Any]]) -> dict[str, Any]:
    light = [v for v in per_vessel if v["is_light_intervention"]]
    light_in_review = [v for v in light if v["review_band_records"] > 0]
    light_in_deep = [v for v in light if v["deepwater_records"] > 0]

    by_verdict: Counter = Counter(v["verdict"] for v in per_vessel)
    light_by_verdict: Counter = Counter(v["verdict"] for v in light)

    confirmed_band = bool(light_in_review)
    headline = (
        "CONFIRMED: 0 light-intervention/RLWI vessels have any depth-stamped WAR "
        "record in the 5,000-10,000 ft band."
        if not confirmed_band
        else (
            f"{len(light_in_review)} light-intervention/RLWI vessel(s) DO appear "
            "in the 5,000-10,000 ft band -- review finding not reproduced."
        )
    )

    return {
        "headline": headline,
        "review_claim": (
            "0 light-intervention assets recorded in 5,000-10,000 ft (epic #591 "
            "review of the subsea-intervention supply gap)."
        ),
        "review_claim_confirmed": not confirmed_band,
        "vessels_total": len(per_vessel),
        "light_intervention_vessels_total": len(light),
        "light_in_review_band": len(light_in_review),
        "light_in_any_deepwater_band": len(light_in_deep),
        "light_intervention_names": [v["vessel_name"] for v in light],
        "verdict_counts_all": dict(sorted(by_verdict.items())),
        "verdict_counts_light_intervention": dict(sorted(light_by_verdict.items())),
        "interpretation": (
            "No dedicated light-intervention/RLWI vessel is confirmed in 5,000-"
            "10,000 ft. Absences split into 'not_in_war' (genuine absence from "
            "GoM-only WAR -- mostly North Sea/Brazil units) and "
            "'in_war_depth_unknown' (in WAR but no depth stamp -- a coverage "
            "gap, NOT proof of scarcity). Confirmed deepwater intervention "
            "presence is carried by heavy semis (e.g. Helix Q4000), not the "
            "light RLWI fleet."
        ),
    }


def probe(
    war: pd.DataFrame,
    vessels: list[dict[str, Any]],
    max_df: int = DEFAULT_MAX_TOKEN_DF,
) -> dict[str, Any]:
    """Assemble the full RLWI/intervention WAR-coverage result (pure)."""
    war_canon = war.get(RIG_COL)
    if war_canon is None:
        raise KeyError(f"{RIG_COL} not in WAR frame (cols={list(war.columns)})")
    war_canon = war_canon.astype(str).map(canonicalize_name)
    war_canon_uniques = sorted({c for c in war_canon.unique() if c})
    token_df = build_token_df(war_canon_uniques)

    per_vessel = [
        probe_vessel(v, war, war_canon, war_canon_uniques, token_df, max_df)
        for v in vessels
    ]

    depths = pd.to_numeric(war.get(DEPTH_COL), errors="coerce")
    total = int(len(war))
    present = int(depths.notna().sum())
    depth_coverage = {
        "war_records_total": total,
        "records_with_water_depth": present,
        "records_missing_water_depth": total - present,
        "depth_coverage_fraction": round(present / total, 4) if total else None,
        "is_floor": True,
    }

    return {
        "overall_verdict": _overall_verdict(per_vessel),
        "depth_coverage": depth_coverage,
        "vessels": per_vessel,
        "parameters": {
            "max_token_df": max_df,
            "deepwater_bands": list(DEEPWATER_BANDS),
            "review_band": REVIEW_BAND,
            "light_intervention_types": sorted(LIGHT_INTERVENTION_TYPES),
            "band_scheme_ft": dict(BAND_LABELS),
        },
        "caveats": [
            "FLOOR: WATER_DEPTH is populated on only ~6% of WAR rows (~94% NULL); "
            "every band-resolved count is a hard lower bound, not a total.",
            "Banding uses only depth-stamped records; depth-null rows are counted "
            "under records_with_water_depth, never silently bucketed.",
            "'in_war_depth_unknown' means the vessel IS in WAR but has no depth "
            "stamp -- a coverage gap, NOT evidence of deepwater absence.",
            "'not_in_war' in GoM-only WAR means genuine absence from the recorded "
            "GoM population; many dedicated units are North Sea / Brazil vessels.",
            "Name matching is canonical-name + distinctive-token-anchored "
            "subsequence; rare aliases of generic vessels can still be missed or "
            "(less likely) over-matched. matched_war_rig_names is shown for audit.",
            "A single physical asset can appear under several RIG_NAME spellings; "
            "all spellings matching a vessel are unioned before counting.",
        ],
        "provenance": {
            "war_source": "BSEE war/mv_war_main.bin (well-activity reports)",
            "vessel_sources": [
                "vessel_fleet/data/intervention_osv_roster.yml (#593)",
                "vessel_fleet/data/intervention_vessels_seed.yml (#598)",
            ],
            "name_normalizer": "vessel_fleet.identity_resolver.canonicalize_name (#599)",
            "band_scheme": "bsee...well_inventory_by_band (#583)",
            "issue": "worldenergydata#628 (epic #591)",
        },
    }


def build_coverage(
    data_dir: Optional[Path] = None,
    war_path: Optional[Path] = None,
    roster_path: Optional[Path] = None,
    seed_path: Optional[Path] = None,
    vessel_data_dir: Optional[Path] = None,
    out_path: Optional[Path] = None,
    max_df: int = DEFAULT_MAX_TOKEN_DF,
) -> dict[str, Any]:
    """Load WAR + the intervention rosters, run the probe, optionally write YAML."""
    if war_path is None and data_dir is not None:
        war_path = Path(data_dir) / _WAR_REL
    war = load_war(data_dir=data_dir, war_path=war_path)
    vessels = load_intervention_vessels(roster_path, seed_path, vessel_data_dir)
    result = probe(war, vessels, max_df=max_df)

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result
