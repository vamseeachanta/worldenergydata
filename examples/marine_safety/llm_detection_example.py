#!/usr/bin/env python3
"""
LLM-Based Incident Detection Example

Demonstrates how to use LLM-based detection for marine safety incidents
with the HatchMaloperationAnalyzer.

This example shows:
- Basic LLM detection configuration
- Single incident classification
- Confidence score interpretation
- Detection method identification
- Comparison with regex detection
"""

import pandas as pd
from worldenergydata.modules.marine_safety.analysis import HatchMaloperationAnalyzer


def main():
    print("=" * 80)
    print("LLM-BASED INCIDENT DETECTION EXAMPLE")
    print("=" * 80)
    print()

    # Sample incidents
    incidents = [
        {
            'incident_id': 'HATCH-2024-001',
            'description': 'Engine room flooding occurred when the access hatch seal failed during heavy seas.',
            'severity': 'Serious',
            'fatalities': 0,
            'injuries': 2
        },
        {
            'incident_id': 'HATCH-2024-002',
            'description': 'Crew member injured when deck access cover was not properly secured.',
            'severity': 'Moderate',
            'fatalities': 0,
            'injuries': 1
        },
        {
            'incident_id': 'NAV-2024-001',
            'description': 'Vessel ran aground due to navigation error in poor visibility.',
            'severity': 'Serious',
            'fatalities': 0,
            'injuries': 0
        },
        {
            'incident_id': 'HATCH-2024-003',
            'description': 'Machinery compartment water ingress after maintenance hatch left unsealed.',
            'severity': 'Critical',
            'fatalities': 0,
            'injuries': 3
        }
    ]

    # Example 1: Basic LLM Detection
    print("1. BASIC LLM DETECTION (Recommended)")
    print("-" * 80)
    print()

    # Initialize analyzer with LLM (default configuration)
    llm_analyzer = HatchMaloperationAnalyzer(
        use_llm=True,
        llm_confidence_threshold=0.7,
        fallback_to_regex=True
    )

    print("Configuration:")
    print(f"  - LLM Model: facebook/bart-large-mnli")
    print(f"  - Confidence Threshold: 0.7")
    print(f"  - Fallback to Regex: Enabled")
    print()

    for incident in incidents:
        print(f"Analyzing: {incident['incident_id']}")
        print(f"Description: {incident['description'][:70]}...")

        result = llm_analyzer.is_hatch_maloperation_incident(incident)

        print(f"  ✓ Is hatch incident: {result['is_hatch_incident']}")
        print(f"  ✓ Confidence: {result['llm_confidence']:.2%}")
        print(f"  ✓ Detection method: {result['detection_method']}")
        print(f"  ✓ Reasoning: {result.get('llm_reasoning', 'N/A')[:80]}...")
        print()

    # Example 2: Batch Processing
    print("\n2. BATCH PROCESSING WITH LLM")
    print("-" * 80)
    print()

    incidents_df = pd.DataFrame(incidents)
    print(f"Processing {len(incidents_df)} incidents in batch...")

    results_df = llm_analyzer.detect_incidents(incidents_df)

    print("\nResults Summary:")
    print(results_df[['incident_id', 'is_hatch_incident', 'llm_confidence', 'detection_method']])

    # Statistics
    print("\nDetection Statistics:")
    hatch_count = results_df['is_hatch_incident'].sum()
    print(f"  - Total incidents: {len(results_df)}")
    print(f"  - Hatch incidents detected: {hatch_count}")
    print(f"  - Detection rate: {hatch_count / len(results_df):.1%}")
    print(f"  - Average confidence: {results_df['llm_confidence'].mean():.2%}")

    # Example 3: LLM vs Regex Comparison
    print("\n3. LLM vs REGEX COMPARISON")
    print("-" * 80)
    print()

    # Regex-only analyzer
    regex_analyzer = HatchMaloperationAnalyzer(use_llm=False)

    comparison_data = []
    for incident in incidents:
        llm_result = llm_analyzer.is_hatch_maloperation_incident(incident)
        regex_result = regex_analyzer.is_hatch_maloperation_incident(incident)

        comparison_data.append({
            'incident_id': incident['incident_id'],
            'llm_detected': llm_result['is_hatch_incident'],
            'regex_detected': regex_result,
            'llm_confidence': llm_result['llm_confidence'],
            'agreement': llm_result['is_hatch_incident'] == regex_result
        })

    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df)

    agreement_rate = comparison_df['agreement'].mean()
    print(f"\nAgreement rate: {agreement_rate:.1%}")

    # Show discrepancies
    discrepancies = comparison_df[~comparison_df['agreement']]
    if len(discrepancies) > 0:
        print(f"\nDiscrepancies found: {len(discrepancies)}")
        for _, row in discrepancies.iterrows():
            incident = next(i for i in incidents if i['incident_id'] == row['incident_id'])
            print(f"\n  {row['incident_id']}:")
            print(f"    Description: {incident['description'][:70]}...")
            print(f"    LLM: {row['llm_detected']} (confidence: {row['llm_confidence']:.2%})")
            print(f"    Regex: {row['regex_detected']}")

    # Example 4: Confidence Filtering
    print("\n4. CONFIDENCE-BASED FILTERING")
    print("-" * 80)
    print()

    results_df['confidence_tier'] = pd.cut(
        results_df['llm_confidence'],
        bins=[0, 0.5, 0.7, 0.85, 1.0],
        labels=['low', 'medium', 'high', 'very_high']
    )

    print("Incidents by Confidence Tier:")
    tier_summary = results_df.groupby('confidence_tier').agg({
        'incident_id': 'count',
        'is_hatch_incident': 'sum',
        'llm_confidence': 'mean'
    }).round(3)
    print(tier_summary)

    # Example 5: Model Comparison
    print("\n5. DIFFERENT MODEL COMPARISON")
    print("-" * 80)
    print()

    models_to_test = [
        ("BART (default)", "facebook/bart-large-mnli"),
        ("DistilBERT (fast)", "distilbert-base-uncased-mnli"),
    ]

    print("Testing incident HATCH-2024-001 with different models:")
    test_incident = incidents[0]
    print(f"Description: {test_incident['description']}\n")

    for model_name, model_id in models_to_test:
        try:
            analyzer = HatchMaloperationAnalyzer(
                use_llm=True,
                llm_model_name=model_id,
                llm_confidence_threshold=0.7
            )

            result = analyzer.is_hatch_maloperation_incident(test_incident)

            print(f"{model_name}:")
            print(f"  - Detected: {result['is_hatch_incident']}")
            print(f"  - Confidence: {result['llm_confidence']:.2%}")
            print()
        except Exception as e:
            print(f"{model_name}: Error - {str(e)}\n")

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  ✓ LLM detection provides confidence scores and reasoning")
    print("  ✓ Hybrid mode (LLM + regex) offers best accuracy")
    print("  ✓ Batch processing is efficient for large datasets")
    print("  ✓ Different models offer speed vs accuracy tradeoffs")
    print("\nFor more details, see:")
    print("  - docs/modules/marine_safety/LLM_INTEGRATION_GUIDE.md")
    print("  - docs/modules/marine_safety/INCIDENT_CAUSE_ANALYSIS_MODULE.md")


if __name__ == "__main__":
    import os
    if not os.environ.get("WORLDENERGYDATA_RUN_LLM_EXAMPLES"):
        print("Skipped: set WORLDENERGYDATA_RUN_LLM_EXAMPLES=1 to run LLM examples (downloads large models).")
        raise SystemExit(0)
    main()
