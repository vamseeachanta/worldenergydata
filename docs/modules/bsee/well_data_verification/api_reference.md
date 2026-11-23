# Well Data Verification - API Reference

## Table of Contents
1. [Core Classes](#core-classes)
2. [Workflow Engine](#workflow-engine)
3. [Data Quality Framework](#data-quality-framework)
4. [Cross-Reference Module](#cross-reference-module)
5. [Audit System](#audit-system)
6. [Report Generation](#report-generation)
7. [Utilities](#utilities)
8. [Exceptions](#exceptions)

## Core Classes

### `VerificationEngine`

Main orchestrator for verification workflows.

```python
from worldenergydata.analysis.verification import VerificationEngine

class VerificationEngine:
    """Main verification engine coordinating all verification activities."""
    
    def __init__(self, config: Optional[VerificationConfig] = None):
        """
        Initialize verification engine.
        
        Args:
            config: Verification configuration object
        """
    
    def verify_data(self, 
                   data: pd.DataFrame, 
                   rules: Optional[List[ValidationRule]] = None) -> VerificationResult:
        """
        Verify production data against configured rules.
        
        Args:
            data: Production data DataFrame
            rules: Optional list of validation rules
            
        Returns:
            VerificationResult object with findings
            
        Raises:
            VerificationError: If verification fails
        """
    
    def generate_report(self, 
                       results: VerificationResult,
                       format: str = "pdf") -> Report:
        """
        Generate verification report.
        
        Args:
            results: Verification results
            format: Output format ("pdf", "excel", "html")
            
        Returns:
            Report object
        """
```

### `VerificationResult`

Container for verification results.

```python
from worldenergydata.analysis.verification.base import VerificationResult

class VerificationResult:
    """Results from verification process."""
    
    @property
    def quality_score(self) -> float:
        """Overall quality score (0-1)."""
    
    @property
    def completeness_score(self) -> float:
        """Data completeness score (0-1)."""
    
    @property
    def issues(self) -> List[ValidationIssue]:
        """List of validation issues found."""
    
    @property
    def statistics(self) -> Dict[str, Any]:
        """Statistical summary of data."""
    
    def has_critical_issues(self) -> bool:
        """Check if critical issues exist."""
    
    def export_json(self, file_path: str) -> None:
        """Export results to JSON file."""
    
    def export_csv(self, file_path: str) -> None:
        """Export results to CSV file."""
```

### `VerificationConfig`

Configuration management for verification.

```python
from worldenergydata.analysis.verification.config import VerificationConfig

class VerificationConfig:
    """Configuration for verification process."""
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'VerificationConfig':
        """
        Load configuration from YAML file.
        
        Args:
            file_path: Path to YAML configuration
            
        Returns:
            VerificationConfig instance
        """
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'VerificationConfig':
        """Create configuration from dictionary."""
    
    def to_yaml(self, file_path: str) -> None:
        """Save configuration to YAML file."""
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
```

## Workflow Engine

### `WorkflowEngine`

Manages verification workflows with state tracking.

```python
from worldenergydata.analysis.verification.engine import WorkflowEngine

class WorkflowEngine:
    """Engine for managing verification workflows."""
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        """Initialize workflow engine."""
    
    def start_workflow(self, 
                      workflow_name: str,
                      context: Optional[Dict] = None) -> WorkflowSession:
        """
        Start a new workflow session.
        
        Args:
            workflow_name: Name of workflow to execute
            context: Optional context data
            
        Returns:
            WorkflowSession object
        """
    
    def execute_step(self, 
                    session: WorkflowSession) -> StepResult:
        """
        Execute next step in workflow.
        
        Args:
            session: Active workflow session
            
        Returns:
            StepResult with execution details
        """
    
    def create_checkpoint(self, 
                         session: WorkflowSession) -> WorkflowCheckpoint:
        """Create checkpoint for session."""
    
    def load_checkpoint(self, 
                       checkpoint_file: str) -> WorkflowSession:
        """Load session from checkpoint."""
    
    def cancel_workflow(self, session: WorkflowSession) -> None:
        """Cancel active workflow."""
```

### `WorkflowSession`

Represents an active workflow session.

```python
class WorkflowSession:
    """Active workflow session."""
    
    @property
    def id(self) -> str:
        """Unique session identifier."""
    
    @property
    def state(self) -> WorkflowState:
        """Current workflow state."""
    
    @property
    def progress(self) -> float:
        """Progress percentage (0-100)."""
    
    @property
    def current_step(self) -> Optional[WorkflowStep]:
        """Current step being executed."""
    
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
    
    def get_context(self, key: str) -> Any:
        """Get value from session context."""
    
    def set_context(self, key: str, value: Any) -> None:
        """Set value in session context."""
```

### `WorkflowStep`

Individual step in a workflow.

```python
class WorkflowStep:
    """Workflow step definition."""
    
    def __init__(self, 
                id: str,
                name: str,
                step_type: str,
                config: Optional[Dict] = None):
        """Initialize workflow step."""
    
    def execute(self, context: Dict) -> StepResult:
        """
        Execute the step.
        
        Args:
            context: Execution context
            
        Returns:
            StepResult with execution details
        """
    
    def validate_inputs(self, inputs: Dict) -> List[str]:
        """Validate step inputs."""
    
    def validate_outputs(self, outputs: Dict) -> List[str]:
        """Validate step outputs."""
```

## Data Quality Framework

### `DataQualityFramework`

Comprehensive data quality assessment.

```python
from worldenergydata.analysis.verification.quality import DataQualityFramework

class DataQualityFramework:
    """Framework for data quality assessment."""
    
    def __init__(self, config: Optional[QualityConfig] = None):
        """Initialize quality framework."""
    
    def analyze(self, data: pd.DataFrame) -> QualityReport:
        """
        Perform comprehensive quality analysis.
        
        Args:
            data: Data to analyze
            
        Returns:
            QualityReport with findings
        """
    
    def validate_completeness(self, 
                            data: pd.DataFrame,
                            required_fields: List[str]) -> CompletenessResult:
        """Check data completeness."""
    
    def detect_outliers(self, 
                       data: pd.DataFrame,
                       columns: List[str]) -> OutlierResult:
        """Detect statistical outliers."""
    
    def validate_ranges(self, 
                       data: pd.DataFrame,
                       range_rules: Dict) -> RangeValidationResult:
        """Validate value ranges."""
```

### `ProductionVolumeValidator`

Validates oil and gas production volumes.

```python
class ProductionVolumeValidator:
    """Validator for production volumes."""
    
    def __init__(self,
                oil_min: float = 0,
                oil_max: float = 100000,
                gas_min: float = 0,
                gas_max: float = 500000):
        """
        Initialize validator with ranges.
        
        Args:
            oil_min: Minimum oil production
            oil_max: Maximum oil production
            gas_min: Minimum gas production
            gas_max: Maximum gas production
        """
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate production volumes."""
    
    def validate_oil(self, values: pd.Series) -> List[ValidationIssue]:
        """Validate oil production values."""
    
    def validate_gas(self, values: pd.Series) -> List[ValidationIssue]:
        """Validate gas production values."""
```

### `OutlierDetector`

Statistical outlier detection.

```python
class OutlierDetector:
    """Detector for statistical outliers."""
    
    def __init__(self, 
                method: str = "iqr",
                threshold: float = 1.5):
        """
        Initialize outlier detector.
        
        Args:
            method: Detection method ("iqr", "z_score", "isolation_forest")
            threshold: Detection threshold
        """
    
    def detect(self, data: pd.Series) -> List[Tuple[int, float]]:
        """
        Detect outliers in data.
        
        Args:
            data: Series to analyze
            
        Returns:
            List of (index, value) tuples for outliers
        """
    
    def detect_multivariate(self, 
                          data: pd.DataFrame) -> List[int]:
        """Detect multivariate outliers."""
```

### `ValidationRuleBuilder`

Fluent API for building validation rules.

```python
class ValidationRuleBuilder:
    """Builder for validation rules."""
    
    def add_range_rule(self,
                      field: str,
                      min_value: Optional[float] = None,
                      max_value: Optional[float] = None,
                      message: Optional[str] = None) -> 'ValidationRuleBuilder':
        """Add range validation rule."""
    
    def add_pattern_rule(self,
                        field: str,
                        pattern: str,
                        message: Optional[str] = None) -> 'ValidationRuleBuilder':
        """Add pattern validation rule."""
    
    def add_custom_rule(self,
                       name: str,
                       validator: Callable,
                       message: Optional[str] = None) -> 'ValidationRuleBuilder':
        """Add custom validation rule."""
    
    def build(self) -> List[ValidationRule]:
        """Build validation rules."""
```

## Cross-Reference Module

### `CrossReferenceModule`

Compares data with Excel benchmarks.

```python
from worldenergydata.analysis.verification.cross_reference import CrossReferenceModule

class CrossReferenceModule:
    """Module for cross-referencing with benchmarks."""
    
    def __init__(self, config: Optional[CrossReferenceConfig] = None):
        """Initialize cross-reference module."""
    
    def load_benchmark(self, 
                      file_path: str,
                      sheet: Optional[str] = None) -> None:
        """
        Load benchmark from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet: Sheet name (optional)
        """
    
    def add_mapping(self, 
                   db_field: str,
                   excel_field: str) -> None:
        """Add field mapping."""
    
    def compare(self, 
               data: pd.DataFrame,
               tolerance: float = 0.05) -> ComparisonResult:
        """
        Compare data with benchmark.
        
        Args:
            data: Data to compare
            tolerance: Numeric tolerance (0-1)
            
        Returns:
            ComparisonResult with discrepancies
        """
    
    def generate_discrepancy_report(self,
                                   results: ComparisonResult) -> DiscrepancyReport:
        """Generate discrepancy report."""
```

### `FieldMapper`

Maps fields between different data sources.

```python
class FieldMapper:
    """Maps fields between data sources."""
    
    def add_mapping(self, 
                   source_field: str,
                   target_field: str) -> None:
        """Add field mapping."""
    
    def map_fields(self, 
                  data: pd.DataFrame) -> pd.DataFrame:
        """Apply field mappings to data."""
    
    def fuzzy_match(self, 
                   source_fields: List[str],
                   target_fields: List[str],
                   threshold: float = 0.8) -> Dict[str, str]:
        """
        Fuzzy match field names.
        
        Args:
            source_fields: Source field names
            target_fields: Target field names
            threshold: Match threshold (0-1)
            
        Returns:
            Dictionary of matches
        """
```

## Audit System

### `AuditSystem`

Comprehensive audit trail management.

```python
from worldenergydata.analysis.verification.audit import AuditSystem

class AuditSystem:
    """System for audit trail management."""
    
    def __init__(self, 
                user: str,
                db_path: Optional[str] = None):
        """
        Initialize audit system.
        
        Args:
            user: Current user identifier
            db_path: Path to audit database
        """
    
    def log_activity(self,
                    activity_type: str,
                    description: str,
                    metadata: Optional[Dict] = None) -> None:
        """Log audit activity."""
    
    def track_session(self, 
                     session_name: str) -> ContextManager:
        """
        Context manager for session tracking.
        
        Example:
            with audit.track_session("verification"):
                # Perform verification
        """
    
    def query_logs(self,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  user: Optional[str] = None,
                  activity_type: Optional[str] = None) -> List[AuditEntry]:
        """Query audit logs."""
    
    def export_logs(self,
                   format: str = "json",
                   file_path: str = None) -> None:
        """Export audit logs."""
```

### `ComplianceManager`

Manages regulatory compliance.

```python
class ComplianceManager:
    """Manager for regulatory compliance."""
    
    def check_compliance(self,
                        standard: str,
                        audit_logs: List[AuditEntry]) -> ComplianceStatus:
        """
        Check compliance with standard.
        
        Args:
            standard: Compliance standard ("SOX", "GDPR", "HIPAA")
            audit_logs: Audit entries to check
            
        Returns:
            ComplianceStatus object
        """
    
    def generate_compliance_report(self,
                                 standard: str,
                                 period: str) -> ComplianceReport:
        """Generate compliance report."""
    
    def get_requirements(self, standard: str) -> List[str]:
        """Get requirements for compliance standard."""
```

### `SecurityController`

Role-based access control.

```python
class SecurityController:
    """Controller for security and access control."""
    
    def has_permission(self,
                      user: str,
                      permission: str) -> bool:
        """Check if user has permission."""
    
    def get_user_role(self, user: str) -> str:
        """Get user's role."""
    
    def validate_access(self,
                       user: str,
                       resource: str,
                       action: str) -> bool:
        """Validate access to resource."""
```

## Report Generation

### `VerificationReportGenerator`

Generates verification reports.

```python
from worldenergydata.analysis.verification.reports import VerificationReportGenerator

class VerificationReportGenerator:
    """Generator for verification reports."""
    
    def create_report(self,
                     verification_results: VerificationResult,
                     template: Optional[ReportTemplate] = None,
                     include_sections: Optional[List[str]] = None) -> Report:
        """
        Create verification report.
        
        Args:
            verification_results: Results to report
            template: Optional report template
            include_sections: Sections to include
            
        Returns:
            Report object
        """
    
    def export_pdf(self,
                  report: Report,
                  file_path: str,
                  include_charts: bool = True) -> None:
        """Export report to PDF."""
    
    def export_excel(self,
                    report: Report,
                    file_path: str,
                    include_pivot: bool = False) -> None:
        """Export report to Excel."""
    
    def export_html(self,
                   report: Report,
                   file_path: str,
                   interactive: bool = True) -> None:
        """Export report to HTML."""
```

### `ReportTemplate`

Template for report generation.

```python
class ReportTemplate:
    """Template for report structure."""
    
    def __init__(self,
                name: str,
                sections: List[Dict],
                metadata: Optional[Dict] = None):
        """
        Initialize report template.
        
        Args:
            name: Template name
            sections: List of section definitions
            metadata: Optional metadata
        """
    
    def add_section(self,
                   section_id: str,
                   section_type: str,
                   config: Optional[Dict] = None) -> None:
        """Add section to template."""
    
    def remove_section(self, section_id: str) -> None:
        """Remove section from template."""
    
    def to_yaml(self, file_path: str) -> None:
        """Save template to YAML."""
```

## Utilities

### `DataLoader`

Utility for loading data from various sources.

```python
from worldenergydata.analysis.verification.utils import DataLoader

class DataLoader:
    """Loader for various data formats."""
    
    @staticmethod
    def load_csv(file_path: str,
                **kwargs) -> pd.DataFrame:
        """Load CSV file."""
    
    @staticmethod
    def load_excel(file_path: str,
                  sheet: Optional[str] = None,
                  **kwargs) -> pd.DataFrame:
        """Load Excel file."""
    
    @staticmethod
    def load_json(file_path: str) -> pd.DataFrame:
        """Load JSON file."""
    
    @staticmethod
    def load_from_database(connection_string: str,
                         query: str) -> pd.DataFrame:
        """Load data from database."""
```

### `MetricsCalculator`

Calculates verification metrics.

```python
class MetricsCalculator:
    """Calculator for verification metrics."""
    
    @staticmethod
    def calculate_quality_score(results: VerificationResult) -> float:
        """Calculate overall quality score."""
    
    @staticmethod
    def calculate_completeness(data: pd.DataFrame) -> float:
        """Calculate data completeness."""
    
    @staticmethod
    def calculate_accuracy(actual: pd.Series,
                         expected: pd.Series) -> float:
        """Calculate accuracy metric."""
    
    @staticmethod
    def calculate_consistency(data: pd.DataFrame,
                            rules: List[ConsistencyRule]) -> float:
        """Calculate consistency score."""
```

## Exceptions

### Exception Hierarchy

```python
# Base exception
class VerificationError(Exception):
    """Base exception for verification errors."""
    
    def __init__(self, 
                message: str,
                error_type: str = "general",
                details: Optional[Dict] = None):
        """Initialize verification error."""

# Specific exceptions
class DataValidationError(VerificationError):
    """Error during data validation."""

class ConfigurationError(VerificationError):
    """Error in configuration."""

class WorkflowError(VerificationError):
    """Error during workflow execution."""

class AuditError(VerificationError):
    """Error in audit system."""

class ReportGenerationError(VerificationError):
    """Error generating report."""

class CrossReferenceError(VerificationError):
    """Error in cross-reference operation."""
```

### Error Handling

```python
from worldenergydata.analysis.verification import (
    VerificationEngine,
    VerificationError,
    DataValidationError
)

try:
    engine = VerificationEngine()
    results = engine.verify_data(data)
    
except DataValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Details: {e.details}")
    
except VerificationError as e:
    print(f"Verification failed: {e}")
    # Log error
    logger.error(e, exc_info=True)
    
except Exception as e:
    print(f"Unexpected error: {e}")
    raise
```

## Usage Examples

### Basic Verification

```python
from worldenergydata.analysis.verification import VerificationEngine
from worldenergydata.analysis.verification.config import VerificationConfig

# Load configuration
config = VerificationConfig.from_yaml("config.yaml")

# Create engine
engine = VerificationEngine(config)

# Load and verify data
data = pd.read_csv("production_data.csv")
results = engine.verify_data(data)

# Check results
print(f"Quality Score: {results.quality_score:.2%}")
print(f"Issues Found: {len(results.issues)}")

# Generate report
report = engine.generate_report(results, format="pdf")
report.save("verification_report.pdf")
```

### Custom Validation Rules

```python
from worldenergydata.analysis.verification.quality import ValidationRuleBuilder

# Build custom rules
builder = ValidationRuleBuilder()
rules = builder \
    .add_range_rule("oil_production", min_value=0, max_value=100000) \
    .add_pattern_rule("well_name", pattern=r"^[A-Z]{2}-\d{4}$") \
    .add_custom_rule("water_cut_check", 
                    lambda row: 0 <= row['water_cut'] <= 1,
                    "Water cut must be between 0 and 1") \
    .build()

# Apply rules
results = engine.verify_data(data, rules=rules)
```

### Workflow with Checkpoints

```python
from worldenergydata.analysis.verification.engine import WorkflowEngine

# Initialize workflow
engine = WorkflowEngine()
session = engine.start_workflow("monthly_verification")

try:
    # Execute steps
    while not session.is_complete():
        result = engine.execute_step(session)
        print(f"Completed: {result.step_name}")
        
        # Create checkpoint every 5 steps
        if session.progress % 5 == 0:
            checkpoint = engine.create_checkpoint(session)
            checkpoint.save(f"checkpoint_{session.id}.json")
            
except Exception as e:
    print(f"Workflow failed: {e}")
    # Can resume from checkpoint later
```

### Audit Trail

```python
from worldenergydata.analysis.verification.audit import AuditSystem

# Initialize audit
audit = AuditSystem(user="john.doe@company.com")

# Track verification session
with audit.track_session("Q1_2024_verification"):
    results = engine.verify_data(data)
    
    # Log specific activities
    audit.log_activity(
        "data_validation",
        "Validated production data for Q1 2024",
        metadata={"records": len(data), "issues": len(results.issues)}
    )

# Query audit logs
logs = audit.query_logs(
    start_date=datetime(2024, 1, 1),
    activity_type="data_validation"
)

for log in logs:
    print(f"{log.timestamp}: {log.description}")
```

This API reference provides comprehensive documentation for all major classes and functions in the Well Data Verification System.