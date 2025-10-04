"""
FDAS Financial Analysis Module

Provides cashflow modeling, CAPEX/OPEX calculations, and complete
financial analysis workflows.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .cashflow import (
    CashflowEngine,
    MonthlyCashflowModel,
    generate_monthly_cashflow,
    CashflowError,
)

__all__ = [
    'CashflowEngine',
    'MonthlyCashflowModel',
    'generate_monthly_cashflow',
    'CashflowError',
]
