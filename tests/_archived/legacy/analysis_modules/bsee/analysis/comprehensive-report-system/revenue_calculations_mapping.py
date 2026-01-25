"""
Map revenue calculations from go-by reports and create comprehensive
economic calculation framework for the reporting system
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

def map_revenue_calculations():
    """Map revenue calculation methodology based on go-by reports"""
    
    revenue_mapping = {
        "revenue_components": {
            "oil_revenue": {
                "formula": "oil_volume * oil_price * (1 - royalty_rate)",
                "inputs": {
                    "oil_volume": {
                        "source": "BSEE production data",
                        "field": "OIL_PROD_VOLUME",
                        "unit": "BBL"
                    },
                    "oil_price": {
                        "source": "Price deck or market data",
                        "field": "WTI_PRICE or BRENT_PRICE",
                        "unit": "$/BBL"
                    },
                    "royalty_rate": {
                        "source": "Lease terms",
                        "field": "ROYALTY_RATE",
                        "unit": "fraction",
                        "default": 0.1875  # 18.75% standard federal royalty
                    }
                },
                "aggregation": "sum across time periods"
            },
            "gas_revenue": {
                "formula": "gas_volume * gas_price * (1 - royalty_rate)",
                "inputs": {
                    "gas_volume": {
                        "source": "BSEE production data",
                        "field": "GAS_PROD_VOLUME",
                        "unit": "MCF"
                    },
                    "gas_price": {
                        "source": "Price deck or market data",
                        "field": "HENRY_HUB_PRICE",
                        "unit": "$/MCF"
                    },
                    "royalty_rate": {
                        "source": "Lease terms",
                        "field": "ROYALTY_RATE",
                        "unit": "fraction",
                        "default": 0.1875
                    }
                },
                "aggregation": "sum across time periods"
            },
            "ngl_revenue": {
                "formula": "ngl_volume * ngl_price * (1 - royalty_rate)",
                "inputs": {
                    "ngl_volume": {
                        "source": "BSEE production data",
                        "field": "NGL_PROD_VOLUME",
                        "unit": "BBL"
                    },
                    "ngl_price": {
                        "source": "Price deck or market data",
                        "field": "NGL_PRICE",
                        "unit": "$/BBL"
                    }
                },
                "aggregation": "sum across time periods"
            },
            "total_revenue": {
                "formula": "oil_revenue + gas_revenue + ngl_revenue",
                "aggregation": "sum of components"
            }
        },
        "cost_components": {
            "operating_costs": {
                "lease_operating_expense": {
                    "formula": "production_volume * loe_per_barrel",
                    "typical_range": "$5-15/BBL",
                    "factors": ["water_depth", "well_complexity", "field_maturity"]
                },
                "workover_costs": {
                    "formula": "workover_count * avg_workover_cost",
                    "typical_range": "$1-5M per workover",
                    "frequency": "as needed"
                },
                "transportation": {
                    "formula": "production_volume * transport_rate",
                    "typical_range": "$2-8/BBL",
                    "factors": ["distance_to_shore", "pipeline_capacity"]
                }
            },
            "capital_costs": {
                "drilling_costs": {
                    "formula": "well_count * avg_drilling_cost",
                    "typical_range": "$50-150M per deepwater well",
                    "factors": ["water_depth", "total_depth", "complexity"]
                },
                "completion_costs": {
                    "formula": "well_count * avg_completion_cost",
                    "typical_range": "$20-50M per well",
                    "factors": ["completion_type", "number_of_zones"]
                },
                "facilities": {
                    "formula": "facility_capex / field_life",
                    "typical_range": "$500M-2B for deepwater",
                    "depreciation": "straight_line or units_of_production"
                }
            },
            "abandonment_costs": {
                "well_p&a": {
                    "formula": "well_count * p&a_cost_per_well",
                    "typical_range": "$10-30M per well",
                    "timing": "end of field life"
                },
                "facility_removal": {
                    "formula": "facility_count * removal_cost",
                    "typical_range": "$100-500M",
                    "timing": "end of field life"
                }
            }
        },
        "economic_metrics": {
            "net_revenue": {
                "formula": "total_revenue - operating_costs",
                "unit": "$",
                "aggregation": "period sum"
            },
            "ebitda": {
                "formula": "net_revenue - g&a_costs",
                "unit": "$",
                "use": "operational performance"
            },
            "free_cash_flow": {
                "formula": "ebitda - capital_costs - taxes",
                "unit": "$",
                "use": "investment analysis"
            },
            "npv": {
                "formula": "sum(free_cash_flow / (1 + discount_rate)^t)",
                "discount_rate": 0.10,  # 10% typical
                "unit": "$",
                "use": "project valuation"
            },
            "irr": {
                "formula": "rate where NPV = 0",
                "target": "> 15%",
                "use": "return measurement"
            },
            "payback_period": {
                "formula": "time when cumulative_fcf >= 0",
                "unit": "years",
                "target": "< 5 years"
            }
        }
    }
    
    return revenue_mapping

def create_calculation_workflow():
    """Create step-by-step calculation workflow"""
    
    workflow = {
        "calculation_steps": [
            {
                "step": 1,
                "name": "Production Data Preparation",
                "tasks": [
                    "Load monthly production volumes",
                    "Convert units to standard (BBL, MCF)",
                    "Handle missing data interpolation",
                    "Apply allocation factors if needed"
                ],
                "output": "clean_production_data"
            },
            {
                "step": 2,
                "name": "Price Deck Application",
                "tasks": [
                    "Load price assumptions",
                    "Match prices to production periods",
                    "Apply price differentials if applicable",
                    "Handle price escalation"
                ],
                "output": "priced_production"
            },
            {
                "step": 3,
                "name": "Gross Revenue Calculation",
                "tasks": [
                    "Calculate oil revenue (volume * price)",
                    "Calculate gas revenue (volume * price)",
                    "Calculate NGL revenue if applicable",
                    "Sum to gross revenue"
                ],
                "output": "gross_revenue"
            },
            {
                "step": 4,
                "name": "Royalty and Tax Calculation",
                "tasks": [
                    "Apply royalty rate to gross revenue",
                    "Calculate severance taxes",
                    "Apply other government takes",
                    "Calculate net revenue after royalties"
                ],
                "output": "net_revenue"
            },
            {
                "step": 5,
                "name": "Operating Cost Allocation",
                "tasks": [
                    "Apply lease operating expenses",
                    "Add workover costs",
                    "Include transportation costs",
                    "Calculate total operating costs"
                ],
                "output": "operating_income"
            },
            {
                "step": 6,
                "name": "Capital Cost Treatment",
                "tasks": [
                    "Amortize drilling costs",
                    "Depreciate facilities",
                    "Apply depletion allowance",
                    "Calculate capital charges"
                ],
                "output": "ebitda"
            },
            {
                "step": 7,
                "name": "Cash Flow Generation",
                "tasks": [
                    "Calculate free cash flow",
                    "Apply working capital changes",
                    "Include abandonment provisions",
                    "Generate cash flow timeline"
                ],
                "output": "cash_flow_schedule"
            },
            {
                "step": 8,
                "name": "NPV and Metrics Calculation",
                "tasks": [
                    "Apply discount rate",
                    "Calculate NPV",
                    "Calculate IRR",
                    "Determine payback period",
                    "Calculate other metrics"
                ],
                "output": "economic_metrics"
            }
        ]
    }
    
    return workflow

def create_price_deck_template():
    """Create template for price assumptions"""
    
    price_deck = {
        "base_prices": {
            "oil": {
                "2024": 75.00,
                "2025": 77.00,
                "2026": 78.00,
                "2027": 79.00,
                "2028_plus": 80.00,
                "unit": "$/BBL",
                "benchmark": "WTI"
            },
            "gas": {
                "2024": 3.50,
                "2025": 3.75,
                "2026": 4.00,
                "2027": 4.00,
                "2028_plus": 4.25,
                "unit": "$/MCF",
                "benchmark": "Henry Hub"
            },
            "ngl": {
                "percentage_of_oil": 0.45,
                "unit": "fraction of oil price"
            }
        },
        "escalation": {
            "method": "inflation",
            "rate": 0.02,  # 2% annual
            "apply_to": ["operating_costs", "capital_costs"]
        },
        "differentials": {
            "oil_quality": {
                "API_gravity_adjustment": "formula based on API",
                "sulfur_content_adjustment": "formula based on sulfur %"
            },
            "location": {
                "gulf_coast_differential": -2.00,
                "unit": "$/BBL"
            }
        }
    }
    
    return price_deck

def create_cost_assumptions():
    """Create template for cost assumptions"""
    
    cost_assumptions = {
        "operating_costs": {
            "lease_operating_expense": {
                "shallow_water": 8.00,
                "deepwater": 12.00,
                "ultra_deepwater": 15.00,
                "unit": "$/BBL"
            },
            "workover_frequency": {
                "years_between": 3,
                "cost_per_workover": 3000000,
                "unit": "$"
            },
            "transportation": {
                "pipeline": 3.00,
                "tanker": 5.00,
                "unit": "$/BBL"
            },
            "g&a": {
                "percentage_of_revenue": 0.03,
                "unit": "fraction"
            }
        },
        "capital_costs": {
            "drilling": {
                "shallow_water": 30000000,
                "deepwater": 100000000,
                "ultra_deepwater": 150000000,
                "unit": "$/well"
            },
            "completion": {
                "simple": 15000000,
                "complex": 35000000,
                "unit": "$/well"
            }
        },
        "tax_assumptions": {
            "federal_tax_rate": 0.21,
            "state_tax_rate": 0.05,
            "royalty_rate": 0.1875,
            "severance_tax": 0.04
        }
    }
    
    return cost_assumptions

def save_revenue_mapping():
    """Save all revenue calculation mappings and templates"""
    
    output_path = Path("tests/modules/bsee/analysis/comprehensive-report-system/results")
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create all components
    revenue_map = map_revenue_calculations()
    workflow = create_calculation_workflow()
    price_deck = create_price_deck_template()
    cost_assumptions = create_cost_assumptions()
    
    # Combine into comprehensive economic framework
    economic_framework = {
        "revenue_mapping": revenue_map,
        "calculation_workflow": workflow,
        "price_deck_template": price_deck,
        "cost_assumptions": cost_assumptions,
        "metadata": {
            "created": datetime.now().isoformat(),
            "version": "1.0",
            "purpose": "Comprehensive report system economic calculations"
        }
    }
    
    # Save as JSON
    with open(output_path / "economic_framework.json", "w") as f:
        json.dump(economic_framework, f, indent=2)
    
    print(f"Economic framework saved to: {output_path / 'economic_framework.json'}")
    
    # Create summary documentation
    create_economic_documentation(economic_framework, output_path)
    
    return economic_framework

def create_economic_documentation(framework: Dict, output_path: Path):
    """Create markdown documentation for economic calculations"""
    
    doc = """# Revenue Calculation Mapping

