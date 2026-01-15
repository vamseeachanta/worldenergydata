"""
ABOUTME: Test configuration helper for integration tests
ABOUTME: Provides test config generation functions for engine integration tests
"""

from pathlib import Path
from typing import Dict, Any


def get_complete_test_config(tmp_path: Path) -> Dict[str, Any]:
    """
    Get complete test configuration with all required fields.

    Args:
        tmp_path: pytest tmp_path fixture for temporary directory

    Returns:
        Dictionary with complete test configuration
    """
    return {
        'basename': 'bsee',
        'data_dir': str(tmp_path / 'data'),
        'output_dir': str(tmp_path / 'output'),
        'fields': {
            'production': True,
            'completion': True,
            'directional': False
        },
        'processing': {
            'clean': True,
            'validate': True
        },
        'analysis': {
            'npv': False,
            'statistics': True
        }
    }


def get_minimal_test_config(tmp_path: Path) -> Dict[str, Any]:
    """
    Get minimal test configuration with only required fields.

    Args:
        tmp_path: pytest tmp_path fixture for temporary directory

    Returns:
        Dictionary with minimal test configuration
    """
    return {
        'basename': 'bsee',
        'data_dir': str(tmp_path / 'data'),
        'output_dir': str(tmp_path / 'output')
    }
