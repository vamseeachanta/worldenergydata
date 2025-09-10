# Well Data Verification - Workflow Tutorial

## Table of Contents
1. [Basic Verification Workflow](#basic-verification-workflow)
2. [Advanced Multi-Field Verification](#advanced-multi-field-verification)
3. [Cross-Reference Workflow](#cross-reference-workflow)
4. [Monthly Production Verification](#monthly-production-verification)
5. [Anomaly Investigation Workflow](#anomaly-investigation-workflow)

## Basic Verification Workflow

This tutorial walks through a complete verification workflow for a single well field's production data.

### Step 1: Prepare Your Data

First, ensure your production data is in the correct format:

```csv
well_name,production_date,oil_production,gas_production,water_production
JK-001,2024-01-01,5234.5,12450.0,1023.4
JK-002,2024-01-01,4856.2,10234.5,856.7
...
```

### Step 2: Create Configuration File

Create a `verification_config.yaml` file:

```yaml
# verification_config.yaml
verification:
  data_source:
    type: "csv"
    file: "jack_field_production.csv"
    
  validation_rules:
    oil_production:
      min: 0
      max: 10000
      unit: "BBL/day"
    gas_production:
      min: 0
      max: 50000
      unit: "MCF/day"
    water_production:
      min: 0
      max: 5000
      unit: "BBL/day"
      
  quality_checks:
    completeness_threshold: 0.95
    outlier_detection:
      method: "iqr"
      threshold: 1.5
      
  output:
    directory: "./verification_results"
    format: ["pdf", "excel"]
```

### Step 3: Run the Verification

Execute the verification using the CLI:

```bash
python -m worldenergydata.modules.analysis.verification.cli verify \
    --config verification_config.yaml
```

### Step 4: Monitor Progress

The system will display progress in real-time:

```
[INFO] Starting verification workflow...
[INFO] Step 1/6: Loading data... ✓
[INFO] Step 2/6: Checking completeness... ✓
[INFO] Step 3/6: Validating ranges... ✓
[INFO] Step 4/6: Detecting outliers... ✓
[INFO] Step 5/6: Running quality checks... ✓
[INFO] Step 6/6: Generating report... ✓

Verification Complete!
- Total Wells: 25
- Records Processed: 9,125
- Issues Found: 12 warnings, 3 errors
- Quality Score: 94.5%
- Report saved to: ./verification_results/verification_report_2024-01-15.pdf
```

### Step 5: Review Results

Open the generated report to review findings:

```python
# Example: Programmatically review results
import pandas as pd

# Load the Excel report
results_df = pd.read_excel(
    "./verification_results/verification_report_2024-01-15.xlsx",
    sheet_name="Validation Results"
)

# Check critical issues
critical_issues = results_df[results_df['severity'] == 'error']
print(f"Critical issues found: {len(critical_issues)}")

for idx, issue in critical_issues.iterrows():
    print(f"- {issue['well_name']}: {issue['description']}")
```

## Advanced Multi-Field Verification

Verify multiple fields in a single workflow with field-specific rules.

### Step 1: Organize Multi-Field Data

Structure your data with field identifiers:

```csv
field_name,well_name,production_date,oil_production,gas_production
Jack Field,JK-001,2024-01-01,5234.5,12450.0
Jack Field,JK-002,2024-01-01,4856.2,10234.5
Mary Field,MR-001,2024-01-01,7654.3,18976.5
Mary Field,MR-002,2024-01-01,6543.2,16543.2
```

### Step 2: Define Field-Specific Rules

Create `multi_field_config.yaml`:

```yaml
# multi_field_config.yaml
verification:
  fields:
    jack_field:
      filter: "field_name == 'Jack Field'"
      rules:
        oil_production:
          min: 0
          max: 10000
        gas_production:
          min: 0
          max: 50000
          
    mary_field:
      filter: "field_name == 'Mary Field'"
      rules:
        oil_production:
          min: 0
          max: 15000  # Higher production expected
        gas_production:
          min: 0
          max: 75000
          
  comparison:
    enable_cross_field: true
    metrics: ["total_production", "average_production", "production_efficiency"]
```

### Step 3: Run Multi-Field Verification

```python
from worldenergydata.modules.analysis.verification import VerificationEngine
from worldenergydata.modules.analysis.verification.config import MultiFieldConfig

# Load configuration
config = MultiFieldConfig.from_yaml("multi_field_config.yaml")

# Initialize engine
engine = VerificationEngine(config)

# Load data
data = pd.read_csv("multi_field_production.csv")

# Run verification for each field
results = {}
for field_name, field_config in config.fields.items():
    field_data = data.query(field_config['filter'])
    results[field_name] = engine.verify_data(field_data, field_config['rules'])
    
# Generate comparative report
comparative_report = engine.generate_comparative_report(results)
print(comparative_report.summary())
```

### Step 4: Compare Field Performance

```python
# Analyze field performance
for field_name, result in results.items():
    print(f"\n{field_name}:")
    print(f"  Quality Score: {result.quality_score:.2%}")
    print(f"  Completeness: {result.completeness_score:.2%}")
    print(f"  Issues: {len(result.issues)}")
    print(f"  Outliers: {result.outlier_count}")
```

## Cross-Reference Workflow

Validate production data against Excel benchmarks.

### Step 1: Prepare Benchmark Excel File

Create an Excel file with benchmark data:

| Well Name | Expected Oil (BBL) | Expected Gas (MCF) | Tolerance (%) |
|-----------|-------------------|-------------------|---------------|
| JK-001    | 5200              | 12500             | 5             |
| JK-002    | 4900              | 10200             | 5             |

### Step 2: Configure Cross-Reference

```yaml
# cross_reference_config.yaml
cross_reference:
  benchmark_file: "production_benchmarks.xlsx"
  sheet_name: "Q1_2024_Targets"
  
  field_mapping:
    database_to_excel:
      well_name: "Well Name"
      oil_production: "Expected Oil (BBL)"
      gas_production: "Expected Gas (MCF)"
      
  comparison:
    numeric_tolerance: 0.05  # 5% tolerance
    date_tolerance_days: 1
    string_matching: "fuzzy"  # or "exact"
    
  reporting:
    highlight_discrepancies: true
    export_comparison_table: true
```

### Step 3: Run Cross-Reference

```python
from worldenergydata.modules.analysis.verification.cross_reference import CrossReferenceModule

# Initialize cross-reference module
cross_ref = CrossReferenceModule.from_config("cross_reference_config.yaml")

# Load production data
production_data = pd.read_csv("actual_production.csv")

# Load benchmark
cross_ref.load_benchmark("production_benchmarks.xlsx")

# Perform comparison
comparison_results = cross_ref.compare(production_data)

# Review discrepancies
print(f"Total discrepancies: {len(comparison_results.discrepancies)}")
for discrepancy in comparison_results.discrepancies[:5]:
    print(f"Well {discrepancy.well_name}:")
    print(f"  Field: {discrepancy.field}")
    print(f"  Expected: {discrepancy.expected_value}")
    print(f"  Actual: {discrepancy.actual_value}")
    print(f"  Difference: {discrepancy.difference:.2%}")
```

### Step 4: Generate Discrepancy Report

```python
# Generate detailed discrepancy report
report = cross_ref.generate_discrepancy_report(
    comparison_results,
    include_charts=True,
    severity_threshold="warning"
)

# Export to Excel with highlighting
report.export_excel(
    "discrepancy_report.xlsx",
    highlight_errors=True,
    include_pivot_table=True
)
```

## Monthly Production Verification

Automate monthly verification with scheduled workflows.

### Step 1: Create Monthly Workflow Configuration

```yaml
# monthly_workflow.yaml
workflow:
  name: "Monthly Production Verification"
  schedule: "0 6 1 * *"  # Run at 6 AM on the 1st of each month
  
  steps:
    - name: "Extract Previous Month Data"
      type: "data_extraction"
      config:
        source: "bsee_database"
        query: |
          SELECT * FROM production
          WHERE production_date >= DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH)
          AND production_date < CURRENT_DATE
          
    - name: "Validate Completeness"
      type: "completeness_check"
      config:
        expected_records_per_well: 30  # Daily records
        tolerance: 0.95
        
    - name: "Check Month-over-Month Changes"
      type: "trend_analysis"
      config:
        max_change_percent: 20
        flag_sudden_drops: true
        
    - name: "Compare with Forecast"
      type: "forecast_comparison"
      config:
        forecast_file: "monthly_forecasts.xlsx"
        tolerance_percent: 10
        
    - name: "Generate Monthly Report"
      type: "report_generation"
      config:
        template: "monthly_verification_template"
        recipients: ["operations@company.com", "compliance@company.com"]
```

### Step 2: Implement Monthly Verification

```python
from worldenergydata.modules.analysis.verification.engine import WorkflowEngine
from datetime import datetime, timedelta

class MonthlyVerification:
    def __init__(self, config_file):
        self.engine = WorkflowEngine.from_yaml(config_file)
        
    def run_monthly_verification(self):
        """Run verification for previous month"""
        # Calculate previous month
        today = datetime.now()
        first_day_current = today.replace(day=1)
        last_day_previous = first_day_current - timedelta(days=1)
        month_year = last_day_previous.strftime("%B %Y")
        
        print(f"Running verification for {month_year}")
        
        # Start workflow
        session = self.engine.start_workflow()
        
        # Execute all steps
        while not session.is_complete():
            step_result = self.engine.execute_next_step(session)
            print(f"Completed: {step_result.step_name}")
            
            # Handle any issues
            if step_result.has_issues():
                self.handle_issues(step_result.issues)
                
        # Generate final report
        report = self.engine.generate_report(session)
        self.send_report(report, month_year)
        
    def handle_issues(self, issues):
        """Handle verification issues"""
        critical_issues = [i for i in issues if i.severity == "critical"]
        
        if critical_issues:
            # Send immediate alert
            self.send_alert(critical_issues)
            
        # Log all issues
        for issue in issues:
            logger.warning(f"Verification issue: {issue}")
            
    def send_report(self, report, month_year):
        """Send monthly report to stakeholders"""
        # Save report
        filename = f"monthly_verification_{month_year.replace(' ', '_')}.pdf"
        report.save(filename)
        
        # Email to stakeholders
        print(f"Report saved: {filename}")
        print("Email sent to stakeholders")

# Run monthly verification
verifier = MonthlyVerification("monthly_workflow.yaml")
verifier.run_monthly_verification()
```

### Step 3: Schedule Automated Runs

```python
import schedule
import time

def run_monthly_check():
    verifier = MonthlyVerification("monthly_workflow.yaml")
    verifier.run_monthly_verification()

# Schedule for the 1st of each month at 6 AM
schedule.every().month.do(run_monthly_check)

# Keep the scheduler running
while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
```

## Anomaly Investigation Workflow

Deep-dive workflow for investigating data anomalies.

### Step 1: Configure Anomaly Detection

```yaml
# anomaly_config.yaml
anomaly_detection:
  methods:
    - type: "statistical"
      config:
        z_score_threshold: 3
        iqr_multiplier: 1.5
        
    - type: "time_series"
      config:
        seasonal_decomposition: true
        trend_analysis: true
        change_point_detection: true
        
    - type: "clustering"
      config:
        algorithm: "dbscan"
        eps: 0.5
        min_samples: 5
        
  investigation:
    auto_investigate: true
    investigation_depth: "comprehensive"
    
  reporting:
    include_visualizations: true
    export_investigation_log: true
```

### Step 2: Run Anomaly Investigation

```python
from worldenergydata.modules.analysis.verification.quality import AnomalyInvestigator

class AnomalyWorkflow:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.investigator = AnomalyInvestigator(self.config)
        
    def investigate_anomalies(self, data):
        """Comprehensive anomaly investigation"""
        
        # Step 1: Detect anomalies
        print("Step 1: Detecting anomalies...")
        anomalies = self.investigator.detect_anomalies(data)
        print(f"Found {len(anomalies)} anomalies")
        
        # Step 2: Classify anomalies
        print("Step 2: Classifying anomalies...")
        classified = self.investigator.classify_anomalies(anomalies)
        
        # Step 3: Investigate root causes
        print("Step 3: Investigating root causes...")
        investigations = {}
        for anomaly in classified:
            investigation = self.investigate_single_anomaly(anomaly, data)
            investigations[anomaly.id] = investigation
            
        # Step 4: Generate investigation report
        print("Step 4: Generating investigation report...")
        report = self.generate_investigation_report(investigations)
        
        return report
        
    def investigate_single_anomaly(self, anomaly, data):
        """Deep investigation of a single anomaly"""
        investigation = {
            'anomaly': anomaly,
            'context': {},
            'possible_causes': [],
            'recommendations': []
        }
        
        # Get temporal context
        investigation['context']['temporal'] = self.get_temporal_context(
            anomaly, data
        )
        
        # Get spatial context (nearby wells)
        investigation['context']['spatial'] = self.get_spatial_context(
            anomaly, data
        )
        
        # Analyze patterns
        patterns = self.analyze_patterns(anomaly, data)
        
        # Determine possible causes
        if patterns['sudden_drop']:
            investigation['possible_causes'].append("Equipment failure")
            investigation['recommendations'].append("Check equipment logs")
            
        if patterns['gradual_decline']:
            investigation['possible_causes'].append("Natural decline")
            investigation['recommendations'].append("Review decline curve analysis")
            
        if patterns['data_quality_issue']:
            investigation['possible_causes'].append("Data entry error")
            investigation['recommendations'].append("Verify source data")
            
        return investigation
        
    def get_temporal_context(self, anomaly, data, window_days=30):
        """Get data around the anomaly time period"""
        anomaly_date = anomaly.date
        start_date = anomaly_date - timedelta(days=window_days)
        end_date = anomaly_date + timedelta(days=window_days)
        
        context_data = data[
            (data['production_date'] >= start_date) &
            (data['production_date'] <= end_date) &
            (data['well_name'] == anomaly.well_name)
        ]
        
        return {
            'before': context_data[context_data['production_date'] < anomaly_date],
            'after': context_data[context_data['production_date'] > anomaly_date],
            'trend': self.calculate_trend(context_data)
        }
        
    def get_spatial_context(self, anomaly, data):
        """Get data from nearby wells"""
        # Assuming we have well location data
        nearby_wells = self.find_nearby_wells(anomaly.well_name)
        
        context = {}
        for well in nearby_wells:
            well_data = data[
                (data['well_name'] == well) &
                (data['production_date'] == anomaly.date)
            ]
            context[well] = well_data
            
        return context
        
    def generate_investigation_report(self, investigations):
        """Generate comprehensive investigation report"""
        report = {
            'summary': {
                'total_anomalies': len(investigations),
                'critical': 0,
                'warning': 0,
                'info': 0
            },
            'investigations': investigations,
            'recommendations': [],
            'visualizations': []
        }
        
        # Aggregate recommendations
        all_recommendations = set()
        for inv in investigations.values():
            all_recommendations.update(inv['recommendations'])
            
            # Count by severity
            if inv['anomaly'].severity == 'critical':
                report['summary']['critical'] += 1
            elif inv['anomaly'].severity == 'warning':
                report['summary']['warning'] += 1
            else:
                report['summary']['info'] += 1
                
        report['recommendations'] = list(all_recommendations)
        
        # Generate visualizations
        report['visualizations'] = self.create_visualizations(investigations)
        
        return report

# Run anomaly investigation
workflow = AnomalyWorkflow("anomaly_config.yaml")
data = pd.read_csv("production_data_with_anomalies.csv")
investigation_report = workflow.investigate_anomalies(data)

# Review findings
print(f"Investigation Summary:")
print(f"  Critical anomalies: {investigation_report['summary']['critical']}")
print(f"  Warnings: {investigation_report['summary']['warning']}")
print(f"  Recommendations: {len(investigation_report['recommendations'])}")

# Export detailed report
with open("anomaly_investigation_report.json", "w") as f:
    json.dump(investigation_report, f, indent=2, default=str)
```

### Step 3: Visualize Anomalies

```python
import matplotlib.pyplot as plt
import seaborn as sns

def visualize_anomalies(data, anomalies):
    """Create visualization of anomalies in production data"""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Time series with anomalies highlighted
    ax1 = axes[0, 0]
    ax1.plot(data['production_date'], data['oil_production'], 
             label='Normal', alpha=0.7)
    
    anomaly_dates = [a.date for a in anomalies]
    anomaly_values = [a.value for a in anomalies]
    ax1.scatter(anomaly_dates, anomaly_values, 
                color='red', s=50, label='Anomalies')
    ax1.set_title('Production Time Series with Anomalies')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Oil Production (BBL)')
    ax1.legend()
    
    # Plot 2: Distribution with outliers
    ax2 = axes[0, 1]
    ax2.hist(data['oil_production'], bins=50, alpha=0.7, label='Normal')
    ax2.hist(anomaly_values, bins=20, alpha=0.7, color='red', label='Anomalies')
    ax2.set_title('Production Distribution')
    ax2.set_xlabel('Oil Production (BBL)')
    ax2.set_ylabel('Frequency')
    ax2.legend()
    
    # Plot 3: Box plot by well
    ax3 = axes[1, 0]
    well_groups = data.groupby('well_name')['oil_production'].apply(list)
    ax3.boxplot(well_groups.values, labels=well_groups.index)
    ax3.set_title('Production by Well')
    ax3.set_xlabel('Well Name')
    ax3.set_ylabel('Oil Production (BBL)')
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 4: Anomaly heatmap
    ax4 = axes[1, 1]
    # Create anomaly matrix (wells x months)
    anomaly_matrix = create_anomaly_matrix(data, anomalies)
    sns.heatmap(anomaly_matrix, cmap='RdYlGn_r', ax=ax4, 
                cbar_kws={'label': 'Anomaly Score'})
    ax4.set_title('Anomaly Heatmap')
    ax4.set_xlabel('Month')
    ax4.set_ylabel('Well')
    
    plt.tight_layout()
    plt.savefig('anomaly_visualization.png', dpi=300)
    plt.show()

# Create visualizations
visualize_anomalies(data, anomalies)
```

## Summary

These workflow tutorials demonstrate:

1. **Basic Verification**: Simple, straightforward validation of production data
2. **Multi-Field Processing**: Handling multiple fields with different rules
3. **Cross-Reference Validation**: Comparing against Excel benchmarks
4. **Monthly Automation**: Scheduled verification workflows
5. **Anomaly Investigation**: Deep-dive analysis of data issues

Each workflow can be customized and combined to meet specific verification needs. The modular design allows you to pick and choose components that best fit your requirements.

## Next Steps

- Review the [CLI Reference](cli_reference.md) for command-line options
- Check the [API Documentation](api_reference.md) for programmatic access
- See the [Configuration Guide](configuration_guide.md) for customization options
- Consult the [Troubleshooting Guide](troubleshooting.md) if you encounter issues