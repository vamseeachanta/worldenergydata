"""
Script to generate the final comprehensive report with all enhanced tables and methodology documentation.
"""

import os
import pandas as pd
from datetime import datetime
from report_generator import (
    compile_comprehensive_report,
    save_report_to_file,
    export_analysis_data
)
from root_cause_analyzer import (
    load_actual_comparison_data
)
from enhanced_report_generator import (
    generate_enhanced_comprehensive_report
)


def main():
    """Generate comprehensive report with all enhanced features."""
    
    print("Loading comparison data...")
    comparison_data = load_actual_comparison_data()
    
    # Define comprehensive methodology data
    methodology_data = {
        'lease_method': {
            'approach': 'Timeline-based with gap analysis',
            'gap_threshold_drilling': 300,
            'gap_threshold_completion': 8,
            'data_sources': [
                'WAR main binary files (mv_war_main.bin)',
                'Boreholes data (mv_war_boreholes_view.bin)',
                'Properties data (mv_war_main_prop.bin)',
                'Lease CSV data'
            ],
            'processing_steps': [
                'Load pickle files and CSV data',
                'Match wells by API12',
                'Extract WAR timeline data',
                'Apply gap thresholds',
                'Calculate drilling and completion days',
                'Export to Excel'
            ]
        },
        'api12_method': {
            'approach': 'Milestone-based phase calculation',
            'framework': 'WellRigDays integration',
            'data_sources': [
                'Well data structure',
                'WellRigDays framework',
                'Directional surveys',
                'Borehole integration'
            ],
            'processing_steps': [
                'Access well objects through framework',
                'Extract milestone data',
                'Calculate DRL phases',
                'Extract completion phases',
                'Generate CSV outputs',
                'Create visualizations'
            ]
        }
    }
    
    print("Generating base comprehensive report with enhanced tables...")
    base_report = compile_comprehensive_report(comparison_data, methodology_data)
    
    # Save base report
    base_output_path = "results/comprehensive_report_with_enhanced_tables.md"
    os.makedirs(os.path.dirname(base_output_path), exist_ok=True)
    save_report_to_file(base_report, base_output_path)
    print(f"Base report saved to: {base_output_path}")
    print(f"Base report length: {len(base_report)} characters")
    
    print("\nGenerating enhanced report with root cause integration...")
    enhanced_report = generate_enhanced_comprehensive_report()
    
    # Save enhanced report
    enhanced_output_path = "results/final_enhanced_comprehensive_report.md"
    save_report_to_file(enhanced_report, enhanced_output_path)
    print(f"Enhanced report saved to: {enhanced_output_path}")
    print(f"Enhanced report length: {len(enhanced_report)} characters")
    
    # Export analysis data to JSON
    json_output_path = "results/comprehensive_analysis_data.json"
    export_analysis_data(comparison_data, methodology_data, json_output_path)
    print(f"\nAnalysis data exported to: {json_output_path}")
    
    # Create summary statistics
    print("\n" + "="*60)
    print("REPORT GENERATION SUMMARY")
    print("="*60)
    print(f"Total wells analyzed: {len(comparison_data)}")
    print(f"Fields covered: {len(comparison_data['field_name'].unique())}")
    print(f"Average drilling difference: {comparison_data['drilling_diff'].mean():.1f} days")
    print(f"Average completion difference: {comparison_data['completion_diff'].mean():.1f} days")
    print(f"Wells with extreme differences (>200 days): {len(comparison_data[comparison_data['total_diff'] > 200])}")
    print(f"Report generation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    return base_report, enhanced_report


if __name__ == "__main__":
    base_report, enhanced_report = main()