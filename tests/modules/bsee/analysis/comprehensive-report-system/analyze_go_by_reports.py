"""
Analyze go-by Excel reports to understand structure and requirements
for the comprehensive report system.
"""

import os
from pathlib import Path

import pandas as pd


def analyze_excel_report(file_path, report_name):
    """Analyze Excel report structure and content"""
    print(f"\n{'='*60}")
    print(f"Analyzing {report_name}")
    print("=" * 60)

    try:
        # Load Excel file
        xl_file = pd.ExcelFile(file_path)
        sheet_names = xl_file.sheet_names

        print(f"Number of sheets: {len(sheet_names)}")
        print(f"Sheet names: {sheet_names}")

        report_structure = {"report_name": report_name, "sheets": {}}

        # Analyze each sheet
        for sheet in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet)

            print(f"\n--- Sheet: '{sheet}' ---")
            print(f"Dimensions: {df.shape[0]} rows x {df.shape[1]} columns")

            # Column analysis
            print(f"Columns ({len(df.columns)} total):")
            for i, col in enumerate(df.columns[:10], 1):
                dtype = str(df[col].dtype)
                null_count = df[col].isna().sum()
                print(f"  {i}. {col} ({dtype}) - {null_count} nulls")

            if len(df.columns) > 10:
                print(f"  ... and {len(df.columns) - 10} more columns")

            # Data types summary
            dtypes = df.dtypes.value_counts()
            print(f"\nData types distribution:")
            for dtype, count in dtypes.items():
                print(f"  - {dtype}: {count} columns")

            # Sample data
            print(f"\nFirst 3 rows preview:")
            print(df.head(3).to_string(max_cols=5))

            # Store structure
            report_structure["sheets"][sheet] = {
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": {str(k): v for k, v in df.dtypes.to_dict().items()},
                "has_nulls": df.isna().any().any(),
            }

        return report_structure

    except Exception as e:
        print(f"Error analyzing {report_name}: {e}")
        return None


def main():
    """Main analysis function"""
    # Base path for go-by reports
    base_path = Path(r"specs\modules\bsee\comprehensive-report-system\sub-specs\go_by")

    # Reports to analyze
    reports = {
        "Jack_field_data.xlsx": "Jack Field Report",
        "Julia_field_data.xlsx": "Julia Field Report",
        "St Malo_field_data.xlsx": "St Malo Field Report",
        "Stones_field_data.xlsx": "Stones Field Report",
    }

    all_structures = {}

    for file_name, report_name in reports.items():
        file_path = base_path / file_name
        if file_path.exists():
            structure = analyze_excel_report(file_path, report_name)
            if structure:
                all_structures[report_name] = structure
        else:
            print(f"File not found: {file_path}")

    # Find common patterns
    print("\n" + "=" * 60)
    print("COMMON PATTERNS ACROSS REPORTS")
    print("=" * 60)

    # Collect all sheet names
    all_sheets = set()
    for report in all_structures.values():
        all_sheets.update(report["sheets"].keys())

    print(f"\nUnique sheet names across all reports:")
    for sheet in sorted(all_sheets):
        reports_with_sheet = [
            name for name, struct in all_structures.items() if sheet in struct["sheets"]
        ]
        print(f"  - '{sheet}': found in {len(reports_with_sheet)} reports")
        if len(reports_with_sheet) < 4:
            print(f"    Reports: {', '.join(reports_with_sheet)}")

    # Common columns analysis
    print("\nAnalyzing common column patterns...")
    all_columns = {}
    for report_name, structure in all_structures.items():
        for sheet_name, sheet_data in structure["sheets"].items():
            for col in sheet_data["columns"]:
                if col not in all_columns:
                    all_columns[col] = []
                all_columns[col].append(f"{report_name}/{sheet_name}")

    # Most common columns
    common_cols = sorted(all_columns.items(), key=lambda x: len(x[1]), reverse=True)
    print("\nMost common columns across all sheets:")
    for col, locations in common_cols[:20]:
        print(f"  - '{col}': appears in {len(locations)} sheets")

    return all_structures


if __name__ == "__main__":
    structures = main()
    print("\n✅ Analysis complete!")
