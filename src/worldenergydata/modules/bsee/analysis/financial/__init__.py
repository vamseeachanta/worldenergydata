"""
SME Financial Analysis Module for BSEE Data

This module provides comprehensive financial analysis capabilities for BSEE oil and gas lease data,
implementing SME Roy's financial analysis V20 methodology.

Main Components:
- SMEAnalyzer: Main orchestrator for financial analysis
- SMEDataLoader: Data loading with matrix production support
- LeaseGrouper: Lease grouping and aggregation
- DrillingCompletion: D&C cost processing
- CashFlowCalculator: Monthly cash flow and NPV calculations
- ReportGenerator: Excel report generation with V20 formatting
- SMEFinancialCLI: Command-line interface
"""

from typing import Dict, Any, Optional

__version__ = "1.0.0"
__author__ = "WorldEnergyData Team"

# Module exports
__all__ = [
    # Main classes
    'SMEAnalyzer',
    'SMEDataLoader',
    'LeaseGrouper',
    'DrillingCompletion',
    'CashFlowCalculator',
    'ReportGenerator',
    'SMEFinancialCLI',
    'SMEConfigLoader',
    
    # Utilities
    'load_sme_config',
    'run_sme_analysis',
    
    # Version
    '__version__'
]

# Lazy imports to avoid circular dependencies
def _lazy_import():
    """Lazy import of module components"""
    global SMEAnalyzer, SMEDataLoader, LeaseGrouper, DrillingCompletion
    global CashFlowCalculator, ReportGenerator, SMEFinancialCLI, SMEConfigLoader
    
    try:
        from .sme_analyzer import SMEAnalyzer
    except ImportError:
        SMEAnalyzer = None
    
    try:
        from .sme_data_loader import SMEDataLoader
    except ImportError:
        SMEDataLoader = None
    
    try:
        from .lease_grouper import LeaseGrouper
    except ImportError:
        LeaseGrouper = None
    
    try:
        from .drilling_completion import DrillingCompletion
    except ImportError:
        DrillingCompletion = None
    
    try:
        from .cash_flow_calculator import CashFlowCalculator
    except ImportError:
        CashFlowCalculator = None
    
    try:
        from .report_generator import ReportGenerator
    except ImportError:
        ReportGenerator = None
    
    try:
        from .sme_cli import SMEFinancialCLI
    except ImportError:
        SMEFinancialCLI = None
    
    try:
        from .config_loader import SMEConfigLoader
    except ImportError:
        SMEConfigLoader = None


def load_sme_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load SME financial configuration
    
    Args:
        config_path: Path to configuration file (optional)
        
    Returns:
        Configuration dictionary
    """
    _lazy_import()
    
    if SMEConfigLoader is None:
        raise ImportError("SMEConfigLoader not available")
    
    loader = SMEConfigLoader()
    return loader.load_config(config_path)


def run_sme_analysis(
    config: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Run SME financial analysis
    
    Args:
        config: Configuration dictionary (optional)
        config_path: Path to configuration file (optional)
        output_path: Output directory for reports (optional)
        
    Returns:
        Path to generated report
    """
    _lazy_import()
    
    if SMEAnalyzer is None:
        raise ImportError("SMEAnalyzer not available")
    
    # Load config if not provided
    if config is None:
        config = load_sme_config(config_path)
    
    # Run analysis
    analyzer = SMEAnalyzer(config)
    report_path = analyzer.run_analysis(output_path)
    
    return report_path


# Initialize lazy imports
_lazy_import()