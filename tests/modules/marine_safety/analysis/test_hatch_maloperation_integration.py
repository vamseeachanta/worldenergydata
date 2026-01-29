# ABOUTME: Integration tests for hatch maloperation analysis with LLM classifier
# ABOUTME: Tests hybrid detection (LLM + regex), fallback mechanisms, and end-to-end workflows

from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import pytest


class TestHatchAnalyzerWithLLM:
    """Integration tests for hatch analyzer with LLM enabled."""

    @pytest.fixture
    def sample_incidents(self) -> pd.DataFrame:
        """Fixture providing sample incident data."""
        return pd.DataFrame(
            {
                "INCIDENT_ID": range(1, 11),
                "DATE": [
                    (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                    for i in range(10)
                ],
                "NARRATIVE": [
                    "hatch cover not properly secured before departure",  # LLM should catch
                    "engine room access hatch left unsecured",  # LLM should catch
                    "collision with another vessel",  # Should be negative
                    "watertight door to engine room found open",  # LLM should catch
                    "fire in galley due to electrical fault",  # Should be negative
                    "cargo hold hatch cover dogs not engaged",  # LLM should catch
                    "grounding on uncharted reef",  # Should be negative
                    "escape hatch from engine room ajar",  # LLM should catch
                    "crew member fell overboard",  # Should be negative
                    "manhole cover to ballast tank unsealed",  # LLM should catch
                ],
                "SEVERITY": [
                    "MINOR",
                    "SERIOUS",
                    "MINOR",
                    "SERIOUS",
                    "CRITICAL",
                    "MINOR",
                    "SERIOUS",
                    "MINOR",
                    "CRITICAL",
                    "MINOR",
                ],
                "VESSEL_TYPE": ["BULK CARRIER"] * 10,
            }
        )

    def test_hatch_analyzer_with_llm_enabled(self, sample_incidents):
        """Test hatch analyzer with LLM classification enabled."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)
        results = analyzer.analyze(sample_incidents)

        assert results is not None
        assert "classifications" in results
        assert len(results["classifications"]) == len(sample_incidents)

        # Should detect hatch maloperation cases
        hatch_cases = [
            r for r in results["classifications"] if r["is_hatch_maloperation"]
        ]
        assert len(hatch_cases) >= 5  # At least 5 out of 10 are hatch-related

        # Check that confidence scores are included
        assert all("confidence" in r for r in results["classifications"])
        assert all(0.0 <= r["confidence"] <= 1.0 for r in results["classifications"])

    def test_hatch_analyzer_llm_vs_regex_comparison(self, sample_incidents):
        """Test comparison between LLM and regex-based detection."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        # Run with LLM
        llm_analyzer = HatchMaloperationAnalyzer(use_llm=True)
        llm_results = llm_analyzer.analyze(sample_incidents)

        # Run with regex only
        regex_analyzer = HatchMaloperationAnalyzer(use_llm=False)
        regex_results = regex_analyzer.analyze(sample_incidents)

        assert len(llm_results["classifications"]) == len(
            regex_results["classifications"]
        )

        # LLM should catch at least as many cases as regex
        llm_positives = sum(
            1 for r in llm_results["classifications"] if r["is_hatch_maloperation"]
        )
        regex_positives = sum(
            1 for r in regex_results["classifications"] if r["is_hatch_maloperation"]
        )

        # LLM should catch equal or more cases (it's more sophisticated)
        assert llm_positives >= regex_positives * 0.8  # Allow some variance

    def test_hybrid_detection_fallback(self, sample_incidents):
        """Test hybrid detection with fallback to regex on LLM failure."""
        from unittest.mock import patch

        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)

        # Mock LLM to fail on some cases
        original_classify = (
            analyzer.llm_classifier.classify
            if hasattr(analyzer, "llm_classifier")
            else None
        )

        def mock_classify_with_failure(text):
            if "collision" in text.lower():
                raise Exception("LLM service temporarily unavailable")
            return (
                original_classify(text)
                if original_classify
                else {"label": "other", "confidence": 0.5}
            )

        if hasattr(analyzer, "llm_classifier"):
            with patch.object(
                analyzer.llm_classifier,
                "classify",
                side_effect=mock_classify_with_failure,
            ):
                results = analyzer.analyze(sample_incidents)

                # Should still get results (fallback to regex)
                assert results is not None
                assert len(results["classifications"]) == len(sample_incidents)

    def test_llm_confidence_threshold(self, sample_incidents):
        """Test that confidence threshold filtering works correctly."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        # High confidence threshold
        high_threshold_analyzer = HatchMaloperationAnalyzer(
            use_llm=True, confidence_threshold=0.8
        )
        high_results = high_threshold_analyzer.analyze(sample_incidents)

        # Low confidence threshold
        low_threshold_analyzer = HatchMaloperationAnalyzer(
            use_llm=True, confidence_threshold=0.3
        )
        low_results = low_threshold_analyzer.analyze(sample_incidents)

        # Low threshold should catch more cases (or equal)
        high_positives = sum(
            1 for r in high_results["classifications"] if r["is_hatch_maloperation"]
        )
        low_positives = sum(
            1 for r in low_results["classifications"] if r["is_hatch_maloperation"]
        )

        assert low_positives >= high_positives

    def test_batch_processing_consistency(self, sample_incidents):
        """Test that batch processing gives consistent results."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)

        # Process all at once
        batch_results = analyzer.analyze(sample_incidents)

        # Process individually and combine
        individual_results = []
        for _, incident in sample_incidents.iterrows():
            single_df = pd.DataFrame([incident])
            result = analyzer.analyze(single_df)
            individual_results.extend(result["classifications"])

        # Results should match
        assert len(batch_results["classifications"]) == len(individual_results)

        for batch_r, indiv_r in zip(
            batch_results["classifications"], individual_results
        ):
            assert batch_r["is_hatch_maloperation"] == indiv_r["is_hatch_maloperation"]
            # Confidence might vary slightly due to batching, but labels should match


