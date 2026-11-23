"""Tests for the myshiptracking particulars parser (#988)."""

from worldenergydata.vessel_fleet.parsers.myshiptracking import (
    parse_particulars_html,
    vessel_url,
)

# Verbatim structure of the particulars rows (Grande Spagna, retrieved
# 2026-07-13) — th/td pairs as served.
SAMPLE_HTML = """
<table><tbody>
<tr><th>Type</th><td></td></tr>
<tr><th>IMO</th><td>9227924</td></tr>
<tr><th>MMSI</th><td>247056200</td></tr>
<tr><th>Flag</th><td><img class="Flag" title="Italy"/> Italy</td></tr>
<tr><th>Call Sign</th><td>IBTD</td></tr>
<tr><th>Size</th><td>177 x 31 m</td></tr>
<tr><th>GT</th><td>37,726 Tons</td></tr>
<tr><th>DWT</th><td>12,594 Tons</td></tr>
<tr><th>Build</th><td>2002  ( 24 years old )</td></tr>
<tr><th>AVG Speed</th><td>14.6 Knots</td></tr>
</tbody></table>
"""


class TestParseParticulars:
    def setup_method(self):
        self.spec = parse_particulars_html(SAMPLE_HTML)

    def test_identifiers(self):
        assert self.spec["IMO_NUMBER"] == "9227924"
        assert self.spec["MMSI"] == "247056200"
        assert self.spec["FLAG_STATE"] == "Italy"

    def test_size_split(self):
        assert self.spec["LOA_M"] == 177.0
        assert self.spec["BEAM_M"] == 31.0

    def test_tonnages_and_year(self):
        assert self.spec["GROSS_TONNAGE"] == 37726.0
        assert self.spec["DEADWEIGHT_TONNES"] == 12594.0
        assert self.spec["YEAR_BUILT"] == 2002

    def test_ais_state_not_ingested(self):
        # Current speeds/draught describe state, not design particulars.
        assert not any("SPEED" in k for k in self.spec)

    def test_unknown_vessel_shell_returns_empty(self):
        assert parse_particulars_html("<html><body>Not found</body></html>") == {}


class TestVesselUrl:
    def test_slug_normalization(self):
        url = vessel_url(369550000, 8767123, "Q4000")
        assert url.endswith("/q4000-mmsi-369550000-imo-8767123")

    def test_empty_name_fallback(self):
        assert "/vessel-mmsi-1-imo-2" in vessel_url(1, 2, "!!!")