## Overview
This document maps the revenue calculation methodology for the comprehensive reporting system based on analysis of go-by reports.

## Revenue Components

### Oil Revenue
- **Formula**: `oil_volume × oil_price × (1 - royalty_rate)`
- **Source**: BSEE production data
- **Royalty**: 18.75% federal standard

### Gas Revenue
- **Formula**: `gas_volume × gas_price × (1 - royalty_rate)`
- **Source**: BSEE production data
- **Benchmark**: Henry Hub pricing

### Total Revenue
- **Formula**: `oil_revenue + gas_revenue + ngl_revenue`

## Cost Structure

### Operating Costs
- **Lease Operating Expense**: $5-15/BBL depending on water depth
- **Workover Costs**: $1-5M per workover
- **Transportation**: $2-8/BBL

### Capital Costs
- **Drilling**: $50-150M per deepwater well
- **Completion**: $20-50M per well
- **Facilities**: $500M-2B for deepwater development

## Economic Metrics

### Key Performance Indicators
1. **Net Revenue**: Total revenue - Operating costs
2. **EBITDA**: Net revenue - G&A costs
3. **Free Cash Flow**: EBITDA - Capital costs - Taxes
4. **NPV**: Discounted cash flows at 10%
5. **IRR**: Target > 15%
6. **Payback Period**: Target < 5 years

