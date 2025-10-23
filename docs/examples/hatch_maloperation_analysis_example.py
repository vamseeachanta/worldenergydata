"""
Example usage of the Hatch Maloperation Analysis Module

This example demonstrates how to use the HatchMaloperationAnalyzer
to analyze marine safety incidents involving hatch and opening maloperation.
"""

from datetime import datetime
from worldenergydata.modules.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
    HatchMaloperationAnalyzer
)


def main():
    """Demonstrate hatch maloperation analysis capabilities."""

    # Initialize the analyzer
    analyzer = HatchMaloperationAnalyzer()

    # Sample incidents (would typically come from database or CSV)
    incidents = [
        {
            'incident_id': 'HATCH-2024-001',
            'date': datetime(2024, 1, 15),
            'incident_type': 'Flooding',
            'severity': 'Serious',
            'description': (
                'Engine room flooding occurred due to hatch maloperation. '
                'Crew member failed to properly secure engine room access hatch, '
                'resulting in water ingress during heavy seas. Bilge pumps engaged '
                'automatically. No injuries reported but significant equipment damage.'
            ),
            'location': 'Gulf of Mexico',
            'fatalities': 0,
            'injuries': 0,
            'estimated_damage_usd': 150000
        },
        {
            'incident_id': 'HATCH-2024-002',
            'date': datetime(2024, 2, 10),
            'incident_type': 'Fire',
            'severity': 'Critical',
            'description': (
                'Fire in engine room enclosure caused by hatch failure. '
                'Access cover maloperation prevented proper ventilation, '
                'leading to fuel vapor accumulation and subsequent ignition. '
                'Two crew members sustained burns. Fire suppression system activated.'
            ),
            'location': 'North Atlantic',
            'fatalities': 0,
            'injuries': 2,
            'estimated_damage_usd': 500000
        },
        {
            'incident_id': 'NON-HATCH-001',
            'date': datetime(2024, 6, 1),
            'incident_type': 'Collision',
            'severity': 'Moderate',
            'description': (
                'Vessel collision during restricted visibility. '
                'No hatch-related issues. Bridge watchkeeping failure '
                'led to contact with another vessel.'
            ),
            'location': 'English Channel',
            'fatalities': 0,
            'injuries': 0,
            'estimated_damage_usd': 75000
        }
    ]

    print("=" * 80)
    print("HATCH MALOPERATION INCIDENT ANALYSIS")
    print("=" * 80)
    print()

    # Filter to only hatch maloperation incidents
    print("1. IDENTIFYING HATCH MALOPERATION INCIDENTS")
    print("-" * 80)
    hatch_incidents = []
    for incident in incidents:
        is_hatch = analyzer.is_hatch_maloperation_incident(incident)
        print(f"Incident {incident['incident_id']}: {'YES' if is_hatch else 'NO'}")
        if is_hatch:
            hatch_incidents.append(incident)
    print(f"\nTotal hatch incidents found: {len(hatch_incidents)}")
    print()

    # Analyze each hatch incident
    print("2. DETAILED INCIDENT ANALYSIS")
    print("-" * 80)
    for incident in hatch_incidents:
        print(f"\nIncident: {incident['incident_id']}")
        print(f"Date: {incident['date'].strftime('%Y-%m-%d')}")
        print(f"Location Type: {analyzer.classify_location(incident)}")
        print(f"Severity: {incident['severity']}")

        # Analyze consequences
        consequences = analyzer.analyze_consequences(incident)
        print(f"Consequences: {', '.join(consequences)}")

        # Identify contributing factors
        factors = analyzer.identify_contributing_factors(incident)
        print(f"Contributing Factors: {', '.join(factors)}")

        # Calculate risk score
        risk_score = analyzer.calculate_risk_score(incident)
        print(f"Risk Score: {risk_score:.1f}/100")

        # Check if significant
        is_significant = analyzer.is_significant_incident(incident)
        print(f"Significant for Case Study: {'Yes' if is_significant else 'No'}")
        print()

    # Generate recommendations
    print("3. SAFETY RECOMMENDATIONS")
    print("-" * 80)
    for idx, incident in enumerate(hatch_incidents, 1):
        print(f"\nIncident {incident['incident_id']}:")
        recommendations = analyzer.generate_recommendations(incident)
        for rec_idx, rec in enumerate(recommendations, 1):
            print(f"  {rec_idx}. {rec}")
    print()

    # Generate comprehensive report
    print("4. COMPREHENSIVE ANALYSIS REPORT")
    print("-" * 80)
    report = analyzer.generate_comprehensive_report(incidents)

    if 'error' not in report:
        print(f"\nSummary Statistics:")
        print(f"  Total Incidents: {report['summary_statistics']['total_incidents']}")
        print(f"  Severity Distribution: {report['summary_statistics']['severity_distribution']}")

        print(f"\nLocation Analysis:")
        for location, count in report['location_analysis'].items():
            print(f"  {location}: {count}")

        print(f"\nConsequence Analysis:")
        print(f"  Total Fatalities: {report['consequence_analysis']['total_fatalities']}")
        print(f"  Total Injuries: {report['consequence_analysis']['total_injuries']}")

        print(f"\nRisk Assessment:")
        print(f"  Average Risk Score: {report['risk_assessment']['average_risk_score']}")
        print(f"  High Risk Incidents: {report['risk_assessment']['high_risk_incidents']}")
        print(f"  Moderate Risk Incidents: {report['risk_assessment']['moderate_risk_incidents']}")
        print(f"  Low Risk Incidents: {report['risk_assessment']['low_risk_incidents']}")

        print(f"\nTrend Analysis:")
        print(f"  Direction: {report['trends']['direction']}")
        print(f"  Change Rate: {report['trends']['change_rate']}%")

        print(f"\nTop Recommendations:")
        sorted_recs = sorted(report['recommendations'].items(), key=lambda x: x[1], reverse=True)
        for rec, count in sorted_recs[:5]:
            print(f"  [{count}x] {rec}")

        print(f"\nCase Studies: {len(report['case_studies'])} significant incidents identified")
        for case_study in report['case_studies']:
            print(f"  - {case_study['incident_id']}: Risk Score {case_study['risk_score']:.1f}")

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
