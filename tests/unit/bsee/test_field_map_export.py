"""Regression example for supplied locations and standalone plot data.

Numeric source: this independent synthetic example, not the field catalog.
All coordinates, depths, volumes, rates and years below are synthetic inputs;
they describe no real field or reserve estimate. The coordinate table is:

    label                  latitude    longitude
    Synthetic location A    27.125      -93.375
    Synthetic location B    26.625      -91.875
    Synthetic location C    28.375      -92.625

Each synthetic depth is 1000 m, gas volume and peak rate are zero, and the
synthetic year is 2000. Synthetic oil volumes are respectively 1000000,
2000000 and 3000000 bbl. Hand calculation using a million bbl per MMbbl gives
the expected hover volumes 1.0, 2.0 and 3.0 MMbbl. One trace represents the
whole example; marker sizes and colors must be uniform rather than encode
these volumes. Inline Plotly does not establish offline basemap availability.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from plotly.offline import get_plotlyjs

from worldenergydata.bsee.visualization.field_map import (
    FieldMapConfig,
    FieldRecord,
    GomFieldMap,
)


@pytest.fixture
def synthetic_fields():
    """Explicit inputs from the synthetic example in the module docstring."""
    return [
        FieldRecord(
            field_name="Synthetic location A",
            lat=27.125,
            lon=-93.375,
            water_depth_m=1000.0,
            geological_era="unknown",
            operator="Synthetic operator",
            cumulative_oil_bbl=1_000_000.0,
            cumulative_gas_mcf=0.0,
            peak_rate_bopd=0.0,
            first_production_year=2000,
            status="inactive",
        ),
        FieldRecord(
            field_name="Synthetic location B",
            lat=26.625,
            lon=-91.875,
            water_depth_m=1000.0,
            geological_era="unknown",
            operator="Synthetic operator",
            cumulative_oil_bbl=2_000_000.0,
            cumulative_gas_mcf=0.0,
            peak_rate_bopd=0.0,
            first_production_year=2000,
            status="inactive",
        ),
        FieldRecord(
            field_name="Synthetic location C",
            lat=28.375,
            lon=-92.625,
            water_depth_m=1000.0,
            geological_era="unknown",
            operator="Synthetic operator",
            cumulative_oil_bbl=3_000_000.0,
            cumulative_gas_mcf=0.0,
            peak_rate_bopd=0.0,
            first_production_year=2000,
            status="inactive",
        ),
    ]


def _assert_supplied_trace(traces):
    """Compare both representations with independent example literals."""
    (trace,) = traces
    assert trace["type"] == "scattermap"
    assert list(trace["lat"]) == [27.125, 26.625, 28.375]
    assert list(trace["lon"]) == [-93.375, -91.875, -92.625]
    assert list(trace["text"]) == [
        "<b>Synthetic location A</b><br>Operator: Synthetic operator<br>"
        "Era: Unknown<br>Water depth: 1000 m<br>"
        "Cum. oil: 1.0 MMbbl<br>Status: inactive",
        "<b>Synthetic location B</b><br>Operator: Synthetic operator<br>"
        "Era: Unknown<br>Water depth: 1000 m<br>"
        "Cum. oil: 2.0 MMbbl<br>Status: inactive",
        "<b>Synthetic location C</b><br>Operator: Synthetic operator<br>"
        "Era: Unknown<br>Water depth: 1000 m<br>"
        "Cum. oil: 3.0 MMbbl<br>Status: inactive",
    ]
    assert trace["mode"] == "markers"
    assert trace["hoverinfo"] == "text"
    for attribute in ("size", "color"):
        values = trace["marker"][attribute]
        assert len(values) == len(trace["lat"])
        assert len(set(values)) == 1  # Uniform markers for the whole example.


class _ExportParser(HTMLParser):
    """Inspect script tags, avoiding URL-like strings inside the runtime."""

    def __init__(self):
        super().__init__()
        self.graph_ids = []
        self.scripts = []
        self.script_sources = []
        self._script_parts = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "plotly-graph-div" in attrs.get("class", "").split():
            self.graph_ids.append(attrs["id"])
        if tag == "script":
            if "src" in attrs:
                self.script_sources.append(attrs["src"])
            self._script_parts = []

    def handle_data(self, data):
        if self._script_parts is not None:
            self._script_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script_parts is not None:
            self.scripts.append("".join(self._script_parts))
            self._script_parts = None


def test_supplied_locations_share_one_map(synthetic_fields):
    config = FieldMapConfig(size_by="uniform", title="Synthetic locations")
    figure = GomFieldMap(config).plot(fields=synthetic_fields)

    _assert_supplied_trace(figure.to_plotly_json()["data"])


@pytest.mark.parametrize("suffix", [".html", ""], ids=["html", "extensionless"])
def test_map_export_embeds_plot_runtime_and_data(synthetic_fields, tmp_path, suffix):
    field_map = GomFieldMap(FieldMapConfig(size_by="uniform"))
    figure = field_map.plot(fields=synthetic_fields)
    destination = tmp_path / f"synthetic_locations{suffix}"

    returned = field_map.export_html(figure, str(destination))

    expected_path = tmp_path / "synthetic_locations.html"
    assert returned == str(expected_path)
    assert Path(returned).suffix == ".html"
    assert set(tmp_path.iterdir()) == {expected_path}
    parser = _ExportParser()
    parser.feed(expected_path.read_text(encoding="utf-8"))
    parser.close()
    assert not parser.script_sources
    # The installed dependency supplies the real runtime, not a stub or CDN tag.
    assert any(get_plotlyjs() in script for script in parser.scripts)

    (graph_id,) = parser.graph_ids
    call = re.compile(
        r"Plotly\.newPlot\(\s*" + re.escape(json.dumps(graph_id)) + r"\s*,\s*"
    )
    embedded_traces = []
    for script in parser.scripts:
        match = call.search(script)
        if match:
            # Decode the data argument of the actual plot call, not text in JS.
            traces, _ = json.JSONDecoder().raw_decode(script[match.end() :].lstrip())
            embedded_traces.append(traces)
    (traces,) = embedded_traces
    _assert_supplied_trace(traces)
