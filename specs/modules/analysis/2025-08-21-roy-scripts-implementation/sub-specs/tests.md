# Tests Specification

This is the tests coverage details for the spec detailed in @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/spec.md

> Module: bsee/analysis
> Created: 2025-08-21
> Version: 1.0.0

## Test Structure

### Test Organization
```
tests/
└── modules/
    └── bsee/
        └── analysis/
            ├── 2025-08-21-enhanced-bsee-testing/
            │   ├── results/
            │   ├── test_drilling_enhanced.py
            │   ├── test_matrix_enhanced.py
            │   ├── test_financials_enhanced.py
            │   └── test_integration_enhanced.py
            ├── fixtures/
            │   ├── sample_war_data.pkl
            │   ├── sample_ogora.zip
            │   └── reference_outputs/
            └── configs/
                ├── drilling_completion_days_config_enhanced.yml
                ├── month_matrix_config_enhanced.yml
                └── financials_config_enhanced.yml
```

## Unit Tests

### ExtractDrillingCompletionEnhanced Tests

**File:** `test_drilling_enhanced.py`

```python
class TestExtractDrillingEnhanced:
    """Unit tests for enhanced drilling analysis."""
    
    def test_binary_file_loading(self):
        """Test loading WAR data from binary files."""
        # Test successful pickle load
        # Test handling corrupt files
        # Test missing files
    
    def test_lease_normalization(self):
        """Test lease number normalization logic."""
        # Test G-prefix handling
        # Test various formats
        # Test edge cases
    
    def test_spud_date_adjustment(self):
        """Test spud date adjustment with gaps."""
        # Test gap threshold logic
        # Test early days calculation
        # Test boundary conditions
    
    def test_completion_segmentation(self):
        """Test completion days segmentation."""
        # Test gap detection
        # Test segment merging
        # Test post-TD filtering
    
    def test_data_validation(self):
        """Test input data validation."""
        # Test missing columns
        # Test invalid dates
        # Test data type conversions
```

### BuildMonthMatrixEnhanced Tests

**File:** `test_matrix_enhanced.py`

```python
class TestBuildMonthMatrixEnhanced:
    """Unit tests for enhanced matrix generation."""
    
    def test_ogora_zip_reading(self):
        """Test direct OGORA zip file processing."""
        # Test zip file reading
        # Test encoding handling
        # Test corrupt zip handling
    
    def test_production_aggregation(self):
        """Test production data aggregation."""
        # Test monthly aggregation
        # Test BBL/day calculations
        # Test missing data handling
    
    def test_lease_grouping(self):
        """Test lease grouping logic."""
        # Test group_mode options
        # Test sheet name generation
        # Test name truncation
    
    def test_matrix_pivoting(self):
        """Test production matrix pivoting."""
        # Test pivot structure
        # Test column ordering
        # Test value aggregation
```

### BuildDevelopmentFinancialsEnhanced Tests

**File:** `test_financials_enhanced.py`

```python
class TestBuildFinancialsEnhanced:
    """Unit tests for enhanced financial analysis."""
    
    def test_npv_calculation(self):
        """Test NPV calculation accuracy."""
        # Test monthly discounting
        # Test cash flow handling
        # Test rate conversions
    
    def test_mirr_calculation(self):
        """Test MIRR calculation logic."""
        # Test finance rate
        # Test reinvestment rate
        # Test edge cases
    
    def test_capex_allocation(self):
        """Test CAPEX allocation logic."""
        # Test facilities allocation
        # Test drilling costs
        # Test timing logic
    
    def test_tax_calculations(self):
        """Test tax calculation accuracy."""
        # Test corporate tax
        # Test tax savings
        # Test after-tax cash flows
```

## Integration Tests

### Module Integration Tests

**File:** `test_integration_enhanced.py`

```python
class TestEnhancedIntegration:
    """Integration tests for enhanced modules."""
    
    def test_drilling_to_matrix_flow(self):
        """Test data flow from drilling to matrix."""
        # Run drilling analysis
        # Verify output structure
        # Use output in matrix generation
        # Validate matrix results
    
    def test_matrix_to_financials_flow(self):
        """Test data flow from matrix to financials."""
        # Generate production matrix
        # Load in financial analysis
        # Verify data integration
        # Check financial outputs
    
    def test_complete_workflow(self):
        """Test complete end-to-end workflow."""
        # Execute all three analyses
        # Verify data dependencies
        # Check final outputs
        # Validate against reference
    
    def test_router_integration(self):
        """Test custom router integration."""
        # Test flag detection
        # Test routing logic
        # Test error handling
        # Test configuration passing
```

## Feature Tests

### End-to-End Validation

