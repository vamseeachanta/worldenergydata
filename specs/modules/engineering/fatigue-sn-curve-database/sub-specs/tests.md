# Tests Specification

This is the tests coverage details for the spec detailed in @specs/fatigue-sn-curve-database/spec.md

> Created: 2025-08-16
> Version: 1.0.0

## Test Coverage

### Unit Tests

**SNcurve Class**
- Test bilinear curve calculation with two segments
- Test single-slope curve calculation
- Test endurance limit behavior
- Test thickness correction factor application
- Test stress/life interpolation within segments
- Test extrapolation warning beyond curve range
- Verify log-log linear relationship

**Database Query**
- Test query by standard and classification
- Test filtering by material type
- Test environment-based filtering
- Test multiple filter combinations
- Test empty result handling
- Test invalid query parameters
- Test case-insensitive matching

**Data Validation**
- Test slope parameter bounds (2.0 < m < 10.0)
- Test log A parameter reasonable range
- Test stress must be positive
- Test cycles must be positive
- Test segment continuity (no gaps)
- Test segment order (decreasing stress)

**Calculation Methods**
- Test life calculation accuracy against known values
- Test stress calculation inverse relationship
- Test cumulative damage calculation (Miner's rule)
- Test thickness correction formula
- Test stress unit conversion (MPa/ksi)

### Integration Tests

**Data Loading**
- Test loading from Parquet files
- Test loading from JSON metadata
- Test handling missing data files
- Test corrupted file recovery
- Test schema version compatibility
- Test lazy loading performance

**Standard Coverage**
- Test API RP 2A curves match published values
- Test DNV-RP-C203 curves against examples
- Test ISO 19902 implementation
- Test ABS guideline curves
- Cross-validate equivalent classifications

**Cross-Repository Integration**
- Test integration with digitalmodel repository
- Test data export for external tools
- Test API compatibility
- Test batch processing capabilities

### Feature Tests

**Complete Data Collection Workflow**
- Extract S-N curve from PDF standard
- Digitize and validate curve parameters
- Store in database with metadata
- Query and retrieve curve
- Calculate fatigue life
- Export for analysis tool

**Multi-Standard Comparison**
- Load curves from different standards
- Compare same material across standards
- Generate comparison plots
- Identify most conservative curve
- Export comparison results

**Engineering Analysis Integration**
- Import stress time history
- Apply rainflow counting
- Calculate damage for each cycle
- Sum cumulative damage
- Report fatigue life

### Performance Tests

**Query Performance**
- Single curve retrieval: < 10ms
- Batch query (100 curves): < 100ms
- Complex filter query: < 50ms
- Full database load: < 500ms

**Calculation Performance**
- Single life calculation: < 1ms
- Batch calculation (1000 points): < 100ms
- Damage summation (10000 cycles): < 500ms
- Thickness correction: < 1ms additional

**Memory Usage**
- Full database in memory: < 100MB
- Single curve object: < 1KB
- Query result set (100 curves): < 100KB
- Export generation: < 2x data size

### Edge Case Tests

**Boundary Conditions**
- Stress at exactly segment transition
- Cycles at exactly 10^7 (typical transition)
- R = -1 (fully reversed loading)
- R = 0 (zero to tension)
- Thickness = reference thickness

**Invalid Inputs**
- Negative stress values
- Zero stress
- Negative cycles
- Non-existent standard
- Invalid classification
- Thickness < 0

**Data Quality Issues**
- Missing segments in curve
- Overlapping segments
- Non-monotonic curve
- Unrealistic parameters (m > 10)
- Missing metadata fields

### Validation Tests

**Engineering Validation**
- Verify fatigue life decreases with increasing stress
- Verify slope typically 3.0 for welded joints
- Verify slope typically 5.0 after transition
- Verify air curves less conservative than seawater
- Verify cathodic protection effect

**Cross-Standard Validation**
- DNV Class D ≈ API RP 2A X-curve
- ISO 19902 aligns with DNV for same class
- BS 7608 Class F similar to DNV Class F
- Consistent ranking of curve conservatism

**Benchmark Validation**
- Test against published example problems
- Verify against industry software results
- Compare with hand calculations
- Validate using case studies

## Test Data Sets

### Reference Curves
```python
# Known S-N curve for validation
test_curve_dnv_d = {
    "standard": "DNV-RP-C203",
    "classification": "D",
    "segments": [
        {"log_a": 12.164, "m": 3.0, "range": [52.63, 1000]},
        {"log_a": 15.606, "m": 5.0, "range": [0, 52.63]}
    ],
    "test_points": [
        {"stress": 100, "expected_life": 2.16e6},
        {"stress": 200, "expected_life": 2.70e5},
        {"stress": 50, "expected_life": 1.14e8}
    ]
}
```

### Stress Histories
```python
# Typical offshore loading spectrum
test_stress_history = [
    {"stress": 150, "cycles": 1e5},
    {"stress": 120, "cycles": 5e5},
    {"stress": 100, "cycles": 2e6},
    {"stress": 80, "cycles": 1e7}
]
# Expected damage: ~0.55
```

### Material Properties
```python
test_materials = {
    "carbon_steel": {
        "grades": ["S355", "S420", "S460"],
        "yield_range": [355, 460],
        "environment": ["air", "seawater", "seawater_cp"]
    },
    "stainless_steel": {
        "grades": ["316L", "2205"],
        "yield_range": [240, 450],
        "environment": ["air", "seawater"]
    }
}
```

## Mocking Requirements

### External Dependencies
- **PDF Parser**: Mock PDF extraction for testing
- **File System**: Mock file I/O for unit tests
- **Network**: No network dependencies

### Data Mocking
```python
@pytest.fixture
def mock_sn_database():
    """Provide test database with known curves"""
    return SNcurveDatabase(data_path="tests/fixtures/test_data.parquet")

@pytest.fixture
def mock_dnv_curve():
    """Standard DNV D-curve for testing"""
    return SNcurve(
        standard="DNV-RP-C203",
        classification="D",
        segments=[...],
        environment="seawater_cp"
    )
```

## Test Execution Strategy

### Continuous Integration
```yaml
# GitHub Actions workflow
test:
  - pytest tests/unit --cov=worldenergydata.fatigue
  - pytest tests/integration
  - pytest tests/validation --slow
  - pytest tests/performance --benchmark
```

### Test Organization
```
tests/
├── unit/
│   ├── test_sn_curve.py
│   ├── test_database.py
│   └── test_calculations.py
├── integration/
│   ├── test_data_loading.py
│   ├── test_standards.py
│   └── test_external_integration.py
├── validation/
│   ├── test_engineering_validation.py
│   └── test_benchmark_cases.py
└── fixtures/
    ├── test_curves.json
    └── test_data.parquet
```

## Success Criteria

- 95% code coverage for core modules
- All engineering validation tests pass
- Performance benchmarks met
- Zero data integrity errors
- Successful integration with digitalmodel
- All standard curves validated against sources