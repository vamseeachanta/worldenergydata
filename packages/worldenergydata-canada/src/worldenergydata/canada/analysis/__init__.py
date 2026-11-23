# ABOUTME: Canada cross-provincial analysis module package initialization
# ABOUTME: Provides analysis capabilities for combined AER and BCER data

"""
Canada Cross-Provincial Analysis Module.

This submodule provides analysis capabilities that span both Alberta (AER)
and British Columbia (BCER) data, including:
- Cross-provincial production comparisons
- Regional trend analysis
- Operator portfolio analysis
- Well performance benchmarking

Example usage:
    from worldenergydata.canada.analysis import CanadaAnalysis

    analysis = CanadaAnalysis()
    cfg = {"analysis": {"type": "production_comparison"}}
    results = analysis.router(cfg, collected_data)
"""

from worldenergydata.canada.analysis.analysis import CanadaAnalysis

__all__ = ["CanadaAnalysis"]
