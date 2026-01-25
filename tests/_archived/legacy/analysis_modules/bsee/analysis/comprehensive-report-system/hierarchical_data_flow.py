"""
Design hierarchical data flow for comprehensive reporting system
Well → Lease → Field → Block
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def design_hierarchical_structure():
    """Design the hierarchical data flow structure"""
    
    hierarchy = {
        "levels": {
            "well": {
                "level": 1,
                "parent": "lease",
                "key_fields": ["api_number", "well_name"],
                "attributes": [
                    "spud_date", "completion_date", "total_depth",
                    "wellbore_status", "construction_days", "completion_days",
                    "rig_name", "tree_height", "side_tracks"
                ],
                "metrics": [
                    "daily_production", "cumulative_production",
                    "peak_rate", "decline_rate", "uptime_percentage"
                ],
                "aggregation": "individual"
            },
            "lease": {
                "level": 2,
                "parent": "field",
                "key_fields": ["lease_number", "lease_name"],
                "attributes": [
                    "operator", "ownership_percentage", "lease_area",
                    "lease_status", "first_production_date"
                ],
                "metrics": [
                    "total_wells", "active_wells", "total_production",
                    "average_well_performance", "lease_reserves"
                ],
                "aggregation": "sum_of_wells"
            },
            "field": {
                "level": 3,
                "parent": "block",
                "key_fields": ["field_name", "field_code"],
                "attributes": [
                    "discovery_date", "water_depth", "field_type",
                    "primary_operator", "field_status"
                ],
                "metrics": [
                    "total_leases", "total_wells", "field_production",
                    "field_reserves", "recovery_factor"
                ],
                "aggregation": "sum_of_leases"
            },
            "block": {
                "level": 4,
                "parent": None,
                "key_fields": ["block_number", "protraction_area"],
                "attributes": [
                    "block_area", "water_depth_range", "block_status",
                    "lease_sale_date", "operators"
                ],
                "metrics": [
                    "total_fields", "total_leases", "total_wells",
                    "block_production", "block_reserves"
                ],
                "aggregation": "sum_of_fields"
            }
        },
        "data_flow": {
            "bottom_up": {
                "description": "Aggregate data from wells up to blocks",
                "steps": [
                    {
                        "step": 1,
                        "action": "Collect well-level data",
                        "source": "BSEE production data, well data",
                        "output": "Well metrics and attributes"
                    },
                    {
                        "step": 2,
                        "action": "Aggregate wells to lease",
                        "method": "Group by lease_number, sum production, count wells",
                        "output": "Lease-level summaries"
                    },
                    {
                        "step": 3,
                        "action": "Aggregate leases to field",
                        "method": "Group by field_name, sum lease metrics",
                        "output": "Field-level summaries"
                    },
                    {
                        "step": 4,
                        "action": "Aggregate fields to block",
                        "method": "Group by block_number, sum field metrics",
                        "output": "Block-level summaries"
                    }
                ]
            },
            "top_down": {
                "description": "Drill down from blocks to wells",
                "steps": [
                    {
                        "step": 1,
                        "action": "Select block",
                        "filter": "block_number = selected",
                        "output": "List of fields in block"
                    },
                    {
                        "step": 2,
                        "action": "Select field",
                        "filter": "field_name = selected",
                        "output": "List of leases in field"
                    },
                    {
                        "step": 3,
                        "action": "Select lease",
                        "filter": "lease_number = selected",
                        "output": "List of wells in lease"
                    },
                    {
                        "step": 4,
                        "action": "Select well",
                        "filter": "api_number = selected",
                        "output": "Well details and history"
                    }
                ]
            }
        }
    }
    
    return hierarchy

def create_aggregation_rules():
    """Define aggregation rules for each level"""
    
    aggregation_rules = {
        "production_aggregation": {
            "well_to_lease": {
                "daily_production": "sum",
                "cumulative_production": "sum",
                "peak_rate": "max",
                "average_rate": "mean",
                "well_count": "count"
            },
            "lease_to_field": {
                "lease_production": "sum",
                "lease_count": "count",
                "total_wells": "sum",
                "active_wells": "sum",
                "average_lease_performance": "mean"
            },
            "field_to_block": {
                "field_production": "sum",
                "field_count": "count",
                "total_leases": "sum",
                "total_wells": "sum",
                "average_field_performance": "mean"
            }
        },
        "economic_aggregation": {
            "well_to_lease": {
                "well_npv": "sum",
                "well_revenue": "sum",
                "well_costs": "sum",
                "well_profit": "sum"
            },
            "lease_to_field": {
                "lease_npv": "sum",
                "lease_revenue": "sum",
                "lease_costs": "sum",
                "lease_profit": "sum"
            },
            "field_to_block": {
                "field_npv": "sum",
                "field_revenue": "sum",
                "field_costs": "sum",
                "field_profit": "sum"
            }
        },
        "temporal_aggregation": {
            "daily_to_monthly": {
                "production": "sum",
                "days_online": "sum",
                "average_rate": "mean"
            },
            "monthly_to_yearly": {
                "production": "sum",
                "months_online": "count",
                "average_monthly_rate": "mean"
            }
        }
    }
    
    return aggregation_rules

def create_data_mapping():
    """Create mapping between BSEE data and hierarchy levels"""
    
    mapping = {
        "bsee_to_hierarchy": {
            "well_level": {
                "bsee_production": {
                    "API_WELL_NUMBER": "api_number",
                    "WELL_NAME": "well_name",
                    "PRODUCTION_DATE": "production_date",
                    "OIL_PROD_DAYS": "production_days",
                    "OIL_PROD_VOLUME": "oil_volume",
                    "GAS_PROD_VOLUME": "gas_volume"
                },
                "bsee_well_data": {
                    "SPUD_DATE": "spud_date",
                    "TOTAL_DEPTH": "total_depth",
                    "WELL_STATUS": "wellbore_status",
                    "RIG_NAME": "rig_name"
                }
            },
            "lease_level": {
                "bsee_lease": {
                    "LEASE_NUMBER": "lease_number",
                    "LEASE_AREA_CODE": "area_code",
                    "LEASE_BLOCK_NUMBER": "block_number",
                    "OPERATOR": "operator"
                }
            },
            "field_level": {
                "bsee_field": {
                    "FIELD_NAME": "field_name",
                    "FIELD_CODE": "field_code",
                    "WATER_DEPTH": "water_depth",
                    "DISCOVERY_DATE": "discovery_date"
                }
            },
            "block_level": {
                "bsee_block": {
                    "BLOCK_NUMBER": "block_number",
                    "PROTRACTION_NAME": "protraction_area",
                    "BLOCK_AREA": "block_area"
                }
            }
        }
    }
    
    return mapping

def create_report_workflow():
    """Create step-by-step report generation workflow"""
    
    workflow = {
        "report_generation_steps": [
            {
                "step": 1,
                "name": "Data Collection",
                "tasks": [
                    "Query BSEE production data for date range",
                    "Query well master data",
                    "Query lease information",
                    "Query field definitions"
                ],
                "inputs": ["date_range", "field_filter", "operator_filter"],
                "outputs": ["raw_production_data", "well_data", "lease_data", "field_data"]
            },
            {
                "step": 2,
                "name": "Data Validation",
                "tasks": [
                    "Validate API numbers",
                    "Check data completeness",
                    "Identify missing values",
                    "Flag anomalies"
                ],
                "inputs": ["raw_data"],
                "outputs": ["validated_data", "quality_report"]
            },
            {
                "step": 3,
                "name": "Hierarchical Aggregation",
                "tasks": [
                    "Group wells by lease",
                    "Calculate lease metrics",
                    "Group leases by field",
                    "Calculate field metrics",
                    "Group fields by block",
                    "Calculate block metrics"
                ],
                "inputs": ["validated_data"],
                "outputs": ["hierarchical_data"]
            },
            {
                "step": 4,
                "name": "Economic Calculations",
                "tasks": [
                    "Apply commodity prices",
                    "Calculate revenues",
                    "Apply cost allocations",
                    "Calculate NPV/IRR",
                    "Generate economic metrics"
                ],
                "inputs": ["hierarchical_data", "price_deck", "cost_assumptions"],
                "outputs": ["economic_data"]
            },
            {
                "step": 5,
                "name": "Template Processing",
                "tasks": [
                    "Select report template",
                    "Populate template variables",
                    "Generate tables",
                    "Create visualizations",
                    "Format report sections"
                ],
                "inputs": ["hierarchical_data", "economic_data", "template"],
                "outputs": ["formatted_report"]
            },
            {
                "step": 6,
                "name": "Export Generation",
                "tasks": [
                    "Generate Excel workbook",
                    "Create PDF document",
                    "Generate HTML dashboard",
                    "Export JSON data",
                    "Create visualization files"
                ],
                "inputs": ["formatted_report"],
                "outputs": ["report_files"]
            }
        ],
        "parallel_processing": {
            "enabled": True,
            "parallel_steps": [3, 4],
            "max_workers": 4
        },
        "caching": {
            "enabled": True,
            "cache_levels": ["lease", "field", "block"],
            "cache_duration": "1 hour"
        }
    }
    
    return workflow

def save_hierarchical_design():
    """Save all hierarchical design documents"""
    
    output_path = Path("tests/modules/bsee/analysis/comprehensive-report-system/results")
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create all design components
    hierarchy = design_hierarchical_structure()
    aggregation_rules = create_aggregation_rules()
    mapping = create_data_mapping()
    workflow = create_report_workflow()
    
    # Combine into comprehensive design
    comprehensive_design = {
        "hierarchy": hierarchy,
        "aggregation_rules": aggregation_rules,
        "data_mapping": mapping,
        "workflow": workflow
    }
    
    # Save as JSON
    with open(output_path / "hierarchical_data_flow.json", "w") as f:
        json.dump(comprehensive_design, f, indent=2)
    
    print(f"Hierarchical data flow saved to: {output_path / 'hierarchical_data_flow.json'}")
    
    # Create markdown documentation
    create_markdown_documentation(comprehensive_design, output_path)
    
    return comprehensive_design

def create_markdown_documentation(design: Dict, output_path: Path):
    """Create markdown documentation for the hierarchical design"""
    
    doc = """# Hierarchical Data Flow Design

