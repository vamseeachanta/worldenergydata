# Marine Safety Analysis Test Suite

## Overview

This directory contains comprehensive tests for the marine safety analysis modules, with a focus on the LLM-based incident classification system.

## Test Files

### Core Test Files

1. **`test_llm_classifier.py`** - Comprehensive tests for LLM-based incident classifier
   - Model loading and initialization
   - Basic classification functionality
   - Hatch detection pattern recognition
   - Edge cases (empty, None, multilingual, very long text)
   - Performance benchmarks
   - Classification accuracy metrics
   - Robustness and error handling

2. **`test_hatch_maloperation_integration.py`** - Integration tests for hatch analyzer
   - LLM vs regex comparison
   - Hybrid detection with fallback
   - Confidence threshold testing
   - Large dataset performance
   - Error handling and graceful degradation
   - Report generation with LLM results

3. **`conftest.py`** - Pytest configuration and shared fixtures
   - Custom command line options (--runslow, --with-llm)
   - Test markers configuration
   - Shared fixtures for test data
   - Performance monitoring utilities
   - Mock LLM classifier for testing

## Running Tests

### Basic Test Execution

```bash
# Run all tests (excluding slow and LLM tests by default)
pytest tests/modules/marine_safety/analysis/

# Run with verbose output
pytest -v tests/modules/marine_safety/analysis/
```

### Running LLM Tests

LLM tests are skipped by default because they require additional dependencies. To run them:

```bash
# Install LLM dependencies first
pip install transformers torch

# Run tests with LLM integration
pytest --with-llm tests/modules/marine_safety/analysis/
```

### Running Slow Tests

Performance and memory tests are marked as "slow" and skipped by default:

```bash
# Run slow tests
pytest --runslow tests/modules/marine_safety/analysis/

# Run both slow and LLM tests
pytest --runslow --with-llm tests/modules/marine_safety/analysis/
```

### Running Specific Test Classes

```bash
# Run only model loading tests
pytest tests/modules/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization

# Run only classification tests
pytest tests/modules/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification

# Run only edge case tests
pytest tests/modules/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases

# Run only performance tests
pytest tests/modules/marine_safety/analysis/test_llm_classifier.py::TestPerformance
```

### Running by Test Markers

```bash
# Run only unit tests
pytest -m unit tests/modules/marine_safety/analysis/

# Run only integration tests
pytest -m integration tests/modules/marine_safety/analysis/

# Run only slow tests
pytest -m slow tests/modules/marine_safety/analysis/

# Run only LLM tests (requires --with-llm flag)
pytest -m llm --with-llm tests/modules/marine_safety/analysis/

# Exclude slow tests
pytest -m "not slow" tests/modules/marine_safety/analysis/
```

## Test Coverage

Generate test coverage reports:

```bash
# Generate HTML coverage report
pytest --cov=worldenergydata.marine_safety.analysis --cov-report=html tests/modules/marine_safety/analysis/

# View coverage report
open reports/coverage/htmlcov/index.html  # macOS
xdg-open reports/coverage/htmlcov/index.html  # Linux
```

## Test Data

### Sample Narratives

The tests use realistic incident narratives:

**Positive Cases (Hatch Maloperation):**
- "hatch cover not properly secured before departure"
- "engine room access hatch left unsecured"
- "watertight door to engine room found open"
- "cargo hold hatch cover dogs not properly engaged"

**Negative Cases (Other Incidents):**
- "collision with another vessel in restricted waters"
- "fire in engine room due to fuel line rupture"
- "grounding on uncharted reef"
- "crew member fell overboard"

### Edge Cases

The tests cover various edge cases:
- Empty strings
- None values
- Whitespace-only text
- Very long text (>10,000 characters)
- Multilingual text (Spanish, French, German, Chinese, Russian)
- Special characters and numeric text

## Performance Expectations

### Speed Benchmarks

- Single classification: < 5 seconds
- Batch processing (100 items): < 60 seconds
- Batch throughput: ≥ 2 texts/second

### Memory Usage

- Memory increase for 100 incidents: < 500 MB
- No memory leaks (stable across 100+ classifications)

### Accuracy Targets

- Positive case accuracy: ≥ 80%
- Negative case accuracy: ≥ 80%
- F1 score: ≥ 0.75
- Precision: ≥ 0.75
- Recall: ≥ 0.75

## Test-Driven Development (TDD)

These tests were written **before** implementation as part of TDD workflow:

1. **RED Phase**: All tests should fail initially (no implementation exists)
2. **GREEN Phase**: Implement minimal code to make tests pass
3. **REFACTOR Phase**: Improve code while keeping tests green

### Running TDD Workflow

```bash
# Step 1: Run tests to verify they fail (RED)
pytest tests/modules/marine_safety/analysis/test_llm_classifier.py

# Expected: All tests should fail with import errors or assertion failures

# Step 2: Implement the LLM classifier
# (Create worldenergydata/marine_safety/analysis/llm_classifier.py)

# Step 3: Run tests again to verify they pass (GREEN)
pytest --with-llm tests/modules/marine_safety/analysis/test_llm_classifier.py

# Step 4: Refactor while keeping tests green
# (Improve code quality, performance, readability)
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Install dependencies
  run: |
    pip install -e .
    pip install transformers torch

- name: Run unit tests
  run: pytest -m "not slow and not llm"

- name: Run integration tests
  run: pytest -m integration --with-llm

- name: Run performance tests
  run: pytest -m slow --runslow
```

## Troubleshooting

### Common Issues

**Issue: Tests fail with "ModuleNotFoundError: No module named 'transformers'"**

Solution:
```bash
pip install transformers torch
```

**Issue: Tests are very slow**

Solution:
- Skip slow tests: `pytest -m "not slow"`
- Use mock classifier instead of real LLM (see conftest.py)
- Run tests in parallel: `pytest -n auto`

**Issue: Memory errors during performance tests**

Solution:
- Skip performance tests: `pytest -m "not slow"`
- Reduce batch sizes in tests
- Increase system memory allocation

**Issue: Multilingual tests fail**

Solution:
- Ensure UTF-8 encoding is properly configured
- Install language-specific tokenizers if needed

## Contributing

When adding new tests:

1. Follow TDD: Write tests first, then implementation
2. Use appropriate markers (@pytest.mark.slow, @pytest.mark.llm)
3. Add fixtures to conftest.py for shared test data
4. Document test purpose and expected behavior
5. Ensure tests are deterministic (no random behavior)
6. Keep tests isolated (no dependencies between tests)

## Documentation

For more information:
- [Pytest Documentation](https://docs.pytest.org/)
- [Transformers Testing Guide](https://huggingface.co/docs/transformers/testing)
- [Marine Safety Analysis Spec](/mnt/github/workspace-hub/worldenergydata/specs/modules/analysis/marine/)
