"""
ABOUTME: Calibration sub-package — multivariate cost prediction model.
ABOUTME: Provides CostPredictor trained on sanctioned-project calibration data.
"""

from worldenergydata.cost.calibration.cost_predictor import CostPredictor, PredictionResult

__all__ = ["CostPredictor", "PredictionResult"]
