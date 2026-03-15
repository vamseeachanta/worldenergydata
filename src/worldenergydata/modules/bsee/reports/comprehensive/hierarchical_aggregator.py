"""
Hierarchical aggregation classes for comprehensive report generation
Aggregates data from well → lease → field → block levels
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .data_loader_enhanced import HierarchicalDataLoader
from .models import (
    Block,
    EconomicMetrics,
    Field,
    Lease,
    ProductionMetrics,
    Well,
    WellSummary,
)

logger = logging.getLogger(__name__)


@dataclass
class PriceDeck:
    """Price deck for revenue calculations"""

    oil_price: float = 75.00  # $/bbl
    gas_price: float = 3.50  # $/mcf
    ngl_price: float = 30.00  # $/bbl

    def get_oil_revenue(self, volume_bbls: float) -> float:
        """Calculate oil revenue"""
        return volume_bbls * self.oil_price

    def get_gas_revenue(self, volume_mcf: float) -> float:
        """Calculate gas revenue"""
        return volume_mcf * self.gas_price

    def get_ngl_revenue(self, volume_bbls: float) -> float:
        """Calculate NGL revenue"""
        return volume_bbls * self.ngl_price


@dataclass
class CostStructure:
    """Cost structure for economic calculations"""

    operating_cost_per_bbl: float = 12.50
    royalty_rate: float = 0.1875  # 18.75%
    severance_tax_rate: float = 0.05  # 5%

    def get_operating_cost(self, oil_bbls: float, gas_mcf: float) -> float:
        """Calculate operating costs"""
        # Convert gas to BOE (6 mcf = 1 BOE)
        boe = oil_bbls + (gas_mcf / 6)
        return boe * self.operating_cost_per_bbl

    def get_royalties(self, gross_revenue: float) -> float:
        """Calculate royalties"""
        return gross_revenue * self.royalty_rate

    def get_severance_tax(self, gross_revenue: float) -> float:
        """Calculate severance tax"""
        return gross_revenue * self.severance_tax_rate


class BaseAggregator:
    """Base class for hierarchical aggregators"""

    def __init__(
        self,
        price_deck: Optional[PriceDeck] = None,
        cost_structure: Optional[CostStructure] = None,
    ):
        """
        Initialize aggregator

        Args:
            price_deck: Price deck for revenue calculations
            cost_structure: Cost structure for economic calculations
        """
        self.price_deck = price_deck or PriceDeck()
        self.cost_structure = cost_structure or CostStructure()
        self.data_loader = HierarchicalDataLoader()

    def aggregate(self, entity: Any) -> Dict[str, Any]:
        """
        Aggregate data for an entity

        Args:
            entity: Entity to aggregate (Well, Lease, Field, or Block)

        Returns:
            Aggregated metrics dictionary
        """
        raise NotImplementedError("Must implement aggregate method")

    def calculate_revenue(self, production: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate revenue from production volumes

        Args:
            production: Production volumes (oil_bbls, gas_mcf, ngl_bbls)

        Returns:
            Revenue breakdown dictionary
        """
        oil_revenue = self.price_deck.get_oil_revenue(production.get("oil_bbls", 0))
        gas_revenue = self.price_deck.get_gas_revenue(production.get("gas_mcf", 0))
        ngl_revenue = self.price_deck.get_ngl_revenue(production.get("ngl_bbls", 0))

        gross_revenue = oil_revenue + gas_revenue + ngl_revenue

        return {
            "oil_revenue": oil_revenue,
            "gas_revenue": gas_revenue,
            "ngl_revenue": ngl_revenue,
            "gross_revenue": gross_revenue,
        }

    def calculate_costs(
        self, production: Dict[str, float], revenue: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate costs and net income

        Args:
            production: Production volumes
            revenue: Revenue breakdown

        Returns:
            Cost breakdown dictionary
        """
        operating_cost = self.cost_structure.get_operating_cost(
            production.get("oil_bbls", 0), production.get("gas_mcf", 0)
        )
        royalties = self.cost_structure.get_royalties(revenue.get("gross_revenue", 0))
        severance_tax = self.cost_structure.get_severance_tax(
            revenue.get("gross_revenue", 0)
        )

        total_costs = operating_cost + royalties + severance_tax
        net_income = revenue.get("gross_revenue", 0) - total_costs

        return {
            "operating_cost": operating_cost,
            "royalties": royalties,
            "severance_tax": severance_tax,
            "total_costs": total_costs,
            "net_income": net_income,
        }


class WellAggregator(BaseAggregator):
    """Aggregator for individual well data"""

    def aggregate(self, well: Well) -> Dict[str, Any]:
        """
        Extract and calculate metrics for a single well

        Args:
            well: Well entity

        Returns:
            Well metrics dictionary
        """
        logger.debug(f"Aggregating well {well.id}")

        # Get production data from well
        production = well.get_production_data()

        # Calculate revenue
        revenue = self.calculate_revenue(production)

        # Calculate costs
        costs = self.calculate_costs(production, revenue)

        # Build metrics dictionary
        metrics = {
            "well_id": well.id,
            "well_name": well.name,
            "api_number": well.api_number,
            "status": well.status,
            "water_depth_ft": well.water_depth_ft,
            "total_depth_ft": well.total_depth_ft,
            "spud_date": well.spud_date,
            # Production metrics
            "oil_production_bbls": production.get("oil_bbls", 0),
            "gas_production_mcf": production.get("gas_mcf", 0),
            "water_production_bbls": production.get("water_bbls", 0),
            "ngl_production_bbls": production.get("ngl_bbls", 0),
            "production_days": production.get("days_on", 0),
            # Economic metrics
            "oil_revenue": revenue["oil_revenue"],
            "gas_revenue": revenue["gas_revenue"],
            "ngl_revenue": revenue["ngl_revenue"],
            "gross_revenue": revenue["gross_revenue"],
            "operating_cost": costs["operating_cost"],
            "royalties": costs["royalties"],
            "severance_tax": costs["severance_tax"],
            "total_costs": costs["total_costs"],
            "net_income": costs["net_income"],
        }

        # Calculate per-day metrics if production days available
        if production.get("days_on", 0) > 0:
            days = production["days_on"]
            metrics["oil_rate_bopd"] = metrics["oil_production_bbls"] / days
            metrics["gas_rate_mcfd"] = metrics["gas_production_mcf"] / days
            metrics["water_rate_bwpd"] = metrics["water_production_bbls"] / days

        return metrics


class LeaseAggregator(BaseAggregator):
    """Aggregator for lease-level data"""

    def __init__(self, well_aggregator: Optional[WellAggregator] = None, **kwargs):
        """
        Initialize lease aggregator

        Args:
            well_aggregator: Well aggregator to use
            **kwargs: Additional arguments for base class
        """
        super().__init__(**kwargs)
        self.well_aggregator = well_aggregator or WellAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

    def aggregate(self, lease: Lease) -> Dict[str, Any]:
        """
        Aggregate all wells in a lease

        Args:
            lease: Lease entity

        Returns:
            Lease metrics dictionary
        """
        logger.info(f"Aggregating lease {lease.id}")

        # Aggregate all wells in the lease
        well_metrics = []
        for well in lease.children:
            well_data = self.well_aggregator.aggregate(well)
            well_metrics.append(well_data)

        # Sum production volumes
        total_oil = sum(w["oil_production_bbls"] for w in well_metrics)
        total_gas = sum(w["gas_production_mcf"] for w in well_metrics)
        total_water = sum(w["water_production_bbls"] for w in well_metrics)
        total_ngl = sum(w.get("ngl_production_bbls", 0) for w in well_metrics)

        # Sum economic metrics
        total_gross_revenue = sum(w["gross_revenue"] for w in well_metrics)
        total_operating_cost = sum(w["operating_cost"] for w in well_metrics)
        total_royalties = sum(w["royalties"] for w in well_metrics)
        total_severance_tax = sum(w["severance_tax"] for w in well_metrics)
        total_costs = sum(w["total_costs"] for w in well_metrics)
        total_net_income = sum(w["net_income"] for w in well_metrics)

        # Well counts by status
        active_wells = sum(1 for w in well_metrics if w["status"] == "active")
        total_wells = len(well_metrics)

        # Build lease metrics
        metrics = {
            "lease_id": lease.id,
            "lease_number": lease.number,
            "field_id": lease.field_id,
            # Well counts
            "total_wells": total_wells,
            "active_wells": active_wells,
            "inactive_wells": total_wells - active_wells,
            # Production totals
            "oil_production_bbls": total_oil,
            "gas_production_mcf": total_gas,
            "water_production_bbls": total_water,
            "ngl_production_bbls": total_ngl,
            # Economic totals
            "gross_revenue": total_gross_revenue,
            "operating_cost": total_operating_cost,
            "royalties": total_royalties,
            "severance_tax": total_severance_tax,
            "total_costs": total_costs,
            "net_income": total_net_income,
            # Well details
            "wells": well_metrics,
        }

        # Calculate averages per well
        if total_wells > 0:
            metrics["avg_oil_per_well"] = total_oil / total_wells
            metrics["avg_gas_per_well"] = total_gas / total_wells
            metrics["avg_revenue_per_well"] = total_gross_revenue / total_wells

        return metrics


class FieldAggregator(BaseAggregator):
    """Aggregator for field-level data"""

    def __init__(self, lease_aggregator: Optional[LeaseAggregator] = None, **kwargs):
        """
        Initialize field aggregator

        Args:
            lease_aggregator: Lease aggregator to use
            **kwargs: Additional arguments for base class
        """
        super().__init__(**kwargs)
        self.lease_aggregator = lease_aggregator or LeaseAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

    def aggregate(self, field: Field) -> Dict[str, Any]:
        """
        Aggregate all leases in a field

        Args:
            field: Field entity

        Returns:
            Field metrics dictionary
        """
        logger.info(f"Aggregating field {field.id}")

        # Aggregate all leases in the field
        lease_metrics = []
        for lease in field.children:
            lease_data = self.lease_aggregator.aggregate(lease)
            lease_metrics.append(lease_data)

        # Sum production volumes
        total_oil = sum(l["oil_production_bbls"] for l in lease_metrics)
        total_gas = sum(l["gas_production_mcf"] for l in lease_metrics)
        total_water = sum(l["water_production_bbls"] for l in lease_metrics)
        total_ngl = sum(l.get("ngl_production_bbls", 0) for l in lease_metrics)

        # Sum economic metrics
        total_gross_revenue = sum(l["gross_revenue"] for l in lease_metrics)
        total_operating_cost = sum(l["operating_cost"] for l in lease_metrics)
        total_royalties = sum(l["royalties"] for l in lease_metrics)
        total_severance_tax = sum(l["severance_tax"] for l in lease_metrics)
        total_costs = sum(l["total_costs"] for l in lease_metrics)
        total_net_income = sum(l["net_income"] for l in lease_metrics)

        # Aggregate well counts
        total_wells = sum(l["total_wells"] for l in lease_metrics)
        active_wells = sum(l["active_wells"] for l in lease_metrics)
        total_leases = len(lease_metrics)

        # Build field metrics
        metrics = {
            "field_id": field.id,
            "field_name": field.name,
            "block_id": field.block_id,
            # Lease and well counts
            "total_leases": total_leases,
            "total_wells": total_wells,
            "active_wells": active_wells,
            "inactive_wells": total_wells - active_wells,
            # Production totals
            "oil_production_bbls": total_oil,
            "gas_production_mcf": total_gas,
            "water_production_bbls": total_water,
            "ngl_production_bbls": total_ngl,
            # Economic totals
            "gross_revenue": total_gross_revenue,
            "operating_cost": total_operating_cost,
            "royalties": total_royalties,
            "severance_tax": total_severance_tax,
            "total_costs": total_costs,
            "net_income": total_net_income,
            # Lease details
            "leases": lease_metrics,
        }

        # Calculate field-level metrics
        if total_wells > 0:
            metrics["avg_oil_per_well"] = total_oil / total_wells
            metrics["avg_gas_per_well"] = total_gas / total_wells

        if total_leases > 0:
            metrics["avg_wells_per_lease"] = total_wells / total_leases
            metrics["avg_revenue_per_lease"] = total_gross_revenue / total_leases

        # Calculate BOE (Barrel of Oil Equivalent)
        boe = total_oil + (total_gas / 6) + total_ngl
        metrics["total_boe"] = boe

        return metrics


class BlockAggregator(BaseAggregator):
    """Aggregator for block-level data"""

    def __init__(self, field_aggregator: Optional[FieldAggregator] = None, **kwargs):
        """
        Initialize block aggregator

        Args:
            field_aggregator: Field aggregator to use
            **kwargs: Additional arguments for base class
        """
        super().__init__(**kwargs)
        self.field_aggregator = field_aggregator or FieldAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

    def aggregate(self, block: Block) -> Dict[str, Any]:
        """
        Aggregate all fields in a block

        Args:
            block: Block entity

        Returns:
            Block metrics dictionary
        """
        logger.info(f"Aggregating block {block.id}")

        # Aggregate all fields in the block
        field_metrics = []
        for field in block.children:
            field_data = self.field_aggregator.aggregate(field)
            field_metrics.append(field_data)

        # Sum production volumes
        total_oil = sum(f["oil_production_bbls"] for f in field_metrics)
        total_gas = sum(f["gas_production_mcf"] for f in field_metrics)
        total_water = sum(f["water_production_bbls"] for f in field_metrics)
        total_ngl = sum(f.get("ngl_production_bbls", 0) for f in field_metrics)

        # Sum economic metrics
        total_gross_revenue = sum(f["gross_revenue"] for f in field_metrics)
        total_operating_cost = sum(f["operating_cost"] for f in field_metrics)
        total_royalties = sum(f["royalties"] for f in field_metrics)
        total_severance_tax = sum(f["severance_tax"] for f in field_metrics)
        total_costs = sum(f["total_costs"] for f in field_metrics)
        total_net_income = sum(f["net_income"] for f in field_metrics)

        # Aggregate counts
        total_fields = len(field_metrics)
        total_leases = sum(f["total_leases"] for f in field_metrics)
        total_wells = sum(f["total_wells"] for f in field_metrics)
        active_wells = sum(f["active_wells"] for f in field_metrics)

        # Build block metrics
        metrics = {
            "block_id": block.id,
            "block_number": block.number,
            "area": block.area,
            # Hierarchical counts
            "total_fields": total_fields,
            "total_leases": total_leases,
            "total_wells": total_wells,
            "active_wells": active_wells,
            "inactive_wells": total_wells - active_wells,
            # Production totals
            "oil_production_bbls": total_oil,
            "gas_production_mcf": total_gas,
            "water_production_bbls": total_water,
            "ngl_production_bbls": total_ngl,
            # Economic totals
            "gross_revenue": total_gross_revenue,
            "operating_cost": total_operating_cost,
            "royalties": total_royalties,
            "severance_tax": total_severance_tax,
            "total_costs": total_costs,
            "net_income": total_net_income,
            # Field details
            "fields": field_metrics,
        }

        # Calculate block-level metrics
        if total_fields > 0:
            metrics["avg_leases_per_field"] = total_leases / total_fields
            metrics["avg_wells_per_field"] = total_wells / total_fields
            metrics["avg_revenue_per_field"] = total_gross_revenue / total_fields

        if total_wells > 0:
            metrics["avg_oil_per_well"] = total_oil / total_wells
            metrics["avg_gas_per_well"] = total_gas / total_wells
            metrics["avg_revenue_per_well"] = total_gross_revenue / total_wells

        # Calculate BOE
        boe = total_oil + (total_gas / 6) + total_ngl
        metrics["total_boe"] = boe

        # Identify top performers
        if field_metrics:
            top_oil_field = max(field_metrics, key=lambda f: f["oil_production_bbls"])
            top_gas_field = max(field_metrics, key=lambda f: f["gas_production_mcf"])
            top_revenue_field = max(field_metrics, key=lambda f: f["gross_revenue"])

            metrics["top_oil_field"] = top_oil_field["field_name"]
            metrics["top_gas_field"] = top_gas_field["field_name"]
            metrics["top_revenue_field"] = top_revenue_field["field_name"]

        return metrics


class HierarchicalAggregator:
    """Main aggregator for hierarchical report generation"""

    def __init__(
        self,
        price_deck: Optional[PriceDeck] = None,
        cost_structure: Optional[CostStructure] = None,
    ):
        """
        Initialize hierarchical aggregator

        Args:
            price_deck: Price deck for revenue calculations
            cost_structure: Cost structure for economic calculations
        """
        self.price_deck = price_deck or PriceDeck()
        self.cost_structure = cost_structure or CostStructure()

        # Initialize aggregators for each level
        self.well_aggregator = WellAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )
        self.lease_aggregator = LeaseAggregator(
            well_aggregator=self.well_aggregator,
            price_deck=self.price_deck,
            cost_structure=self.cost_structure,
        )
        self.field_aggregator = FieldAggregator(
            lease_aggregator=self.lease_aggregator,
            price_deck=self.price_deck,
            cost_structure=self.cost_structure,
        )
        self.block_aggregator = BlockAggregator(
            field_aggregator=self.field_aggregator,
            price_deck=self.price_deck,
            cost_structure=self.cost_structure,
        )

        # Data loader for fetching hierarchy
        self.data_loader = HierarchicalDataLoader()

    def aggregate_hierarchy(
        self, hierarchy: Dict[str, Any], level: str = "block"
    ) -> Dict[str, Any]:
        """
        Aggregate data at specified hierarchical level

        Args:
            hierarchy: Hierarchical data structure from data loader
            level: Target aggregation level ('well', 'lease', 'field', 'block')

        Returns:
            Aggregated metrics at specified level
        """
        logger.info(f"Aggregating hierarchy at {level} level")

        aggregated_data = {}

        if level == "block":
            # Aggregate all blocks
            for block_id, block in hierarchy.get("blocks", {}).items():
                aggregated_data[block_id] = self.block_aggregator.aggregate(block)

        elif level == "field":
            # Aggregate all fields
            for field_id, field in hierarchy.get("fields", {}).items():
                aggregated_data[field_id] = self.field_aggregator.aggregate(field)

        elif level == "lease":
            # Aggregate all leases
            for lease_id, lease in hierarchy.get("leases", {}).items():
                aggregated_data[lease_id] = self.lease_aggregator.aggregate(lease)

        elif level == "well":
            # Extract well metrics
            for well_id, well in hierarchy.get("wells", {}).items():
                aggregated_data[well_id] = self.well_aggregator.aggregate(well)
        else:
            raise ValueError(f"Invalid aggregation level: {level}")

        return aggregated_data

    def generate_report_data(
        self,
        block_number: Optional[str] = None,
        field_name: Optional[str] = None,
        lease_number: Optional[str] = None,
        cfg: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete report data with hierarchical aggregation

        Args:
            block_number: Optional block filter
            field_name: Optional field filter
            lease_number: Optional lease filter
            cfg: Configuration dictionary

        Returns:
            Complete report data with all aggregations
        """
        logger.info("Generating hierarchical report data")

        # Load hierarchy using existing data loader
        hierarchy = self.data_loader.load_hierarchy(
            block_number=block_number,
            field_name=field_name,
            lease_number=lease_number,
            cfg=cfg,
        )

        # Determine aggregation level based on filters
        if lease_number:
            level = "lease"
        elif field_name:
            level = "field"
        elif block_number:
            level = "block"
        else:
            level = "block"  # Default to block level

        # Aggregate at appropriate level
        aggregated_data = self.aggregate_hierarchy(hierarchy, level)

        # Build report data structure
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "aggregation_level": level,
                "filters": {
                    "block_number": block_number,
                    "field_name": field_name,
                    "lease_number": lease_number,
                },
                "price_deck": {
                    "oil_price": self.price_deck.oil_price,
                    "gas_price": self.price_deck.gas_price,
                    "ngl_price": self.price_deck.ngl_price,
                },
                "cost_structure": {
                    "operating_cost_per_bbl": self.cost_structure.operating_cost_per_bbl,
                    "royalty_rate": self.cost_structure.royalty_rate,
                    "severance_tax_rate": self.cost_structure.severance_tax_rate,
                },
            },
            "data": aggregated_data,
            "summary": self._generate_summary(aggregated_data),
        }

        return report_data

    def _generate_summary(self, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics from aggregated data

        Args:
            aggregated_data: Aggregated metrics

        Returns:
            Summary statistics
        """
        if not aggregated_data:
            return {}

        # Collect all metrics
        all_metrics = list(aggregated_data.values())

        # Calculate totals
        total_oil = sum(m.get("oil_production_bbls", 0) for m in all_metrics)
        total_gas = sum(m.get("gas_production_mcf", 0) for m in all_metrics)
        total_water = sum(m.get("water_production_bbls", 0) for m in all_metrics)
        total_revenue = sum(m.get("gross_revenue", 0) for m in all_metrics)
        total_costs = sum(m.get("total_costs", 0) for m in all_metrics)
        total_net_income = sum(m.get("net_income", 0) for m in all_metrics)

        # Count entities
        entity_count = len(all_metrics)

        # Build summary
        summary = {
            "entity_count": entity_count,
            "total_oil_bbls": total_oil,
            "total_gas_mcf": total_gas,
            "total_water_bbls": total_water,
            "total_boe": total_oil + (total_gas / 6),
            "total_gross_revenue": total_revenue,
            "total_costs": total_costs,
            "total_net_income": total_net_income,
            "profit_margin": (
                (total_net_income / total_revenue * 100) if total_revenue > 0 else 0
            ),
        }

        # Add averages if entities exist
        if entity_count > 0:
            summary["avg_oil_per_entity"] = total_oil / entity_count
            summary["avg_gas_per_entity"] = total_gas / entity_count
            summary["avg_revenue_per_entity"] = total_revenue / entity_count
            summary["avg_net_income_per_entity"] = total_net_income / entity_count

        return summary
