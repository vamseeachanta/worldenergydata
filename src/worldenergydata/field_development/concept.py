# ABOUTME: Assemble a per-field concept/development block for the Explorer field view.
# ABOUTME: Real concept for all fields; FDP link is registry-gated, else a placeholder (#759).
"""
worldenergydata.field_development.concept
=========================================

Build the concept/development panel: the field's development concept (tree
type + host), play, and its lead development milestone (first oil for producers,
sanction year for pre-production fields), plus a link to its FDP portfolio page
when one exists.

Only 3 of the 10 Lower Tertiary fields have a committed FDP page
(``surfaces.fdp_page: true`` — cascade_chinook/julia/stones); the other 7 carry
an ``fdp_slug`` but no page yet, so the panel shows a **placeholder linking the
FDP-authoring ingest issue** (owner principle: missing data → grabbable issue,
never silent omission).
"""

from __future__ import annotations


def build_concept(
    *,
    concept_label: str | None,
    host_type: str | None,
    play: str | None,
    first_oil: str | None,
    fid_year: int | None,
    fdp_slug: str | None,
    has_fdp: bool,
    fdp_issue: int,
) -> dict:
    """Return the concept block for one field.

    ``first_oil`` is a display string (or ``None``); ``fid_year`` an int (or
    ``None``). Lead milestone prefers first oil (producers) and falls back to
    the sanction year (pre-production).
    """
    if first_oil:
        milestone = {"label": "First oil", "value": first_oil}
    elif fid_year is not None:
        milestone = {"label": "Sanctioned", "value": str(fid_year)}
    else:
        milestone = None
    fdp_href = (
        f"../field-development/portfolio/{fdp_slug}.html"
        if (has_fdp and fdp_slug)
        else None
    )
    return {
        "type": concept_label or host_type,
        "host": host_type,
        "play": play,
        "milestone": milestone,
        "fdp_href": fdp_href,
        "fdp_issue": fdp_issue,
    }
