# ABOUTME: Regression tests for incident JSON embedded in the timeline script.
# ABOUTME: Uses synthetic data and an HTML parser without executing scripts.

"""Keep incident text inside the timeline script and preserve its JSON value."""

from __future__ import annotations

import json
from html.parser import HTMLParser

import pytest

from worldenergydata.hse.grounding_card import AnalysisSummary, render_html


class _Document(HTMLParser):
    def __init__(self, document: str):
        super().__init__()
        self.elements = []
        self.scripts = []
        self.in_script = False
        self.feed(document)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, attrs))
        if tag == "script":
            self.in_script = True
            self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts[-1] += data


@pytest.fixture(
    params=[
        '</script><span id="incident-marker">inert marker</span>'
        '<script type="application/json" id="incident-script">{}</script>',
        '</ScRiPt><span id="incident-marker">inert marker</span>'
        '<script type="application/json" id="incident-script">{}</script>',
        '</SCRIPT><span id="incident-marker">inert marker</span>'
        '<script type="application/json" id="incident-script">{}</script>',
        "Ordinary \"quotes\", 'apostrophes', backslash \\ and newline\ntext",
        "Unicode: café, 海, ⚓, e\u0301; < & >; literal \\u003c; </ScRiPt>"
        '<span id="incident-marker">inert marker</span>',
    ],
    ids=["lowercase", "mixed-case", "uppercase", "quotes-backslashes", "unicode"],
)
def description(request):
    return request.param


def _render(description: str) -> _Document:
    # Synthetic inputs, not engineering results. The date matches the existing
    # grounding-card test example; rank zero is an arbitrary plotting coordinate.
    incident = {
        "date": "2026-06-18",
        "severity": "minor",
        "severity_rank": 0,
        "location": "Synthetic block",
        "description": description,
        "source": "Synthetic record",
    }
    grounding = {
        "failure_mode": "Synthetic failure",
        "latest_2": [incident],
        "most_severe_2": [incident],
        "vintage_note": "Synthetic vintage",
    }
    return _Document(
        render_html(
            grounding,
            AnalysisSummary(title="Synthetic analysis", headline="Synthetic result"),
            generated_on=incident["date"],
        )
    )


def test_incident_json_cannot_terminate_script(description):
    document = _render(description)
    control = _render("Plain incident text")

    # Independent structural count: an external include and an inline plot call.
    assert len(document.scripts) == 2
    assert document.elements == control.elements


def test_timeline_json_round_trip_preserves_text(description):
    document = _render(description)
    (timeline,) = [s for s in document.scripts if 'Plotly.newPlot("timeline",' in s]
    _, separator, arguments = timeline.partition('Plotly.newPlot("timeline",')
    assert separator
    traces, _ = json.JSONDecoder().raw_decode(arguments.lstrip())

    # Hand-constructed expectation from the fixture, independent of serialization.
    expected_hover = (
        "2026-06-18 · Synthetic block<br>"
        + description
        + "<br><b>minor</b> (Synthetic record)"
    )
    assert [trace["text"] for trace in traces] == [[expected_hover], [expected_hover]]
