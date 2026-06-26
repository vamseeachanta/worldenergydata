# ABOUTME: SubseaIQ host-registry enrichment of FieldConcept inputs (calibration v2).
# ABOUTME: Issue #567 — host reserves/wells + tieback distance feed the engine.
"""
worldenergydata.field_development.host_enrichment
=================================================

Closes part of the recommendation engine's *input gap* (see :mod:`calibration`).

The engine already reasons about ``distance_to_host_km``, ``host_spare_capacity``,
``recoverable_reserves_mmboe`` and ``num_wells`` — but the SubseaIQ field loader
(:mod:`subseaiq`) fills none of them, so the engine runs on water depth + fluid
alone. In particular a ``subsea_tieback`` is *removed from feasibility* whenever
distance-to-host is unknown, which is always — so it can never be predicted.

This module reads the curated **host registry** (``subseaiq_hosts.csv``, ingested
from the SubseaIQ ``og_host`` table by
``scripts/field_development/ingest_subseaiq_hosts.py``) and uses it to populate
those inputs:

* A field named as a **subsea-tieback satellite** of a host (e.g. *Great White* →
  *Perdido*) genuinely has a reachable host nearby — knowledge an operator holds
  at concept-select. We set ``host_spare_capacity=True`` and a screening
  ``distance_to_host_km`` (the table carries no per-tieback offset, so a
  GoM-typical median is used and documented), plus the satellite's well count.
* A **host field** (e.g. *Perdido*, *Holstein*) gains its real reserves and well
  count — but no tieback distance, because it is a standalone host.

**Leakage discipline:** enrichment only ever fills *input* features and only when
they are currently ``None``; it never sets ``concept_type``. The distance for a
tieback is an approximation, disclosed here, not the true measured offset.

The runtime reads only the committed CSV — it never depends on ``llm-wiki``.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.models import FieldConcept

# GoM subsea tiebacks typically sit within a few tens of km of their host; the
# og_host table records no per-tieback offset, so this median stands in as a
# screening value. It is well inside the engine's tieback_max_km (60) and
# flow_assurance_warn_km (32), so a known tieback reads as a clean, attractive
# tieback rather than a marginal long offset.
GOM_TYPICAL_TIEBACK_KM = 25.0

# A field name must be at least this many normalized chars to prefix-match a host
# vessel name — guards against a 2-letter area code spuriously matching.
_MIN_HOST_MATCH_LEN = 4


@dataclass(frozen=True)
class HostRecord:
    """One curated host facility with its field link and tieback satellites."""

    host_name: str
    host_concept: ConceptType
    general_location: str
    block_raw: str
    bsee_block_key: Optional[str]
    water_depth_m: Optional[float]
    reserves_mmboe: Optional[float]
    total_wells: Optional[int]
    dry_tree_wells: Optional[int]
    wet_tree_wells: Optional[int]
    throughput_mboed: Optional[float]
    tieback_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TiebackLink:
    """A resolved tieback satellite → host relationship."""

    field_name: str
    host_name: str
    host_concept: ConceptType
    wells: Optional[int]


def _norm(name: str) -> str:
    """Lowercase alphanumeric key for forgiving name joins."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _curated_path() -> Path:
    return (
        Path(__file__).parents[3]
        / "data"
        / "modules"
        / "offshore_assets"
        / "curated"
        / "subseaiq_hosts.csv"
    )


def _int(text: str) -> Optional[int]:
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _float(text: str) -> Optional[float]:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _split_tiebacks(cell: str) -> list[str]:
    """Split the ``tieback_fields`` cell into one satellite per entry.

    The curated CSV is canonically ``"; "``-separated, but we also split on
    commas defensively (a "(n)" well-count never contains a comma).
    """
    return [p.strip() for p in re.split(r"[;,]", cell or "") if p.strip()]


def _parse_satellite(entry: str) -> tuple[str, Optional[int]]:
    """Parse one satellite entry ("Great White (30)" → ("Great White", 30))."""
    m = re.match(r"\s*(.*?)\s*(?:\((\d+)[^)]*\))?\s*$", entry)
    if not m:
        return entry.strip(), None
    name = m.group(1).strip()
    return name, _int(m.group(2)) if m.group(2) else None


