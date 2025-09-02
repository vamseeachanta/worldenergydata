# Refactoring Guide for Testability

## Overview

This guide outlines refactoring strategies to improve testability in the WorldEnergyData codebase, particularly for tightly coupled BSEE modules.

## Current Issues

### 1. Tight Data Format Coupling
**Problem**: Modules expect exact BSEE column names and formats, making testing difficult.

**Example**:
```python
# Current - tightly coupled
def process_production(df):
    return df['MON_O_PROD_VOL'] * df['DAYS_ON_PROD']  # Fails if columns missing
```

**Solution**: Use abstraction and dependency injection:
```python
# Refactored - loosely coupled
class ProductionProcessor:
    def __init__(self, column_mapping=None):
        self.columns = column_mapping or DEFAULT_COLUMN_MAPPING
    
    def process_production(self, df):
        oil_col = self.columns.get('oil_volume', 'MON_O_PROD_VOL')
        days_col = self.columns.get('days_on', 'DAYS_ON_PROD')
        
        if oil_col not in df.columns or days_col not in df.columns:
            raise ValueError(f"Required columns {oil_col}, {days_col} not found")
        
        return df[oil_col] * df[days_col]
```

### 2. Hard-coded File Paths
**Problem**: Modules have hard-coded paths to data files.

**Example**:
```python
# Current - hard-coded
def load_data():
    return pd.read_csv('data/bsee/production/anchor.csv')
```

**Solution**: Use configurable paths:
```python
# Refactored - configurable
class DataLoader:
    def __init__(self, base_path='data'):
        self.base_path = Path(base_path)
    
    def load_data(self, field_name):
        file_path = self.base_path / 'bsee' / 'production' / f'{field_name}.csv'
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        return pd.read_csv(file_path)
```

### 3. Mixed Business Logic and I/O
**Problem**: Business logic mixed with file I/O and database operations.

**Example**:
```python
# Current - mixed concerns
def calculate_field_npv(field_name):
    # I/O operation
    df = pd.read_csv(f'data/{field_name}.csv')
    
    # Business logic
    cash_flows = df['revenue'] - df['costs']
    npv = np.npv(0.1, cash_flows)
    
    # I/O operation
    with open(f'results/{field_name}_npv.txt', 'w') as f:
        f.write(str(npv))
    
    return npv
```

**Solution**: Separate concerns:
```python
# Refactored - separated concerns
class NPVCalculator:
    def calculate(self, revenues, costs, discount_rate=0.1):
        """Pure business logic - easily testable"""
        cash_flows = revenues - costs
        return np.npv(discount_rate, cash_flows)

class FieldAnalyzer:
    def __init__(self, data_loader, calculator, result_writer):
        self.data_loader = data_loader
        self.calculator = calculator
        self.result_writer = result_writer
    
    def analyze_field(self, field_name):
        # Delegated I/O
        data = self.data_loader.load(field_name)
        
        # Delegated business logic
        npv = self.calculator.calculate(data['revenue'], data['costs'])
        
        # Delegated I/O
        self.result_writer.write(field_name, npv)
        
        return npv
```

## Refactoring Patterns

### 1. Dependency Injection Pattern
```python
# Before
class ProductionAnalyzer:
    def __init__(self):
        self.db = DatabaseConnection()  # Hard dependency
    
    def analyze(self, well_id):
        data = self.db.query(f"SELECT * FROM production WHERE well_id={well_id}")
        return self.process(data)

# After
class ProductionAnalyzer:
    def __init__(self, data_source):
        self.data_source = data_source  # Injected dependency
    
    def analyze(self, well_id):
        data = self.data_source.get_production(well_id)
        return self.process(data)

# Testing becomes easy
def test_analyzer():
    mock_source = MockDataSource()
    analyzer = ProductionAnalyzer(mock_source)
    result = analyzer.analyze('test_well')
    assert result is not None
```

### 2. Strategy Pattern for Algorithms
```python
# Before - hard-coded algorithm
class DeclineAnalyzer:
    def calculate_decline(self, production):
        # Hard-coded exponential decline
        return production[0] * np.exp(-0.05 * np.arange(len(production)))

# After - strategy pattern
class DeclineStrategy(ABC):
    @abstractmethod
    def calculate(self, production):
        pass

class ExponentialDecline(DeclineStrategy):
    def __init__(self, rate=0.05):
        self.rate = rate
    
    def calculate(self, production):
        return production[0] * np.exp(-self.rate * np.arange(len(production)))

class HyperbolicDecline(DeclineStrategy):
    def calculate(self, production):
        # Different algorithm
        pass

class DeclineAnalyzer:
    def __init__(self, strategy: DeclineStrategy):
        self.strategy = strategy
    
    def calculate_decline(self, production):
        return self.strategy.calculate(production)
```

