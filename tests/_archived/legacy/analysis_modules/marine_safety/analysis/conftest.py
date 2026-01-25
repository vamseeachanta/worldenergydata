# ABOUTME: Pytest configuration and shared fixtures for marine safety analysis tests
# ABOUTME: Configures test options, markers, and provides reusable test fixtures

import pytest
import warnings
from typing import Generator


def pytest_addoption(parser):
    """Add custom command line options for pytest."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests (performance, memory tests)"
    )
    parser.addoption(
        "--with-llm",
        action="store_true",
        default=False,
        help="run LLM integration tests (requires transformers and torch)"
    )


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: mark test as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "llm: mark test as requiring LLM dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--with-llm"):
        skip_llm = pytest.mark.skip(reason="need --with-llm option to run")
        for item in items:
            if "llm" in item.keywords:
                item.add_marker(skip_llm)


@pytest.fixture(scope="session", autouse=True)
def suppress_warnings():
    """Suppress common warnings during testing."""
    # Suppress tokenizer warnings from transformers
    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
    warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

    # Suppress pandas warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")

    yield


@pytest.fixture(scope="session")
def check_llm_dependencies():
    """Check if LLM dependencies are available."""
    try:
        import transformers
        import torch
        return True
    except ImportError:
        return False


@pytest.fixture(scope="session")
def check_performance_dependencies():
    """Check if performance testing dependencies are available."""
    try:
        import psutil
        return True
    except ImportError:
        return False


@pytest.fixture
def sample_hatch_narratives():
    """Provide sample hatch maloperation narratives for testing."""
    return {
        'positive': [
            "hatch cover not properly secured before departure",
            "engine room access hatch left unsecured",
            "watertight door to engine room found open",
            "cargo hold hatch cover dogs not properly engaged",
            "escape hatch from engine room found ajar",
            "manhole cover to ballast tank not properly secured",
            "quick-acting watertight door mechanism malfunction",
            "access hatch to void space discovered unsealed",
        ],
        'negative': [
            "collision with another vessel in restricted waters",
            "fire in engine room due to fuel line rupture",
            "grounding on uncharted reef in shallow water",
            "crew member fell overboard during deck operations",
            "rudder failure caused loss of steering control",
            "main engine breakdown in heavy seas",
            "cargo shift in rough weather conditions",
            "flooding due to hull breach from container strike",
        ]
    }


@pytest.fixture
def sample_incident_dataframe():
    """Provide sample incident DataFrame for testing."""
    import pandas as pd
    from datetime import datetime, timedelta

    data = {
        'INCIDENT_ID': range(1, 11),
        'DATE': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(10)],
        'NARRATIVE': [
            "hatch cover not properly secured before departure",
            "collision with another vessel",
            "engine room access hatch left unsecured",
            "fire in galley",
            "watertight door to engine room found open",
            "grounding incident",
            "cargo hold hatch cover dogs not engaged",
            "crew injury",
            "escape hatch from engine room ajar",
            "equipment failure",
        ],
        'SEVERITY': ['MINOR', 'SERIOUS', 'MINOR', 'CRITICAL', 'SERIOUS',
                    'SERIOUS', 'MINOR', 'MINOR', 'SERIOUS', 'MINOR'],
        'VESSEL_TYPE': ['BULK CARRIER'] * 10,
    }

    return pd.DataFrame(data)


@pytest.fixture
def edge_case_narratives():
    """Provide edge case narratives for testing."""
    return {
        'empty': "",
        'none': None,
        'whitespace': "   \t\n  ",
        'very_long': "The hatch was not closed properly. " * 500,
        'special_chars': "hatch #12 not secured!!! [critical]",
        'multilingual': {
            'spanish': "La escotilla no estaba cerrada correctamente",
            'french': "L'écoutille n'était pas correctement fermée",
            'german': "Die Luke war nicht richtig geschlossen",
            'chinese': "艙口蓋未正確關閉",
        }
    }


@pytest.fixture(scope="session")
def mock_llm_classifier():
    """Provide a mock LLM classifier for testing without real model."""
    class MockLLMClassifier:
        """Mock classifier that simulates LLM behavior without loading model."""

        def __init__(self):
            self.call_count = 0

        def classify(self, text: str) -> dict:
            """Mock classify method."""
            self.call_count += 1

            if text is None or text.strip() == "":
                return {'label': 'other', 'confidence': 0.3}

            # Simple keyword-based mock classification
            hatch_keywords = ['hatch', 'door', 'cover', 'opening', 'access', 'manhole']
            text_lower = text.lower()

            has_hatch_keyword = any(kw in text_lower for kw in hatch_keywords)
            not_keywords = ['not', 'un', 'failed', 'left', 'found']
            has_negative = any(kw in text_lower for kw in not_keywords)

            if has_hatch_keyword and has_negative:
                return {'label': 'hatch_maloperation', 'confidence': 0.85}
            elif has_hatch_keyword:
                return {'label': 'hatch_maloperation', 'confidence': 0.65}
            else:
                return {'label': 'other', 'confidence': 0.75}

        def classify_batch(self, texts: list) -> list:
            """Mock batch classify method."""
            return [self.classify(text) for text in texts]

    return MockLLMClassifier()


@pytest.fixture
def performance_monitor():
    """Provide performance monitoring utilities."""
    try:
        import psutil
        import os

        class PerformanceMonitor:
            """Monitor performance metrics during tests."""

            def __init__(self):
                self.process = psutil.Process(os.getpid())
                self.start_memory = None
                self.start_time = None

            def start(self):
                """Start monitoring."""
                import gc
                import time
                gc.collect()
                self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                self.start_time = time.time()

            def stop(self):
                """Stop monitoring and return metrics."""
                import gc
                import time
                gc.collect()
                end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                end_time = time.time()

                return {
                    'memory_increase_mb': end_memory - self.start_memory,
                    'elapsed_time_seconds': end_time - self.start_time,
                }

        return PerformanceMonitor()
    except ImportError:
        pytest.skip("psutil not installed, performance monitoring unavailable")


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """Cleanup after all tests complete."""
    yield

    # Force garbage collection
    import gc
    gc.collect()


# Helper functions for tests
def assert_valid_classification_result(result: dict):
    """Assert that a classification result has valid structure."""
    assert result is not None
    assert 'label' in result
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 0.0 <= result['confidence'] <= 1.0


def assert_valid_batch_results(results: list, expected_count: int):
    """Assert that batch results are valid."""
    assert len(results) == expected_count
    assert all('label' in r for r in results)
    assert all('confidence' in r for r in results)
    assert all(0.0 <= r['confidence'] <= 1.0 for r in results)
