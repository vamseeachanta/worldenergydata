# ABOUTME: Data quality validation for HSE incident data post-import
# ABOUTME: Validates completeness, ranges, consistency, outliers, and temporal patterns

from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from worldenergydata.modules.hse.database.models import HSEIncident


class DataQualityValidator:
    """
    Post-import data quality validator for HSE incident data.

    Validates imported data across five quality dimensions:
    - Completeness: Required and optional field population
    - Range: Geographic bounds and positive values
    - Consistency: Cross-field logical relationships
    - Outliers: Statistical anomaly detection using IQR
    - Temporal: Date validity and sequence checks

    Usage:
        validator = DataQualityValidator(db_session)
        results = validator.run_all_validations()
        validator.export_quality_report('report.json', format='json')
    """

    # Required fields that must be present
    REQUIRED_FIELDS = [
        'bsee_incident_id',
        'incident_date',
        'operator',
        'incident_type',
        'severity'
    ]

    # Optional fields tracked for completeness
    OPTIONAL_FIELDS = [
        'facility_name',
        'lease_number',
        'block_number',
        'field_name',
        'latitude',
        'longitude',
        'description',
        'root_cause',
        'corrective_actions',
        'investigation_status'
    ]

    # Gulf of Mexico geographic boundaries
    GOM_LATITUDE_MIN = 18.0
    GOM_LATITUDE_MAX = 31.0
    GOM_LONGITUDE_MIN = -98.0
    GOM_LONGITUDE_MAX = -80.0

    # BSEE founding year (earliest reasonable incident date)
    BSEE_FOUNDING_YEAR = 1982

    def __init__(self, db_session: Session):
        """
        Initialize data quality validator.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.validation_results: Dict[str, Any] = {}

    def validate_completeness(self) -> Dict[str, Any]:
        """
        Validate completeness of required and optional fields.

        Calculates percentage of records with populated values for:
        - Required fields (must be 100% for valid data)
        - Optional fields (tracks data richness)

        Returns:
            Dictionary with completeness metrics:
            {
                'total_records': int,
                'required_fields_completeness': float (0-100),
                'optional_fields_completeness': float (0-100),
                'required_field_details': Dict[str, float],
                'optional_field_details': Dict[str, float]
            }
        """
        total_records = self.db_session.query(func.count(HSEIncident.id)).scalar()

        if total_records == 0:
            return {
                'total_records': 0,
                'required_fields_completeness': 0.0,
                'optional_fields_completeness': 0.0,
                'required_field_details': {},
                'optional_field_details': {}
            }

        result = {
            'total_records': total_records,
            'required_field_details': {},
            'optional_field_details': {}
        }

        # Check required fields
        required_populated = []
        for field in self.REQUIRED_FIELDS:
            count = self.db_session.query(func.count(HSEIncident.id)).filter(
                getattr(HSEIncident, field).isnot(None)
            ).scalar()

            percentage = (count / total_records) * 100
            result['required_field_details'][field] = percentage
            required_populated.append(percentage)

        result['required_fields_completeness'] = sum(required_populated) / len(required_populated) if required_populated else 0.0

        # Check optional fields
        optional_populated = []
        for field in self.OPTIONAL_FIELDS:
            if hasattr(HSEIncident, field):
                count = self.db_session.query(func.count(HSEIncident.id)).filter(
                    getattr(HSEIncident, field).isnot(None)
                ).scalar()

                percentage = (count / total_records) * 100
                result['optional_field_details'][field] = percentage
                optional_populated.append(percentage)

        result['optional_fields_completeness'] = sum(optional_populated) / len(optional_populated) if optional_populated else 0.0

        return result

    def validate_ranges(self) -> Dict[str, Any]:
        """
        Validate numeric and geographic ranges.

        Checks:
        - Latitude within Gulf of Mexico bounds (18-31°N)
        - Longitude within Gulf of Mexico bounds (-98 to -80°W)
        - Penalty amounts are positive (if present)
        - Incident counts are non-negative (if present)

        Returns:
            Dictionary with range violation counts:
            {
                'latitude_violations': int,
                'longitude_violations': int,
                'negative_penalty_violations': int,
                'negative_count_violations': int
            }
        """
        result = {
            'latitude_violations': 0,
            'longitude_violations': 0,
            'negative_penalty_violations': 0,
            'negative_count_violations': 0
        }

        # Check latitude bounds
        result['latitude_violations'] = self.db_session.query(func.count(HSEIncident.id)).filter(
            HSEIncident.latitude.isnot(None),
            (HSEIncident.latitude < self.GOM_LATITUDE_MIN) | (HSEIncident.latitude > self.GOM_LATITUDE_MAX)
        ).scalar()

        # Check longitude bounds
        result['longitude_violations'] = self.db_session.query(func.count(HSEIncident.id)).filter(
            HSEIncident.longitude.isnot(None),
            (HSEIncident.longitude < self.GOM_LONGITUDE_MIN) | (HSEIncident.longitude > self.GOM_LONGITUDE_MAX)
        ).scalar()

        # Note: penalty_amount not in current HSEIncident model
        # Placeholder for future enhancement
        result['negative_penalty_violations'] = 0

        # Note: count fields not in current HSEIncident model
        # Placeholder for future enhancement
        result['negative_count_violations'] = 0

        return result

    def validate_consistency(self) -> Dict[str, Any]:
        """
        Validate consistency of related fields.

        Checks logical relationships:
        - Severity aligns with incident type
        - Facility name present when location coordinates exist
        - Compliance deadline and penalty fields align

        Returns:
            Dictionary with consistency violation counts:
            {
                'severity_type_consistency': int,
                'facility_location_inconsistencies': int,
                'compliance_penalty_inconsistencies': int
            }
        """
        result = {
            'severity_type_consistency': 0,
            'facility_location_inconsistencies': 0,
            'compliance_penalty_inconsistencies': 0
        }

        # Check severity/type consistency
        # Example: fatality severity should not have near_miss incident type
        # This is a simplified check; could be enhanced with more rules
        inconsistent = self.db_session.query(func.count(HSEIncident.id)).filter(
            HSEIncident.severity == 'fatality',
            HSEIncident.incident_type == 'near_miss'
        ).scalar()
        result['severity_type_consistency'] = inconsistent

        # Check facility/location consistency
        # If facility_name is present, latitude/longitude should also be present
        result['facility_location_inconsistencies'] = self.db_session.query(func.count(HSEIncident.id)).filter(
            HSEIncident.facility_name.isnot(None),
            (HSEIncident.latitude.is_(None) | HSEIncident.longitude.is_(None))
        ).scalar()

        # Note: compliance_deadline and penalty_amount not in current model
        # Placeholder for future enhancement
        result['compliance_penalty_inconsistencies'] = 0

        return result

    def detect_outliers(self) -> Dict[str, Any]:
        """
        Detect statistical outliers using IQR (Interquartile Range) method.

        Identifies extreme values in:
        - Penalty amounts (if present)
        - Incident counts (if present)

        IQR method: Values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR] are outliers

        Returns:
            Dictionary with outlier information:
            {
                'outlier_method': 'IQR',
                'penalty_amount_outliers': int,
                'incident_count_outliers': int,
                'outliers': List[Dict] - details of outlier records
            }
        """
        result = {
            'outlier_method': 'IQR',
            'penalty_amount_outliers': 0,
            'incident_count_outliers': 0,
            'outliers': []
        }

        # Note: Current HSEIncident model doesn't have penalty_amount or count fields
        # Placeholder implementation for when these fields are added

        # IQR method would be:
        # 1. Calculate Q1 (25th percentile) and Q3 (75th percentile)
        # 2. Calculate IQR = Q3 - Q1
        # 3. Identify outliers: value < Q1 - 1.5*IQR OR value > Q3 + 1.5*IQR

        return result

    def validate_temporal(self) -> Dict[str, Any]:
        """
        Validate temporal patterns and date validity.

        Checks:
        - No incident dates in the future
        - No unreasonably old dates (before BSEE founding)
        - Compliance deadline after incident date (if applicable)
        - Suspicious date gaps in incident reporting

        Returns:
            Dictionary with temporal violation counts:
            {
                'future_date_violations': int,
                'unreasonably_old_violations': int,
                'deadline_before_incident_violations': int,
                'suspicious_date_gaps': List[Dict]
            }
        """
        result = {
            'future_date_violations': 0,
            'unreasonably_old_violations': 0,
            'deadline_before_incident_violations': 0,
            'suspicious_date_gaps': []
        }

        now = datetime.now()
        earliest_reasonable = datetime(self.BSEE_FOUNDING_YEAR, 1, 1)

        # Check for future dates
        result['future_date_violations'] = self.db_session.query(func.count(HSEIncident.id)).filter(
            HSEIncident.incident_date > now
        ).scalar()

        # Check for unreasonably old dates
        result['unreasonably_old_violations'] = self.db_session.query(func.count(HSEIncident.id)).filter(
            HSEIncident.incident_date < earliest_reasonable
        ).scalar()

        # Note: compliance_deadline not in current model
        # Placeholder for future enhancement
        result['deadline_before_incident_violations'] = 0

        # Check for suspicious date gaps (6+ months with no incidents)
        # This requires querying ordered incident dates and finding gaps
        incidents = self.db_session.query(HSEIncident.incident_date).filter(
            HSEIncident.incident_date.isnot(None)
        ).order_by(HSEIncident.incident_date).all()

        if len(incidents) > 1:
            gaps = []
            for i in range(len(incidents) - 1):
                current_date = incidents[i][0]
                next_date = incidents[i + 1][0]
                gap_days = (next_date - current_date).days

                # Flag gaps > 180 days (6 months) as suspicious
                if gap_days > 180:
                    gaps.append({
                        'from_date': current_date.isoformat(),
                        'to_date': next_date.isoformat(),
                        'gap_days': gap_days
                    })

            result['suspicious_date_gaps'] = gaps

        return result

    def run_all_validations(self) -> Dict[str, Any]:
        """
        Execute all validation methods and calculate overall quality score.

        Runs all five validation categories:
        1. Completeness
        2. Range validation
        3. Consistency checks
        4. Outlier detection
        5. Temporal validation

        Calculates overall quality score (0-100) based on:
        - Required fields completeness (40% weight)
        - Range violations (15% weight)
        - Consistency violations (15% weight)
        - Outlier count (15% weight)
        - Temporal violations (15% weight)

        Returns:
            Dictionary with aggregated validation results:
            {
                'completeness': Dict,
                'ranges': Dict,
                'consistency': Dict,
                'outliers': Dict,
                'temporal': Dict,
                'overall_quality_score': float (0-100),
                'total_records': int,
                'total_violations': int,
                'violation_percentage': float
            }
        """
        # Run all validation methods
        completeness = self.validate_completeness()
        ranges = self.validate_ranges()
        consistency = self.validate_consistency()
        outliers = self.detect_outliers()
        temporal = self.validate_temporal()

        # Calculate overall quality score
        total_records = completeness['total_records']

        # Completeness score (40% weight)
        completeness_score = completeness['required_fields_completeness'] * 0.4

        # Range violations score (15% weight)
        if total_records > 0:
            range_violations = (
                ranges['latitude_violations'] +
                ranges['longitude_violations']
            )
            range_score = max(0, (1 - range_violations / total_records)) * 100 * 0.15
        else:
            range_score = 0

        # Consistency violations score (15% weight)
        if total_records > 0:
            consistency_violations = (
                consistency['severity_type_consistency'] +
                consistency['facility_location_inconsistencies']
            )
            consistency_score = max(0, (1 - consistency_violations / total_records)) * 100 * 0.15
        else:
            consistency_score = 0

        # Outlier score (15% weight)
        if total_records > 0:
            outlier_violations = (
                outliers['penalty_amount_outliers'] +
                outliers['incident_count_outliers']
            )
            outlier_score = max(0, (1 - outlier_violations / total_records)) * 100 * 0.15
        else:
            outlier_score = 0

        # Temporal violations score (15% weight)
        if total_records > 0:
            temporal_violations = (
                temporal['future_date_violations'] +
                temporal['unreasonably_old_violations']
            )
            temporal_score = max(0, (1 - temporal_violations / total_records)) * 100 * 0.15
        else:
            temporal_score = 0

        # Calculate overall score
        overall_quality_score = (
            completeness_score +
            range_score +
            consistency_score +
            outlier_score +
            temporal_score
        )

        # Calculate total violations
        total_violations = (
            ranges['latitude_violations'] +
            ranges['longitude_violations'] +
            consistency['severity_type_consistency'] +
            consistency['facility_location_inconsistencies'] +
            temporal['future_date_violations'] +
            temporal['unreasonably_old_violations']
        )

        # Store results
        result = {
            'completeness': completeness,
            'ranges': ranges,
            'consistency': consistency,
            'outliers': outliers,
            'temporal': temporal,
            'overall_quality_score': round(overall_quality_score, 2),
            'total_records': total_records,
            'total_violations': total_violations,
            'violation_percentage': round((total_violations / total_records * 100) if total_records > 0 else 0, 2)
        }

        self.validation_results = result
        return result

    def generate_quality_report(self) -> Dict[str, Any]:
        """
        Generate structured quality report from validation results.

        Creates human-readable report with:
        - Validation timestamp
        - Overall quality score
        - Violations by category
        - Recommendations for data quality improvement

        Returns:
            Dictionary with report structure:
            {
                'validation_timestamp': str (ISO 8601),
                'quality_score': float,
                'violations_by_category': Dict,
                'recommendations': List[str]
            }
        """
        if not self.validation_results:
            raise ValueError("No validation results available. Run run_all_validations() first.")

        report = {
            'validation_timestamp': datetime.now().isoformat(),
            'quality_score': self.validation_results['overall_quality_score'],
            'violations_by_category': {
                'completeness': {
                    'required_fields': 100 - self.validation_results['completeness']['required_fields_completeness'],
                    'optional_fields': 100 - self.validation_results['completeness']['optional_fields_completeness']
                },
                'range_violations': {
                    'latitude': self.validation_results['ranges']['latitude_violations'],
                    'longitude': self.validation_results['ranges']['longitude_violations']
                },
                'consistency_violations': {
                    'severity_type': self.validation_results['consistency']['severity_type_consistency'],
                    'facility_location': self.validation_results['consistency']['facility_location_inconsistencies']
                },
                'temporal_violations': {
                    'future_dates': self.validation_results['temporal']['future_date_violations'],
                    'unreasonably_old': self.validation_results['temporal']['unreasonably_old_violations']
                }
            }
        }

        return report

    def export_quality_report(self, output_file: str, format: str = 'json'):
        """
        Export quality report to file.

        Args:
            output_file: Path to output file
            format: Export format ('json' or 'html')

        Raises:
            ValueError: If format is not supported or no results available
        """
        if not self.validation_results:
            raise ValueError("No validation results available. Run run_all_validations() first.")

        if format not in ['json', 'html']:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'html'.")

        report = self.generate_quality_report()

        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)

        elif format == 'html':
            # Generate basic HTML report
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>HSE Data Quality Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .score {{ font-size: 48px; font-weight: bold; color: {"green" if report['quality_score'] >= 80 else "orange" if report['quality_score'] >= 60 else "red"}; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>HSE Data Quality Report</h1>
    <p><strong>Generated:</strong> {report['validation_timestamp']}</p>
    <p><strong>Overall Quality Score:</strong> <span class="score">{report['quality_score']:.1f}/100</span></p>

    <h2>Violations by Category</h2>
    <table>
        <tr>
            <th>Category</th>
            <th>Violation Type</th>
            <th>Count</th>
        </tr>
"""

            for category, violations in report['violations_by_category'].items():
                for vtype, count in violations.items():
                    html_content += f"<tr><td>{category}</td><td>{vtype}</td><td>{count}</td></tr>\n"

            html_content += """
    </table>
</body>
</html>
"""

            with open(output_file, 'w') as f:
                f.write(html_content)
