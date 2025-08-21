# Implementation Strategy for Source Code Integration

> Document: Strategy for Implementing Financial Analysis in src/
> Created: 2025-08-21
> Target: src/worldenergydata/modules/bsee/analysis/

## Executive Summary

This document outlines the strategy for implementing SME Roy's consolidated financial analysis methodology into the worldenergydata source code, ensuring clean architecture, maintainability, and full test coverage.

## Architecture Overview

### Module Hierarchy
```
src/worldenergydata/modules/bsee/analysis/sme_financial/
├── __init__.py                    # Module exports and version
├── config.py                      # Configuration and constants
├── models/                        # Data models
│   ├── __init__.py
│   ├── lease.py                  # Lease data model
│   ├── production.py             # Production data model
│   └── financial.py              # Financial results model
├── processors/                    # Core processing logic
│   ├── __init__.py
│   ├── lease_processor.py        # Lease grouping and aggregation
│   ├── drilling_completion.py    # D&C analysis
│   ├── cash_flow_calculator.py   # Financial calculations
│   └── npv_calculator.py         # NPV and economic metrics
├── io/                           # Input/Output handling
│   ├── __init__.py
│   ├── data_loader.py           # File loading utilities
│   ├── excel_reader.py          # Excel-specific reading
│   └── report_generator.py      # Output generation
├── adapters/                     # BSEE data adapters
│   ├── __init__.py
│   └── bsee_adapter.py          # BSEE format conversion
├── utils/                        # Utilities
│   ├── __init__.py
│   ├── validators.py            # Data validation
│   ├── formatters.py            # Output formatting
│   └── date_utils.py            # Date handling
├── cli.py                        # Command-line interface
└── financial_analyzer.py        # Main orchestrator
```

## Implementation Phases

### Phase 1: Core Infrastructure (Days 1-2)

#### 1.1 Configuration Module
```python
# config.py
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FinancialConfig:
    """Configuration for financial analysis"""
    discount_rate: float = 0.10
    tax_rate: float = 0.35
    royalty_rate: float = 0.1875
    opex_per_bbl: float = 10.0
    gap_threshold_days: int = 300
    
    @classmethod
    def from_yaml(cls, path: str) -> 'FinancialConfig':
        """Load configuration from YAML file"""
        pass

LEASE_GROUP_MAPPINGS: Dict[str, str] = {
    'Stones': 'Stones',
    'Cascade': 'Cascade Chinook',
    'Chinook': 'Cascade Chinook',
    # ... rest of mappings
}
```

#### 1.2 Data Models
```python
# models/lease.py
from dataclasses import dataclass
from typing import Optional, List
import pandas as pd

@dataclass
class Lease:
    """Lease data model"""
    name: str
    group: str
    api_numbers: List[str]
    start_date: pd.Timestamp
    assumptions: Optional[Dict] = None
    
    def validate(self) -> bool:
        """Validate lease data"""
        pass
```

### Phase 2: Data Processing (Days 3-4)

#### 2.1 Lease Processor
```python
# processors/lease_processor.py
class LeaseProcessor:
    """Process and group lease data"""
    
    def __init__(self, config: FinancialConfig):
        self.config = config
        self.group_mappings = LEASE_GROUP_MAPPINGS
    
    def process_leases(self, lease_df: pd.DataFrame) -> Dict[str, Lease]:
        """Process lease DataFrame into Lease objects"""
        pass
    
    def group_leases(self, leases: List[Lease]) -> Dict[str, List[Lease]]:
        """Group leases by configured mappings"""
        pass
```

#### 2.2 Cash Flow Calculator
```python
# processors/cash_flow_calculator.py
class CashFlowCalculator:
    """Calculate monthly cash flows"""
    
    def calculate_revenue(self, production: pd.Series, 
                         oil_price: pd.Series,
                         royalty_rate: float) -> pd.Series:
        """Calculate gross and net revenue"""
        pass
    
    def calculate_opex(self, production: pd.Series,
                       opex_rate: float) -> pd.Series:
        """Calculate operating expenses"""
        pass
    
    def calculate_taxes(self, ebitda: pd.Series,
                       tax_rate: float) -> pd.Series:
        """Calculate tax obligations"""
        pass
```

