"""
Enhanced report generator that combines comprehensive analysis with root cause findings.
"""

import json
import os
from datetime import datetime

from report_generator import compile_comprehensive_report
from root_cause_analyzer import (
    generate_comprehensive_root_cause_analysis,
    load_actual_comparison_data,
)


def generate_enhanced_comprehensive_report() -> str:
    """
    Generate enhanced comprehensive report with root cause analysis integration.

    Returns:
        str: Enhanced comprehensive markdown report
    """
    # Load data and generate analyses
    comparison_data = load_actual_comparison_data()
    root_cause_analysis = generate_comprehensive_root_cause_analysis()

    methodology_data = {
        "lease_method": {
            "approach": "Timeline-based with gap analysis (300-day drilling, 8-day completion thresholds)",
            "gap_threshold_drilling": 300,
            "gap_threshold_completion": 8,
            "data_sources": [
                "WAR main binary files",
                "Boreholes data",
                "Properties data",
                "Lease CSV",
            ],
        },
        "api12_method": {
            "approach": "Milestone-based phase calculation through WellRigDays framework",
            "framework": "WellRigDays integration",
            "data_sources": [
                "Structured well data",
                "WellRigDays framework",
                "Directional surveys",
                "Borehole integration",
            ],
        },
    }

    # Generate base comprehensive report
    base_report = compile_comprehensive_report(comparison_data, methodology_data)

    # Extract root cause findings
    synthesis = root_cause_analysis["synthesized_findings"]
    drilling_analysis = root_cause_analysis["drilling_pattern_analysis"]
    completion_analysis = root_cause_analysis["completion_pattern_analysis"]
    case_studies = root_cause_analysis["case_study_validation"]["case_studies"]

    # Create enhanced report with additional root cause sections
    enhanced_sections = f"""
## Deep Root Cause Analysis

Based on comprehensive pattern analysis and case study validation, the following root causes have been identified:

### Primary Root Causes

{chr(10).join(f'#### {i+1}. {cause["cause"]} (Impact: {cause["impact"]})' + chr(10) +
              f'**Evidence**: {cause["evidence"]}' + chr(10) +
              f'**Mechanism**: {cause["mechanism"]}' + chr(10) for i, cause in enumerate(synthesis['primary_root_causes']))}

### Quantified Impact Analysis

- **Wells with Extreme Drilling Differences (>200 days)**: {synthesis['quantified_impact']['extreme_drilling_differences']} wells
- **Wells with Negative Drilling Differences**: {synthesis['quantified_impact']['negative_drilling_differences']} wells
- **Wells with Zero API12 Completion Days**: {synthesis['quantified_impact']['api12_zero_completions']} wells
- **Wells with High Completion Differences**: {synthesis['quantified_impact']['high_completion_differences']} wells
- **Total Dataset**: {synthesis['quantified_impact']['total_wells_analyzed']} wells across {synthesis['quantified_impact']['fields_affected']} fields

### Pattern Analysis Findings

#### Drilling Day Patterns

**Categorization of Wells by Drilling Differences:**
- **Extreme High (>200 days)**: {drilling_analysis['categorization']['extreme_high']} wells
- **High (50-200 days)**: {drilling_analysis['categorization']['high']} wells
- **Moderate (-50 to 50 days)**: {drilling_analysis['categorization']['moderate']} wells
- **Negative (<-50 days)**: {drilling_analysis['categorization']['negative']} wells

**Statistical Analysis:**
- **Overall Mean**: {drilling_analysis['statistical_analysis']['overall_mean']:.2f} days
- **Standard Deviation**: {drilling_analysis['statistical_analysis']['overall_std']:.2f} days
- **Skewness**: {drilling_analysis['statistical_analysis']['skewness']:.3f} (indicates distribution asymmetry)
- **Kurtosis**: {drilling_analysis['statistical_analysis']['kurtosis']:.3f} (indicates tail heaviness)

#### Completion Day Patterns

**Zero Completion Analysis:**
- **API12 Method Zero Completion Wells**: {completion_analysis['zero_completion_analysis']['api12_zero_wells']} wells
- **Lease Method Zero Completion Wells**: {completion_analysis['zero_completion_analysis']['lease_zero_wells']} wells
- **Wells with Zero API12 Completions**: {', '.join(completion_analysis['zero_completion_analysis']['api12_zero_wells_list'])}

**Completion Difference Categorization:**
- **High Positive (>50 days)**: {completion_analysis['categorization']['high_positive']} wells
- **Moderate Positive (0-50 days)**: {completion_analysis['categorization']['moderate_positive']} wells
- **Negative Differences**: {completion_analysis['categorization']['negative']} wells
- **Zero Differences**: {completion_analysis['categorization']['zero_diff']} wells

### Case Study Deep Dive

{chr(10).join(f'#### {study["case_name"]}' + chr(10) +
              f'**API12**: {study["api12"]} | **Total Difference**: {study["total_difference"]} days' + chr(10) +
              f'**Drilling Analysis**: Lease={study["drilling_analysis"]["lease_days"]}d, API12={study["drilling_analysis"]["api12_days"]}d, Diff={study["drilling_analysis"]["difference"]}d' +
              (f' (Ratio: {study["drilling_analysis"]["ratio"]:.1f}:1)' if "ratio" in study["drilling_analysis"] else '') + chr(10) +
              f'**Completion Analysis**: Lease={study["completion_analysis"]["lease_days"]}d, API12={study["completion_analysis"]["api12_days"]}d, Diff={study["completion_analysis"]["difference"]}d' + chr(10) +
              f'**Root Cause Hypothesis**:' + chr(10) +
              chr(10).join(f'- {hyp}' for hyp in study["root_cause_hypothesis"]) + chr(10) +
              f'**Validation Evidence**:' + chr(10) +
              chr(10).join(f'- {ev}' for ev in study["validation_evidence"]) + chr(10)
              for study in case_studies)}

### Contributing Factors

{chr(10).join(f'• {factor}' for factor in synthesis['contributing_factors'])}

## Methodology Deep Dive

### Timeline Construction Fundamental Differences

**Lease Method Approach:**
- **Data Source**: Individual WAR records with precise start/end timestamps
- **Logic**: Direct date arithmetic with custom gap handling
- **Strengths**: Captures actual drilling interruptions, uses precise timestamps, handles complex timelines
- **Weaknesses**: Dependent on WAR data completeness, may include non-drilling activities, uses fixed gap thresholds

**API12 Method Approach:**
- **Data Source**: WellRigDays framework processed milestone data
- **Logic**: Framework-calculated milestone durations and phase aggregation
- **Strengths**: Consistent methodology, framework validation, specialized processing
- **Weaknesses**: May smooth out interruptions, framework dependency, less granular

**Fundamental Difference**: Lease method reconstructs timelines from raw data while API12 method uses pre-processed milestone phases

### Gap Handling Philosophy Comparison

| Aspect | Lease Method | API12 Method |
|--------|--------------|--------------|
| **Drilling Threshold** | 300 days (fixed empirical) | Framework-determined |
| **Completion Threshold** | 8 days (fixed empirical) | WellRigDays milestone logic |
| **Logic Basis** | Based on typical drilling interruption patterns | Integrated framework calculation |
| **Interruption Handling** | Explicit timeline restart after major gaps | May not explicitly handle long gaps |
| **Rationale** | Empirical analysis of drilling operations | Standardized framework methodology |

### Data Granularity Impact Analysis

**Lease Method:**
- **Processing Level**: WAR record level with individual activity timestamps
- **Detail**: Sequential timeline analysis of start/end dates
- **Accuracy**: High for wells with complete WAR data
- **Limitation**: Quality dependent on WAR record completeness

**API12 Method:**
- **Processing Level**: Milestone phase level with aggregated durations
- **Detail**: Framework-calculated phase summaries
- **Accuracy**: Depends on WellRigDays milestone calculation quality
- **Limitation**: Less granular, potential smoothing of interruptions

## Validation Summary

### Hypothesis Confirmation

The analysis confirms several key hypotheses about the methodological differences:

1. **Gap Threshold Impact Confirmed**: Extreme drilling ratios (8:1 in highest difference case) confirm that fixed gap thresholds capture interruptions not reflected in milestone calculations

2. **Timeline Complexity Correlation**: Wells with complex drilling histories show amplified differences between methods, validating the hypothesis that methodological differences scale with operational complexity

3. **Method Convergence for Simple Wells**: Low-complexity wells (like St Malo 001 with 2-day total difference) show that both methods converge for straightforward drilling operations

### Additional Evidence

4. **Field-Specific Patterns**: Stones field consistently shows highest differences, suggesting geological/operational factors influence methodology sensitivity

5. **Completion Method Independence**: Completion day differences appear independent of drilling complexity, indicating separate methodological issues

6. **Framework vs Custom Logic**: Systematic differences between standardized framework processing and custom gap-based logic are evident across all analysis dimensions

## Strategic Implications

### For Industry Practice

1. **Method Selection**: Simple wells can use either method; complex wells require careful method selection based on analysis objectives

2. **Data Quality Importance**: WAR data completeness critical for lease method accuracy; milestone calculation quality essential for API12 method

3. **Threshold Optimization**: Fixed gap thresholds may need field-specific or well-specific calibration for optimal accuracy

### For Future Development

1. **Hybrid Approach**: Combine WAR granularity with framework standardization for optimal accuracy and consistency

2. **Adaptive Thresholds**: Implement machine learning or field-specific algorithms for optimal gap threshold determination

3. **Uncertainty Quantification**: Develop confidence intervals for both methods based on data quality and well complexity indicators

---

*Enhanced analysis completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} integrating comprehensive statistical analysis, root cause investigation, and case study validation.*
"""

    # Insert enhanced sections before the conclusion
    conclusion_marker = "## Conclusion"
    if conclusion_marker in base_report:
        parts = base_report.split(conclusion_marker)
        enhanced_report = (
            parts[0] + enhanced_sections + "\n" + conclusion_marker + parts[1]
        )
    else:
        enhanced_report = base_report + enhanced_sections

    return enhanced_report


if __name__ == "__main__":
    # Generate and save enhanced report
    enhanced_report = generate_enhanced_comprehensive_report()

    output_path = "results/enhanced_comprehensive_report.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(enhanced_report)

    print(f"Enhanced comprehensive report saved to: {output_path}")
    print(f"Report length: {len(enhanced_report)} characters")