## Overview
The comprehensive reporting system uses a four-level hierarchy:
**Well → Lease → Field → Block**

## Hierarchy Levels

### 1. Well Level (Base)
- **Key Fields**: API Number, Well Name
- **Data Source**: BSEE production and well data
- **Aggregation**: Individual well metrics

### 2. Lease Level
- **Key Fields**: Lease Number, Lease Name
- **Parent**: Field
- **Aggregation**: Sum of wells in lease

### 3. Field Level
- **Key Fields**: Field Name, Field Code
- **Parent**: Block
- **Aggregation**: Sum of leases in field

### 4. Block Level (Top)
- **Key Fields**: Block Number, Protraction Area
- **Parent**: None (top level)
- **Aggregation**: Sum of fields in block

## Data Flow Patterns

### Bottom-Up Aggregation
1. Collect well-level data from BSEE
2. Aggregate wells to lease level
3. Aggregate leases to field level
4. Aggregate fields to block level

### Top-Down Drill-Down
1. Select block → View fields
2. Select field → View leases
3. Select lease → View wells
4. Select well → View details

## Aggregation Rules

### Production Metrics
- **Daily Production**: Sum at each level
- **Cumulative Production**: Sum at each level
- **Peak Rate**: Maximum at each level
- **Average Rate**: Mean at each level

