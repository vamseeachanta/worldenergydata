
import pytest
from pathlib import Path

def test_module_initialization():
    """Test that all modules initialize correctly."""
    modules_to_test = [
        'worldenergydata.modules.bsee',
        'worldenergydata.modules.bsee.analysis',
        'worldenergydata.modules.bsee.data',
        'worldenergydata.testing.performance',
        'worldenergydata.validation',
    ]
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[''])
            assert module is not None, f"Module {module_name} failed to import"
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")