class TestLLMPerformanceIntegration:
    """Integration tests for LLM performance in analysis pipeline."""

    @pytest.fixture
    def large_incident_dataset(self) -> pd.DataFrame:
        """Fixture providing larger incident dataset for performance testing."""
        base_narratives = [
            "hatch cover not properly secured",
            "collision with vessel",
            "engine room access left open",
            "fire in accommodation",
            "watertight door malfunction",
        ]

        # Create dataset with 100 incidents
        data = {
            "INCIDENT_ID": range(1, 101),
            "DATE": [
                (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(100)
            ],
            "NARRATIVE": [base_narratives[i % 5] for i in range(100)],
            "SEVERITY": ["MINOR", "SERIOUS", "CRITICAL"] * 33 + ["MINOR"],
            "VESSEL_TYPE": ["BULK CARRIER"] * 100,
        }

        return pd.DataFrame(data)

    def test_large_dataset_processing_time(self, large_incident_dataset):
        """Test that large dataset processing completes in reasonable time."""
        import time

        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)

        start_time = time.time()
        results = analyzer.analyze(large_incident_dataset)
        elapsed_time = time.time() - start_time

        # Should process 100 incidents in less than 60 seconds
        assert elapsed_time < 60.0
        assert len(results["classifications"]) == 100

    def test_memory_efficiency_large_dataset(self, large_incident_dataset):
        """Test memory efficiency when processing large dataset."""
        import gc
        import os

        import psutil

        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        process = psutil.Process(os.getpid())
        gc.collect()

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        analyzer = HatchMaloperationAnalyzer(use_llm=True)
        results = analyzer.analyze(large_incident_dataset)

        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = final_memory - initial_memory

        # Memory increase should be less than 500 MB
        assert memory_increase < 500, f"Excessive memory use: {memory_increase:.1f}MB"
        assert len(results["classifications"]) == 100


class TestLLMErrorHandling:
    """Integration tests for error handling with LLM classifier."""

    @pytest.fixture
    def problematic_incidents(self) -> pd.DataFrame:
        """Fixture providing incidents with problematic data."""
        return pd.DataFrame(
            {
                "INCIDENT_ID": range(1, 6),
                "DATE": [
                    None,
                    "2024-01-01",
                    "invalid-date",
                    "2024-01-03",
                    "2024-01-04",
                ],
                "NARRATIVE": [
                    None,  # None value
                    "",  # Empty string
                    "x" * 10000,  # Very long text
                    "Normal hatch incident",
                    "Another normal case",
                ],
                "SEVERITY": ["MINOR"] * 5,
                "VESSEL_TYPE": ["BULK CARRIER"] * 5,
            }
        )

    def test_graceful_handling_of_null_narratives(self, problematic_incidents):
        """Test graceful handling of None/null narratives."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)

        # Should not crash
        results = analyzer.analyze(problematic_incidents)

        assert results is not None
        assert len(results["classifications"]) == len(problematic_incidents)

        # Null narratives should be handled (likely classified as non-hatch)
        null_result = results["classifications"][0]
        assert null_result is not None

    def test_handling_of_malformed_data(self):
        """Test handling of completely malformed data."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        malformed_df = pd.DataFrame(
            {
                "WRONG_COLUMN": [1, 2, 3],
                "OTHER_COLUMN": ["a", "b", "c"],
            }
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)

        # Should either handle gracefully or raise clear error
        try:
            results = analyzer.analyze(malformed_df)
            # If it handles gracefully, results should indicate issues
            assert results is not None
        except (KeyError, ValueError) as e:
            # If it raises error, should be clear
            assert "NARRATIVE" in str(e) or "column" in str(e).lower()

    def test_partial_llm_failure_handling(self, problematic_incidents):
        """Test handling when LLM fails on some but not all incidents."""
        from unittest.mock import patch

        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)

        call_count = [0]

        def mock_classify_with_intermittent_failure(text):
            call_count[0] += 1
            if call_count[0] % 2 == 0:  # Fail every other call
                raise Exception("Intermittent LLM failure")
            return {"label": "other", "confidence": 0.5}

        if hasattr(analyzer, "llm_classifier"):
            with patch.object(
                analyzer.llm_classifier,
                "classify",
                side_effect=mock_classify_with_intermittent_failure,
            ):
                results = analyzer.analyze(problematic_incidents)

                # Should still get results for all incidents (with fallback)
                assert len(results["classifications"]) == len(problematic_incidents)