## Calculation Workflow

### Step-by-Step Process
1. **Production Data**: Load and clean monthly volumes
2. **Price Application**: Apply price deck to production
3. **Gross Revenue**: Calculate product revenues
4. **Royalties/Taxes**: Apply government takes
5. **Operating Costs**: Deduct operating expenses
6. **Capital Treatment**: Apply depreciation/amortization
7. **Cash Flow**: Generate cash flow schedule
8. **NPV/Metrics**: Calculate economic indicators

## Price Assumptions

### Base Case (2024-2028)
- **Oil**: $75-80/BBL (WTI)
- **Gas**: $3.50-4.25/MCF (Henry Hub)
- **NGL**: 45% of oil price
- **Escalation**: 2% annual inflation

## Implementation Notes
- All calculations performed at monthly granularity
- Aggregation to field/block level as needed
- Sensitivity analysis on key variables
- Monte Carlo simulation for uncertainty

---
*Generated for Comprehensive Report System*
"""
    
    with open(output_path / "revenue_calculations.md", "w", encoding="utf-8") as f:
        f.write(doc)
    
    print(f"Revenue documentation saved to: {output_path / 'revenue_calculations.md'}")

def main():
    """Execute revenue mapping creation"""
    
    print("Mapping Revenue Calculations")
    print("=" * 50)
    
    framework = save_revenue_mapping()
    
    print("\nRevenue mapping completed!")
    print("\nKey components created:")
    print("  1. Revenue calculation formulas")
    print("  2. Cost structure templates")
    print("  3. Economic metrics definitions")
    print("  4. Step-by-step calculation workflow")
    print("  5. Price deck and assumptions")

if __name__ == "__main__":
    main()