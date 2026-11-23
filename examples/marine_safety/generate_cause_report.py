#!/usr/bin/env python
# ABOUTME: Example script demonstrating HTML cause analysis report generation
# ABOUTME: Generates a sample report with realistic incident data and filters

from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from worldenergydata.modules.marine_safety.analysis.cause_report import (
    CauseAnalysisReport,
    ReportFilters,
)
from worldenergydata.modules.marine_safety.constants import (
    CauseCategory,
    SeverityLevel,
)


def generate_sample_incident_data(count=50):
    """Generate realistic sample incident data."""
    incidents = []
    base_date = datetime(2024, 1, 1)

    incident_types = [
        "Flooding",
        "Grounding",
        "Collision",
        "Fire",
        "Equipment Failure",
        "Personnel Injury",
    ]

    vessel_names = [
        "Ocean Explorer",
        "Deep Sea Pioneer",
        "Gulf Trader",
        "Atlantic Star",
        "Pacific Navigator",
        "Northern Venture",
        "Southern Cross",
        "Eastern Spirit",
        "Western Pride",
        "Maritime Crown",
    ]

    locations = [
        "Gulf of Mexico",
        "North Sea",
        "Caribbean Sea",
        "Pacific Ocean",
        "Atlantic Ocean",
        "Mediterranean Sea",
    ]

    descriptions_templates = [
        "Vessel experienced {} due to equipment malfunction",
        "Incident involving {} caused by human error",
        "Weather-related {} resulting in structural damage",
        "Operational {} with hatch opening maloperation",
        "Safety incident involving {} and improper procedures",
        "Critical {} requiring emergency response with hatch seal failure",
        "Minor {} with no significant damage",
        "Severe {} requiring evacuation with hatch mechanism failure",
    ]

    cause_categories = [
        CauseCategory.HUMAN_ERROR,
        CauseCategory.EQUIPMENT_FAILURE,
        CauseCategory.MAINTENANCE_ISSUE,
        CauseCategory.WEATHER,
        CauseCategory.PROCEDURAL,
        CauseCategory.TRAINING,
    ]

    severity_levels = [
        SeverityLevel.MINIMAL,
        SeverityLevel.MINOR,
        SeverityLevel.MODERATE,
        SeverityLevel.SERIOUS,
        SeverityLevel.CATASTROPHIC,
    ]

    for i in range(count):
        incident_type = incident_types[i % len(incident_types)]
        description_template = descriptions_templates[i % len(descriptions_templates)]

        incidents.append(
            {
                "incident_id": f"INC-2024-{i+1:04d}",
                "date": base_date + timedelta(days=i * 7),
                "incident_type": incident_type,
                "cause_category": cause_categories[i % len(cause_categories)],
                "severity": severity_levels[i % len(severity_levels)],
                "vessel_name": vessel_names[i % len(vessel_names)],
                "location": locations[i % len(locations)],
                "description": description_template.format(incident_type.lower()),
                "fatalities": 1 if i % 15 == 0 else 0,
                "injuries": i % 4,
                "investigation_complete": True,
            }
        )

    return incidents


def main():
    """Generate example HTML reports."""
    print("Generating sample incident data...")
    incidents = generate_sample_incident_data(count=50)

    # Create output directory
    output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(exist_ok=True)

    # Example 1: Full report with all incidents
    print("\n1. Generating full report with all incidents...")
    report1 = CauseAnalysisReport(
        incidents, title="Marine Safety Incident Analysis - Full Report 2024"
    )
    output_file1 = output_dir / "full_cause_analysis_report.html"
    report1.generate_html(output_file1)
    print(f"   ✓ Generated: {output_file1}")
    print(f"   Total incidents: {len(report1.incidents)}")

    # Example 2: Filtered report - Human error only
    print("\n2. Generating filtered report - Human Error incidents only...")
    filters2 = ReportFilters(cause_categories=[CauseCategory.HUMAN_ERROR])
    report2 = CauseAnalysisReport(
        incidents, title="Human Error Incident Analysis", filters=filters2
    )
    output_file2 = output_dir / "human_error_report.html"
    report2.generate_html(output_file2)
    print(f"   ✓ Generated: {output_file2}")
    print(f"   Filtered incidents: {len(report2.incidents)}")

    # Example 3: Filtered report - Serious incidents in Q1 2024
    print("\n3. Generating filtered report - Serious incidents Q1 2024...")
    filters3 = ReportFilters(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 31),
        min_severity=SeverityLevel.SERIOUS,
    )
    report3 = CauseAnalysisReport(
        incidents, title="Q1 2024 Serious Incidents Analysis", filters=filters3
    )
    output_file3 = output_dir / "q1_serious_incidents_report.html"
    report3.generate_html(output_file3)
    print(f"   ✓ Generated: {output_file3}")
    print(f"   Filtered incidents: {len(report3.incidents)}")

    # Example 4: Combined filters - Equipment failures, moderate+, first half 2024
    print("\n4. Generating filtered report - Equipment failures (moderate+), H1 2024...")
    filters4 = ReportFilters(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        cause_categories=[CauseCategory.EQUIPMENT_FAILURE, CauseCategory.MAINTENANCE_ISSUE],
        min_severity=SeverityLevel.MODERATE,
    )
    report4 = CauseAnalysisReport(
        incidents, title="H1 2024 Equipment-Related Incidents (Moderate+)", filters=filters4
    )
    output_file4 = output_dir / "equipment_failures_h1_report.html"
    report4.generate_html(output_file4)
    print(f"   ✓ Generated: {output_file4}")
    print(f"   Filtered incidents: {len(report4.incidents)}")

    print("\n" + "=" * 70)
    print("✓ All example reports generated successfully!")
    print("=" * 70)
    print(f"\nReports saved to: {output_dir.absolute()}")
    print("\nGenerated reports:")
    print("  1. full_cause_analysis_report.html - Complete incident dataset")
    print("  2. human_error_report.html - Human error incidents only")
    print("  3. q1_serious_incidents_report.html - Q1 serious+ incidents")
    print("  4. equipment_failures_h1_report.html - Equipment issues, H1 2024")
    print("\nOpen any HTML file in a web browser to view interactive reports.")


if __name__ == "__main__":
    main()
