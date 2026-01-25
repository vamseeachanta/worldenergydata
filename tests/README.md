# WorldEnergyData Test Suite

## Overview

This test suite provides comprehensive testing for the WorldEnergyData library, including unit tests, integration tests, performance benchmarks, and validation tests.

## Test Organization

### Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   └── modules/            # Module-specific unit tests
│       ├── bsee/          # BSEE module tests
│       └── financial/     # Financial analysis tests
├── integration/            # Integration tests for workflows
├── performance/            # Performance benchmarks
├── validation/             # Data validation tests
├── consolidated/           # Consolidated parameterized tests
└── _archived_tests/        # Archived/deprecated tests
```

### Test Categories

#### Unit Tests
- Test individual functions and classes in isolation
- Mock external dependencies
- Fast execution (< 1 second per test)
- Located in `tests/unit/`

#### Integration Tests
- Test complete workflows and module interactions
- Use real data when possible
- May take longer to execute
- Located in `tests/integration/`

#### Performance Tests
- Benchmark critical operations
- Track performance over time
- Detect performance regressions
- Located in `tests/performance/`

#### Validation Tests
- Verify data quality and integrity
- Test schema compliance
- Validate transformations
- Located in `tests/validation/`

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run in parallel
pytest tests/ -n auto

# Run with markers
pytest tests/ -m "not slow"
```

### Performance Testing

```bash
# Run performance benchmarks
pytest tests/performance/ --benchmark-only

# Compare with baseline
pytest tests/performance/ --benchmark-compare

# Generate performance report
python -m worldenergydata.testing.performance.cli report
```

### Test Markers

Tests are marked with various markers for selective execution:

- `@pytest.mark.slow` - Tests that take > 5 seconds
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.benchmark` - Performance benchmarks
- `@pytest.mark.requires_data` - Tests requiring external data

## Test Coverage

Current coverage target: 30-40% (realistic for legacy codebase)

### Coverage by Module

| Module | Coverage | Status |
|--------|----------|--------|
| worldenergydata.validation | 85% | ✅ Good |
| worldenergydata.testing | 75% | ✅ Good |
| worldenergydata.modules.bsee | 25% | 🟡 Improving |
| worldenergydata.modules.financial | 20% | 🟡 Needs work |

## Test Cleanup History

### Recent Consolidation (2025-08-21)

- **Removed**: 7 empty test files
- **Archived**: 2 obsolete tests
- **Consolidated**: 27 redundant tests into 3 parameterized tests
- **Result**: Cleaner, more maintainable test suite

### Consolidation Benefits

1. **Reduced Duplication**: 27 similar tests → 3 parameterized tests
2. **Improved Maintainability**: Single source of truth for test logic
3. **Better Coverage**: Parameterized tests cover more scenarios
4. **Faster Execution**: Less overhead from repeated setup/teardown

## Writing Tests

### Test Guidelines

1. **Follow TDD**: Write tests before implementation
2. **Use Descriptive Names**: `test_calculate_npv_with_negative_cash_flows`
3. **One Assertion Per Test**: Keep tests focused
4. **Use Fixtures**: Share setup code via pytest fixtures
5. **Mock External Dependencies**: Keep tests isolated

### Example Test Structure

```python
import pytest
from worldenergydata.modules.bsee import ProductionAnalyzer

class TestProductionAnalyzer:
    """Test suite for ProductionAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing."""
        return ProductionAnalyzer()
    
    def test_calculate_decline_rate(self, analyzer):
        """Test decline rate calculation."""
        production_data = [100, 95, 90, 85]
        rate = analyzer.calculate_decline_rate(production_data)
        assert rate == pytest.approx(0.05, rel=1e-3)
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- All pull requests
- Scheduled daily runs

See `.github/workflows/` for CI configuration.

## Performance Tracking

Performance metrics are tracked over time:
- Test execution times
- Memory usage
- Coverage trends

Access performance dashboard:
```bash
python -m worldenergydata.testing.performance.cli dashboard
```

## Contributing

When adding new tests:
1. Place in appropriate category directory
2. Use appropriate markers
3. Follow naming conventions
4. Update this documentation if needed
5. Ensure tests pass locally before pushing

## Support

For test-related issues:
- Check test output for detailed error messages
- Review test documentation
- Consult team for complex scenarios