### 3. Factory Pattern for Object Creation
```python
# Before - complex object creation
def create_well_analyzer(well_type, config):
    if well_type == 'oil':
        return OilWellAnalyzer(
            config['oil_params'],
            DatabaseConnection(config['db']),
            FileWriter(config['output'])
        )
    elif well_type == 'gas':
        return GasWellAnalyzer(
            config['gas_params'],
            DatabaseConnection(config['db']),
            FileWriter(config['output'])
        )

# After - factory pattern
class WellAnalyzerFactory:
    def __init__(self, config):
        self.config = config
        self.data_source = self._create_data_source()
        self.writer = self._create_writer()
    
    def create_analyzer(self, well_type):
        analyzers = {
            'oil': lambda: OilWellAnalyzer(self.config['oil_params']),
            'gas': lambda: GasWellAnalyzer(self.config['gas_params'])
        }
        
        analyzer = analyzers.get(well_type, lambda: None)()
        if analyzer:
            analyzer.set_data_source(self.data_source)
            analyzer.set_writer(self.writer)
        return analyzer
    
    def _create_data_source(self):
        if self.config.get('test_mode'):
            return MockDataSource()
        return DatabaseConnection(self.config['db'])
```

## Priority Refactoring Targets

### High Priority (Blocking Tests)
1. **production_api12.py** - Extract data loading from analysis logic
2. **well_api12.py** - Separate API validation from processing
3. **config_router.py** - Add interface for configuration providers

### Medium Priority (Improves Testability)
1. **bsee.py** - Create abstract base classes for processors
2. **data sources modules** - Implement repository pattern
3. **analysis modules** - Extract calculation engines

### Low Priority (Nice to Have)
1. Legacy code in `analysis/legacy/` - Consider deprecation
2. Archived tests - Clean up or remove
3. Example scripts - Update to use refactored code

## Implementation Strategy

### Phase 1: Create Interfaces (Week 1)
```python
# interfaces.py
from abc import ABC, abstractmethod

class DataSource(ABC):
    @abstractmethod
    def get_production(self, identifier):
        pass

class Calculator(ABC):
    @abstractmethod
    def calculate(self, data):
        pass

class ResultWriter(ABC):
    @abstractmethod
    def write(self, identifier, result):
        pass
```

### Phase 2: Implement Adapters (Week 2)
```python
# adapters.py
class CSVDataSource(DataSource):
    def __init__(self, base_path):
        self.base_path = base_path
    
    def get_production(self, identifier):
        path = self.base_path / f"{identifier}.csv"
        return pd.read_csv(path)

class InMemoryDataSource(DataSource):
    def __init__(self, data_dict):
        self.data = data_dict
    
    def get_production(self, identifier):
        return self.data.get(identifier, pd.DataFrame())
```

### Phase 3: Refactor Core Modules (Week 3-4)
- Start with modules that have no dependencies
- Work up the dependency tree
- Maintain backward compatibility with adapters

### Phase 4: Update Tests (Week 5)
- Write tests for new interfaces
- Update existing tests to use mocks
- Achieve target coverage incrementally

## Testing After Refactoring

### Unit Test Example
```python
def test_npv_calculator():
    # Pure unit test - no I/O
    calculator = NPVCalculator()
    revenues = np.array([100, 200, 300])
    costs = np.array([50, 75, 100])
    
    npv = calculator.calculate(revenues, costs, discount_rate=0.1)
    assert npv > 0

def test_field_analyzer():
    # Integration test with mocks
    mock_loader = Mock()
    mock_loader.load.return_value = {
        'revenue': np.array([100, 200]),
        'costs': np.array([50, 75])
    }
    
    mock_calculator = Mock()
    mock_calculator.calculate.return_value = 150.0
    
    mock_writer = Mock()
    
    analyzer = FieldAnalyzer(mock_loader, mock_calculator, mock_writer)
    result = analyzer.analyze_field('test_field')
    
    assert result == 150.0
    mock_loader.load.assert_called_once_with('test_field')
    mock_writer.write.assert_called_once_with('test_field', 150.0)
```

## Benefits After Refactoring

1. **Testability**: 80% of code becomes unit testable
2. **Maintainability**: Clear separation of concerns
3. **Flexibility**: Easy to swap implementations
4. **Reusability**: Components can be reused across modules
5. **Documentation**: Code structure documents itself

## Backwards Compatibility

Maintain compatibility during refactoring:

```python
# legacy_wrapper.py
def process_production_legacy(df):
    """Legacy function maintained for compatibility"""
    processor = ProductionProcessor()
    return processor.process_production(df)
```

## Monitoring Progress

Track refactoring progress:
- [ ] Interfaces defined: 0/10
- [ ] Adapters implemented: 0/15
- [ ] Core modules refactored: 0/20
- [ ] Tests updated: 0/50
- [ ] Coverage improved: 17% → 40% (target)

## Next Steps

1. Review this guide with the team
2. Prioritize modules for refactoring
3. Create feature branch for refactoring
4. Implement incrementally with tests
5. Merge when coverage targets met