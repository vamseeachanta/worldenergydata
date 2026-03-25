# ABOUTME: Runnable PHMSA FFS case study using synthetic incident data.
# ABOUTME: Demonstrates full workflow: load -> assess -> summarize -> narrative.

"""
PHMSA FFS Case Study Example
=============================

Demonstrates the PipelineSafetyWorkflow end-to-end using 20 synthetic
PHMSA-style incident records spanning 2015-2024.

Run:
    python -m worldenergydata.pipeline_safety.examples.phmsa_ffs_case_study
"""

import pandas as pd

from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow

# ---------------------------------------------------------------------------
# Synthetic PHMSA incident dataset — 20 records, 2015-2024
# ---------------------------------------------------------------------------

_INCIDENTS = [
    # id, year, pipeline_type, defect_type, depth%, length_mm, od_mm, wt_mm,
    #   smys_mpa, maop_mpa, location
    {
        "incident_id": "INC-2015-001",
        "year": 2015,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 25.0,
        "length_mm": 120.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TX-Segment-A",
    },
    {
        "incident_id": "INC-2015-002",
        "year": 2015,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 55.0,
        "length_mm": 200.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TX-Segment-B",
    },
    {
        "incident_id": "INC-2016-001",
        "year": 2016,
        "pipeline_type": "hazardous_liquid",
        "defect_type": "corrosion",
        "depth_pct_wall": 40.0,
        "length_mm": 180.0,
        "pipe_od_mm": 406.4,
        "wall_thickness_mm": 12.7,
        "smys_mpa": 414.0,
        "maop_mpa": 5.516,
        "location": "OK-Segment-C",
    },
    {
        "incident_id": "INC-2016-002",
        "year": 2016,
        "pipeline_type": "gas_transmission",
        "defect_type": "weld",
        "depth_pct_wall": 20.0,
        "length_mm": 50.0,
        "pipe_od_mm": 508.0,
        "wall_thickness_mm": 11.13,
        "smys_mpa": 448.16,
        "maop_mpa": 7.24,
        "location": "KS-Segment-D",
    },
    {
        "incident_id": "INC-2017-001",
        "year": 2017,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 60.0,
        "length_mm": 250.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "LA-Segment-E",
    },
    {
        "incident_id": "INC-2017-002",
        "year": 2017,
        "pipeline_type": "hazardous_liquid",
        "defect_type": "mechanical",
        "depth_pct_wall": 15.0,
        "length_mm": 75.0,
        "pipe_od_mm": 406.4,
        "wall_thickness_mm": 12.7,
        "smys_mpa": 414.0,
        "maop_mpa": 5.516,
        "location": "NM-Segment-F",
    },
    {
        "incident_id": "INC-2018-001",
        "year": 2018,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 82.0,
        "length_mm": 300.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "MS-Segment-G",
    },
    {
        "incident_id": "INC-2018-002",
        "year": 2018,
        "pipeline_type": "gas_distribution",
        "defect_type": "third_party",
        "depth_pct_wall": 35.0,
        "length_mm": 100.0,
        "pipe_od_mm": 168.3,
        "wall_thickness_mm": 7.11,
        "smys_mpa": 241.32,
        "maop_mpa": 2.758,
        "location": "AL-Segment-H",
    },
    {
        "incident_id": "INC-2019-001",
        "year": 2019,
        "pipeline_type": "hazardous_liquid",
        "defect_type": "corrosion",
        "depth_pct_wall": 45.0,
        "length_mm": 160.0,
        "pipe_od_mm": 609.6,
        "wall_thickness_mm": 14.27,
        "smys_mpa": 448.16,
        "maop_mpa": 5.516,
        "location": "WY-Segment-I",
    },
    {
        "incident_id": "INC-2019-002",
        "year": 2019,
        "pipeline_type": "gas_transmission",
        "defect_type": "material",
        "depth_pct_wall": 18.0,
        "length_mm": 60.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "CO-Segment-J",
    },
    {
        "incident_id": "INC-2020-001",
        "year": 2020,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 70.0,
        "length_mm": 220.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "AR-Segment-K",
    },
    {
        "incident_id": "INC-2020-002",
        "year": 2020,
        "pipeline_type": "hazardous_liquid",
        "defect_type": "third_party",
        "depth_pct_wall": 28.0,
        "length_mm": 90.0,
        "pipe_od_mm": 406.4,
        "wall_thickness_mm": 12.7,
        "smys_mpa": 414.0,
        "maop_mpa": 5.516,
        "location": "ND-Segment-L",
    },
    {
        "incident_id": "INC-2021-001",
        "year": 2021,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 48.0,
        "length_mm": 175.0,
        "pipe_od_mm": 508.0,
        "wall_thickness_mm": 11.13,
        "smys_mpa": 448.16,
        "maop_mpa": 7.24,
        "location": "MT-Segment-M",
    },
    {
        "incident_id": "INC-2021-002",
        "year": 2021,
        "pipeline_type": "gas_distribution",
        "defect_type": "corrosion",
        "depth_pct_wall": 52.0,
        "length_mm": 140.0,
        "pipe_od_mm": 168.3,
        "wall_thickness_mm": 7.11,
        "smys_mpa": 241.32,
        "maop_mpa": 2.758,
        "location": "OH-Segment-N",
    },
    {
        "incident_id": "INC-2022-001",
        "year": 2022,
        "pipeline_type": "hazardous_liquid",
        "defect_type": "weld",
        "depth_pct_wall": 33.0,
        "length_mm": 110.0,
        "pipe_od_mm": 609.6,
        "wall_thickness_mm": 14.27,
        "smys_mpa": 448.16,
        "maop_mpa": 5.516,
        "location": "KY-Segment-O",
    },
    {
        "incident_id": "INC-2022-002",
        "year": 2022,
        "pipeline_type": "gas_transmission",
        "defect_type": "mechanical",
        "depth_pct_wall": 10.0,
        "length_mm": 45.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TN-Segment-P",
    },
    {
        "incident_id": "INC-2023-001",
        "year": 2023,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 65.0,
        "length_mm": 230.0,
        "pipe_od_mm": 508.0,
        "wall_thickness_mm": 11.13,
        "smys_mpa": 448.16,
        "maop_mpa": 7.24,
        "location": "IN-Segment-Q",
    },
    {
        "incident_id": "INC-2023-002",
        "year": 2023,
        "pipeline_type": "hazardous_liquid",
        "defect_type": "corrosion",
        "depth_pct_wall": 38.0,
        "length_mm": 130.0,
        "pipe_od_mm": 406.4,
        "wall_thickness_mm": 12.7,
        "smys_mpa": 414.0,
        "maop_mpa": 5.516,
        "location": "WI-Segment-R",
    },
    {
        "incident_id": "INC-2024-001",
        "year": 2024,
        "pipeline_type": "gas_distribution",
        "defect_type": "third_party",
        "depth_pct_wall": 22.0,
        "length_mm": 85.0,
        "pipe_od_mm": 168.3,
        "wall_thickness_mm": 7.11,
        "smys_mpa": 241.32,
        "maop_mpa": 2.758,
        "location": "IL-Segment-S",
    },
    {
        "incident_id": "INC-2024-002",
        "year": 2024,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 75.0,
        "length_mm": 280.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "MO-Segment-T",
    },
]


def main() -> None:
    """Run the PHMSA FFS case study and print results."""
    print("Loading PHMSA synthetic incident dataset...")
    df = pd.DataFrame(_INCIDENTS)
    print(f"  {len(df)} incidents loaded, years {df['year'].min()}-{df['year'].max()}")

    workflow = PipelineSafetyWorkflow()

    print("\nRunning batch FFS assessment (Modified B31G)...")
    report = workflow.generate_report(df, method="modified_b31g")
    print(f"  Assessment complete: {len(report)} results")

    print("\nVerdict summary:")
    summary = workflow.verdict_summary(report)
    for verdict, count in summary.items():
        print(f"  {verdict:<10}: {count}")

    print("\nCase Study Narrative:")
    print(workflow.case_study_narrative(report))


if __name__ == "__main__":
    main()
