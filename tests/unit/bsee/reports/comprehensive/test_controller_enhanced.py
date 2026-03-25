"""Tests for controller_enhanced report module."""

from datetime import date
from pathlib import Path

import pytest

from worldenergydata.bsee.reports.comprehensive.controller_enhanced import (
    Hierarchy,
    HierarchyNode,
    ReportConfiguration,
    ReportController,
    ReportParameters,
    ReportType,
)


class TestReportType:
    def test_values(self):
        assert ReportType.WELL.value == "well"
        assert ReportType.LEASE.value == "lease"
        assert ReportType.FIELD.value == "field"
        assert ReportType.BLOCK.value == "block"

    def test_from_string(self):
        assert ReportType.from_string("well") == ReportType.WELL
        assert ReportType.from_string("lease") == ReportType.LEASE
        assert ReportType.from_string("field") == ReportType.FIELD
        assert ReportType.from_string("block") == ReportType.BLOCK

    def test_from_string_case_insensitive(self):
        assert ReportType.from_string("WELL") == ReportType.WELL
        assert ReportType.from_string("Field") == ReportType.FIELD

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid report type"):
            ReportType.from_string("invalid")

    def test_get_hierarchy_level(self):
        assert ReportType.get_hierarchy_level(ReportType.WELL) == 1
        assert ReportType.get_hierarchy_level(ReportType.LEASE) == 2
        assert ReportType.get_hierarchy_level(ReportType.FIELD) == 3
        assert ReportType.get_hierarchy_level(ReportType.BLOCK) == 4


class TestReportParameters:
    def test_defaults(self):
        rp = ReportParameters()
        assert rp.discount_rate == 0.10
        assert rp.royalty_rate == 0.1875
        assert rp.operating_cost_per_bbl == 12.50
        assert rp.aggregation_level == "default"
        assert "oil" in rp.price_deck
        assert "gas" in rp.price_deck

    def test_custom(self):
        rp = ReportParameters(
            discount_rate=0.08,
            royalty_rate=0.25,
            operating_cost_per_bbl=15.0,
        )
        assert rp.discount_rate == 0.08
        assert rp.royalty_rate == 0.25
        assert rp.operating_cost_per_bbl == 15.0

    def test_invalid_discount_rate_too_high(self):
        with pytest.raises(ValueError, match="Invalid discount rate"):
            ReportParameters(discount_rate=1.5)

    def test_invalid_discount_rate_negative(self):
        with pytest.raises(ValueError, match="Invalid discount rate"):
            ReportParameters(discount_rate=-0.1)

    def test_invalid_royalty_rate_negative(self):
        with pytest.raises(ValueError, match="Invalid royalty rate"):
            ReportParameters(royalty_rate=-0.1)

    def test_boundary_discount_rates(self):
        # Should not raise
        ReportParameters(discount_rate=0.0)
        ReportParameters(discount_rate=1.0)


class TestReportConfiguration:
    def test_defaults(self):
        rc = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Test Field",
        )
        assert rc.report_type == ReportType.FIELD
        assert rc.entity_name == "Test Field"
        assert rc.output_formats == ["excel"]
        assert rc.include_economics is True
        assert rc.include_visualizations is True

    def test_custom_date_range(self):
        rc = ReportConfiguration(
            report_type=ReportType.WELL,
            entity_name="W001",
            date_range=(date(2023, 1, 1), date(2024, 12, 31)),
        )
        assert rc.date_range == (date(2023, 1, 1), date(2024, 12, 31))

    def test_invalid_date_range(self):
        with pytest.raises(ValueError, match="end date before start date"):
            ReportConfiguration(
                report_type=ReportType.FIELD,
                entity_name="Test",
                date_range=(date(2024, 12, 31), date(2023, 1, 1)),
            )

    def test_invalid_output_format(self):
        with pytest.raises(ValueError, match="Invalid output format"):
            ReportConfiguration(
                report_type=ReportType.FIELD,
                entity_name="Test",
                output_formats=["docx"],
            )

    def test_valid_output_formats(self):
        rc = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Test",
            output_formats=["excel", "pdf", "html", "json"],
        )
        assert len(rc.output_formats) == 4

    def test_from_dict_basic(self):
        rc = ReportConfiguration.from_dict({
            "report_type": "field",
            "entity_name": "Test Field",
        })
        assert rc.report_type == ReportType.FIELD
        assert rc.entity_name == "Test Field"

    def test_from_dict_with_dates(self):
        rc = ReportConfiguration.from_dict({
            "report_type": "well",
            "entity_name": "W001",
            "date_range": ["2023-01-01", "2024-12-31"],
        })
        assert rc.date_range[0] == date(2023, 1, 1)
        assert rc.date_range[1] == date(2024, 12, 31)

    def test_from_dict_defaults(self):
        rc = ReportConfiguration.from_dict({})
        assert rc.report_type == ReportType.FIELD
        assert rc.entity_name == ""


