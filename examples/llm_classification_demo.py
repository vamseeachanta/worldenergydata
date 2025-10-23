#!/usr/bin/env python3
"""
ABOUTME: Demonstrates LLM-based classification of marine incidents using zero-shot learning.
ABOUTME: Shows BART-large-mnli for incident type classification and cause analysis.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import pandas as pd
from typing import List, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def setup_classifier():
    """
    Initialize the zero-shot classification pipeline.

    First-time run downloads model (~1.6GB).
    Subsequent runs load from cache.
    """
    print("Loading BART-large-mnli model...")
    print("(First time: Downloads ~1.6GB, may take 2-5 minutes)")

    try:
        from transformers import pipeline

        classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1  # Use CPU (-1), or 0 for GPU
        )

        print("✓ Model loaded successfully!\n")
        return classifier

    except ImportError:
        print("ERROR: transformers library not installed")
        print("Install with: pip install transformers torch")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR loading model: {e}")
        sys.exit(1)


# Marine incident taxonomy from INCIDENT_TAXONOMY.md
INCIDENT_TYPES = [
    "Collision & Contact",
    "Grounding & Stranding",
    "Flooding & Foundering",
    "Fire & Explosion",
    "Machinery & Equipment Failure",
    "Loss of Control",
    "Human Casualties",
    "Cargo & Stability",
    "Environmental & Weather",
    "Hazardous Materials"
]

ROOT_CAUSES = [
    "Operator Inattention",
    "Operator Inexperience",
    "Engine Failure",
    "Steering Failure",
    "Hatch Cover Failure",
    "Door Failure",
    "Hull Failure",
    "Poor Visibility",
    "Heavy Weather",
    "Poor Maintenance",
    "Overloading",
    "Cargo Not Secured",
    "Navigation Error",
    "Excessive Speed",
    "Alcohol Involved"
]


def classify_incident_type(
    classifier,
    incident_text: str,
    labels: List[str] = INCIDENT_TYPES,
    top_k: int = 3,
    confidence_threshold: float = 0.3
) -> Dict:
    """
    Classify incident into primary type categories.

    Args:
        classifier: Hugging Face pipeline
        incident_text: Incident description
        labels: Category labels
        top_k: Number of top predictions to return
        confidence_threshold: Minimum confidence score

    Returns:
        Dict with predicted labels and scores
    """
    if not incident_text or pd.isna(incident_text):
        return {'labels': [], 'scores': []}

    result = classifier(
        incident_text,
        labels,
        multi_label=True  # Allow multiple applicable categories
    )

    # Filter by confidence threshold
    filtered_labels = []
    filtered_scores = []

    for label, score in zip(result['labels'][:top_k], result['scores'][:top_k]):
        if score >= confidence_threshold:
            filtered_labels.append(label)
            filtered_scores.append(score)

    return {
        'labels': filtered_labels,
        'scores': filtered_scores
    }


def classify_root_causes(
    classifier,
    incident_text: str,
    labels: List[str] = ROOT_CAUSES,
    confidence_threshold: float = 0.5
) -> List[Tuple[str, float]]:
    """
    Identify root causes from incident description.

    Args:
        classifier: Hugging Face pipeline
        incident_text: Incident description
        labels: Root cause labels
        confidence_threshold: Minimum confidence (higher for causes)

    Returns:
        List of (cause, confidence_score) tuples
    """
    if not incident_text or pd.isna(incident_text):
        return []

    result = classifier(
        incident_text,
        labels,
        multi_label=True
    )

    # Return all causes above threshold
    causes = [
        (label, score)
        for label, score in zip(result['labels'], result['scores'])
        if score >= confidence_threshold
    ]

    return causes


def batch_classify_incidents(
    classifier,
    incidents: List[str],
    batch_size: int = 32
) -> pd.DataFrame:
    """
    Classify multiple incidents efficiently.

    Args:
        classifier: Hugging Face pipeline
        incidents: List of incident descriptions
        batch_size: Number to process at once

    Returns:
        DataFrame with predictions
    """
    results = []

    print(f"Classifying {len(incidents)} incidents in batches of {batch_size}...")

    for i in range(0, len(incidents), batch_size):
        batch = incidents[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(incidents) + batch_size - 1) // batch_size

        print(f"  Batch {batch_num}/{total_batches}...", end=' ')

        for incident in batch:
            # Classify incident type
            type_pred = classify_incident_type(classifier, incident)

            # Classify root causes
            causes = classify_root_causes(classifier, incident)

            results.append({
                'incident_text': incident,
                'predicted_type': type_pred['labels'][0] if type_pred['labels'] else None,
                'type_confidence': type_pred['scores'][0] if type_pred['scores'] else 0.0,
                'all_types': type_pred['labels'],
                'all_type_scores': type_pred['scores'],
                'root_causes': [c[0] for c in causes],
                'cause_scores': [c[1] for c in causes]
            })

        print("✓")

    return pd.DataFrame(results)


def demo_single_classification():
    """Demo: Classify single incident"""
    print("=" * 80)
    print("DEMO 1: Single Incident Classification")
    print("=" * 80)

    classifier = setup_classifier()

    # Example incident
    incident_text = (
        "Vessel foundered and sank after cargo hatch cover failure during heavy "
        "weather. Progressive flooding occurred in cargo holds 2 and 3. Crew "
        "abandoned ship. No casualties."
    )

    print(f"Incident: {incident_text}\n")

    # Classify incident type
    print("INCIDENT TYPE CLASSIFICATION:")
    type_result = classify_incident_type(classifier, incident_text)

    for label, score in zip(type_result['labels'], type_result['scores']):
        print(f"  {label:30} {score:6.2%}")

    print("\nROOT CAUSE ANALYSIS:")
    causes = classify_root_causes(classifier, incident_text)

    if causes:
        for cause, score in causes:
            print(f"  {cause:30} {score:6.2%}")
    else:
        print("  No root causes identified above threshold")

    print()


def demo_batch_classification():
    """Demo: Batch classify multiple incidents"""
    print("=" * 80)
    print("DEMO 2: Batch Classification")
    print("=" * 80)

    classifier = setup_classifier()

    # Sample incidents
    incidents = [
        "Vessel collided with fixed offshore platform due to operator inattention and excessive speed in poor visibility",
        "Engine room fire caused by fuel line rupture. Fire suppression system activated successfully",
        "Grounding occurred on uncharted reef. Vessel refloated on rising tide with no pollution",
        "Steering failure led to loss of directional control. Vessel drifted into shipping lane",
        "Cargo shift during heavy weather caused severe listing. Vessel stabilized after ballast adjustment",
        "Hatch cover not properly secured. Progressive flooding in rough seas led to foundering",
        "Collision with another vessel during overtaking maneuver. Both vessels sustained damage",
        "Explosion in engine room due to gas accumulation. Three crew members injured"
    ]

    # Batch classify
    results_df = batch_classify_incidents(classifier, incidents)

    print("\nRESULTS:")
    print("-" * 80)

    for idx, row in results_df.iterrows():
        print(f"\nIncident {idx + 1}:")
        print(f"  Text: {row['incident_text'][:70]}...")
        print(f"  Type: {row['predicted_type']} ({row['type_confidence']:.2%})")

        if row['root_causes']:
            print(f"  Causes: {', '.join(row['root_causes'])}")

    # Save to CSV
    output_file = project_root / "data" / "temp" / "classified_incidents.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(output_file, index=False)
    print(f"\n✓ Results saved to: {output_file}")


def demo_confidence_filtering():
    """Demo: Confidence-based filtering"""
    print("=" * 80)
    print("DEMO 3: Confidence Filtering")
    print("=" * 80)

    classifier = setup_classifier()

    # Ambiguous incident
    incident_text = "Vessel experienced difficulties. Reported to port authority."

    print(f"Ambiguous Incident: {incident_text}\n")

    # Try different confidence thresholds
    thresholds = [0.3, 0.5, 0.7]

    for threshold in thresholds:
        result = classify_incident_type(
            classifier,
            incident_text,
            confidence_threshold=threshold
        )

        print(f"Confidence Threshold: {threshold:.1%}")

        if result['labels']:
            for label, score in zip(result['labels'], result['scores']):
                print(f"  {label:30} {score:6.2%}")
        else:
            print("  → No predictions above threshold (human review needed)")

        print()


def demo_phrase_matching():
    """Demo: Specific phrase detection"""
    print("=" * 80)
    print("DEMO 4: Phrase Matching (Optional Enhancement)")
    print("=" * 80)

    print("For faster phrase-specific matching, consider sentence-transformers:")
    print()

    print("Example code:")
    print("""
    from sentence_transformers import SentenceTransformer, util

    # Load lightweight model (~90MB)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Target phrases
    phrases = [
        "hatch not closed",
        "hatch cover failure",
        "door malfunction",
        "watertight door failure"
    ]

    phrase_embeddings = model.encode(phrases)

    # Find similar phrases in incident text
    incident_embedding = model.encode(incident_text)
    similarities = util.cos_sim(incident_embedding, phrase_embeddings)

    # Matches with similarity > 0.7
    matches = [(phrase, sim) for phrase, sim in zip(phrases, similarities[0]) if sim > 0.7]
    """)

    print("\nThis approach is:")
    print("  ✓ 10-20x faster than BART")
    print("  ✓ Better for exact phrase matching")
    print("  ✓ Complementary to BART classification")
    print()


def demo_database_integration():
    """Demo: Integration with marine safety database"""
    print("=" * 80)
    print("DEMO 5: Database Integration (Conceptual)")
    print("=" * 80)

    print("To integrate with marine safety database:")
    print()

    print("Step 1: Load incidents from database")
    print("""
    from sqlalchemy import create_engine
    from worldenergydata.modules.marine_safety.database.models import Incident

    engine = create_engine('sqlite:///data/modules/marine_safety/database/marine_safety.db')
    query = "SELECT incident_id, description, title FROM incidents WHERE description IS NOT NULL"

    df = pd.read_sql(query, engine)
    """)

    print("\nStep 2: Classify incidents")
    print("""
    classifier = setup_classifier()
    results = batch_classify_incidents(classifier, df['description'].tolist())
    """)

    print("\nStep 3: Add predictions to database")
    print("""
    # Option A: Add as new columns
    df['predicted_type'] = results['predicted_type']
    df['type_confidence'] = results['type_confidence']
    df['root_causes'] = results['root_causes'].apply(lambda x: ','.join(x) if x else None)

    # Option B: Store in separate classification table
    # (Better for versioning and multiple classification runs)
    """)

    print("\nStep 4: Filter by confidence for quality")
    print("""
    high_confidence = results[results['type_confidence'] > 0.7]
    manual_review = results[results['type_confidence'] <= 0.7]

    print(f"Auto-classified: {len(high_confidence)} incidents")
    print(f"Manual review needed: {len(manual_review)} incidents")
    """)

    print()


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("MARINE INCIDENT LLM CLASSIFICATION - DEMONSTRATION")
    print("=" * 80)
    print()
    print("This demo shows zero-shot classification using facebook/bart-large-mnli")
    print()
    print("Requirements:")
    print("  - transformers library (pip install transformers torch)")
    print("  - ~2.5GB RAM")
    print("  - Internet connection for first-time model download (~1.6GB)")
    print()

    try:
        # Run demos
        demo_single_classification()
        demo_batch_classification()
        demo_confidence_filtering()
        demo_phrase_matching()
        demo_database_integration()

        print("=" * 80)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Review research document: docs/research/llm_model_evaluation_marine_incidents.md")
        print("  2. Install dependencies: pip install transformers torch")
        print("  3. Test on your marine safety database")
        print("  4. Adjust confidence thresholds based on results")
        print("  5. Consider adding sentence-transformers for phrase matching")
        print()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError running demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
