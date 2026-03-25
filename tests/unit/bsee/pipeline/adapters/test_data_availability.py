"""Tests for data availability matrix."""

import pytest

from worldenergydata.bsee.pipeline.adapters.data_availability import (
    ANP_AVAILABILITY,
    AVAILABILITY_MATRIX,
    BSEE_AVAILABILITY,
    CNH_AVAILABILITY,
    RRC_AVAILABILITY,
    SODIR_AVAILABILITY,
    get_availability,
    summary_table,
)


class TestAvailabilityMatrix:
    def test_has_all_sources(self):
        assert "bsee" in AVAILABILITY_MATRIX
        assert "sodir" in AVAILABILITY_MATRIX
        assert "rrc" in AVAILABILITY_MATRIX
        assert "cnh" in AVAILABILITY_MATRIX
        assert "anp" in AVAILABILITY_MATRIX

    def test_count(self):
        assert len(AVAILABILITY_MATRIX) == 5


class TestBSEEAvailability:
    def test_source_id(self):
        assert BSEE_AVAILABILITY.source_id == "bsee"

    def test_wellbore_available(self):
        assert BSEE_AVAILABILITY.wellbore.status == "available"

    def test_production_available(self):
        assert BSEE_AVAILABILITY.production.status == "available"

    def test_casing_available(self):
        assert BSEE_AVAILABILITY.casing.status == "available"


class TestSODIRAvailability:
    def test_source_id(self):
        assert SODIR_AVAILABILITY.source_id == "sodir"

    def test_wellbore_available(self):
        assert SODIR_AVAILABILITY.wellbore.status == "available"

    def test_casing_unavailable(self):
        assert SODIR_AVAILABILITY.casing.status == "unavailable"

    def test_intervention_unavailable(self):
        assert SODIR_AVAILABILITY.intervention.status == "unavailable"


class TestRRCAvailability:
    def test_source_id(self):
        assert RRC_AVAILABILITY.source_id == "rrc"

    def test_production_available(self):
        assert RRC_AVAILABILITY.production.status == "available"

    def test_casing_unavailable(self):
        assert RRC_AVAILABILITY.casing.status == "unavailable"


class TestCNHAvailability:
    def test_source_id(self):
        assert CNH_AVAILABILITY.source_id == "cnh"

    def test_wellbore_unavailable(self):
        assert CNH_AVAILABILITY.wellbore.status == "unavailable"

    def test_production_partial(self):
        assert CNH_AVAILABILITY.production.status == "partial"


class TestANPAvailability:
    def test_source_id(self):
        assert ANP_AVAILABILITY.source_id == "anp"

    def test_all_unavailable(self):
        assert ANP_AVAILABILITY.wellbore.status == "unavailable"
        assert ANP_AVAILABILITY.production.status == "unavailable"
        assert ANP_AVAILABILITY.casing.status == "unavailable"


class TestGetAvailability:
    def test_known_source(self):
        avail = get_availability("bsee")
        assert avail.source_id == "bsee"

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError, match="Unknown source"):
            get_availability("unknown")


class TestSummaryTable:
    def test_returns_list(self):
        rows = summary_table()
        assert isinstance(rows, list)

    def test_row_count(self):
        rows = summary_table()
        # 5 sources * 6 domains = 30 rows
        assert len(rows) == 30

    def test_row_structure(self):
        rows = summary_table()
        row = rows[0]
        assert "source" in row
        assert "domain" in row
        assert "status" in row
        assert "notes" in row

    def test_all_statuses_valid(self):
        rows = summary_table()
        valid_statuses = {"available", "partial", "unavailable"}
        for row in rows:
            assert row["status"] in valid_statuses

    def test_all_domains_present(self):
        rows = summary_table()
        domains = {r["domain"] for r in rows}
        expected = {"wellbore", "well_path", "casing", "drilling_completion", "intervention", "production"}
        assert domains == expected
