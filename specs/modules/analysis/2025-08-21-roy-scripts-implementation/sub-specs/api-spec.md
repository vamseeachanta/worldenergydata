# API Specification

This is the API specification for the spec detailed in @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/spec.md

> Module: bsee/analysis
> Created: 2025-08-21
> Version: 1.0.0

## Module APIs

### ExtractDrillingCompletionEnhanced

**Module Path:** `worldenergydata.modules.bsee.analysis.custom_scripts.Roy.august.extract_drilling_and_completion_days_enhanced`

#### Class Definition
```python
class ExtractDrillingCompletionEnhanced:
    """Enhanced drilling and completion days analysis with binary file support."""
```

#### Public Methods

##### `__init__()`
```python
def __init__(self) -> None:
    """Initialize enhanced drilling analysis module."""
```

##### `router(cfg)`
```python
def router(self, cfg: dict) -> dict:
    """
    Main entry point for framework routing.
    
    Args:
        cfg (dict): Configuration dictionary from YAML
        
    Returns:
        dict: Updated configuration with results
        
    Raises:
        FileNotFoundError: If required data files missing
        KeyError: If required config parameters missing
        ValueError: If data validation fails
    """
```

#### Configuration Interface
```python
{
    'drilling_completion_enhanced': {
        'flag': bool,  # Enable this module
        'filepath': {
            'leases': str,  # Path to leases_enhanced.xlsx
            'war_files': {
                'main': str,  # mv_war_main.bin path
                'boreholes': str,  # mv_war_boreholes_view.bin path
                'prop': str,  # mv_war_main_prop.bin path
                'remarks': str  # mv_war_main_prop_remark.bin path
            },
            'output': str  # Output Excel path
        },
        'parameters': {
            'drill_gap_days': int,  # Default: 20
            'comp_gap_days': int,  # Default: 8
            'spud_gap_threshold': int  # Default: 300
        }
    }
}
```

### BuildMonthMatrixEnhanced

**Module Path:** `worldenergydata.modules.bsee.analysis.custom_scripts.Roy.august.build_month_matrix_by_lease_enhanced`

#### Class Definition
```python
class BuildMonthMatrixEnhanced:
    """Enhanced multi-year production matrix generation from OGORA files."""
```

#### Public Methods

##### `__init__()`
```python
def __init__(self) -> None:
    """Initialize enhanced matrix builder module."""
```

##### `router(cfg)`
```python
def router(self, cfg: dict) -> dict:
    """
    Main entry point for framework routing.
    
    Args:
        cfg (dict): Configuration dictionary
        
    Returns:
        dict: Updated configuration
        
    Raises:
        FileNotFoundError: If OGORA files not found
        ValueError: If data processing fails
    """
```

#### Configuration Interface
```python
{
    'month_matrix_enhanced': {
        'flag': bool,  # Enable this module
        'filepath': {
            'leases': str,  # Path to leases file
            'ogora_dir': str,  # Directory with OGORA zips
            'pattern': str,  # Default: 'ogora20??delimit.zip'
            'output': str  # Output Excel path
        },
        'parameters': {
            'group_mode': str,  # 'leases' or 'group'
            'group_col': str,  # Column for grouping
            'year_range': list  # Optional: [2020, 2023]
        }
    }
}
```

### BuildDevelopmentFinancialsEnhanced

**Module Path:** `worldenergydata.modules.bsee.analysis.custom_scripts.Roy.august.build_development_financials_enhanced`

#### Class Definition
```python
class BuildDevelopmentFinancialsEnhanced:
    """Enhanced financial analysis for development projects."""
```

#### Public Methods

##### `__init__()`
```python
def __init__(self) -> None:
    """Initialize enhanced financial analysis module."""
```

##### `router(cfg)`
```python
def router(self, cfg: dict) -> dict:
    """
    Main entry point for framework routing.
    
    Args:
        cfg (dict): Configuration dictionary
        
    Returns:
        dict: Updated configuration with financial results
        
    Raises:
        FileNotFoundError: If input files missing
        ValueError: If calculations fail
    """
```

#### Configuration Interface
```python
{
    'financials_enhanced': {
        'flag': bool,  # Enable this module
        'filepath': {
            'leases': str,  # Leases configuration
            'assumptions': str,  # Financial assumptions
            'production': str,  # Production matrix input
            'drilling': str,  # Drilling data input
            'wti': str,  # WTI pricing (optional)
            'output': str  # Output Excel path
        },
        'parameters': {
            'discount_rate': float,  # NPV discount rate
            'tax_rate': float,  # Corporate tax rate
            'price_model': str  # 'flat' or 'monthly'
        }
    }
}
```

## Router API Extensions

### CustomRouter Modifications

**Module Path:** `worldenergydata.modules.bsee.custom_router`

#### Extended Router Method
```python
def router(self, cfg: dict) -> dict:
    """
    Extended router with enhanced module support.
    
    New routing conditions:
    - drilling_completion_enhanced
    - month_matrix_enhanced  
    - financials_enhanced
    
    Args:
        cfg (dict): Configuration dictionary
        
    Returns:
        dict: Processed configuration
    """
```

## Data Structures

### Common Data Types

#### LeaseInfo
```python
@dataclass
class LeaseInfo:
    lease_num: str
    lease_name: str
    water_depth: Optional[float]
    dev_name: Optional[str]
```

#### WellData
```python
@dataclass
class WellData:
    api_number: str
    well_name: str
    spud_date: datetime
    td_date: datetime
    drilling_days: int
    completion_days: int
```

#### ProductionData
```python
@dataclass
class ProductionData:
    lease_num: str
    well_name: str
    year_month: str
    bbls_per_day: float
    days_on: int
```

## Error Responses

### Standard Error Format
```python
class EnhancedAnalysisError(Exception):
    """Base exception for enhanced analysis modules."""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
```

### Error Types

#### ConfigurationError
```python
raise ConfigurationError(
    "Missing required configuration parameter",
    {'parameter': 'filepath.war_files.main', 'module': 'drilling_enhanced'}
)
```

#### DataValidationError
```python
raise DataValidationError(
    "Invalid data format in input file",
    {'file': 'leases_enhanced.xlsx', 'issue': 'Missing LEASE_NUM column'}
)
```

#### ProcessingError
```python
raise ProcessingError(
    "Analysis failed during processing",
    {'stage': 'drilling_segments', 'error': str(e)}
)
```

## Usage Examples

### Example 1: Drilling Analysis
```python
from worldenergydata.engine import Engine

config = {
    'meta': {
        'library': 'worldenergydata',
        'basename': 'bsee_custom'
    },
    'basename': 'bsee_custom',
    'drilling_completion_enhanced': {
        'flag': True,
        'filepath': {
            'leases': 'tests/modules/bsee/analysis/leases_enhanced.xlsx',
            'war_files': {
                'main': 'data/modules/bsee/bin/war/mv_war_main.bin'
            },
            'output': 'results/drilling_enhanced.xlsx'
        }
    }
}

engine = Engine()
result = engine.process(config)
```

### Example 2: Complete Workflow
```python
# Run all three analyses in sequence
configs = [
    drilling_config,
    matrix_config,
    financial_config
]

for cfg in configs:
    engine.process(cfg)
    
# Validate results
validate_against_reference()