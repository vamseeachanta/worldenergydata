"""
Comparison Framework for Drilling Days Analysis

This package provides infrastructure for comparing different drilling days 
calculation methods in the worldenergydata BSEE analysis module.
"""

__version__ = "1.0.0"
__author__ = "WorldEnergyData Team"

# Core framework components
from .config_manager import ComparisonConfigManager
from .test_framework import ComparisonTestFramework
from .data_loader import DataLoader, DataLoaderError
from .comparison_engine import ComparisonEngine, ComparisonResult, WellCoverageAnalysis

__all__ = [
    "ComparisonConfigManager", 
    "ComparisonTestFramework",
    "DataLoader",
    "DataLoaderError",
    "ComparisonEngine",
    "ComparisonResult", 
    "WellCoverageAnalysis",
]