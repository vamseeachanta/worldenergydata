# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/modules/bsee/2025-08-06-data-refresh-architecture/spec.md

> Created: 2025-08-06
> Version: 1.0.0

## Test Coverage Requirements

### Coverage Targets
- **Unit Tests:** 90% code coverage minimum
- **Integration Tests:** All major data flows
- **Performance Tests:** Baseline vs. improved metrics
- **End-to-End Tests:** Full refresh scenarios

### Critical Paths
1. Web scraping with fallback to file download
2. Incremental update detection
3. Parallel processing coordination
4. Error recovery and retry logic
5. Binary file generation and validation

## Unit Tests

### DataRefreshController
- `test_init_with_valid_config` - Verify proper initialization
- `test_init_with_invalid_config` - Handle missing required fields
- `test_select_data_source_auto` - Auto-selection logic
- `test_select_data_source_forced` - Respect user preference
- `test_orchestrate_refresh_success` - Happy path execution
- `test_orchestrate_refresh_partial_failure` - Handle mixed results
- `test_progress_tracking` - Verify progress callbacks

### WebScraperSource
- `test_scrape_production_data_single_page` - Basic scraping
- `test_scrape_production_data_pagination` - Multi-page results
- `test_scrape_with_date_filter` - Date range queries
- `test_handle_empty_results` - No data scenarios
- `test_parse_html_table_valid` - Correct data extraction
- `test_parse_html_malformed` - Handle bad HTML gracefully
- `test_rate_limiting` - Respect rate limits
- `test_session_management` - Cookie/session handling

### FileDownloadSource  
- `test_download_production_zip` - Basic file download
- `test_download_with_resume` - Partial download resume
- `test_checksum_validation` - Verify file integrity
- `test_extract_zip_contents` - Unzip handling
- `test_handle_corrupted_zip` - Corrupted file recovery
- `test_disk_space_check` - Pre-download validation
- `test_cleanup_temp_files` - Proper cleanup

### DataValidator
- `test_validate_production_schema` - Schema compliance
- `test_validate_data_types` - Type checking
- `test_validate_date_ranges` - Temporal consistency
- `test_detect_duplicates` - Duplicate detection
- `test_validate_required_fields` - Null handling
- `test_cross_reference_validation` - Relational integrity

### BinaryConverter
- `test_convert_production_to_binary` - Basic conversion
- `test_maintain_backward_compatibility` - Format preservation
- `test_compression_efficiency` - Size optimization
- `test_handle_large_datasets` - Memory efficiency
- `test_metadata_generation` - Index creation
- `test_atomic_file_writes` - Transactional safety

## Integration Tests

### Web Scraping Integration
```python
class TestWebScrapingIntegration:
    def test_full_scraping_workflow(self, mock_bsee_server):
        """Test complete scraping from request to parsed data"""
        # Setup mock BSEE responses
        # Execute scraping
        # Verify data extraction
        
    def test_scraping_fallback_to_download(self, mock_failing_server):
        """Test fallback when scraping fails"""
        # Simulate scraping failure
        # Verify automatic fallback
        # Check file download initiated
```

### Parallel Processing Integration
```python
class TestParallelProcessing:
    def test_concurrent_data_types(self):
        """Test WAR, production, and well data in parallel"""
        # Launch parallel refreshes
        # Verify no conflicts
        # Check result aggregation
        
    def test_resource_constraints(self):
        """Test behavior under resource limits"""
        # Limit worker threads
        # Verify graceful degradation
```

### Configuration Integration
```python
class TestConfigurationIntegration:
    def test_yaml_config_loading(self):
        """Test loading from YAML config"""
        # Load test config
        # Verify all settings applied
        
    def test_cli_override_config(self):
        """Test CLI args override config file"""
        # Set config values
        # Override with CLI
        # Verify precedence
```

## Feature Tests

