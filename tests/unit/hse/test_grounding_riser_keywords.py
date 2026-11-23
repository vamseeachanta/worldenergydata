"""Riser keyword screening; synthetic cases, not observed incident claims.

Basis: docs/hse/grounding-riser-matches.md, revision 2 (2026), Classification
limits, and issue #488's riser VIV/fatigue mode. No engineering equation or
acceptance threshold is applied. Expected matches are hand classifications:
a riser term plus VIV, vortex-induced vibration or fatigue is a candidate;
neither term alone is sufficient. Weather, emergency and dropped classifications
retain their exclusions, including when explicit mechanism terms are present.
"""

from __future__ import annotations

import csv
import json

import pytest


@pytest.fixture
def riser_mode():
    from worldenergydata.hse.grounding import FAILURE_MODES

    return FAILURE_MODES["riser_viv_fatigue"]


@pytest.mark.parametrize(
    "description",
    [
        "Riser VIV",
        "VIV damage to marine riser",
        "Riser fatigue crack",
        "Fatigue failure of drilling riser",
        "Vortex-induced vibration of riser",
        "Riser vortex induced vibration",
        "RISERS - FATIGUE",
        "Riser disconnect",
    ],
)
def test_riser_candidate_keywords(riser_mode, description):
    """Each literal names riser VIV/fatigue or the retained disconnect proxy."""
    assert riser_mode.include.search(description)


@pytest.mark.parametrize(
    "description",
    [
        "VIV damage to pump",
        "Crane fatigue crack",
        "Riser inspection",
        "Riser vibration",
        "Pressurized riser string",
        "Surpriser fatigue",
        "Riser vivarium inspection",
        "Weather - riser disconnect",
        "Emergency riser disconnect",
        "Dropped riser disconnect",
        "Weather - riser VIV",
        "Emergency - riser fatigue",
        "Dropped riser - vortex-induced vibration",
    ],
)
def test_unrelated_terms_and_disconnect_exclusions(riser_mode, description):
    """No riser mechanism term, or an explicitly excluded disconnect proxy."""
    assert not riser_mode.include.search(description)


def test_keyword_candidates_flow_through_bsee_routing(tmp_path, riser_mode):
    """Hand tally: VIV + fatigue = two candidates; pump fatigue is excluded.

    Dates are synthetic ordering inputs. Newer VIV precedes older fatigue;
    the excluded pump row still sets corpus vintage. The synthetic operator
    field is deliberately private and must not enter either public rendering.
    """
    from worldenergydata.hse.grounding import ground, load_bsee

    path = tmp_path / "incidents.csv"
    with path.open("w", newline="") as target:
        writer = csv.writer(target)
        writer.writerows(
            [
                ["DATE_OCCURRED", "ACCIDENT_TYPE", "OPERATOR"],
                ["2026-01-02", "Riser VIV", "PRIVATE_SENTINEL"],
                ["2026-01-01", "Riser fatigue crack", "PRIVATE_SENTINEL"],
                ["2026-01-03", "Pump fatigue crack", "PRIVATE_SENTINEL"],
            ]
        )

    incidents = load_bsee(riser_mode, path)
    assert {record.description for record in incidents} == {
        "Riser VIV",
        "Riser fatigue crack",
    }
    result = ground("riser_viv_fatigue", bsee_path=path)
    assert result.source_counts == {
        "BSEE": 2,  # Hand tally: one VIV row plus one fatigue row.
        "OSHA": "not routed (off-domain for this mode)",
        "EPA_TRI": "not routed (off-domain for this mode)",
    }
    assert [record.date for record in result.latest] == ["2026-01-02", "2026-01-01"]
    assert not result.most_severe
    assert "current to 2026-01-03" in result.vintage_note
    assert "cause unconfirmed" in result.failure_mode
    assert "PRIVATE_SENTINEL" not in result.render_card()
    assert "PRIVATE_SENTINEL" not in json.dumps(result.to_dict())