### Phase 3: Financial Analysis Engine (Days 5-6)

#### 3.1 Main Analyzer
```python
# financial_analyzer.py
class FinancialAnalyzer:
    """Main financial analysis orchestrator"""
    
    def __init__(self, config: Optional[FinancialConfig] = None):
        self.config = config or FinancialConfig()
        self.lease_processor = LeaseProcessor(self.config)
        self.cash_flow_calc = CashFlowCalculator()
        self.report_gen = ReportGenerator()
    
    def analyze(self, **inputs) -> AnalysisResults:
        """Run complete financial analysis"""
        # 1. Load and validate data
        # 2. Process leases
        # 3. Calculate financials
        # 4. Generate results
        pass
```

### Phase 4: Output Generation (Days 7-8)

#### 4.1 Report Generator
```python
# io/report_generator.py
class ReportGenerator:
    """Generate formatted Excel reports"""
    
    def create_workbook(self, results: AnalysisResults) -> None:
        """Create Excel workbook with all sheets"""
        pass
    
    def format_worksheet(self, worksheet: Worksheet) -> None:
        """Apply standard formatting"""
        pass
    
    def add_readme_sheet(self, workbook: Workbook) -> None:
        """Add README as first sheet"""
        pass
```

## Testing Strategy

### Unit Test Structure
```
tests/modules/bsee/analysis/sme_financial/
├── test_config.py
├── test_models/
│   ├── test_lease.py
│   └── test_financial.py
├── test_processors/
│   ├── test_lease_processor.py
│   ├── test_cash_flow_calculator.py
│   └── test_npv_calculator.py
├── test_io/
│   ├── test_data_loader.py
│   └── test_report_generator.py
├── test_integration.py
└── fixtures/
    └── sample_data/
```

### Test Coverage Requirements
- Minimum 90% code coverage
- All public methods must have tests
- Edge cases and error conditions tested
- Integration tests for full pipeline

### Example Unit Test
```python
# test_cash_flow_calculator.py
import pytest
import pandas as pd
from worldenergydata.modules.bsee.analysis.sme_financial.processors import CashFlowCalculator

class TestCashFlowCalculator:
    
    @pytest.fixture
    def calculator(self):
        return CashFlowCalculator()
    
    def test_calculate_revenue(self, calculator):
        production = pd.Series([1000, 2000, 1500])
        oil_price = pd.Series([50, 55, 52])
        royalty = 0.1875
        
        revenue = calculator.calculate_revenue(production, oil_price, royalty)
        
        expected = pd.Series([40625, 89375, 63375])
        pd.testing.assert_series_equal(revenue, expected)
```

## Integration with Existing Code

### Leverage Existing Utilities
```python
# Use existing worldenergydata utilities
from worldenergydata.utils.data_loader import load_excel_data
from worldenergydata.utils.validators import validate_dataframe
from worldenergydata.modules.bsee.common import normalize_api_number
```

### Maintain Compatibility
- Support existing YAML configuration format
- Compatible with current BSEE data structures
- Preserve existing API interfaces where possible

## Performance Optimization

### Optimization Techniques
1. **Vectorization**: Use pandas/numpy operations
2. **Caching**: Cache expensive calculations
3. **Parallel Processing**: Process leases in parallel
4. **Memory Management**: Process large datasets in chunks

### Performance Targets
```python
# Performance decorator for monitoring
from functools import wraps
import time

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        if duration > 1.0:  # Log if takes more than 1 second
            logger.warning(f"{func.__name__} took {duration:.2f}s")
        
        return result
    return wrapper
```

## CLI Implementation

