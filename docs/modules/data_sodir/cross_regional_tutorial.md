# Cross-Regional Analysis Tutorial

> Module: sodir  
> Version: 1.0.0  
> Last Updated: 2025-09-03  
> Tutorial Level: Intermediate  

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Setting Up Data Sources](#setting-up-data-sources)
4. [Data Collection](#data-collection)
5. [Data Normalization](#data-normalization)
6. [Comparative Analysis](#comparative-analysis)
7. [Visualization](#visualization)
8. [Advanced Analysis](#advanced-analysis)
9. [Case Studies](#case-studies)
10. [Best Practices](#best-practices)

## Introduction

This tutorial demonstrates how to perform comprehensive cross-regional analysis between Norwegian Continental Shelf (SODIR) and US Gulf of Mexico (BSEE) petroleum data. You'll learn to:

- Collect data from both regions
- Normalize different data formats and units
- Perform statistical comparisons
- Create insightful visualizations
- Generate actionable insights

### Why Cross-Regional Analysis?

Cross-regional analysis enables:
- **Benchmarking**: Compare operational efficiency across regions
- **Best Practices**: Identify successful strategies from each region
- **Risk Assessment**: Understand regional risk profiles
- **Investment Decisions**: Evaluate opportunities across markets
- **Technology Transfer**: Learn from different technological approaches

## Prerequisites

### Required Libraries

```python
# Install required packages
pip install httpx pandas numpy matplotlib seaborn pyproj scikit-learn

# Import necessary modules
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Import WorldEnergyData modules
from tests.modules.sodir_module.sodir import SodirModule
from tests.modules.sodir_module.cross_regional import CrossRegionalAnalyzer
from tests.modules.sodir_module.visualization import SodirVisualizer
from src.worldenergydata.bsee.bsee import BSEEModule
```

### Configuration Setup

Create configuration files for both modules:

```yaml
# configs/cross_regional.yml
cross_regional:
  regions:
    norway:
      module: "sodir"
      config_path: "configs/sodir.yml"
    usa:
      module: "bsee"
      config_path: "configs/bsee.yml"
  
  analysis:
    normalize_units: true
    time_alignment: "monthly"
    comparison_metrics:
      - drilling_efficiency
      - production_rates
      - discovery_success
      - field_economics
```

## Setting Up Data Sources

### Initialize Both Modules

```python
async def setup_modules():
    """Initialize SODIR and BSEE modules for cross-regional analysis."""
    
    # Initialize SODIR module for Norwegian data
    sodir = SodirModule(config_path="configs/sodir.yml")
    
    # Initialize BSEE module for US Gulf of Mexico data
    bsee = BSEEModule(config_path="configs/bsee.yml")
    
    # Initialize cross-regional analyzer
    analyzer = CrossRegionalAnalyzer()
    
    return sodir, bsee, analyzer

# Setup modules
sodir, bsee, analyzer = asyncio.run(setup_modules())
```

## Data Collection

### Parallel Data Collection

```python
async def collect_regional_data():
    """Collect data from both regions in parallel."""
    
    print("Starting parallel data collection...")
    
    # Define collection tasks
    async def collect_sodir():
        """Collect Norwegian Continental Shelf data."""
        data = {
            "fields": await sodir.api_client.fetch_fields(),
            "wellbores": await sodir.api_client.fetch_wellbores(),
            "blocks": await sodir.api_client.fetch_blocks(),
            "discoveries": await sodir.api_client.fetch_discoveries()
        }
        print(f"SODIR: Collected {len(data['fields'])} fields, "
              f"{len(data['wellbores'])} wellbores")
        return data
    
    async def collect_bsee():
        """Collect US Gulf of Mexico data."""
        data = {
            "fields": bsee.collect_field_data(),
            "wellbores": bsee.collect_wellbore_data(),
            "blocks": bsee.collect_block_data(),
            "production": bsee.collect_production_data()
        }
        print(f"BSEE: Collected {len(data['fields'])} fields, "
              f"{len(data['wellbores'])} wellbores")
        return data
    
    # Execute in parallel
    sodir_data, bsee_data = await asyncio.gather(
        collect_sodir(),
        collect_bsee()
    )
    
    print("Data collection completed!")
    return sodir_data, bsee_data

# Collect data
sodir_data, bsee_data = asyncio.run(collect_regional_data())
```

### Filter for Comparable Data

```python
def filter_comparable_data(sodir_data, bsee_data, years=5):
    """Filter data for comparable time periods and conditions."""
    
    cutoff_date = datetime.now() - timedelta(days=years * 365)
    
    # Filter SODIR data
    sodir_filtered = {
        "fields": [f for f in sodir_data["fields"] 
                  if f.get("production_start") and 
                  datetime.strptime(f["production_start"], "%Y-%m-%d") > cutoff_date],
        "wellbores": [w for w in sodir_data["wellbores"]
                     if w.get("drill_date") and
                     datetime.strptime(w["drill_date"], "%Y-%m-%d") > cutoff_date]
    }
    
    # Filter BSEE data
    bsee_filtered = {
        "fields": [f for f in bsee_data["fields"]
                  if f.get("first_production_date") and
                  pd.to_datetime(f["first_production_date"]) > cutoff_date],
        "wellbores": [w for w in bsee_data["wellbores"]
                     if w.get("spud_date") and
                     pd.to_datetime(w["spud_date"]) > cutoff_date]
    }
    
    return sodir_filtered, bsee_filtered

# Filter for last 5 years
sodir_recent, bsee_recent = filter_comparable_data(sodir_data, bsee_data, years=5)
```

## Data Normalization

### Unit Conversion and Standardization

```python
def normalize_data_for_comparison(sodir_data, bsee_data):
    """Normalize data from both regions for comparison."""
    
    analyzer = CrossRegionalAnalyzer()
    
    # Normalize SODIR data (convert from metric)
    sodir_normalized = analyzer.normalize_sodir_data(sodir_data)
    
    # Normalize BSEE data (already in imperial)
    bsee_normalized = analyzer.normalize_bsee_data(bsee_data)
    
    # Create unified DataFrames
    sodir_df = pd.DataFrame(sodir_normalized["fields"])
    bsee_df = pd.DataFrame(bsee_normalized["fields"])
    
    # Add region identifier
    sodir_df["region"] = "Norway"
    bsee_df["region"] = "US Gulf"
    
    # Combine datasets
    combined_df = pd.concat([sodir_df, bsee_df], ignore_index=True)
    
    return combined_df, sodir_df, bsee_df

# Normalize data
combined_fields, norway_fields, us_fields = normalize_data_for_comparison(
    sodir_recent, bsee_recent
)

print(f"Combined dataset: {len(combined_fields)} fields")
print(f"Columns: {combined_fields.columns.tolist()}")
```

### Handle Different Field Definitions

```python
# Map field status between regions
status_mapping = {
    # SODIR statuses
    "PRODUCING": "Active",
    "SHUT_DOWN": "Inactive",
    "ABANDONED": "Abandoned",
    # BSEE statuses
    "ACTIVE": "Active",
    "INACTIVE": "Inactive",
    "DECOMMISSIONED": "Abandoned"
}

combined_fields["unified_status"] = combined_fields["status"].map(status_mapping)
```

## Comparative Analysis

### Basic Statistical Comparison

```python
def compare_basic_statistics(norway_df, us_df):
    """Compare basic statistics between regions."""
    
    metrics = {
        "Field Count": [len(norway_df), len(us_df)],
        "Avg Water Depth (m)": [
            norway_df["water_depth_m"].mean(),
            us_df["water_depth_m"].mean()
        ],
        "Avg Recovery Factor": [
            norway_df["recovery_factor"].mean(),
            us_df["recovery_factor"].mean()
        ],
        "Total Recoverable (MMBOE)": [
            norway_df["recoverable_boe_mmbbl"].sum(),
            us_df["recoverable_boe_mmbbl"].sum()
        ]
    }
    
    comparison_df = pd.DataFrame(metrics, index=["Norway", "US Gulf"])
    comparison_df = comparison_df.round(2)
    
    print("\n=== Regional Comparison ===")
    print(comparison_df)
    
    return comparison_df

# Compare statistics
stats_comparison = compare_basic_statistics(norway_fields, us_fields)
```

### Drilling Efficiency Analysis

```python
def analyze_drilling_efficiency(sodir_wells, bsee_wells):
    """Compare drilling efficiency between regions."""
    
    # Convert to DataFrames
    norway_wells = pd.DataFrame(sodir_wells)
    us_wells = pd.DataFrame(bsee_wells)
    
    # Calculate drilling metrics
    norway_metrics = {
        "avg_depth_m": norway_wells["total_depth_m"].mean(),
        "avg_days": norway_wells["drilling_days"].mean(),
        "meters_per_day": norway_wells["total_depth_m"].mean() / 
                         norway_wells["drilling_days"].mean(),
        "success_rate": len(norway_wells[norway_wells["status"] == "PRODUCING"]) / 
                       len(norway_wells)
    }
    
    us_metrics = {
        "avg_depth_m": us_wells["total_depth_ft"].mean() * 0.3048,  # Convert to meters
        "avg_days": us_wells["drilling_days"].mean(),
        "meters_per_day": (us_wells["total_depth_ft"].mean() * 0.3048) / 
                         us_wells["drilling_days"].mean(),
        "success_rate": len(us_wells[us_wells["status"] == "PRODUCING"]) / 
                       len(us_wells)
    }
    
    # Create comparison
    efficiency_df = pd.DataFrame([norway_metrics, us_metrics], 
                                 index=["Norway", "US Gulf"])
    
    print("\n=== Drilling Efficiency Comparison ===")
    print(efficiency_df.round(2))
    
    return efficiency_df

# Analyze drilling efficiency
drilling_efficiency = analyze_drilling_efficiency(
    sodir_recent["wellbores"], 
    bsee_recent["wellbores"]
)
```

### Production Performance Comparison

```python
def compare_production_performance(norway_fields, us_fields):
    """Compare production performance metrics."""
    
    # Calculate production metrics
    def calculate_metrics(df, region):
        return {
            "Region": region,
            "Avg Initial Production (BOE/day)": df["initial_production_boepd"].mean(),
            "Avg Peak Production (BOE/day)": df["peak_production_boepd"].mean(),
            "Avg Decline Rate (%/year)": df["decline_rate_pct"].mean(),
            "Avg Field Life (years)": df["field_life_years"].mean(),
            "Avg Recovery Factor": df["recovery_factor"].mean() * 100
        }
    
    norway_metrics = calculate_metrics(norway_fields, "Norway")
    us_metrics = calculate_metrics(us_fields, "US Gulf")
    
    performance_df = pd.DataFrame([norway_metrics, us_metrics])
    performance_df = performance_df.set_index("Region")
    
    print("\n=== Production Performance ===")
    print(performance_df.round(2))
    
    return performance_df

# Compare production
production_comparison = compare_production_performance(norway_fields, us_fields)
```

## Visualization

### Create Comparison Charts

```python
def create_comparison_visualizations(combined_df):
    """Create comprehensive comparison visualizations."""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Water Depth Distribution
    ax1 = axes[0, 0]
    combined_df.boxplot(column="water_depth_m", by="region", ax=ax1)
    ax1.set_title("Water Depth Distribution by Region")
    ax1.set_ylabel("Water Depth (m)")
    ax1.set_xlabel("")
    
    # 2. Recovery Factor Comparison
    ax2 = axes[0, 1]
    recovery_data = combined_df.groupby("region")["recovery_factor"].mean() * 100
    recovery_data.plot(kind="bar", ax=ax2, color=["#1f77b4", "#ff7f0e"])
    ax2.set_title("Average Recovery Factor by Region")
    ax2.set_ylabel("Recovery Factor (%)")
    ax2.set_xlabel("Region")
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=0)
    
    # 3. Field Size Distribution
    ax3 = axes[1, 0]
    for region in combined_df["region"].unique():
        region_data = combined_df[combined_df["region"] == region]
        ax3.hist(region_data["recoverable_boe_mmbbl"], 
                alpha=0.5, label=region, bins=20)
    ax3.set_title("Field Size Distribution")
    ax3.set_xlabel("Recoverable Resources (MMBOE)")
    ax3.set_ylabel("Number of Fields")
    ax3.legend()
    ax3.set_xlim(0, 1000)
    
    # 4. Discovery Timeline
    ax4 = axes[1, 1]
    combined_df["discovery_year"] = pd.to_datetime(
        combined_df["discovery_date"]
    ).dt.year
    discovery_counts = combined_df.groupby(
        ["discovery_year", "region"]
    ).size().unstack(fill_value=0)
    discovery_counts.plot(ax=ax4, kind="line", marker="o")
    ax4.set_title("Discovery Timeline")
    ax4.set_xlabel("Year")
    ax4.set_ylabel("Number of Discoveries")
    ax4.legend(title="Region")
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle("Cross-Regional Comparison: Norway vs US Gulf of Mexico", 
                 fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig("reports/cross_regional_comparison.png", dpi=300, bbox_inches="tight")
    plt.show()
    
    return fig

# Create visualizations
fig = create_comparison_visualizations(combined_fields)
```

### Geographic Comparison Map

```python
def create_geographic_comparison():
    """Create maps showing field locations in both regions."""
    
    visualizer = SodirVisualizer()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Norway Continental Shelf
    norway_bounds = {
        "north": 72.0, "south": 56.0,
        "east": 35.0, "west": -5.0
    }
    
    # Plot Norwegian fields
    for _, field in norway_fields.iterrows():
        ax1.scatter(field["longitude"], field["latitude"],
                   s=field["recoverable_boe_mmbbl"],
                   alpha=0.6, c="blue")
    
    ax1.set_xlim(norway_bounds["west"], norway_bounds["east"])
    ax1.set_ylim(norway_bounds["south"], norway_bounds["north"])
    ax1.set_title("Norwegian Continental Shelf Fields")
    ax1.set_xlabel("Longitude")
    ax1.set_ylabel("Latitude")
    ax1.grid(True, alpha=0.3)
    
    # US Gulf of Mexico
    gom_bounds = {
        "north": 30.5, "south": 23.5,
        "east": -81.0, "west": -98.0
    }
    
    # Plot US Gulf fields
    for _, field in us_fields.iterrows():
        ax2.scatter(field["longitude"], field["latitude"],
                   s=field["recoverable_boe_mmbbl"],
                   alpha=0.6, c="orange")
    
    ax2.set_xlim(gom_bounds["west"], gom_bounds["east"])
    ax2.set_ylim(gom_bounds["south"], gom_bounds["north"])
    ax2.set_title("US Gulf of Mexico Fields")
    ax2.set_xlabel("Longitude")
    ax2.set_ylabel("Latitude")
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle("Geographic Distribution of Oil & Gas Fields", fontsize=14)
    plt.tight_layout()
    plt.savefig("reports/geographic_comparison.png", dpi=300)
    plt.show()
    
    return fig

# Create geographic comparison
geo_fig = create_geographic_comparison()
```

## Advanced Analysis

### Economic Comparison

```python
def compare_field_economics():
    """Compare field economics between regions."""
    
    from tests.modules.sodir_module.npv_norway import NorwayNPVCalculator
    from src.worldenergydata.bsee.analysis.financial.analyzer import FinancialAnalyzer
    
    # Norwegian NPV calculation
    norway_npv = NorwayNPVCalculator()
    norway_fields["npv_musd"] = norway_fields.apply(
        lambda row: norway_npv.calculate_field_npv(
            oil_reserves_sm3=row["recoverable_oil_sm3"],
            gas_reserves_bsm3=row["recoverable_gas_bsm3"],
            capex_mnok=row.get("capex_mnok", 1000),
            opex_mnok_annual=row.get("opex_mnok", 100),
            oil_price_usd=80,
            gas_price_usd_mmbtu=4
        )["npv_musd"],
        axis=1
    )
    
    # US Gulf NPV calculation
    us_analyzer = FinancialAnalyzer()
    us_fields["npv_musd"] = us_fields.apply(
        lambda row: us_analyzer.calculate_npv(
            production_bbl=row["recoverable_oil_bbl"],
            oil_price=80,
            capex=row.get("capex_musd", 100),
            opex_annual=row.get("opex_musd", 10)
        ),
        axis=1
    )
    
    # Compare economics
    economics_comparison = pd.DataFrame({
        "Avg NPV (MUSD)": [
            norway_fields["npv_musd"].mean(),
            us_fields["npv_musd"].mean()
        ],
        "Total NPV (BUSD)": [
            norway_fields["npv_musd"].sum() / 1000,
            us_fields["npv_musd"].sum() / 1000
        ],
        "NPV per BOE (USD)": [
            norway_fields["npv_musd"].sum() * 1e6 / 
            (norway_fields["recoverable_boe_mmbbl"].sum() * 1e6),
            us_fields["npv_musd"].sum() * 1e6 / 
            (us_fields["recoverable_boe_mmbbl"].sum() * 1e6)
        ]
    }, index=["Norway", "US Gulf"])
    
    print("\n=== Economic Comparison ===")
    print(economics_comparison.round(2))
    
    return economics_comparison

# Compare economics
economics = compare_field_economics()
```

### Technology Adoption Analysis

```python
def analyze_technology_adoption():
    """Compare technology adoption between regions."""
    
    # Analyze wellbore technology
    norway_wells_df = pd.DataFrame(sodir_recent["wellbores"])
    us_wells_df = pd.DataFrame(bsee_recent["wellbores"])
    
    technology_metrics = {}
    
    # Horizontal drilling adoption
    technology_metrics["Horizontal Wells (%)"] = [
        len(norway_wells_df[norway_wells_df["well_type"] == "HORIZONTAL"]) / 
        len(norway_wells_df) * 100,
        len(us_wells_df[us_wells_df["well_type"] == "HORIZONTAL"]) / 
        len(us_wells_df) * 100
    ]
    
    # Subsea completions
    technology_metrics["Subsea Completions (%)"] = [
        len(norway_wells_df[norway_wells_df["completion_type"] == "SUBSEA"]) / 
        len(norway_wells_df) * 100,
        len(us_wells_df[us_wells_df["completion_type"] == "SUBSEA"]) / 
        len(us_wells_df) * 100
    ]
    
    # Water depth capabilities
    technology_metrics["Deepwater (>1000m) (%)"] = [
        len(norway_wells_df[norway_wells_df["water_depth_m"] > 1000]) / 
        len(norway_wells_df) * 100,
        len(us_wells_df[us_wells_df["water_depth_m"] > 1000]) / 
        len(us_wells_df) * 100
    ]
    
    tech_df = pd.DataFrame(technology_metrics, index=["Norway", "US Gulf"])
    
    print("\n=== Technology Adoption ===")
    print(tech_df.round(1))
    
    # Visualize technology trends
    fig, ax = plt.subplots(figsize=(10, 6))
    tech_df.T.plot(kind="bar", ax=ax)
    ax.set_title("Technology Adoption Comparison")
    ax.set_ylabel("Percentage (%)")
    ax.set_xlabel("Technology")
    ax.legend(title="Region")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("reports/technology_adoption.png", dpi=300)
    plt.show()
    
    return tech_df

# Analyze technology
technology = analyze_technology_adoption()
```

## Case Studies

### Case Study 1: Large Field Development

```python
def compare_large_fields():
    """Compare development of large fields in each region."""
    
    # Select largest fields
    norway_large = norway_fields.nlargest(5, "recoverable_boe_mmbbl")
    us_large = us_fields.nlargest(5, "recoverable_boe_mmbbl")
    
    print("\n=== Largest Fields Comparison ===")
    print("\nNorway Top 5:")
    print(norway_large[["field_name", "recoverable_boe_mmbbl", 
                        "recovery_factor", "production_start"]])
    
    print("\nUS Gulf Top 5:")
    print(us_large[["field_name", "recoverable_boe_mmbbl", 
                   "recovery_factor", "production_start"]])
    
    # Development timeline comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Norway timeline
    norway_large["years_to_production"] = (
        pd.to_datetime(norway_large["production_start"]) - 
        pd.to_datetime(norway_large["discovery_date"])
    ).dt.days / 365
    
    norway_large.plot(x="field_name", y="years_to_production", 
                     kind="barh", ax=ax1, color="blue")
    ax1.set_title("Norway: Years from Discovery to Production")
    ax1.set_xlabel("Years")
    ax1.set_ylabel("")
    
    # US timeline
    us_large["years_to_production"] = (
        pd.to_datetime(us_large["production_start"]) - 
        pd.to_datetime(us_large["discovery_date"])
    ).dt.days / 365
    
    us_large.plot(x="field_name", y="years_to_production", 
                 kind="barh", ax=ax2, color="orange")
    ax2.set_title("US Gulf: Years from Discovery to Production")
    ax2.set_xlabel("Years")
    ax2.set_ylabel("")
    
    plt.tight_layout()
    plt.savefig("reports/large_fields_development.png", dpi=300)
    plt.show()
    
    return norway_large, us_large

# Compare large fields
norway_giants, us_giants = compare_large_fields()
```

### Case Study 2: Exploration Success Rates

```python
def analyze_exploration_success():
    """Analyze exploration success rates over time."""
    
    # Process discovery data
    norway_disc = pd.DataFrame(sodir_data["discoveries"])
    norway_disc["year"] = pd.to_datetime(norway_disc["discovery_date"]).dt.year
    norway_disc["region"] = "Norway"
    
    # Calculate success rates by year
    def calculate_success_rate(wells_df, discoveries_df, year):
        year_wells = len(wells_df[wells_df["drill_year"] == year])
        year_discoveries = len(discoveries_df[discoveries_df["year"] == year])
        return (year_discoveries / year_wells * 100) if year_wells > 0 else 0
    
    years = range(2015, 2024)
    norway_success = [calculate_success_rate(
        pd.DataFrame(sodir_data["wellbores"]), 
        norway_disc, year
    ) for year in years]
    
    # Plot exploration success trends
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(years, norway_success, marker="o", label="Norway", linewidth=2)
    ax.set_title("Exploration Success Rate Trends")
    ax.set_xlabel("Year")
    ax.set_ylabel("Success Rate (%)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("reports/exploration_success.png", dpi=300)
    plt.show()
    
    return norway_success

# Analyze exploration
success_rates = analyze_exploration_success()
```

## Best Practices

### Data Quality Checks

```python
def perform_data_quality_checks(combined_df):
    """Perform comprehensive data quality checks."""
    
    quality_report = {
        "Total Records": len(combined_df),
        "Missing Values": combined_df.isnull().sum().to_dict(),
        "Duplicate Records": combined_df.duplicated().sum(),
        "Data Types": combined_df.dtypes.to_dict(),
        "Value Ranges": {
            "water_depth_m": f"{combined_df['water_depth_m'].min():.0f} - "
                           f"{combined_df['water_depth_m'].max():.0f}",
            "recovery_factor": f"{combined_df['recovery_factor'].min():.2f} - "
                             f"{combined_df['recovery_factor'].max():.2f}"
        }
    }
    
    print("\n=== Data Quality Report ===")
    for key, value in quality_report.items():
        print(f"{key}: {value}")
    
    # Identify outliers
    from scipy import stats
    numeric_cols = combined_df.select_dtypes(include=[np.number]).columns
    outliers = {}
    
    for col in numeric_cols:
        z_scores = np.abs(stats.zscore(combined_df[col].dropna()))
        outliers[col] = len(z_scores[z_scores > 3])
    
    print(f"\nOutliers (|z-score| > 3): {outliers}")
    
    return quality_report

# Check data quality
quality_report = perform_data_quality_checks(combined_fields)
```

### Statistical Significance Testing

```python
from scipy import stats

def test_statistical_significance(norway_fields, us_fields):
    """Test statistical significance of differences."""
    
    tests = {}
    
    # T-test for recovery factors
    t_stat, p_value = stats.ttest_ind(
        norway_fields["recovery_factor"].dropna(),
        us_fields["recovery_factor"].dropna()
    )
    tests["Recovery Factor"] = {
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant": p_value < 0.05
    }
    
    # Mann-Whitney U test for water depth (non-parametric)
    u_stat, p_value = stats.mannwhitneyu(
        norway_fields["water_depth_m"].dropna(),
        us_fields["water_depth_m"].dropna()
    )
    tests["Water Depth"] = {
        "u_statistic": u_stat,
        "p_value": p_value,
        "significant": p_value < 0.05
    }
    
    print("\n=== Statistical Significance Tests ===")
    for metric, result in tests.items():
        print(f"{metric}:")
        print(f"  p-value: {result['p_value']:.4f}")
        print(f"  Significant difference: {result['significant']}")
    
    return tests

# Test significance
significance_tests = test_statistical_significance(norway_fields, us_fields)
```

### Generate Executive Report

```python
def generate_executive_report(all_results):
    """Generate executive summary report."""
    
    report = f"""
    CROSS-REGIONAL ANALYSIS REPORT
    ===============================
    Date: {datetime.now().strftime("%Y-%m-%d")}
    Regions: Norwegian Continental Shelf vs US Gulf of Mexico
    
    EXECUTIVE SUMMARY
    -----------------
    
    KEY FINDINGS:
    1. Field Development
       - Norway has {len(norway_fields)} active fields
       - US Gulf has {len(us_fields)} active fields
       - Average field size: Norway {norway_fields['recoverable_boe_mmbbl'].mean():.0f} MMBOE, 
         US Gulf {us_fields['recoverable_boe_mmbbl'].mean():.0f} MMBOE
    
    2. Operational Efficiency
       - Average recovery factor: Norway {norway_fields['recovery_factor'].mean()*100:.1f}%, 
         US Gulf {us_fields['recovery_factor'].mean()*100:.1f}%
       - Drilling efficiency: Norway {drilling_efficiency.loc['Norway', 'meters_per_day']:.1f} m/day, 
         US Gulf {drilling_efficiency.loc['US Gulf', 'meters_per_day']:.1f} m/day
    
    3. Economic Performance
       - Total NPV: Norway ${economics.loc['Norway', 'Total NPV (BUSD)']:.1f}B, 
         US Gulf ${economics.loc['US Gulf', 'Total NPV (BUSD)']:.1f}B
       - NPV per BOE: Norway ${economics.loc['Norway', 'NPV per BOE (USD)']:.2f}, 
         US Gulf ${economics.loc['US Gulf', 'NPV per BOE (USD)']:.2f}
    
    4. Technology Adoption
       - Horizontal drilling: Norway {technology.loc['Norway', 'Horizontal Wells (%)']:.1f}%, 
         US Gulf {technology.loc['US Gulf', 'Horizontal Wells (%)']:.1f}%
       - Deepwater capability: Norway {technology.loc['Norway', 'Deepwater (>1000m) (%)']:.1f}%, 
         US Gulf {technology.loc['US Gulf', 'Deepwater (>1000m) (%)']:.1f}%
    
    RECOMMENDATIONS:
    1. Technology Transfer: Share deepwater expertise between regions
    2. Best Practices: Adopt Norwegian recovery optimization techniques
    3. Risk Management: Learn from regional regulatory approaches
    4. Investment Focus: Target high-NPV opportunities in both regions
    
    NEXT STEPS:
    - Detailed field-by-field benchmarking
    - Operator performance comparison
    - Environmental impact assessment
    - Regulatory framework analysis
    """
    
    # Save report
    with open("reports/executive_summary.md", "w") as f:
        f.write(report)
    
    print(report)
    return report

# Generate report
exec_report = generate_executive_report({
    "stats": stats_comparison,
    "drilling": drilling_efficiency,
    "economics": economics,
    "technology": technology
})
```

## Conclusion

This tutorial has demonstrated comprehensive cross-regional analysis capabilities between Norwegian Continental Shelf (SODIR) and US Gulf of Mexico (BSEE) petroleum data. Key takeaways:

1. **Data Integration**: Successfully collected and normalized data from different sources
2. **Comparative Analysis**: Identified key differences in operational metrics
3. **Visualization**: Created insightful charts and maps for decision-making
4. **Statistical Validation**: Ensured findings are statistically significant
5. **Actionable Insights**: Generated executive-ready reports with recommendations

### Further Resources

- [API Guide](api_guide.md) - Detailed API usage
- [Configuration Guide](config_guide.md) - Configuration options
- [Module README](README.md) - Quick start guide

### Support

For questions or issues with cross-regional analysis:
- Consult the WorldEnergyData documentation
- Review the example notebooks in `notebooks/cross_regional/`
- Contact the development team

---

*Happy analyzing! The insights from cross-regional comparison can drive better decision-making in global energy markets.*