import pandas as pd
import numpy as np
from datetime import datetime
import os

print('=== Task 3.1-3.6: Advanced Comparison Analysis Engine ===')

# Read the data generated from Task 2
results_dir = 'tests/modules/bsee/analysis/2025-08-05-multiple-wells-comparison-test/results'
lease_files = [f for f in os.listdir(results_dir) if f.startswith('lease_data_122_wells_')]
api12_files = [f for f in os.listdir(results_dir) if f.startswith('api12_data_122_wells_')]

if lease_files and api12_files:
    latest_lease = sorted(lease_files)[-1]
    latest_api12 = sorted(api12_files)[-1]
    
    lease_data = pd.read_csv(f'{results_dir}/{latest_lease}')
    api12_data = pd.read_csv(f'{results_dir}/{latest_api12}')
    
    print(f'PASS: Loaded lease data: {len(lease_data)} wells')
    print(f'PASS: Loaded API12 data: {len(api12_data)} wells')
else:
    print('ERROR: No data files found')
    exit(1)

# Task 3.3-3.6: Perform comprehensive comparison
print('\n--- Task 3.3-3.6: Performing Advanced Comparison ---')

# Merge data on API12
comparison = pd.merge(lease_data, api12_data, on='API12', suffixes=('_lease', '_api12'))

# Rename columns for consistency
comparison = comparison.rename(columns={
    'Well_Name_lease': 'Well_Name',
    'Drilling_Days_lease': 'Lease_Drilling_Days',
    'Drilling_Days_api12': 'API12_Drilling_Days',
    'Completion_Days_lease': 'Lease_Completion_Days',
    'Completion_Days_api12': 'API12_Completion_Days'
})

# Calculate differences
comparison['Drilling_Diff'] = comparison['API12_Drilling_Days'] - comparison['Lease_Drilling_Days']
comparison['Completion_Diff'] = comparison['API12_Completion_Days'] - comparison['Lease_Completion_Days']

# Calculate percentage differences
comparison['Drilling_Pct_Diff'] = (comparison['Drilling_Diff'] / comparison['Lease_Drilling_Days']) * 100
comparison['Completion_Pct_Diff'] = (comparison['Completion_Diff'] / comparison['Lease_Completion_Days']) * 100

# Advanced outlier detection
outlier_flags = []
for idx, row in comparison.iterrows():
    flags = []
    
    # Absolute difference outliers
    if abs(row['Drilling_Diff']) > 10:
        flags.append('drilling_absolute_outlier')
    if abs(row['Completion_Diff']) > 5:
        flags.append('completion_absolute_outlier')
    
    # Percentage difference outliers
    if abs(row['Drilling_Pct_Diff']) > 25:
        flags.append('drilling_percentage_outlier')
    if abs(row['Completion_Pct_Diff']) > 30:
        flags.append('completion_percentage_outlier')
    
    outlier_flags.append(','.join(flags) if flags else 'none')

comparison['Outlier_Flags'] = outlier_flags

# Status determination with advanced logic
def determine_status(row):
    drilling_diff = abs(row['Drilling_Diff'])
    completion_diff = abs(row['Completion_Diff'])
    has_outliers = row['Outlier_Flags'] != 'none'
    outlier_count = len([f for f in row['Outlier_Flags'].split(',') if f != 'none'])
    
    # ERROR: Multiple outlier flags or very large differences
    if outlier_count >= 3 or drilling_diff > 15 or completion_diff > 8:
        return 'ERROR'
    # REVIEW: Some outlier flags or moderate differences
    elif has_outliers or drilling_diff > 5 or completion_diff > 3:
        return 'REVIEW'
    # OK: Minimal differences
    else:
        return 'OK'

comparison['Status'] = comparison.apply(determine_status, axis=1)

# Statistical analysis
drilling_correlation = np.corrcoef(
    comparison['Lease_Drilling_Days'], 
    comparison['API12_Drilling_Days']
)[0, 1]
completion_correlation = np.corrcoef(
    comparison['Lease_Completion_Days'], 
    comparison['API12_Completion_Days']
)[0, 1]

print(f'PASS: Advanced comparison completed for {len(comparison)} wells')
print(f'  - OK status: {len(comparison[comparison["Status"] == "OK"])} wells')
print(f'  - REVIEW status: {len(comparison[comparison["Status"] == "REVIEW"])} wells')
print(f'  - ERROR status: {len(comparison[comparison["Status"] == "ERROR"])} wells')
print(f'  - Drilling correlation: {drilling_correlation:.3f}')
print(f'  - Completion correlation: {completion_correlation:.3f}')
print(f'  - Mean drilling diff: {comparison["Drilling_Diff"].mean():.1f} days')
print(f'  - Mean completion diff: {comparison["Completion_Diff"].mean():.1f} days')

# Export results
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
comparison_output = f'{results_dir}/advanced_comparison_results_122_wells_{timestamp}.csv'
stats_output = f'{results_dir}/statistical_summary_122_wells_{timestamp}.json'

comparison.to_csv(comparison_output, index=False)

# Export statistical summary
stats_dict = {
    'total_wells': len(comparison),
    'analysis_timestamp': timestamp,
    'drilling_days_analysis': {
        'mean_difference': float(comparison['Drilling_Diff'].mean()),
        'std_difference': float(comparison['Drilling_Diff'].std()),
        'correlation': float(drilling_correlation)
    },
    'completion_days_analysis': {
        'mean_difference': float(comparison['Completion_Diff'].mean()),
        'std_difference': float(comparison['Completion_Diff'].std()),
        'correlation': float(completion_correlation)
    },
    'status_distribution': {
        'OK': int(len(comparison[comparison['Status'] == 'OK'])),
        'REVIEW': int(len(comparison[comparison['Status'] == 'REVIEW'])),
        'ERROR': int(len(comparison[comparison['Status'] == 'ERROR']))
    }
}

import json
with open(stats_output, 'w') as f:
    json.dump(stats_dict, f, indent=2)

print(f'\nSUCCESS: Task 3 Completed!')
print(f'  - Advanced comparison: {comparison_output}')
print(f'  - Statistical summary: {stats_output}')
print(f'  - Ready for Task 4: Strategic Report Generation')