### Economic Metrics
- **NPV**: Sum at each level
- **Revenue**: Sum at each level
- **Costs**: Sum at each level
- **Profit**: Sum at each level

## Report Generation Workflow

### Step 1: Data Collection
- Query BSEE databases
- Retrieve well, lease, field data

### Step 2: Data Validation
- Validate identifiers
- Check completeness
- Flag anomalies

### Step 3: Hierarchical Aggregation
- Group by hierarchy levels
- Calculate metrics at each level

### Step 4: Economic Calculations
- Apply pricing
- Calculate revenues and costs
- Generate NPV/IRR

### Step 5: Template Processing
- Select and populate templates
- Generate visualizations

### Step 6: Export Generation
- Create Excel, PDF, HTML outputs
- Export data files

## Performance Optimizations
- Parallel processing for aggregation
- Caching at lease, field, block levels
- Incremental updates for new data

---
*Generated for Comprehensive Report System*
"""
    
    with open(output_path / "hierarchical_design.md", "w", encoding="utf-8") as f:
        f.write(doc)
    
    print(f"Markdown documentation saved to: {output_path / 'hierarchical_design.md'}")

def main():
    """Execute hierarchical design creation"""
    
    print("Creating Hierarchical Data Flow Design")
    print("=" * 50)
    
    design = save_hierarchical_design()
    
    print("\nHierarchical design completed!")
    print("\nKey components created:")
    print("  1. Four-level hierarchy (Well → Lease → Field → Block)")
    print("  2. Aggregation rules for production and economics")
    print("  3. Data mapping from BSEE sources")
    print("  4. Step-by-step report generation workflow")
    print("  5. Performance optimization strategies")

if __name__ == "__main__":
    main()