"""Tests for classification pipeline helper functions and constants."""

import pytest

from worldenergydata.safety_analysis.nlp.classification_pipeline import (
    _INT_PARAM_KEYS,
    _cast_int_params,
    _load_model_params,
    _require_sklearn,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_int_param_keys(self):
        assert "n_estimators" in _INT_PARAM_KEYS
        assert "max_depth" in _INT_PARAM_KEYS
        assert "min_samples_split" in _INT_PARAM_KEYS
        assert "min_samples_leaf" in _INT_PARAM_KEYS
        assert "max_iter" in _INT_PARAM_KEYS
        assert len(_INT_PARAM_KEYS) == 5


# ---------------------------------------------------------------------------
# _cast_int_params
# ---------------------------------------------------------------------------

class TestCastIntParams:
    def test_casts_known_keys(self):
        params = {"n_estimators": 100.0, "max_depth": 5.7}
        _cast_int_params(params)
        assert params["n_estimators"] == 100
        assert isinstance(params["n_estimators"], int)
        assert params["max_depth"] == 5
        assert isinstance(params["max_depth"], int)

    def test_ignores_unknown_keys(self):
        params = {"learning_rate": 0.1, "n_estimators": 50.0}
        _cast_int_params(params)
        assert params["learning_rate"] == 0.1
        assert isinstance(params["learning_rate"], float)
        assert params["n_estimators"] == 50

    def test_skips_none(self):
        params = {"n_estimators": None, "max_depth": 3.0}
        _cast_int_params(params)
        assert params["n_estimators"] is None
        assert params["max_depth"] == 3

    def test_empty_dict(self):
        params = {}
        _cast_int_params(params)
        assert params == {}


# ---------------------------------------------------------------------------
# _load_model_params
# ---------------------------------------------------------------------------

class TestLoadModelParams:
    def test_returns_dict(self):
        result = _load_model_params()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# _require_sklearn
# ---------------------------------------------------------------------------

class TestRequireSklearn:
    def test_does_not_raise(self):
        # sklearn is available in this env
        _require_sklearn()
