"""
Detailed analysis of go-by reports to understand the actual data structure
and create a template for comprehensive reporting system.
"""

import json
import os
from pathlib import Path

import pandas as pd


def detailed_excel_analysis(file_path, report_name):
    """Perform detailed analysis of Excel report structure"""
    print(f"\n{'='*70}")
    print(f"DETAILED ANALYSIS: {report_name}")
    print("=" * 70)

    try:
        # Load Excel file
        df = pd.read_excel(file_path)

        # The Excel files have a specific structure where:
        # - First column contains row labels/categories
        # - Other columns represent individual wells

        # Extract the structure
        row_labels = df.iloc[:, 0].tolist()  # First column - row labels
        well_columns = df.columns[1:].tolist()  # Rest are well identifiers

        print(f"\nReport Structure:")
        print(f"- Number of data categories (rows): {len(row_labels)}")
        print(f"- Number of wells (columns): {len(well_columns)}")

        print(f"\nData Categories (Row Labels):")
        for i, label in enumerate(row_labels, 1):
            if pd.notna(label):
                print(f"  {i:2d}. {label}")

        print(f"\nWell Identifiers:")
        # Clean well names (remove unnamed columns)
        valid_wells = [w for w in well_columns if not str(w).startswith("Unnamed")]
        for well in valid_wells[:10]:  # First 10 wells
            print(f"  - {well}")
        if len(valid_wells) > 10:
            print(f"  ... and {len(valid_wells) - 10} more wells")

        # Analyze the data structure in detail
        print(f"\nData Analysis:")

        # Create a proper dataframe with row labels as index
        df_clean = df.set_index(df.columns[0])
        df_clean = df_clean.loc[:, ~df_clean.columns.str.contains("Unnamed")]

        # Common field data categories
        common_categories = [
            "Company",
            "Water Depth (ft)",
            "Well Purpose",
            "Rig Name",
            "Spud Date",
            "End Date",
            "Total Depth (ft)",
            "Days to Drill",
            "Completion Type",
            "First Production",
            "Peak Production (bopd)",
            "Cumulative Production (MMbbl)",
            "Status",
        ]

        print("\nIdentified Data Categories:")
        for category in common_categories:
            matching = [
                label
                for label in row_labels
                if label and category.lower() in str(label).lower()
            ]
            if matching:
                print(f"  ✓ {category}: Found as '{matching[0]}'")
            else:
                print(f"  ✗ {category}: Not found")

        # Sample data for first few wells
        print(f"\nSample Data (First 3 wells):")
        print("-" * 50)
        sample_wells = valid_wells[:3] if len(valid_wells) >= 3 else valid_wells
        for well in sample_wells:
            print(f"\nWell: {well}")
            for i, label in enumerate(row_labels):
                if pd.notna(label) and label:
                    value = (
                        df_clean.loc[label, well] if well in df_clean.columns else "N/A"
                    )
                    if pd.notna(value):
                        print(f"  {label}: {value}")

        return {
            "report_name": report_name,
            "structure": {
                "row_count": len(row_labels),
                "well_count": len(valid_wells),
                "categories": [l for l in row_labels if pd.notna(l)],
                "wells": valid_wells,
            },
        }

    except Exception as e:
        print(f"Error analyzing {report_name}: {e}")
        import traceback

        traceback.print_exc()
        return None


def analyze_all_reports():
    """Analyze all go-by reports and document patterns"""

    # Base path for go-by reports
    base_path = Path(r"specs\modules\bsee\comprehensive-report-system\sub-specs\go_by")

    # Reports to analyze
    reports = {
        "Jack_field_data.xlsx": "Jack Field",
        "Julia_field_data.xlsx": "Julia Field",
        "St Malo_field_data.xlsx": "St Malo Field",
        "Stones_field_data.xlsx": "Stones Field",
    }

    all_analyses = {}

    for file_name, report_name in reports.items():
        file_path = base_path / file_name
        if file_path.exists():
            analysis = detailed_excel_analysis(file_path, report_name)
            if analysis:
                all_analyses[report_name] = analysis
        else:
            print(f"File not found: {file_path}")

    # Document common patterns
    print("\n" + "=" * 70)
    print("COMMON REPORT PATTERNS IDENTIFIED")
    print("=" * 70)

    # Collect all categories across reports
    all_categories = set()
    for analysis in all_analyses.values():
        all_categories.update(analysis["structure"]["categories"])

    print("\nCommon Data Categories Across All Reports:")
    sorted_categories = sorted([c for c in all_categories if c])
    for i, category in enumerate(sorted_categories, 1):
        # Count how many reports have this category
        count = sum(
            1 for a in all_analyses.values() if category in a["structure"]["categories"]
        )
        print(f"  {i:2d}. {category} (found in {count}/4 reports)")

    # Summary statistics
    print("\nReport Statistics:")
    for report_name, analysis in all_analyses.items():
        struct = analysis["structure"]
        print(f"  {report_name}:")
        print(f"    - Wells: {struct['well_count']}")
        print(f"    - Data Categories: {struct['row_count']}")

    return all_analyses


def create_report_template(analyses):
    """Create a template structure based on analysis"""

    print("\n" + "=" * 70)
    print("REPORT TEMPLATE STRUCTURE")
    print("=" * 70)

    template = {
        "field_report": {
            "metadata": {
                "field_name": "{{field_name}}",
                "report_date": "{{report_date}}",
                "data_source": "BSEE",
                "report_type": "Field Summary",
            },
            "field_summary": {
                "operator": "{{company}}",
                "water_depth_ft": "{{water_depth}}",
                "block_number": "{{block}}",
                "lease_number": "{{lease}}",
                "discovery_date": "{{discovery_date}}",
                "first_production": "{{first_production}}",
                "status": "{{status}}",
            },
            "production_summary": {
                "total_wells": "{{well_count}}",
                "producing_wells": "{{producing_count}}",
                "cumulative_oil_mmbbl": "{{cum_oil}}",
                "cumulative_gas_bcf": "{{cum_gas}}",
                "peak_production_bopd": "{{peak_prod}}",
                "current_production_bopd": "{{current_prod}}",
            },
            "well_details": {
                "headers": [
                    "Well Name",
                    "API Number",
                    "Spud Date",
                    "TD (ft)",
                    "Days to Drill",
                    "Completion Type",
                    "First Production",
                    "Peak Rate (bopd)",
                    "Cumulative (MMbbl)",
                    "Status",
                ],
                "data": "{{well_data_table}}",
            },
            "economics": {
                "estimated_reserves_mmbbl": "{{reserves}}",
                "recovery_factor": "{{recovery_factor}}",
                "field_life_years": "{{field_life}}",
            },
        }
    }

    print("\nProposed Template Structure:")
    print(json.dumps(template, indent=2))

    # Save template to file
    template_path = Path(
        r"tests\modules\bsee\analysis\comprehensive-report-system\results"
    )
    template_path.mkdir(parents=True, exist_ok=True)

    with open(template_path / "report_template.json", "w") as f:
        json.dump(template, f, indent=2)

    print(f"\nTemplate saved to: {template_path / 'report_template.json'}")

    return template


if __name__ == "__main__":
    analyses = analyze_all_reports()
    template = create_report_template(analyses)
    print("\nAnalysis complete!")
