"""
Incident-Specific Analysis Modules

This package contains specialized analyzers for specific types of marine
safety incidents, such as hatch maloperation, foundering, collisions, etc.
"""

from worldenergydata.modules.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
    HatchMaloperationAnalyzer
)

__all__ = [
    'HatchMaloperationAnalyzer',
]
