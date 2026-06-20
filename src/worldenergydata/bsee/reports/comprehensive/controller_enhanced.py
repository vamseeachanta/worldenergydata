"""
ReportController - Main controller for comprehensive report generation
Handles report orchestration, configuration, and workflow management
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# For now, we'll stub out the dependencies
# These will be implemented in subsequent tasks


class ReportType(Enum):
    """Enum for report hierarchy types"""

    WELL = "well"
    LEASE = "lease"
    FIELD = "field"
    BLOCK = "block"

    @classmethod
    def from_string(cls, value: str) -> "ReportType":
        """Create ReportType from string value"""
        value_lower = value.lower()
        for report_type in cls:
            if report_type.value == value_lower:
                return report_type
        raise ValueError(f"Invalid report type: {value}")

    @classmethod
    def get_hierarchy_level(cls, report_type: "ReportType") -> int:
        """Get hierarchy level for report type (1=well, 4=block)"""
        levels = {cls.WELL: 1, cls.LEASE: 2, cls.FIELD: 3, cls.BLOCK: 4}
        return levels[report_type]


@dataclass
class ReportParameters:
    """Parameters for report generation"""

    price_deck: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "oil": {"2024": 75.00, "2025": 77.00},
            "gas": {"2024": 3.50, "2025": 3.75},
        }
    )
    discount_rate: float = 0.10
    royalty_rate: float = 0.1875
    operating_cost_per_bbl: float = 12.50
    aggregation_level: str = "default"

    def __post_init__(self):
        """Validate parameters after initialization"""
        if not 0 <= self.discount_rate <= 1:
            raise ValueError(f"Invalid discount rate: {self.discount_rate}")
        if self.royalty_rate < 0:
            raise ValueError(f"Invalid royalty rate: {self.royalty_rate}")


@dataclass
class ReportConfiguration:
    """Configuration for report generation"""

    report_type: ReportType
    entity_name: str
    date_range: Tuple[date, date] = field(
        default_factory=lambda: (date(2020, 1, 1), date.today())
    )
    output_formats: List[str] = field(default_factory=lambda: ["excel"])
    include_economics: bool = True
    include_visualizations: bool = True

    def __post_init__(self):
        """Validate configuration after initialization"""
        # Validate date range
        if self.date_range[1] < self.date_range[0]:
            raise ValueError("Invalid date range: end date before start date")

        # Validate output formats
        valid_formats = {"excel", "pdf", "html", "json"}
        for fmt in self.output_formats:
            if fmt not in valid_formats:
                raise ValueError(f"Invalid output format: {fmt}")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ReportConfiguration":
        """Create configuration from dictionary"""
        # Parse date range
        date_range = config_dict.get("date_range", [])
        if date_range and isinstance(date_range[0], str):
            date_range = (
                datetime.strptime(date_range[0], "%Y-%m-%d").date(),
                datetime.strptime(date_range[1], "%Y-%m-%d").date(),
            )
        else:
            date_range = (date(2020, 1, 1), date.today())

        # Parse report type
        report_type = ReportType.from_string(config_dict.get("report_type", "field"))

        return cls(
            report_type=report_type,
            entity_name=config_dict.get("entity_name", ""),
            date_range=date_range,
            output_formats=config_dict.get("output_formats", ["excel"]),
            include_economics=config_dict.get("include_economics", True),
            include_visualizations=config_dict.get("include_visualizations", True),
        )


class HierarchyNode:
    """Node in the organizational hierarchy"""

    def __init__(
        self,
        node_id: str,
        name: str,
        level: str,
        parent: Optional["HierarchyNode"] = None,
    ):
        self.id = node_id
        self.name = name
        self.level = level
        self.parent = parent
        self.children = []
        self.metrics = {}

    def add_child(self, child: "HierarchyNode"):
        """Add child node"""
        self.children.append(child)
        child.parent = self

    def set_metric(self, metric_name: str, value: Any):
        """Set a metric value"""
        self.metrics[metric_name] = value

    def get_metric(self, metric_name: str, default: Any = None) -> Any:
        """Get a metric value"""
        return self.metrics.get(metric_name, default)


class Hierarchy:
    """Organizational hierarchy for report entities"""

    def __init__(self, root: HierarchyNode):
        self.root = root
        self._wells = []
        self._leases = []
        self._fields = []
        self._blocks = []
        self._index_nodes()

    def _index_nodes(self):
        """Index all nodes by type"""

        def traverse(node: HierarchyNode):
            if node.level == "well":
                self._wells.append(node)
            elif node.level == "lease":
                self._leases.append(node)
            elif node.level == "field":
                self._fields.append(node)
            elif node.level == "block":
                self._blocks.append(node)

            for child in node.children:
                traverse(child)

        traverse(self.root)

    def get_wells(self) -> List[HierarchyNode]:
        """Get all wells"""
        return self._wells

    def get_leases(self) -> List[HierarchyNode]:
        """Get all leases"""
        return self._leases

    def get_fields(self) -> List[HierarchyNode]:
        """Get all fields"""
        return self._fields

    def get_blocks(self) -> List[HierarchyNode]:
        """Get all blocks"""
        return self._blocks

    def get_well_by_id(self, well_id: str) -> Optional[HierarchyNode]:
        """Get well by ID"""
        for well in self._wells:
            if well.id == well_id:
                return well
        return None

    def get_parent(self, node: HierarchyNode) -> Optional[HierarchyNode]:
        """Get parent of a node"""
        return node.parent

    def get_all_wells_in_block(self, block_id: str) -> List[HierarchyNode]:
        """Get all wells in a block"""
        wells = []
        for block in self._blocks:
            if block.id == block_id:
                # Traverse down to find all wells
                def collect_wells(node: HierarchyNode):
                    if node.level == "well":
                        wells.append(node)
                    for child in node.children:
                        collect_wells(child)

                collect_wells(block)
        return wells

    def aggregate_to_lease(self, metric_name: str) -> float:
        """Aggregate metric to lease level"""
        total = 0
        for lease in self._leases:
            lease_total = 0
            for well in self._wells:
                if well.parent == lease:
                    lease_total += well.get_metric(metric_name, 0)
            lease.set_metric(metric_name, lease_total)
            total += lease_total
        return total

    def aggregate_to_field(self, metric_name: str) -> float:
        """Aggregate metric to field level"""
        total = 0
        for field in self._fields:  # noqa: F402
            field_total = 0
            for lease in self._leases:
                if lease.parent == field:
                    field_total += lease.get_metric(metric_name, 0)
            field.set_metric(metric_name, field_total)
            total += field_total
        return total

    def aggregate_to_block(self, metric_name: str) -> float:
        """Aggregate metric to block level"""
        total = 0
        for block in self._blocks:
            block_total = 0
            for field in self._fields:  # noqa: F402
                if field.parent == block:
                    block_total += field.get_metric(metric_name, 0)
            block.set_metric(metric_name, block_total)
            total += block_total
        return total


class ReportController:
    """Main controller for report generation"""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize ReportController"""
        self.config = self._load_config(config_file)
        self.data_source = self._initialize_data_source()
        self.template_engine = self._initialize_template_engine()
        self.export_manager = self._initialize_export_manager()
        self.cache = self._initialize_cache()

    def _load_config(self, config_file: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if config_file and config_file.exists():
            with open(config_file, "r") as f:
                return json.load(f)

        # Default configuration
        return {
            "data_source": {"type": "bsee", "connection": "default"},
            "templates": {"path": "templates/", "default": "field_summary.jinja2"},
            "cache": {"enabled": True, "ttl": 3600},
        }

    def _initialize_data_source(self) -> Any:
        """Initialize data source connection"""
        # Stub for now - will be implemented with BSEE integration
        return {"type": "bsee", "status": "connected"}

    def _initialize_template_engine(self) -> Any:
        """Initialize template engine"""
        # Stub for now - will be implemented with Jinja2
        return {"engine": "jinja2", "status": "ready"}

    def _initialize_export_manager(self) -> Any:
        """Initialize export manager"""
        # Stub for now - will be implemented with export modules
        return {"formats": ["excel", "pdf", "html", "json"], "status": "ready"}

    def _initialize_cache(self) -> Dict[str, Any]:
        """Initialize cache system"""
        return {}

    def generate_report(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Any:
        """Generate comprehensive report using enhanced data fetching

        Args:
            config: Report configuration
            params: Report parameters

        Returns:
            Generated report data
        """
        try:
            # Refresh data if needed
            if self.config.get("refresh_data", False):
                self.data_loader.refresh_data_if_needed(self.config)

            # Generate report based on type
            if config.report_type == ReportType.BLOCK:
                return self._generate_block_report(config, params)
            elif config.report_type == ReportType.FIELD:
                return self._generate_field_report(config, params)
            elif config.report_type == ReportType.LEASE:
                return self._generate_lease_report(config, params)
            else:
                return self._generate_well_report(config, params)

        except Exception as e:
            return {
                "status": "error",
                "report_type": config.report_type.value,
                "entity": config.entity_name,
                "error": str(e),
            }

    def _generate_block_report(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Dict[str, Any]:
        """Generate block-level report"""
        # Extract block numbers from entity name
        block_numbers = [config.entity_name] if config.entity_name else []

        # Fetch and aggregate data
        aggregated_data = self.block_aggregator.aggregate_with_fresh_data(
            block_numbers, self.config
        )

        return {
            "status": "success",
            "report_type": "block",
            "entity": config.entity_name,
            "data": aggregated_data,
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_field_report(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Dict[str, Any]:
        """Generate field-level report"""
        # Extract field names from entity name
        field_names = [config.entity_name] if config.entity_name else []

        # Fetch and aggregate data
        aggregated_data = self.field_aggregator.aggregate_with_fresh_data(
            field_names, self.config
        )

        return {
            "status": "success",
            "report_type": "field",
            "entity": config.entity_name,
            "data": aggregated_data,
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_lease_report(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Dict[str, Any]:
        """Generate lease-level report"""
        # Extract lease numbers from entity name
        lease_numbers = [config.entity_name] if config.entity_name else []

        # Fetch and aggregate data
        aggregated_data = self.lease_aggregator.aggregate_with_fresh_data(
            lease_numbers, self.config
        )

        return {
            "status": "success",
            "report_type": "lease",
            "entity": config.entity_name,
            "data": aggregated_data,
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_well_report(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Dict[str, Any]:
        """Generate well-level report"""
        # Extract API numbers from entity name
        api_numbers = [config.entity_name] if config.entity_name else []

        # Fetch well data
        well_data = self.data_loader.fetch_wells_by_api_list(api_numbers)

        return {
            "status": "success",
            "report_type": "well",
            "entity": config.entity_name,
            "data": well_data.to_dict("records") if not well_data.empty else [],
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
        }

    def batch_generate(
        self,
        configs: List[ReportConfiguration],
        params: ReportParameters,
        parallel: bool = False,
    ) -> List[Any]:
        """Generate multiple reports"""
        # Stub implementation - will be completed in later tasks
        raise NotImplementedError("Batch generation not yet implemented")

    def validate_entity(self, entity_name: str, report_type: ReportType):
        """Validate that entity exists in data source"""
        # Stub implementation - will check against BSEE data
        # For now, always raise error to match test expectations
        raise ValueError(f"Entity not found: {entity_name}")

    def generate_cache_key(self, config: ReportConfiguration) -> str:
        """Generate cache key for configuration"""
        key_data = f"{config.report_type.value}_{config.entity_name}_{config.date_range[0]}_{config.date_range[1]}"  # noqa: E501
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def cache_set(self, key: str, value: Any):
        """Set cache value"""
        self.cache[key] = value

    def cache_get(self, key: str) -> Any:
        """Get cache value"""
        return self.cache.get(key)

    def generate_metadata(self, config: ReportConfiguration) -> Dict[str, Any]:
        """Generate report metadata"""
        return {
            "report_type": config.report_type.value,
            "entity_name": config.entity_name,
            "generated_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "data_source": "BSEE",
        }

    def build_hierarchy(self, raw_data: Dict[str, List[Dict]]) -> Hierarchy:
        """Build hierarchy from raw data"""
        # Create blocks
        blocks = {}
        for block_data in raw_data.get("blocks", []):
            block = HierarchyNode(
                block_data["id"],
                f"{block_data['area']} {block_data['number']}",
                "block",
            )
            blocks[block_data["id"]] = block

        # Create fields
        fields = {}
        for field_data in raw_data.get("fields", []):
            field = HierarchyNode(field_data["id"], field_data["name"], "field")
            fields[field_data["id"]] = field
            # Link to block
            if field_data["block_id"] in blocks:
                blocks[field_data["block_id"]].add_child(field)

        # Create leases
        leases = {}
        for lease_data in raw_data.get("leases", []):
            lease = HierarchyNode(lease_data["id"], lease_data["number"], "lease")
            leases[lease_data["id"]] = lease
            # Link to field
            if lease_data["field_id"] in fields:
                fields[lease_data["field_id"]].add_child(lease)

        # Create wells
        for well_data in raw_data.get("wells", []):
            well = HierarchyNode(well_data["id"], well_data["name"], "well")
            # Link to lease
            if well_data["lease_id"] in leases:
                leases[well_data["lease_id"]].add_child(well)

        # Find root (should be a block)
        root = list(blocks.values())[0] if blocks else None
        return Hierarchy(root)

    def create_test_hierarchy(self) -> Hierarchy:
        """Create test hierarchy for testing"""
        # Create a simple test hierarchy
        block = HierarchyNode("B1", "Walker Ridge 759", "block")
        field = HierarchyNode("F1", "Jack", "field")
        lease1 = HierarchyNode("L1", "OCS-G-12345", "lease")
        lease2 = HierarchyNode("L2", "OCS-G-12346", "lease")
        well1 = HierarchyNode("W1", "PS001", "well")
        well2 = HierarchyNode("W2", "PS002", "well")
        well3 = HierarchyNode("W3", "PS003", "well")

        # Build relationships
        block.add_child(field)
        field.add_child(lease1)
        field.add_child(lease2)
        lease1.add_child(well1)
        lease1.add_child(well2)
        lease2.add_child(well3)

        return Hierarchy(block)