class TestHierarchyNode:
    def test_init(self):
        node = HierarchyNode("W1", "Well 1", "well")
        assert node.id == "W1"
        assert node.name == "Well 1"
        assert node.level == "well"
        assert node.parent is None
        assert node.children == []
        assert node.metrics == {}

    def test_add_child(self):
        parent = HierarchyNode("L1", "Lease 1", "lease")
        child = HierarchyNode("W1", "Well 1", "well")
        parent.add_child(child)
        assert child in parent.children
        assert child.parent == parent

    def test_set_get_metric(self):
        node = HierarchyNode("W1", "Well 1", "well")
        node.set_metric("oil_bbl", 1000)
        assert node.get_metric("oil_bbl") == 1000

    def test_get_metric_default(self):
        node = HierarchyNode("W1", "Well 1", "well")
        assert node.get_metric("missing") is None
        assert node.get_metric("missing", 0) == 0


class TestHierarchy:
    def _build_test_hierarchy(self):
        block = HierarchyNode("B1", "Block 1", "block")
        field = HierarchyNode("F1", "Field 1", "field")
        lease1 = HierarchyNode("L1", "Lease 1", "lease")
        lease2 = HierarchyNode("L2", "Lease 2", "lease")
        well1 = HierarchyNode("W1", "Well 1", "well")
        well2 = HierarchyNode("W2", "Well 2", "well")
        well3 = HierarchyNode("W3", "Well 3", "well")

        block.add_child(field)
        field.add_child(lease1)
        field.add_child(lease2)
        lease1.add_child(well1)
        lease1.add_child(well2)
        lease2.add_child(well3)

        return Hierarchy(block)

    def test_get_wells(self):
        h = self._build_test_hierarchy()
        wells = h.get_wells()
        assert len(wells) == 3

    def test_get_leases(self):
        h = self._build_test_hierarchy()
        leases = h.get_leases()
        assert len(leases) == 2

    def test_get_fields(self):
        h = self._build_test_hierarchy()
        fields = h.get_fields()
        assert len(fields) == 1

    def test_get_blocks(self):
        h = self._build_test_hierarchy()
        blocks = h.get_blocks()
        assert len(blocks) == 1

    def test_get_well_by_id(self):
        h = self._build_test_hierarchy()
        well = h.get_well_by_id("W1")
        assert well is not None
        assert well.name == "Well 1"

    def test_get_well_by_id_not_found(self):
        h = self._build_test_hierarchy()
        well = h.get_well_by_id("W999")
        assert well is None

    def test_get_parent(self):
        h = self._build_test_hierarchy()
        well = h.get_well_by_id("W1")
        parent = h.get_parent(well)
        assert parent is not None
        assert parent.id == "L1"

    def test_get_all_wells_in_block(self):
        h = self._build_test_hierarchy()
        wells = h.get_all_wells_in_block("B1")
        assert len(wells) == 3

    def test_get_all_wells_in_block_not_found(self):
        h = self._build_test_hierarchy()
        wells = h.get_all_wells_in_block("B999")
        assert wells == []

    def test_aggregate_to_lease(self):
        h = self._build_test_hierarchy()
        for well in h.get_wells():
            well.set_metric("oil", 100)
        total = h.aggregate_to_lease("oil")
        assert total == 300
        lease1 = [l for l in h.get_leases() if l.id == "L1"][0]
        assert lease1.get_metric("oil") == 200
        lease2 = [l for l in h.get_leases() if l.id == "L2"][0]
        assert lease2.get_metric("oil") == 100

    def test_aggregate_to_field(self):
        h = self._build_test_hierarchy()
        for lease in h.get_leases():
            lease.set_metric("oil", 500)
        total = h.aggregate_to_field("oil")
        assert total == 1000

    def test_aggregate_to_block(self):
        h = self._build_test_hierarchy()
        for field in h.get_fields():
            field.set_metric("oil", 2000)
        total = h.aggregate_to_block("oil")
        assert total == 2000


