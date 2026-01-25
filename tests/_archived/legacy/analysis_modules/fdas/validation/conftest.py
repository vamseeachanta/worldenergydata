"""
Pytest configuration for FDAS validation tests.
Bypasses main conftest to avoid module loading issues.
"""
import pytest

# Empty conftest to override parent