def load_host_registry(csv_path: Optional[Path] = None) -> list[HostRecord]:
    """Load the curated host registry as :class:`HostRecord` objects."""
    path = csv_path or _curated_path()
    out: list[HostRecord] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            concept = ConceptType(row["host_concept"])
            out.append(
                HostRecord(
                    host_name=row["host_name"].strip(),
                    host_concept=concept,
                    general_location=row.get("general_location", ""),
                    block_raw=row.get("block_raw", ""),
                    bsee_block_key=(row.get("bsee_block_key") or None),
                    water_depth_m=_float(row.get("water_depth_m")),
                    reserves_mmboe=_float(row.get("reserves_mmboe")),
                    total_wells=_int(row.get("total_wells")),
                    dry_tree_wells=_int(row.get("dry_tree_wells")),
                    wet_tree_wells=_int(row.get("wet_tree_wells")),
                    throughput_mboed=_float(row.get("throughput_mboed")),
                    tieback_fields=_split_tiebacks(row.get("tieback_fields", "")),
                )
            )
    return out


def match_tieback(field_name: str, registry: list[HostRecord]) -> Optional[TiebackLink]:
    """Resolve a field to the host it ties back to, or None.

    Self-referential entries (a host listing its own field as a tieback) are
    dropped — they describe the host's own wells, not a satellite.
    """
    key = _norm(field_name)
    if not key:
        return None
    for host in registry:
        host_key = _norm(host.host_name)
        for entry in host.tieback_fields:
            sat_name, wells = _parse_satellite(entry)
            sat_key = _norm(sat_name)
            if not sat_key or host_key.startswith(sat_key):
                continue  # self-reference → not a real satellite
            if sat_key == key:
                return TiebackLink(
                    field_name=sat_name,
                    host_name=host.host_name,
                    host_concept=host.host_concept,
                    wells=wells,
                )
    return None


def match_host(field_name: str, registry: list[HostRecord]) -> Optional[HostRecord]:
    """Resolve a field name to its host record by normalized prefix, or None.

    Host names carry the vessel suffix ("BOOMVANG Global Producer VI"), so a
    field matches when its normalized name prefixes the host's (with a minimum
    length to avoid spurious short matches).
    """
    key = _norm(field_name)
    if len(key) < _MIN_HOST_MATCH_LEN:
        return None
    for host in registry:
        if _norm(host.host_name).startswith(key):
            return host
    return None


def enrich_concept(concept: FieldConcept, registry: list[HostRecord]) -> FieldConcept:
    """Return a copy of ``concept`` with host-derived inputs filled (None-only).

    A known tieback satellite wins over a host match (a field can appear in both
    roles, but its satellite role carries the actionable host link). Never sets
    ``concept_type``.
    """
    updates: dict[str, object] = {}
    link = match_tieback(concept.name, registry)
    if link is not None:
        if concept.distance_to_host_km is None:
            updates["distance_to_host_km"] = GOM_TYPICAL_TIEBACK_KM
        if concept.host_spare_capacity is None:
            updates["host_spare_capacity"] = True
        if concept.num_wells is None and link.wells is not None:
            updates["num_wells"] = link.wells
    else:
        host = match_host(concept.name, registry)
        if host is not None:
            if concept.recoverable_reserves_mmboe is None and host.reserves_mmboe:
                updates["recoverable_reserves_mmboe"] = host.reserves_mmboe
            if concept.num_wells is None and host.total_wells is not None:
                updates["num_wells"] = host.total_wells
    return concept.model_copy(update=updates) if updates else concept


def enrich_concepts(
    fields: list[FieldConcept], registry: Optional[list[HostRecord]] = None
) -> list[FieldConcept]:
    """Enrich a list of concepts from the host registry (loads it if not given)."""
    reg = registry if registry is not None else load_host_registry()
    return [enrich_concept(f, reg) for f in fields]


def correct_satellite_labels(
    fields: list[FieldConcept], registry: Optional[list[HostRecord]] = None
) -> list[FieldConcept]:
    """Relabel known tieback satellites to ``subsea_tieback`` (ground-truth fix).

    The SubseaIQ facility-join stamps a satellite field with its *host's* concept
    (so *Great White*, a subsea tieback to the *Perdido* spar, is mislabeled
    ``spar``). og_host is the authoritative source of the host→satellite
    relationship, so a field it lists as a tieback satellite *is* a
    ``subsea_tieback``. Only fields carrying a non-tieback concept are changed.
    """
    reg = registry if registry is not None else load_host_registry()
    out: list[FieldConcept] = []
    for f in fields:
        link = match_tieback(f.name, reg)
        if (
            link is not None
            and f.concept_type is not None
            and f.concept_type != ConceptType.SUBSEA_TIEBACK
        ):
            out.append(
                f.model_copy(update={"concept_type": ConceptType.SUBSEA_TIEBACK})
            )
        else:
            out.append(f)
    return out
