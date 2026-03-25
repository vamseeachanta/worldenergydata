#!/usr/bin/env python3
"""
Batch LLM Processing Example for Large Datasets

Demonstrates efficient batch processing of large marine incident datasets
using LLM-based detection with optimization strategies.

This example shows:
- Large dataset processing techniques
- Memory optimization strategies
- Performance monitoring
- Result export and analysis
- Error handling for production use
"""

import pandas as pd
import time
from typing import Dict, Any
from worldenergydata.modules.marine_safety.analysis import HatchMaloperationAnalyzer


def simulate_large_dataset(size: int = 1000) -> pd.DataFrame:
    """Generate simulated incident dataset for demonstration."""
    import random

    incident_templates = [
        "Engine room hatch seal failed causing flooding in heavy seas",
        "Deck access cover maloperation leading to personnel injury",
        "Machinery space flooding after hatch left unsealed during maintenance",
        "Navigation error caused vessel grounding in foggy conditions",
        "Equipment failure in main engine room requiring repairs",
        "Access hatch mechanism failed during routine operations",
        "Watertight door improperly secured leading to water ingress",
        "Storm damage to vessel superstructure and deck equipment",
        "Fire in galley due to electrical malfunction",
        "Crew member fell from deck access point that wasn't properly secured"
    ]

    severities = ['Minor', 'Moderate', 'Serious', 'Critical', 'Catastrophic']

    incidents = []
    for i in range(size):
        incidents.append({
            'incident_id': f'INC-{i+1:05d}',
            'description': random.choice(incident_templates),
            'severity': random.choice(severities),
            'fatalities': random.choices([0, 1, 2], weights=[90, 7, 3])[0],
            'injuries': random.choices([0, 1, 2, 3], weights=[70, 20, 7, 3])[0],
            'date': f'2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}'
        })

    return pd.DataFrame(incidents)


def process_with_monitoring(
    analyzer: HatchMaloperationAnalyzer,
    incidents_df: pd.DataFrame
) -> Dict[str, Any]:
    """Process incidents with performance monitoring."""

    print("Processing Configuration:")
    print(f"  - Total incidents: {len(incidents_df):,}")
    print(f"  - LLM enabled: {analyzer.use_llm}")
    print(f"  - Batch size: {analyzer.batch_size}")
    print(f"  - Model: {analyzer.llm_model_name if analyzer.use_llm else 'N/A'}")
    print()

    # Start processing
    start_time = time.time()

    try:
        results_df = analyzer.detect_incidents(incidents_df)

        processing_time = time.time() - start_time

        # Calculate metrics
        metrics = {
            'total_processed': len(results_df),
            'processing_time': processing_time,
            'incidents_per_second': len(results_df) / processing_time if processing_time > 0 else 0,
            'hatch_incidents_detected': results_df['is_hatch_incident'].sum(),
            'detection_rate': results_df['is_hatch_incident'].mean(),
            'avg_confidence': results_df['llm_confidence'].mean() if 'llm_confidence' in results_df else None,
            'llm_detections': (results_df['detection_method'] == 'llm').sum() if 'detection_method' in results_df else 0,
            'regex_detections': (results_df['detection_method'] == 'regex').sum() if 'detection_method' in results_df else 0,
            'hybrid_detections': (results_df['detection_method'] == 'llm+regex').sum() if 'detection_method' in results_df else 0
        }

        return {
            'success': True,
            'results': results_df,
            'metrics': metrics
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'processing_time': time.time() - start_time
        }


