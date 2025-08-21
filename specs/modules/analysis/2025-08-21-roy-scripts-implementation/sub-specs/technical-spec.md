# Technical Specification

This is the technical specification for the spec detailed in @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/spec.md

> Module: bsee/analysis
> Created: 2025-08-21
> Version: 1.0.0

## Module Architecture

### Package Structure
```
worldenergydata/
└── modules/
    └── bsee/
        ├── custom_router.py (extended)
        └── analysis/
            └── custom_scripts/
                └── Roy/
                    ├── july/ (existing)
                    └── august/ (new)
                        ├── __init__.py
                        ├── extract_drilling_and_completion_days_enhanced.py
                        ├── build_month_matrix_by_lease_enhanced.py
                        └── build_development_financials_enhanced.py
```

### Class Design Patterns

#### Base Pattern
All enhanced classes follow this structure:
```python
class EnhancedAnalysisBase:
    """Base class for enhanced BSEE analysis modules."""
    
    def __init__(self):
        self.cfg = None
        self.logger = logger
        self.data = {}
        self.results = {}
    
    def router(self, cfg: dict) -> dict:
        """Framework entry point."""
        self.cfg = cfg
        self._validate_config()
        self._load_data()
        self._process_analysis()
        self._save_results()
        return cfg
    
    def _validate_config(self):
        """Validate required configuration parameters."""
        raise NotImplementedError
    
    def _load_data(self):
        """Load input data from configured sources."""
        raise NotImplementedError
    
    def _process_analysis(self):
        """Execute core analysis logic."""
        raise NotImplementedError
    
    def _save_results(self):
        """Save results to configured output."""
        raise NotImplementedError
```

## Technical Requirements

### Data Processing Requirements

#### Binary File Processing
- Use `pickle.load()` for WAR binary files
- Implement chunked reading for large files
- Handle pickle protocol versions 3-5
- Graceful fallback to text if binary fails

#### OGORA Processing
- Direct zip file reading without extraction
- Memory-efficient streaming for large files
- Support for multiple year patterns
- Automatic encoding detection

#### Excel I/O
- Use `openpyxl` for Excel operations
- Preserve formatting where possible
- Support for multiple sheets
- Handle large datasets (>100k rows)

### Performance Requirements

#### Processing Speed
- Drilling analysis: < 0.3 seconds per well
- Matrix generation: < 20 seconds per year
- Financial analysis: < 2 minutes total
- Memory usage: < 2GB peak

#### Optimization Strategies
- Vectorized pandas operations
- Cached lookup tables
- Lazy loading for large datasets
- Parallel processing where applicable

### Integration Requirements

#### Router Integration
```python
# custom_router.py extensions
from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.august import (
    extract_drilling_and_completion_days_enhanced as drilling_enhanced,
    build_month_matrix_by_lease_enhanced as matrix_enhanced,
    build_development_financials_enhanced as financials_enhanced
)

class CustomRouter:
    def __init__(self):
        self.drilling_enhanced = drilling_enhanced.ExtractDrillingCompletionEnhanced()
        self.matrix_enhanced = matrix_enhanced.BuildMonthMatrixEnhanced()
        self.financials_enhanced = financials_enhanced.BuildDevelopmentFinancialsEnhanced()
    
    def router(self, cfg):
        # Enhanced routing conditions
        if cfg.get('drilling_completion_enhanced', {}).get('flag'):
            self.drilling_enhanced.router(cfg)
        elif cfg.get('month_matrix_enhanced', {}).get('flag'):
            self.matrix_enhanced.router(cfg)
        elif cfg.get('financials_enhanced', {}).get('flag'):
            self.financials_enhanced.router(cfg)
        # ... existing conditions
```

#### Configuration Schema
```yaml
# Enhanced module configuration
meta:
  library: worldenergydata
  module: bsee/analysis
  variant: enhanced

# Module-specific settings
module_config:
  performance:
    use_binary: true
    chunk_size: 10000
    parallel: false
  validation:
    strict: true
    tolerance: 0.001
  logging:
    level: INFO
    detailed: true
```

## Implementation Details

### ExtractDrillingCompletionEnhanced

#### Key Methods
```python
def _load_war_binary_data(self):
    """Load WAR data from binary files."""
    with open(self.cfg['filepath']['war_files']['main'], 'rb') as f:
        self.main_war = pickle.load(f)
    # Apply same transformations as text version
    self._normalize_lease_numbers()
    self._process_dates()

def _normalize_lease_numbers(self):
    """Normalize lease numbers to standard format."""
    # Remove G prefix for matching
    # Handle various formats
    
def _calculate_drilling_segments(self):
    """Calculate drilling segments with gap analysis."""
    GAP_THRESHOLD = 20  # days
    # Segment logic implementation
```

### BuildMonthMatrixEnhanced

#### Key Methods
```python
def _process_ogora_files(self):
    """Process OGORA zip files directly."""
    pattern = self.cfg['filepath'].get('pattern', 'ogora20??delimit.zip')
    for zip_path in glob.glob(pattern):
        self._process_single_ogora(zip_path)

def _build_production_matrix(self):
    """Build month-by-month production matrix."""
    # Pivot data by lease and month
    # Calculate BBL/day metrics
```

### BuildDevelopmentFinancialsEnhanced

#### Key Methods
```python
def _calculate_npv(self, cash_flows, discount_rate):
    """Calculate NPV with monthly discounting."""
    monthly_rate = (1 + discount_rate) ** (1/12) - 1
    return npv_from_monthly(cash_flows, monthly_rate)

def _calculate_mirr(self, cash_flows, finance_rate, reinvest_rate):
    """Calculate MIRR with proper rates."""
    # Implementation following original logic
```

## Error Handling Strategy

### Error Categories

#### Configuration Errors
- Missing required parameters
- Invalid file paths
- Incompatible settings

#### Data Errors
- Corrupt binary files
- Missing required columns
- Invalid data types

#### Processing Errors
- Calculation failures
- Memory exhaustion
- Timeout conditions

### Error Response Format
```python
{
    'status': 'error',
    'error_type': 'ConfigurationError',
    'message': 'Required parameter missing',
    'details': {
        'parameter': 'filepath.war_files.main',
        'suggestion': 'Add war file path to configuration'
    },
    'timestamp': '2025-08-21T10:30:00Z'
}
```

## External Dependencies

### Required Packages
```python
# pyproject.toml additions
[project.optional-dependencies]
enhanced-bsee = [
    "pickle",  # Built-in
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "openpyxl>=3.1.0",
    "loguru>=0.7.0",
    "pyyaml>=6.0",
]
```

### Data Dependencies
- Binary WAR files (pre-generated)
- OGORA zip files (historical)
- Reference outputs (validation)
- Configuration files (YAML)

## Security Considerations

### File Access
- Validate all file paths
- Prevent directory traversal
- Check file permissions
- Limit file sizes

### Data Validation
- Sanitize inputs
- Validate data types
- Check ranges and bounds
- Prevent injection attacks