### End-to-End Refresh Scenarios
```python
class TestEndToEndRefresh:
    def test_daily_incremental_refresh(self, test_data):
        """Simulate daily refresh workflow"""
        # Initial full refresh
        # Wait (simulated)
        # Incremental refresh
        # Verify only new data processed
        
    def test_full_refresh_all_types(self):
        """Complete refresh of all data types"""
        # Execute: bsee refresh --data-type all
        # Verify all binaries updated
        # Check metadata consistency
        
    def test_date_range_refresh(self):
        """Refresh specific date range"""
        # Execute: bsee refresh --date-range 2024-01-01:2024-03-31
        # Verify only range data processed
        # Check existing data preserved
```

### Error Recovery Scenarios
```python
class TestErrorRecovery:
    def test_network_failure_recovery(self, flaky_network):
        """Test recovery from network issues"""
        # Simulate intermittent failures
        # Verify retry logic
        # Check eventual success
        
    def test_partial_download_resume(self):
        """Test resuming interrupted downloads"""
        # Start download
        # Interrupt midway
        # Resume and complete
        # Verify data integrity
```

## Performance Tests

### Benchmark Suite
```python
class TestPerformance:
    def test_refresh_speed_improvement(self, benchmark):
        """Compare old vs new implementation"""
        # Benchmark old approach
        # Benchmark new approach
        # Assert >50% improvement
        
    def test_memory_usage(self, memory_profiler):
        """Verify memory constraints"""
        # Process large dataset
        # Monitor memory usage
        # Assert < 100MB peak
        
    def test_concurrent_performance(self):
        """Test parallel processing gains"""
        # Run sequential baseline
        # Run parallel version
        # Verify speedup factor
```

## Mocking Requirements

### External Services
- **BSEE Website:** Mock with local HTML fixtures
  ```python
  @pytest.fixture
  def mock_bsee_server(httpserver):
      httpserver.expect_request("/Production/OCSProduction/Default.aspx").respond_with_data(
          load_fixture("production_query_response.html")
      )
  ```

- **File Downloads:** Mock with test data files
  ```python
  @pytest.fixture
  def mock_zip_download(tmp_path):
      test_zip = create_test_zip(tmp_path)
      return MockResponse(content=test_zip.read_bytes())
  ```

### Time-Based Tests
- **Schedule Testing:** Freeze time for cron-like behavior
  ```python
  @freeze_time("2024-03-15 14:30:00")
  def test_scheduled_refresh():
      # Test scheduled execution
  ```

- **Rate Limiting:** Mock time.sleep for faster tests
  ```python
  @patch('time.sleep', return_value=None)
  def test_rate_limiting(mock_sleep):
      # Test without actual delays
  ```

### Network Conditions
- **Slow Networks:** Simulate various speeds
- **Intermittent Failures:** Random connection drops
- **Timeout Scenarios:** Long response times

## Test Data Management

### Fixtures
```
tests/fixtures/
├── bsee_responses/
│   ├── production_page_1.html
│   ├── production_empty.html
│   └── error_500.html
├── sample_data/
│   ├── production_sample.csv
│   ├── well_sample.csv
│   └── war_sample.txt
└── binary_files/
    ├── production_v1.bin  # Old format
    └── production_v2.bin  # New format
```

### Test Database
- SQLite in-memory for metadata tests
- Sample binary files for compatibility tests
- Generated data for performance tests

## CI/CD Integration

### GitHub Actions Workflow
```yaml
- name: Run Tests
  run: |
    uv run pytest tests/ -v --cov=worldenergydata.modules.bsee.data.refresh
    uv run pytest tests/integration/ -v -m "not slow"
    
- name: Performance Tests
  run: |
    uv run pytest tests/performance/ -v --benchmark-only
```

### Test Markers
- `@pytest.mark.slow` - Long-running tests (>5s)
- `@pytest.mark.integration` - Requires external setup
- `@pytest.mark.benchmark` - Performance tests
- `@pytest.mark.flaky` - Known intermittent issues

## Security Testing

- **Input Validation:** Fuzz testing for CLI inputs
- **Path Traversal:** Verify file access restrictions
- **Data Sanitization:** Check for injection attacks
- **Rate Limit Bypass:** Attempt to circumvent limits