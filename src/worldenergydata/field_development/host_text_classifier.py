# ABOUTME: Classify a free-text host-type string into a dry- vs wet-tree concept.
# ABOUTME: Side-effect-free; drives the dev-type badge on the life-cycle posters.
"""
worldenergydata.field_development.host_text_classifier
======================================================

Map an author-authored, free-text ``host_type`` string (e.g. "Extended
Tension-Leg Platform (eTLP)" or "Semisubmersible FPU") onto a
:class:`ConceptType` and, from that, the authoritative dry-vs-wet tree split
(:data:`recommendation._DRY_TREE`).

Dry-tree keywords are matched **before** wet-tree keywords so a host like
"Extended Tension-Leg Platform (eTLP)" resolves *dry* (TLP) even though its
downstream description mentions an "FPU". Within the wet group, "FPSO" is
matched before "tieback" so "FPSO ... with subsea tieback" reads as an FPSO
host rather than a bare tieback.
"""

from __future__ import annotations

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.recommendation import _DRY_TREE

# Ordered keyword rules. DRY concepts come first (see module docstring); within
# the wet group FPSO precedes tieback which precedes the semisub/FPU/FPS family.
_KEYWORD_RULES: tuple[tuple[tuple[str, ...], ConceptType], ...] = (
    # --- dry trees (surface / vertical well access) ---
    (("tension-leg", "tension leg", "tlp"), ConceptType.TLP),
    (("spar",), ConceptType.SPAR),
    (("compliant tower",), ConceptType.COMPLIANT_TOWER),
    (("fixed", "jacket"), ConceptType.FIXED_JACKET),
    # --- wet trees (subsea completions) ---
    (("fpso",), ConceptType.FPSO),
    (("flng",), ConceptType.FLNG),
    (("tieback", "tie-back", "tie back"), ConceptType.SUBSEA_TIEBACK),
    (("semisub", "fpu", "fps"), ConceptType.SEMISUB_FPS),
)

# Short display token per concept for the poster badge.
_LABELS: dict[ConceptType, str] = {
    ConceptType.TLP: "TLP",
    ConceptType.SPAR: "Spar",
    ConceptType.COMPLIANT_TOWER: "Compliant Tower",
    ConceptType.FIXED_JACKET: "Fixed platform",
    ConceptType.FPSO: "FPSO",
    ConceptType.FLNG: "FLNG",
    ConceptType.SUBSEA_TIEBACK: "Subsea tieback",
    ConceptType.SEMISUB_FPS: "Semisub FPU",
}


def _label_for(concept: ConceptType, low: str) -> str:
    """Display token, refining TLP to 'eTLP' when the text says so."""
    if concept is ConceptType.TLP and ("etlp" in low or "extended tension" in low):
        return "eTLP"
    return _LABELS.get(concept, concept.value)


def classify_tree_type(host_type_text: str) -> tuple[str | None, str]:
    """Classify a free-text host description into a tree type + concept label.

    Args:
        host_type_text: Author-authored host string (may be empty/None).

    Returns:
        ``(tree, label)`` where ``tree`` is ``'dry'`` | ``'wet'`` | ``None``
        (None when nothing matches) and ``label`` is a short display token
        such as ``'eTLP'`` or ``'Semisub FPU'`` (``''`` when unclassifiable).
    """
    if not host_type_text:
        return (None, "")
    low = host_type_text.lower()
    for keywords, concept in _KEYWORD_RULES:
        if any(k in low for k in keywords):
            tree = "dry" if concept in _DRY_TREE else "wet"
            return (tree, _label_for(concept, low))
    return (None, "")
