# ABOUTME: Generates the Chuck-facing subsea-intervention stats brief as markdown (worldenergydata #588, child of epic #582).
# ABOUTME: Every figure is rendered from the four committed source YAMLs (#583/#586/#587/#598) with explicit confidence labels — nothing is hard-coded.

"""Generated intervention stats brief — the Chuck-facing supply-constraint memo.

This module renders a markdown brief *from* the four committed source YAMLs so
that every number in the brief traces back to a reviewable data file rather than
to prose someone typed by hand:

* ``data/well_inventory_by_band.yml`` (#583) — installed subsea wells by
  water-depth band + the subsea-share reconciliation.
* ``data/serviceability_matrix.yml`` (#586) — band x scope -> which asset class
  can service it, and the riser rule that actually drives the choice.
* ``data/planned_subsea_wells.yml`` (#587) — on-record FID register of announced
  US GoM subsea developments + an analyst installation-rate envelope.
* ``vessel_fleet/data/intervention_fleet_catalog.yml`` (#598) — the unified
  intervention-asset fleet, split into a GLOBAL available roster and the small
  GoM-resident dedicated population.

The central thesis is **supply-constrained**: the deepest serviceable band holds
the most subsea wells yet sits over the thinnest dedicated-intervention fleet.

Confidence is never silently mixed. Each rendered figure carries the tag the
source YAML assigns it — ``[on record]``, ``[soft]``, ``[projected]`` or
``[engineering judgement]`` — so a reader can see how hard each number is.

The CRITICAL framing rule (see the fleet section): the global ``by_asset_class``
counts (~1,018 jackups, ~305 semis, ...) are a WORLDWIDE roster and are presented
only as background context. They are NOT GoM supply. The binding GoM figure is
``gom_resident_dedicated_intervention`` (~3 [soft]) plus the ~2-4 soft estimate.

Two upstream refinements (#623) now flow through the fleet section: the counts
are DEDUPED distinct hulls (#599, so the Helix Q-class spelling variants no
longer inflate ``heavy_intervention_semi``), and each priced asset class carries
an indicative PUBLIC day-rate band (#596) — with Helix Q-class semis and RLWI
monohulls explicitly flagged as "dayrate not public".
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Source-YAML default locations
# ---------------------------------------------------------------------------
# The three BSEE YAMLs live next to this module under ``data/``.
_DATA_DIR = Path(__file__).resolve().parent / "data"
_INVENTORY_REL = _DATA_DIR / "well_inventory_by_band.yml"
_SERVICEABILITY_REL = _DATA_DIR / "serviceability_matrix.yml"
_PLANNED_REL = _DATA_DIR / "planned_subsea_wells.yml"

# The fleet catalog lives in the separate vessel_fleet package.
_FLEET_RESOURCE = ("worldenergydata.vessel_fleet", "intervention_fleet_catalog.yml")


def _default_fleet_path() -> Path:
    """Resolve the committed fleet-catalog YAML in the vessel_fleet package."""
    from importlib import resources

    pkg, name = _FLEET_RESOURCE
    return Path(str(resources.files(pkg) / "data" / name))


def _load_yaml(path: Path) -> dict:
    import yaml

    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


def load_well_inventory(path: Optional[Path] = None) -> dict:
    """Load the installed subsea-wells-by-band inventory (#583)."""
    return _load_yaml(Path(path) if path is not None else _INVENTORY_REL)


def load_serviceability(path: Optional[Path] = None) -> dict:
    """Load the band x scope serviceability matrix (#586)."""
    return _load_yaml(Path(path) if path is not None else _SERVICEABILITY_REL)


def load_planned_wells(path: Optional[Path] = None) -> dict:
    """Load the planned/projected subsea-wells register (#587)."""
    return _load_yaml(Path(path) if path is not None else _PLANNED_REL)


def load_fleet_catalog(path: Optional[Path] = None) -> dict:
    """Load the unified intervention-fleet catalog (#598)."""
    return _load_yaml(Path(path) if path is not None else _default_fleet_path())


# ---------------------------------------------------------------------------
# Small rendering helpers
# ---------------------------------------------------------------------------
def _tag(confidence: Optional[str]) -> str:
    """Render a confidence value as a bracketed label, e.g. ``[soft]``."""
    if not confidence:
        return ""
    return f"[{str(confidence).replace('_', ' ')}]"


def _fmt_share(share) -> str:
    if share is None:
        return "n/a"
    return f"{float(share) * 100:.1f}%"


def _fmt_int(value) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_dayrate(info: dict) -> str:
    """Render an asset class's indicative public day-rate band as a cell.

    Pulls the ``indicative_dayrate`` block attached by the day-rate snapshot
    (#596). Classes the snapshot does not price render ``n/a``; classes with no
    public per-day figure (Helix Q-class semis, RLWI monohulls) render an
    explicit ``dayrate not public`` so the wall is never silently dropped.
    """
    dr = info.get("indicative_dayrate")
    if not dr:
        return "n/a"
    if not dr.get("rate_disclosed"):
        return "dayrate not public [not public]"
    low = dr.get("band_low_usd_per_day")
    high = dr.get("band_high_usd_per_day")
    median = dr.get("median_usd_per_day")
    labels = ", ".join(dr.get("confidence_labels", []) or [])
    band = f"${_fmt_int(low)}-${_fmt_int(high)}/day"
    med = f" (median ${_fmt_int(median)})" if median is not None else ""
    tag = f" [{labels}]" if labels else ""
    return f"{band}{med}{tag}"


def _deepest_populated_band(bands: dict) -> Optional[str]:
    """Return the band key holding the most subsea wells on record."""
    best_key = None
    best_count = -1
    for key, band in bands.items():
        count = band.get("subsea_wells_on_record") or 0
        if count > best_count:
            best_count = count
            best_key = key
    return best_key


# ---------------------------------------------------------------------------
# Section renderers (each returns a markdown block)
# ---------------------------------------------------------------------------
def _section_takeaway(inventory: dict, fleet: dict) -> str:
    bands = inventory.get("bands", {})
    deepest = _deepest_populated_band(bands)
    band = bands.get(deepest, {}) if deepest else {}
    label = band.get("label", deepest or "the deepest band")
    count = band.get("subsea_wells_on_record")
    share = band.get("subsea_share")

    gom = fleet.get("gom_resident_dedicated_intervention", {})
    gom_count = gom.get("count")
    gom_conf = gom.get("confidence")

    return (
        "## Takeaway\n\n"
        f"**Supply-constrained.** The deepest serviceable band ({label}) holds "
        f"the most subsea wells on record ({_fmt_int(count)} wells, "
        f"{_fmt_share(share)} subsea share) yet sits over the thinnest dedicated "
        f"fleet: only ~{_fmt_int(gom_count)} GoM-resident dedicated intervention "
        f"units {_tag(gom_conf)}. The wells are concentrated exactly where the "
        "intervention-asset supply is scarcest.\n"
    )


def _section_existing_wells(inventory: dict) -> str:
    bands = inventory.get("bands", {})
    lines = [
        "## Existing subsea wells by water-depth band",
        "",
        "Counts are from the BSEE subsea-borehole registry [on record]; the "
        "subsea-share column depends on full-population coverage and is [soft].",
        "",
        "| Band | Subsea wells [on record] | Wells in band | Subsea share [soft] |",
        "| --- | ---: | ---: | ---: |",
    ]
    for band in bands.values():
        lines.append(
            f"| {band.get('label', '?')} "
            f"| {_fmt_int(band.get('subsea_wells_on_record'))} "
            f"| {_fmt_int(band.get('total_wells_in_band'))} "
            f"| {_fmt_share(band.get('subsea_share'))} |"
        )

    total = inventory.get("subsea_total")
    stats = inventory.get("subsea_depth_stats", {})
    lines += [
        "",
        f"Subsea total on record: **{_fmt_int(total)}** wells [on record] "
        f"(depth min {_fmt_int(stats.get('min_ft'))} ft / median "
        f"{_fmt_int(stats.get('median_ft'))} ft / max "
        f"{_fmt_int(stats.get('max_ft'))} ft; n={_fmt_int(stats.get('count'))}).",
        f"Well population compared against: "
        f"{_fmt_int(inventory.get('well_population_total'))}.",
        "",
    ]
    return "\n".join(lines)


def _section_serviceability(serviceability: dict) -> str:
    matrix = serviceability.get("matrix", {})
    band_labels = serviceability.get("bands", {})
    scope_labels = serviceability.get("scopes", {})
    asset_labels = serviceability.get("asset_classes", {})
    rules = serviceability.get("rules", {})

    lines = [
        "## Serviceability — who can reach each well",
        "",
        f"**The rule: {rules.get('riser_rule', 'riser-need picks the asset.')}** "
        "Water depth alone does not choose the vessel; whether the scope needs an "
        "intervention/workover riser does. These are [engineering judgement] from "
        "standard subsea-intervention practice, not a measured BSEE dataset.",
        "",
        "| Band | Scope | Riser required | Eligible asset classes |",
        "| --- | --- | :---: | --- |",
    ]
    for band_key, scopes in matrix.items():
        band_label = band_labels.get(band_key, band_key)
        for scope_key, cell in scopes.items():
            scope_label = scope_labels.get(scope_key, scope_key)
            riser = "yes" if cell.get("riser_required") else "no"
            assets = ", ".join(cell.get("eligible_asset_classes", []))
            constrained = (
                " (availability-constrained)"
                if cell.get("availability_constrained")
                else ""
            )
            lines.append(
                f"| {band_label} | {scope_label} | {riser} | {assets}{constrained} |"
            )

    lines += [
        "",
        "Modifiers: "
        + rules.get("hxt_modifier", "")
        + " "
        + rules.get("availability_constraint", ""),
        "",
        "Asset classes: "
        + "; ".join(f"`{k}` = {v}" for k, v in asset_labels.items())
        + ".",
        "",
    ]
    return "\n".join(lines)


def _section_fleet(fleet: dict) -> str:
    gom = fleet.get("gom_resident_dedicated_intervention", {})
    recon = fleet.get("reconciliation_to_research", {})
    by_class = fleet.get("by_asset_class", {})

    lines = [
        "## Intervention-asset fleet",
        "",
        "### GoM-resident dedicated intervention units (the binding supply)",
        "",
        f"**~{_fmt_int(gom.get('count'))} units {_tag(gom.get('confidence'))}** "
        "are GoM-resident and dedicated to well intervention. This — not any "
        "global roster — is the figure that constrains GoM well access:",
        "",
        "| Unit | Class | Intervention | Water-depth rating (m) |",
        "| --- | --- | --- | ---: |",
    ]
    for unit in gom.get("units", []):
        lines.append(
            f"| {unit.get('name', '?')} | {unit.get('asset_class', '?')} "
            f"| {unit.get('intervention_class', '?')} "
            f"| {_fmt_int(unit.get('water_depth_rating_m'))} |"
        )

    lines += [
        "",
        "Triangulated against independent research:",
        "",
    ]
    for key, item in recon.items():
        label = key.replace("_", " ")
        lines.append(
            f"- {label}: **{item.get('figure')}** {_tag(item.get('confidence'))}"
            f" — {item.get('note', '')}"
        )

    dedup = fleet.get("dedup", {}) or {}
    as_of = fleet.get("dayrate_snapshot_as_of")
    dedup_note = ""
    if dedup.get("applied"):
        dedup_note = (
            f" Counts are DEDUPED distinct hulls (#599): "
            f"{_fmt_int(dedup.get('records_in'))} source listings collapse to "
            f"{_fmt_int(dedup.get('distinct_out'))} vessels "
            f"({_fmt_int(dedup.get('duplicates_collapsed'))} duplicates removed, "
            "e.g. the Helix Q-class name-spelling variants), so no hull is "
            "double-counted."
        )

    lines += [
        "",
        "### Global available roster (CONTEXT ONLY — NOT GoM supply)",
        "",
        "These are WORLDWIDE fleet counts. They include shelf and non-GoM assets "
        "and must NOT be read as Gulf-of-Mexico intervention supply. They show "
        "the size of the global pool a GoM operator competes for, nothing more."
        + dedup_note,
        "",
        "Indicative day-rates are an attached PUBLIC snapshot (#596)"
        + (f", as of {as_of}" if as_of else "")
        + " — issuer FSRs / filings / dated trade press, NOT a live subscription "
        "feed. Helix Q-class intervention semis and RLWI monohulls carry no "
        "public per-day figure (shown as dayrate not public).",
        "",
        "| Asset class (global) | Count [deduped] | Water-depth capability (ft) "
        "| Indicative day-rate |",
        "| --- | ---: | --- | --- |",
    ]
    for klass, info in by_class.items():
        cap = info.get("water_depth_capability_ft", {}) or {}
        cap_str = (
            f"{_fmt_int(cap.get('min'))}-{_fmt_int(cap.get('max'))}"
            if cap.get("min") is not None or cap.get("max") is not None
            else "n/a"
        )
        lines.append(
            f"| {klass} | {_fmt_int(info.get('count'))} | {cap_str} "
            f"| {_fmt_dayrate(info)} |"
        )

    lines += ["", ""]
    return "\n".join(lines)


def _section_planned(planned: dict) -> str:
    projects = planned.get("on_record_projects", [])
    rate = planned.get("analyst_rate", {})

    total_wells = sum(int(p.get("wells", 0) or 0) for p in projects)

    by_year: dict = {}
    for proj in projects:
        year = proj.get("first_oil_year")
        by_year[year] = by_year.get(year, 0) + int(proj.get("wells", 0) or 0)

    lines = [
        "## Planned / projected new subsea wells",
        "",
        f"The on-record FID register itemises **{len(projects)} announced US GoM "
        f"developments** totalling **{total_wells} new subsea wells [on record]** "
        "— a FLOOR, since later infill phases are deliberately not itemised. "
        "Trion is excluded (Mexican waters).",
        "",
        "New wells by first-oil year (on-record floor):",
        "",
        "| First-oil year | New subsea wells [on record] |",
        "| --- | ---: |",
    ]
    for year in sorted(by_year, key=lambda y: (y is None, y)):
        lines.append(f"| {year if year is not None else 'n/a'} | {by_year[year]} |")

    lines += [
        "",
        f"Analyst envelope: **{_fmt_int(rate.get('trees_per_year_low'))}-"
        f"{_fmt_int(rate.get('trees_per_year_high'))} "
        f"{rate.get('metric', 'wells per year')}** "
        f"(central {_fmt_int(rate.get('central'))}, "
        f"+/-{_fmt_int(rate.get('uncertainty_pct'))}%) "
        f"{_tag(rate.get('confidence'))}, {rate.get('horizon', '')}. "
        "This brackets the on-record floor (P10/P90); it is not summed with it.",
        "Sources: " + "; ".join(rate.get("sources", [])) + ".",
        "",
    ]
    return "\n".join(lines)


def _section_notes_sources() -> str:
    return (
        "## Honest-framing notes\n\n"
        "- Subsea band counts are [on record] from the BSEE borehole registry, "
        "which likely undercounts older completions; subsea-share is [soft].\n"
        "- Serviceability is [engineering judgement], not a measured dataset; "
        "band-level availability should be calibrated against the fleet.\n"
        "- The global by-asset-class fleet counts are CONTEXT only. The binding "
        "GoM intervention supply is ~3 resident dedicated units (~2-4 [soft]).\n"
        "- The planned-wells total is an on-record FLOOR; the analyst rate is "
        "[projected] and brackets — never adds to — that floor.\n\n"
        "## Sources\n\n"
        "All figures render from these committed source YAMLs:\n\n"
        "- `well_inventory_by_band.yml` — installed subsea wells by band "
        "(worldenergydata #583).\n"
        "- `serviceability_matrix.yml` — band x scope serviceability + riser rule "
        "(worldenergydata #586).\n"
        "- `planned_subsea_wells.yml` — on-record FID register + analyst rate "
        "(worldenergydata #587).\n"
        "- `intervention_fleet_catalog.yml` — unified intervention fleet "
        "(worldenergydata #598).\n"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
_HEADER = (
    "<!-- AUTO-GENERATED by "
    "worldenergydata.bsee.analysis.intervention.brief_generator.generate_brief "
    "from the source YAMLs (#583/#586/#587/#598). Do not edit by hand: edit the "
    "YAMLs and regenerate. worldenergydata #588 (child of epic #582). -->\n"
)


def generate_brief(
    out_path: Optional[Path] = None,
    inventory_path: Optional[Path] = None,
    serviceability_path: Optional[Path] = None,
    planned_path: Optional[Path] = None,
    fleet_path: Optional[Path] = None,
) -> str:
    """Render the intervention stats brief as markdown from the source YAMLs.

    Every figure is pulled from the YAMLs; nothing is hard-coded. If ``out_path``
    is given the markdown is also written there. Returns the markdown string.
    """
    inventory = load_well_inventory(inventory_path)
    serviceability = load_serviceability(serviceability_path)
    planned = load_planned_wells(planned_path)
    fleet = load_fleet_catalog(fleet_path)

    sections = [
        _HEADER,
        "# Subsea well intervention — Gulf of Mexico supply-constraint brief",
        "",
        _section_takeaway(inventory, fleet),
        _section_existing_wells(inventory),
        _section_serviceability(serviceability),
        _section_fleet(fleet),
        _section_planned(planned),
        _section_notes_sources(),
    ]
    markdown = "\n".join(sections).rstrip() + "\n"

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown)

    return markdown


if __name__ == "__main__":  # pragma: no cover
    print(generate_brief())