### Command Structure
```bash
# Basic usage
python -m worldenergydata.modules.bsee.analysis.sme_financial analyze \
    --leases data/leases.xlsx \
    --production data/production.xlsx \
    --output results.xlsx

# With configuration
python -m worldenergydata.modules.bsee.analysis.sme_financial analyze \
    --config config/financial.yaml \
    --output results.xlsx

# From BSEE data
python -m worldenergydata.modules.bsee.analysis.sme_financial analyze \
    --from-bsee data/modules/bsee/ \
    --output results.xlsx
```

### CLI Implementation
```python
# cli.py
import click
from pathlib import Path

@click.group()
def cli():
    """BSEE Financial Analysis CLI"""
    pass

@cli.command()
@click.option('--config', type=Path, help='Configuration file')
@click.option('--output', type=Path, required=True, help='Output file')
@click.option('--from-bsee', type=Path, help='BSEE data directory')
def analyze(config, output, from_bsee):
    """Run financial analysis"""
    analyzer = FinancialAnalyzer.from_config(config)
    
    if from_bsee:
        results = analyzer.analyze_from_bsee(from_bsee)
    else:
        results = analyzer.analyze()
    
    analyzer.export_results(results, output)
```

## Documentation Requirements

### API Documentation
```python
def calculate_npv(cash_flows: pd.Series, 
                  discount_rate: float = 0.10) -> float:
    """
    Calculate Net Present Value of cash flows.
    
    Args:
        cash_flows: Monthly cash flow series
        discount_rate: Annual discount rate (default 10%)
    
    Returns:
        NPV in dollars
    
    Example:
        >>> cf = pd.Series([1000, 2000, 3000])
        >>> npv = calculate_npv(cf, 0.10)
        >>> print(f"NPV: ${npv:,.2f}")
    """
    pass
```

### User Documentation
- README.md with installation and usage
- API reference documentation
- Example notebooks
- Configuration guide

## Quality Assurance

### Code Quality Tools
```yaml
# pyproject.toml
[tool.black]
line-length = 100

[tool.isort]
profile = "black"

[tool.mypy]
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8
```

## Deployment Checklist

### Pre-deployment
- [ ] All tests passing
- [ ] Code coverage > 90%
- [ ] Documentation complete
- [ ] Code review completed
- [ ] Performance benchmarks met

### Deployment
- [ ] Version bump in __init__.py
- [ ] Update CHANGELOG.md
- [ ] Create git tag
- [ ] Build package
- [ ] Deploy to PyPI/internal registry

### Post-deployment
- [ ] Verify installation
- [ ] Run smoke tests
- [ ] Monitor for issues
- [ ] Update dependent projects

## Risk Mitigation

### Technical Risks
1. **Data Format Changes**: Use adapters for flexibility
2. **Performance Issues**: Implement caching and optimization
3. **Memory Constraints**: Stream processing for large files
4. **Calculation Errors**: Comprehensive testing and validation

### Mitigation Strategies
- Gradual rollout with feature flags
- Parallel run with existing system
- Comprehensive error logging
- Rollback procedures

## Success Metrics

### Technical Metrics
- Test coverage: > 90%
- Performance: < 60s for 100 leases
- Memory usage: < 2GB
- Error rate: < 0.1%

### Business Metrics
- Calculation accuracy: 99.99%
- User adoption rate
- Processing time reduction
- Support ticket reduction

## Timeline

### Week 1
- Days 1-2: Core infrastructure
- Days 3-4: Data processing
- Day 5: Integration and testing

### Week 2
- Days 6-7: Financial engine
- Days 8-9: Output generation
- Day 10: Testing and documentation

### Week 3
- Days 11-12: Integration testing
- Days 13-14: Performance optimization
- Day 15: Deployment preparation

## Notes

- Follow TDD approach throughout
- Use real BSEE data for testing
- Maintain backward compatibility
- Document all design decisions
- Regular code reviews at phase boundaries