def main():
    print("=" * 80)
    print("BATCH LLM PROCESSING EXAMPLE")
    print("=" * 80)
    print()

    # Example 1: Standard Batch Processing
    print("1. STANDARD BATCH PROCESSING")
    print("-" * 80)
    print()

    # Generate test dataset
    print("Generating test dataset...")
    incidents_df = simulate_large_dataset(size=500)
    print(f"Generated {len(incidents_df)} incidents")
    print()

    # Initialize analyzer
    analyzer = HatchMaloperationAnalyzer(
        use_llm=True,
        llm_confidence_threshold=0.7,
        fallback_to_regex=True,
        batch_size=32
    )

    result = process_with_monitoring(analyzer, incidents_df)

    if result['success']:
        metrics = result['metrics']
        print("\nProcessing Results:")
        print(f"  ✓ Total processed: {metrics['total_processed']:,}")
        print(f"  ✓ Processing time: {metrics['processing_time']:.2f} seconds")
        print(f"  ✓ Speed: {metrics['incidents_per_second']:.1f} incidents/second")
        print(f"  ✓ Hatch incidents found: {metrics['hatch_incidents_detected']}")
        print(f"  ✓ Detection rate: {metrics['detection_rate']:.1%}")
        if metrics['avg_confidence']:
            print(f"  ✓ Average confidence: {metrics['avg_confidence']:.2%}")

        print("\nDetection Method Breakdown:")
        print(f"  - LLM only: {metrics['llm_detections']}")
        print(f"  - Regex only: {metrics['regex_detections']}")
        print(f"  - Hybrid (LLM+regex): {metrics['hybrid_detections']}")
    else:
        print(f"✗ Processing failed: {result['error']}")

    # Example 2: Large Dataset with Chunking
    print("\n2. LARGE DATASET PROCESSING (CHUNKED)")
    print("-" * 80)
    print()

    # Generate larger dataset
    print("Generating large test dataset...")
    large_incidents = simulate_large_dataset(size=2000)
    print(f"Generated {len(large_incidents)} incidents")
    print()

    # Process in chunks to manage memory
    chunk_size = 500
    all_results = []

    print(f"Processing in chunks of {chunk_size}...")

    for i in range(0, len(large_incidents), chunk_size):
        chunk = large_incidents.iloc[i:i+chunk_size]
        print(f"\nProcessing chunk {i//chunk_size + 1} ({len(chunk)} incidents)...")

        chunk_result = process_with_monitoring(analyzer, chunk)

        if chunk_result['success']:
            all_results.append(chunk_result['results'])
            print(f"  ✓ Chunk processed: {chunk_result['metrics']['incidents_per_second']:.1f} inc/sec")
        else:
            print(f"  ✗ Chunk failed: {chunk_result['error']}")

    # Combine results
    if all_results:
        combined_results = pd.concat(all_results, ignore_index=True)
        print(f"\nTotal Results:")
        print(f"  - Total incidents: {len(combined_results):,}")
        print(f"  - Hatch incidents: {combined_results['is_hatch_incident'].sum()}")
        print(f"  - Detection rate: {combined_results['is_hatch_incident'].mean():.1%}")

    # Example 3: Performance Comparison
    print("\n3. PERFORMANCE COMPARISON")
    print("-" * 80)
    print()

    test_dataset = simulate_large_dataset(size=300)

    configurations = [
        ("LLM Only (BART)", {'use_llm': True, 'fallback_to_regex': False, 'batch_size': 32}),
        ("Hybrid (LLM+Regex)", {'use_llm': True, 'fallback_to_regex': True, 'batch_size': 32}),
        ("Regex Only", {'use_llm': False}),
    ]

    comparison_results = []

    for config_name, config in configurations:
        print(f"\nTesting: {config_name}")

        analyzer = HatchMaloperationAnalyzer(**config)
        result = process_with_monitoring(analyzer, test_dataset)

        if result['success']:
            comparison_results.append({
                'Configuration': config_name,
                'Speed (inc/sec)': result['metrics']['incidents_per_second'],
                'Detections': result['metrics']['hatch_incidents_detected'],
                'Detection Rate': f"{result['metrics']['detection_rate']:.1%}",
                'Avg Confidence': f"{result['metrics']['avg_confidence']:.2%}" if result['metrics']['avg_confidence'] else 'N/A'
            })

    if comparison_results:
        comparison_df = pd.DataFrame(comparison_results)
        print("\nPerformance Comparison:")
        print(comparison_df.to_string(index=False))

    # Example 4: Export Results
    print("\n4. EXPORTING RESULTS")
    print("-" * 80)
    print()

    # Use results from first example
    if result['success']:
        results_df = result['results']

        # Export to CSV
        csv_file = 'hatch_incident_detections.csv'
        results_df.to_csv(csv_file, index=False)
        print(f"✓ Exported to CSV: {csv_file}")

        # Export high-confidence detections
        high_confidence = results_df[results_df['llm_confidence'] > 0.85]
        if len(high_confidence) > 0:
            high_conf_file = 'high_confidence_hatch_incidents.csv'
            high_confidence.to_csv(high_conf_file, index=False)
            print(f"✓ Exported high-confidence incidents: {high_conf_file} ({len(high_confidence)} incidents)")

        # Create summary statistics
        summary = {
            'total_incidents': len(results_df),
            'hatch_incidents': int(results_df['is_hatch_incident'].sum()),
            'detection_rate': float(results_df['is_hatch_incident'].mean()),
            'avg_confidence': float(results_df['llm_confidence'].mean()),
            'confidence_std': float(results_df['llm_confidence'].std()),
            'detection_methods': results_df['detection_method'].value_counts().to_dict()
        }

        print("\nSummary Statistics:")
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"  - {key}: {value:.3f}")
            else:
                print(f"  - {key}: {value}")

    print("\n" + "=" * 80)
    print("BATCH PROCESSING EXAMPLE COMPLETE")
    print("=" * 80)
    print("\nKey Optimizations Demonstrated:")
    print("  ✓ Batch processing for efficiency")
    print("  ✓ Chunking for large datasets")
    print("  ✓ Performance monitoring")
    print("  ✓ Memory management strategies")
    print("  ✓ Result export and analysis")
    print("\nProduction Tips:")
    print("  - Use batch_size=64-128 for GPU processing")
    print("  - Process in chunks for datasets > 10,000 incidents")
    print("  - Monitor memory usage with large models")
    print("  - Export results incrementally for very large datasets")


if __name__ == "__main__":
    main()
