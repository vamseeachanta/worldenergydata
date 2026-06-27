# ABOUTME: Build the BSEE-matched FDP portfolio — engine recommendation vs as-built.
# ABOUTME: Issue #567 — crosswalk→FieldConcept, host-enriched, probe-blind recommend.
"""
worldenergydata.field_development.portfolio_matched
===================================================

Assembles the **BSEE-matched** field portfolio: the SubseaIQ fields that
crosswalk to a real BSEE block (``subseaiq_bsee_block_crosswalk.csv``, the rows
flagged ``matched``). For each field it builds a :class:`FieldConcept` whose
``concept_type`` is the **as-built** host concept (the ★ ground truth), applies
the calibration-v2 host layer to the *inputs*
(:func:`correct_satellite_labels` then :func:`enrich_concepts`), and runs the
recommendation engine on a **probe** copy with the answer stripped — mirroring
:func:`worldenergydata.field_development.calibration.backtest_fields` so the
engine can never see the concept it is being scored against.

This is the data layer behind ``scripts/field_development/build_fdp_portfolio_matched.py``;
it is HTML-free and unit-tested. The summary it emits (per-field actual vs
recommended + an aggregate top-1 match rate) is the same metric calibration pins,
restricted to the matched-field universe.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.host_enrichment import (
    correct_satellite_labels,
    enrich_concepts,
)
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.field_development.subseaiq import load_subseaiq_fields


@dataclass(frozen=True)
class CrosswalkMatch:
    """One matched SubseaIQ→BSEE crosswalk row (``matched`` == 1)."""

    og_field_name: str
    block: str
    bsee_block_code: str
    host_concept: Optional[ConceptType]  # as-built concept, or None if unrecorded
    operator: Optional[str]


@dataclass
class PortfolioRow:
    """A matched field: its enriched concept, source row, and engine pick."""

    concept: FieldConcept  # host-enriched; ``concept_type`` is the as-built actual
    match: CrosswalkMatch
    recommended: Optional[ConceptType]

    @property
    def actual(self) -> Optional[ConceptType]:
        return self.concept.concept_type

    @property
    def is_match(self) -> Optional[bool]:
        """True/False top-1 match, or None when there is no ground truth."""
        if self.actual is None:
            return None
        return self.recommended == self.actual


def _curated_crosswalk_path() -> Path:
    return (
        Path(__file__).parents[3]
        / "data"
        / "modules"
        / "offshore_assets"
        / "curated"
        / "subseaiq_bsee_block_crosswalk.csv"
    )


def _concept(value: str) -> Optional[ConceptType]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return ConceptType(value)
    except ValueError:
        return None


def load_matched_crosswalk(csv_path: Optional[Path] = None) -> list[CrosswalkMatch]:
    """Load the crosswalk rows flagged ``matched`` as :class:`CrosswalkMatch`."""
    path = csv_path or _curated_crosswalk_path()
    out: list[CrosswalkMatch] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("matched") or "").strip() != "1":
                continue
            name = (row.get("og_field_name") or "").strip()
            if not name:
                continue
            out.append(
                CrosswalkMatch(
                    og_field_name=name,
                    block=(row.get("block") or "").strip(),
                    bsee_block_code=(row.get("bsee_block_code") or "").strip(),
                    host_concept=_concept(row.get("host_concept", "")),
                    operator=((row.get("operator") or "").strip() or None),
                )
            )
    return out


def to_concept_from_crosswalk(
    match: CrosswalkMatch, base: Optional[FieldConcept] = None
) -> FieldConcept:
    """Map a crosswalk row (+ optional SubseaIQ ``fields.csv`` base) to a concept.

    ``concept_type`` is set to the crosswalk ``host_concept`` — the **as-built**
    concept the engine will be scored against. ``base`` supplies the join-derived
    inputs (water depth, region, fluid) parsed by the SubseaIQ loader; pass None
    when no fields.csv record exists for the name.
    """
    return FieldConcept(
        name=match.og_field_name,
        operator=match.operator,
        region=base.region if base else None,
        water_depth_m=base.water_depth_m if base else None,
        fluid_type=base.fluid_type if base else None,
        concept_type=match.host_concept,
        data_source="SubseaIQ + BSEE block crosswalk (matched portfolio)",
    )


def probe_of(concept: FieldConcept) -> FieldConcept:
    """Return a copy with the answer stripped (``concept_type``/``operator``).

    Mirrors ``calibration.backtest_fields``: the engine must score the inputs
    blind, never the as-built concept.
    """
    return concept.model_copy(update={"concept_type": None, "operator": None})


def top_recommendation(concept: FieldConcept) -> Optional[ConceptType]:
    """Engine's top-1 pick for a field, run on the blind probe copy."""
    picks = recommend(probe_of(concept), top_n=1)
    return picks[0].concept_type if picks else None


def build_portfolio(
    crosswalk_path: Optional[Path] = None, fields_path: Optional[Path] = None
) -> list[PortfolioRow]:
    """Build the matched-field portfolio rows from the curated data.

    Pipeline (mirrors calibration v2): load matched crosswalk → join fields.csv
    inputs → set as-built ``concept_type`` → :func:`correct_satellite_labels`
    (fix the ground truth for known tieback satellites) → :func:`enrich_concepts`
    (fill host-proximity inputs) → recommend on the blind probe.
    """
    matches = load_matched_crosswalk(crosswalk_path)
    catalog = {f.name: f for f in load_subseaiq_fields(csv_path=fields_path)}
    concepts = [
        to_concept_from_crosswalk(m, base=catalog.get(m.og_field_name)) for m in matches
    ]
    enriched = enrich_concepts(correct_satellite_labels(concepts))
    return [
        PortfolioRow(concept=c, match=m, recommended=top_recommendation(c))
        for m, c in zip(matches, enriched)
    ]


def summarize(rows: list[PortfolioRow]) -> dict:
    """Per-field {name, block, actual, recommended, match} + aggregate top-1 rate.

    The match rate's denominator is only the fields with a known as-built concept
    (rows without ground truth are still listed but cannot be scored).
    """
    per_field: list[dict] = []
    n_actual = 0
    n_matched = 0
    for r in rows:
        actual = r.actual.value if r.actual else None
        recommended = r.recommended.value if r.recommended else None
        is_match = r.is_match
        if actual is not None:
            n_actual += 1
            if is_match:
                n_matched += 1
        per_field.append(
            {
                "name": r.match.og_field_name,
                "block": r.match.bsee_block_code,
                "actual": actual,
                "recommended": recommended,
                "match": is_match,
            }
        )
    return {
        "fields": per_field,
        "n_total": len(rows),
        "n_with_actual": n_actual,
        "n_matched": n_matched,
        "top1_match_rate": (n_matched / n_actual) if n_actual else 0.0,
    }