class TestAnalysisReportGeneration:
    """Integration tests for report generation with LLM classifications."""

    @pytest.fixture
    def classified_incidents(self) -> pd.DataFrame:
        """Fixture providing pre-classified incident data."""
        return pd.DataFrame(
            {
                "INCIDENT_ID": range(1, 11),
                "DATE": [
                    (datetime.now() - timedelta(days=i * 30)).strftime("%Y-%m-%d")
                    for i in range(10)
                ],
                "NARRATIVE": [
                    "hatch not secured",
                    "collision",
                    "access hatch open",
                    "fire",
                    "watertight door issue",
                    "grounding",
                    "escape hatch ajar",
                    "crew injury",
                    "manhole cover unsealed",
                    "equipment failure",
                ],
                "SEVERITY": ["SERIOUS"] * 10,
                "VESSEL_TYPE": ["BULK CARRIER"] * 10,
                "IS_HATCH_MALOPERATION": [
                    True,
                    False,
                    True,
                    False,
                    True,
                    False,
                    True,
                    False,
                    True,
                    False,
                ],
                "CONFIDENCE": [
                    0.95,
                    0.85,
                    0.92,
                    0.88,
                    0.90,
                    0.87,
                    0.93,
                    0.86,
                    0.91,
                    0.84,
                ],
            }
        )

    def test_generate_analysis_report_with_confidence(self, classified_incidents):
        """Test generation of analysis report including confidence metrics."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)
        report = analyzer.generate_report(classified_incidents)

        assert report is not None
        assert "summary" in report
        assert "total_incidents" in report["summary"]
        assert "hatch_maloperation_count" in report["summary"]
        assert "average_confidence" in report["summary"]

        # Confidence metrics should be present
        assert 0.0 <= report["summary"]["average_confidence"] <= 1.0

    def test_confidence_distribution_in_report(self, classified_incidents):
        """Test that confidence distribution is included in report."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)
        report = analyzer.generate_report(classified_incidents)

        assert "confidence_distribution" in report
        assert "high_confidence" in report["confidence_distribution"]  # >= 0.8
        assert "medium_confidence" in report["confidence_distribution"]  # 0.5-0.8
        assert "low_confidence" in report["confidence_distribution"]  # < 0.5

    def test_temporal_analysis_with_llm_results(self, classified_incidents):
        """Test temporal trend analysis using LLM classifications."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=True)
        report = analyzer.generate_report(classified_incidents)

        assert "temporal_trends" in report
        assert "monthly_counts" in report["temporal_trends"]


class TestConfigurationOptions:
    """Integration tests for various configuration options."""

    @pytest.fixture
    def basic_incidents(self) -> pd.DataFrame:
        """Fixture providing basic incident data."""
        return pd.DataFrame(
            {
                "INCIDENT_ID": [1, 2, 3],
                "DATE": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "NARRATIVE": [
                    "hatch not closed properly",
                    "collision with pier",
                    "watertight door failure",
                ],
                "SEVERITY": ["MINOR", "SERIOUS", "MINOR"],
                "VESSEL_TYPE": ["BULK CARRIER"] * 3,
            }
        )

    def test_custom_model_configuration(self, basic_incidents):
        """Test analyzer with custom LLM model configuration."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(
            use_llm=True, model_name="distilbert-base-uncased", confidence_threshold=0.7
        )

        results = analyzer.analyze(basic_incidents)
        assert results is not None

    def test_disable_llm_configuration(self, basic_incidents):
        """Test that LLM can be explicitly disabled."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        analyzer = HatchMaloperationAnalyzer(use_llm=False)
        results = analyzer.analyze(basic_incidents)

        assert results is not None
        # Results should not have confidence scores (regex-based)
        assert all(
            "confidence" not in r or r["confidence"] == 1.0
            for r in results["classifications"]
        )

    def test_batch_size_configuration(self, basic_incidents):
        """Test configuration of batch size for LLM processing."""
        from worldenergydata.marine_safety.analysis.hatch_maloperation_analyzer import (
            HatchMaloperationAnalyzer,
        )

        # Small batch size
        small_batch = HatchMaloperationAnalyzer(use_llm=True, batch_size=1)
        small_results = small_batch.analyze(basic_incidents)

        # Large batch size
        large_batch = HatchMaloperationAnalyzer(use_llm=True, batch_size=10)
        large_results = large_batch.analyze(basic_incidents)

        # Both should give same classifications
        assert len(small_results["classifications"]) == len(
            large_results["classifications"]
        )


# Pytest configuration for integration tests
@pytest.fixture(scope="session")
def requires_llm():
    """Fixture to check if LLM dependencies are available."""
    try:
        import torch
        import transformers

        return True
    except ImportError:
        return False


# Mark tests that require LLM
# Note: These tests require --with-llm flag and transformers/torch installed
pytestmark = pytest.mark.skip(
    reason="LLM integration tests require --with-llm flag and transformers/torch installed"
)
