"""
BSEE Paleowells Module

This module provides functionality for processing and analyzing paleontological well data
from the Gulf of Mexico, including geological epoch analysis and well data visualization.
"""

from .data_processor import PaleowellsDataProcessor
from .era_classifier import GeologicalEraClassifier

try:
    from .visualizer import PaleowellsVisualizer
except ImportError:
    PaleowellsVisualizer = None  # matplotlib not available

__all__ = ['PaleowellsDataProcessor', 'GeologicalEraClassifier', 'PaleowellsVisualizer']