class TestReportController:
    def test_init_no_config(self):
        rc = ReportController()
        assert rc.config is not None
        assert rc.cache == {}

    def test_init_with_config_file(self, tmp_path):
        import json

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "data_source": {"type": "test"},
            "templates": {"path": "templates/"},
            "cache": {"enabled": False},
        }))
        rc = ReportController(config_file=config_file)
        assert rc.config["data_source"]["type"] == "test"

    def test_init_missing_config_file(self):
        rc = ReportController(config_file=Path("/nonexistent/config.json"))
        # Should fall back to defaults
        assert rc.config["data_source"]["type"] == "bsee"

    def test_validate_entity_raises(self):
        rc = ReportController()
        with pytest.raises(ValueError, match="Entity not found"):
            rc.validate_entity("Test", ReportType.WELL)

    def test_generate_cache_key(self):
        rc = ReportController()
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Test",
            date_range=(date(2023, 1, 1), date(2024, 12, 31)),
        )
        key = rc.generate_cache_key(config)
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest

    def test_cache_set_get(self):
        rc = ReportController()
        rc.cache_set("key1", {"data": 42})
        assert rc.cache_get("key1") == {"data": 42}

    def test_cache_get_miss(self):
        rc = ReportController()
        assert rc.cache_get("missing") is None

    def test_generate_metadata(self):
        rc = ReportController()
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Jack",
        )
        metadata = rc.generate_metadata(config)
        assert metadata["report_type"] == "field"
        assert metadata["entity_name"] == "Jack"
        assert metadata["version"] == "1.0.0"
        assert metadata["data_source"] == "BSEE"
        assert "generated_at" in metadata

    def test_batch_generate_not_implemented(self):
        rc = ReportController()
        with pytest.raises(NotImplementedError):
            rc.batch_generate([], ReportParameters())

    def test_create_test_hierarchy(self):
        rc = ReportController()
        h = rc.create_test_hierarchy()
        assert isinstance(h, Hierarchy)
        assert len(h.get_wells()) == 3
        assert len(h.get_leases()) == 2
        assert len(h.get_fields()) == 1
        assert len(h.get_blocks()) == 1

    def test_build_hierarchy(self):
        rc = ReportController()
        raw = {
            "blocks": [{"id": "B1", "area": "GC", "number": "640"}],
            "fields": [{"id": "F1", "name": "Tahiti", "block_id": "B1"}],
            "leases": [{"id": "L1", "number": "OCS-001", "field_id": "F1"}],
            "wells": [{"id": "W1", "name": "A1", "lease_id": "L1"}],
        }
        h = rc.build_hierarchy(raw)
        assert isinstance(h, Hierarchy)
        assert len(h.get_wells()) == 1
        assert len(h.get_blocks()) == 1

    def test_build_hierarchy_multiple(self):
        rc = ReportController()
        raw = {
            "blocks": [{"id": "B1", "area": "GC", "number": "640"}],
            "fields": [
                {"id": "F1", "name": "Tahiti", "block_id": "B1"},
                {"id": "F2", "name": "Caesar", "block_id": "B1"},
            ],
            "leases": [
                {"id": "L1", "number": "OCS-001", "field_id": "F1"},
                {"id": "L2", "number": "OCS-002", "field_id": "F2"},
            ],
            "wells": [
                {"id": "W1", "name": "A1", "lease_id": "L1"},
                {"id": "W2", "name": "A2", "lease_id": "L1"},
                {"id": "W3", "name": "B1", "lease_id": "L2"},
            ],
        }
        h = rc.build_hierarchy(raw)
        assert len(h.get_wells()) == 3
        assert len(h.get_leases()) == 2
        assert len(h.get_fields()) == 2

    def test_generate_report_error_handling(self):
        rc = ReportController()
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Test",
        )
        params = ReportParameters()
        result = rc.generate_report(config, params)
        # Should return error dict since data_loader etc. aren't set up
        assert result["status"] == "error"
        assert result["report_type"] == "field"