```python
class TestEndToEndValidation:
    """Complete workflow validation tests."""
    
    @pytest.fixture
    def reference_data(self):
        """Load reference output files."""
        return {
            'drilling': pd.read_excel('reference/drilling.xlsx'),
            'matrix': pd.read_excel('reference/matrix.xlsx'),
            'financials': pd.read_excel('reference/financials.xlsx')
        }
    
    def test_drilling_reference_match(self, reference_data):
        """Validate drilling output against reference."""
        output = run_drilling_enhanced()
        ref = reference_data['drilling']
        
        # Check row count
        assert len(output) == len(ref)
        
        # Check first 5 rows
        assert_frame_equal(
            output.head(5),
            ref.head(5),
            check_dtype=False
        )
    
    def test_matrix_reference_match(self, reference_data):
        """Validate matrix output against reference."""
        output = run_matrix_enhanced()
        ref = reference_data['matrix']
        
        # Check sheet names
        assert set(output.sheet_names) == set(ref.sheet_names)
        
        # Check data structure
        for sheet in output.sheet_names:
            assert_structure_match(output[sheet], ref[sheet])
    
    def test_financials_reference_match(self, reference_data):
        """Validate financial output against reference."""
        output = run_financials_enhanced()
        ref = reference_data['financials']
        
        # Check NPV within tolerance
        assert abs(output['NPV'] - ref['NPV']) < 1000
        
        # Check MIRR within tolerance
        assert abs(output['MIRR'] - ref['MIRR']) < 0.001
```

## Performance Tests

### Benchmark Tests

```python
class TestPerformance:
    """Performance benchmark tests."""
    
    @pytest.mark.benchmark
    def test_drilling_performance(self, benchmark):
        """Benchmark drilling analysis performance."""
        result = benchmark(run_drilling_enhanced)
        assert benchmark.stats['mean'] < 30  # seconds
    
    @pytest.mark.benchmark
    def test_matrix_performance(self, benchmark):
        """Benchmark matrix generation performance."""
        result = benchmark(run_matrix_enhanced)
        assert benchmark.stats['mean'] < 60  # seconds
    
    @pytest.mark.benchmark
    def test_memory_usage(self):
        """Test peak memory usage."""
        import tracemalloc
        tracemalloc.start()
        
        run_complete_workflow()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        assert peak / 1024 / 1024 < 2000  # MB
```

## Mocking Requirements

### Mock Data Generation

```python
@pytest.fixture
def mock_war_data():
    """Generate mock WAR binary data."""
    data = pd.DataFrame({
        'API_WELL_NUMBER': ['1234567890'] * 100,
        'SURF_LEASE_NUM': ['G12345'] * 100,
        'WAR_START_DT': pd.date_range('2020-01-01', periods=100),
        'WAR_END_DT': pd.date_range('2020-01-02', periods=100)
    })
    
    with tempfile.NamedTemporaryFile(suffix='.bin') as f:
        pickle.dump(data, f)
        yield f.name

@pytest.fixture
def mock_ogora_zip():
    """Generate mock OGORA zip file."""
    data = "header\n" + "\n".join([
        f"G12345,WELL-{i},202001,30,OIL,1000,500"
        for i in range(100)
    ])
    
    with tempfile.NamedTemporaryFile(suffix='.zip') as f:
        with zipfile.ZipFile(f, 'w') as z:
            z.writestr('ogora2020.txt', data)
        yield f.name
```

## Test Execution Strategy

### Phase 1: Unit Testing (Day 1)
- Implement all unit tests
- Achieve 80% code coverage
- Focus on edge cases

### Phase 2: Integration Testing (Day 2)
- Test module interactions
- Verify data flow
- Test router integration

### Phase 3: Validation Testing (Day 3)
- Compare with reference outputs
- Verify calculation accuracy
- Document any variations

### Phase 4: Performance Testing (Day 4)
- Run performance benchmarks
- Optimize bottlenecks
- Verify memory usage

## Test Data Requirements

### Input Test Data
```yaml
test_data:
  drilling:
    - leases_enhanced.xlsx (20 leases)
    - sample_war_main.bin (1000 records)
    - sample_war_boreholes.bin (500 records)
  
  matrix:
    - sample_ogora_2020.zip
    - sample_ogora_2021.zip
    - sample_ogora_2022.zip
  
  financials:
    - assumptions.xlsx
    - wti_monthly.xlsx
```

### Expected Outputs
```yaml
expected_outputs:
  drilling:
    row_count: 150
    columns: [LEASE_NAME, API_WELL_NUMBER, DRILLING_DAYS, COMPLETION_DAYS]
  
  matrix:
    sheet_count: 20
    months: 36
    format: pivot_table
  
  financials:
    npv_range: [1000000, 5000000]
    mirr_range: [0.08, 0.15]
    sheets: [Executive Summary, Project Summary, QC]
```

## Coverage Requirements

### Code Coverage Targets
- Overall: > 80%
- Critical paths: > 95%
- Error handling: > 90%
- Edge cases: > 85%

### Test Categories
- Unit tests: 60%
- Integration tests: 25%
- Validation tests: 10%
- Performance tests: 5%