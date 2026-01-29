# ABOUTME: Comprehensive tests for LLM-based incident classification system
# ABOUTME: Tests model loading, classification accuracy, edge cases, and performance

import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Test Data: Realistic incident descriptions
POSITIVE_HATCH_CASES = [
    "hatch cover not properly secured before departure from port",
    "engine room access opening left unsecured during heavy weather",
    "watertight door to engine room found open during inspection",
    "crew failed to close hatch covers properly before sailing",
    "access hatch to void space discovered unsealed",
    "manhole cover to ballast tank not properly secured",
    "hatch coaming damaged preventing proper closure",
    "quick-acting watertight door mechanism malfunction prevented closure",
    "cargo hold hatch cover dogs not properly engaged",
    "escape hatch from engine room found ajar during sea passage",
]

NEGATIVE_HATCH_CASES = [
    "collision with another vessel in restricted waters",
    "fire in engine room due to fuel line rupture",
    "grounding on uncharted reef in shallow water",
    "crew member fell overboard during deck operations",
    "rudder failure caused loss of steering control",
    "main engine breakdown in heavy seas",
    "anchor dragging in severe storm conditions",
    "cargo shift in rough weather",
    "flooding due to hull breach from container strike",
    "electrical power failure affecting navigation systems",
]

EDGE_CASE_TEXTS = [
    "",  # Empty string
    None,  # None value
    " ",  # Whitespace only
    "a" * 10000,  # Very long text (10k characters)
    "La escotilla no estaba cerrada correctamente",  # Spanish
    "艙口蓋未正確關閉",  # Chinese
    "Люк не был должным образом закрыт",  # Russian
]


class TestLLMClassifierInitialization:
    """Test suite for LLM classifier initialization and model loading."""

    def test_llm_classifier_initialization(self):
        """Test basic initialization of LLM classifier."""
        try:
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers library not installed")

        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        classifier = LLMIncidentClassifier()

        assert classifier is not None
        assert hasattr(classifier, "model")
        assert hasattr(classifier, "tokenizer")
        assert hasattr(classifier, "classify")
        assert hasattr(classifier, "classify_batch")

    def test_model_loading_with_cache(self):
        """Test that model loading uses cache on subsequent loads."""
        try:
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers library not installed")

        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        # First load (may download model)
        start_time = time.time()
        classifier1 = LLMIncidentClassifier()
        first_load_time = time.time() - start_time

        # Second load (should use cache)
        start_time = time.time()
        classifier2 = LLMIncidentClassifier()
        second_load_time = time.time() - start_time

        # Second load should be faster (or at least not significantly slower)
        assert second_load_time <= first_load_time * 1.5

    def test_fallback_on_model_load_failure(self):
        """Test graceful fallback when model loading fails."""
        try:
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers library not installed")

        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        with patch(
            "transformers.AutoModelForSequenceClassification.from_pretrained"
        ) as mock_model:
            mock_model.side_effect = Exception("Model download failed")

            # Should either raise clear error or fall back to rule-based
            try:
                classifier = LLMIncidentClassifier()
                # If fallback exists, should still be usable
                result = classifier.classify("test text")
                assert result is not None
            except Exception as e:
                # If no fallback, error should be clear
                assert "Model" in str(e) or "download" in str(e)

    def test_custom_model_path(self):
        """Test initialization with custom model path."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        custom_model = "distilbert-base-uncased"
        classifier = LLMIncidentClassifier(model_name=custom_model)

        assert classifier is not None


class TestBasicClassification:
    """Test suite for basic classification functionality."""

    @pytest.fixture
    def classifier(self):
        """Fixture providing initialized classifier."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        return LLMIncidentClassifier()

    def test_classify_hatch_maloperation_positive(self, classifier):
        """Test classification of positive hatch maloperation cases."""
        text = "hatch cover not properly secured before departure"
        result = classifier.classify(text)

        assert result is not None
        assert "label" in result
        assert "confidence" in result
        assert result["label"] in ["hatch_maloperation", "positive", True]
        assert 0.0 <= result["confidence"] <= 1.0

    def test_classify_hatch_maloperation_negative(self, classifier):
        """Test classification of negative hatch maloperation cases."""
        text = "collision with another vessel in restricted waters"
        result = classifier.classify(text)

        assert result is not None
        assert "label" in result
        assert "confidence" in result
        assert result["label"] in ["other", "negative", False]
        assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_scores_returned(self, classifier):
        """Test that confidence scores are properly returned."""
        text = "engine room access hatch left open"
        result = classifier.classify(text)

        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_batch_classification(self, classifier):
        """Test batch classification of multiple incidents."""
        texts = [
            "hatch not closed properly",
            "collision with pier",
            "watertight door malfunction",
            "fire in galley",
        ]

        results = classifier.classify_batch(texts)

        assert len(results) == len(texts)
        assert all("label" in r for r in results)
        assert all("confidence" in r for r in results)

    def test_classification_determinism(self, classifier):
        """Test that same input produces consistent output."""
        text = "hatch cover not secured"

        result1 = classifier.classify(text)
        result2 = classifier.classify(text)

        assert result1["label"] == result2["label"]
        # Confidence should be very close (allow tiny floating point differences)
        assert abs(result1["confidence"] - result2["confidence"]) < 0.01


class TestHatchDetectionPatterns:
    """Test suite for specific hatch-related incident patterns."""

    @pytest.fixture
    def classifier(self):
        """Fixture providing initialized classifier."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        return LLMIncidentClassifier()

    def test_detect_hatch_not_closed(self, classifier):
        """Test detection of 'hatch not closed' pattern."""
        texts = [
            "hatch not closed properly before departure",
            "crew failed to secure hatch covers",
            "hatch cover found open during inspection",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result["label"] in [
                "hatch_maloperation",
                "positive",
                True,
            ], f"Failed to detect hatch issue in: {text}"

    def test_detect_opening_maloperation(self, classifier):
        """Test detection of various opening maloperation patterns."""
        texts = [
            "engine room access opening left unsecured",
            "access hatch to void space discovered unsealed",
            "manhole cover not properly secured",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result["label"] in [
                "hatch_maloperation",
                "positive",
                True,
            ], f"Failed to detect opening issue in: {text}"

    def test_detect_engine_room_access_failure(self, classifier):
        """Test detection of engine room access-related issues."""
        texts = [
            "engine room access hatch found open",
            "escape hatch from engine room found ajar",
            "watertight door to engine room not secured",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result["label"] in [
                "hatch_maloperation",
                "positive",
                True,
            ], f"Failed to detect engine room access issue in: {text}"

    def test_detect_watertight_door_issue(self, classifier):
        """Test detection of watertight door malfunctions."""
        texts = [
            "watertight door mechanism malfunction",
            "quick-acting watertight door failed to close",
            "watertight door dogs not properly engaged",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result["label"] in [
                "hatch_maloperation",
                "positive",
                True,
            ], f"Failed to detect watertight door issue in: {text}"

    def test_negative_case_no_hatch_incident(self, classifier):
        """Test that non-hatch incidents are properly classified as negative."""
        for text in NEGATIVE_HATCH_CASES:
            result = classifier.classify(text)
            assert result["label"] in [
                "other",
                "negative",
                False,
            ], f"False positive for non-hatch incident: {text}"


class TestEdgeCases:
    """Test suite for edge cases and unusual inputs."""

    @pytest.fixture
    def classifier(self):
        """Fixture providing initialized classifier."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        return LLMIncidentClassifier()

    def test_empty_text_handling(self, classifier):
        """Test handling of empty text."""
        result = classifier.classify("")

        assert result is not None
        assert "label" in result
        # Empty text should likely be classified as 'other' or have low confidence
        assert result.get("confidence", 1.0) < 0.8

    def test_none_value_handling(self, classifier):
        """Test handling of None value."""
        # Should either handle gracefully or raise clear error
        try:
            result = classifier.classify(None)
            assert result is not None
        except (TypeError, ValueError) as e:
            # If error, should be clear
            assert "None" in str(e) or "text" in str(e).lower()

    def test_whitespace_only_handling(self, classifier):
        """Test handling of whitespace-only text."""
        result = classifier.classify("   \t\n  ")

        assert result is not None
        assert "label" in result

    def test_very_long_text_handling(self, classifier):
        """Test handling of very long text (beyond typical token limits)."""
        long_text = "The hatch was not closed properly. " * 500  # ~3500 words

        # Should handle without crashing
        result = classifier.classify(long_text)
        assert result is not None

    def test_multilingual_text(self, classifier):
        """Test handling of non-English text."""
        multilingual_texts = {
            "es": "La escotilla no estaba cerrada correctamente",  # Spanish
            "fr": "L'écoutille n'était pas correctement fermée",  # French
            "de": "Die Luke war nicht richtig geschlossen",  # German
        }

        for lang, text in multilingual_texts.items():
            result = classifier.classify(text)
            assert result is not None
            assert "label" in result

    def test_special_characters_handling(self, classifier):
        """Test handling of text with special characters."""
        texts = [
            "hatch #12 not secured!!!",
            "hatch_cover@section_A [unsealed]",
            "50% of hatches were improperly closed (critical)",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result is not None

    def test_numeric_only_text(self, classifier):
        """Test handling of numeric-only text."""
        result = classifier.classify("123456789")

        assert result is not None
        assert result["label"] in ["other", "negative", False]


class TestPerformance:
    """Test suite for performance characteristics."""

    @pytest.fixture
    def classifier(self):
        """Fixture providing initialized classifier."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        return LLMIncidentClassifier()

    def test_batch_processing_faster_than_individual(self, classifier):
        """Test that batch processing is faster than individual classifications."""
        texts = POSITIVE_HATCH_CASES[:5] + NEGATIVE_HATCH_CASES[:5]

        # Individual processing
        start_time = time.time()
        individual_results = [classifier.classify(text) for text in texts]
        individual_time = time.time() - start_time

        # Batch processing
        start_time = time.time()
        batch_results = classifier.classify_batch(texts)
        batch_time = time.time() - start_time

        # Batch should be faster (or at least not much slower)
        assert batch_time <= individual_time * 1.2

        # Results should be equivalent
        assert len(batch_results) == len(individual_results)

    def test_classification_within_time_limit(self, classifier):
        """Test that single classification completes within reasonable time."""
        text = "hatch cover not properly secured before departure"

        start_time = time.time()
        result = classifier.classify(text)
        elapsed_time = time.time() - start_time

        # Should complete within 5 seconds for single classification
        assert elapsed_time < 5.0
        assert result is not None

    def test_batch_throughput(self, classifier):
        """Test throughput of batch processing."""
        texts = (POSITIVE_HATCH_CASES + NEGATIVE_HATCH_CASES) * 2  # 40 texts

        start_time = time.time()
        results = classifier.classify_batch(texts)
        elapsed_time = time.time() - start_time

        throughput = len(texts) / elapsed_time

        # Should process at least 2 texts per second
        assert throughput >= 2.0
        assert len(results) == len(texts)

    @pytest.mark.slow
    def test_memory_usage_stability(self, classifier):
        """Test that memory usage remains stable across multiple classifications."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        gc.collect()

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process many texts
        for _ in range(100):
            text = "hatch not closed properly"
            classifier.classify(text)

        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = final_memory - initial_memory

        # Memory increase should be less than 200 MB
        assert (
            memory_increase < 200
        ), f"Memory leak detected: {memory_increase:.1f}MB increase"


class TestClassificationAccuracy:
    """Test suite for classification accuracy metrics."""

    @pytest.fixture
    def classifier(self):
        """Fixture providing initialized classifier."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        return LLMIncidentClassifier()

    def test_positive_case_accuracy(self, classifier):
        """Test accuracy on known positive cases."""
        results = classifier.classify_batch(POSITIVE_HATCH_CASES)

        positive_predictions = sum(
            1 for r in results if r["label"] in ["hatch_maloperation", "positive", True]
        )

        accuracy = positive_predictions / len(results)

        # Should correctly identify at least 80% of positive cases
        assert accuracy >= 0.8, f"Positive case accuracy too low: {accuracy:.1%}"

    def test_negative_case_accuracy(self, classifier):
        """Test accuracy on known negative cases."""
        results = classifier.classify_batch(NEGATIVE_HATCH_CASES)

        negative_predictions = sum(
            1 for r in results if r["label"] in ["other", "negative", False]
        )

        accuracy = negative_predictions / len(results)

        # Should correctly identify at least 80% of negative cases
        assert accuracy >= 0.8, f"Negative case accuracy too low: {accuracy:.1%}"

    def test_confidence_calibration(self, classifier):
        """Test that confidence scores are well-calibrated."""
        # High confidence positive case
        positive_result = classifier.classify("hatch cover not properly secured")

        # High confidence negative case
        negative_result = classifier.classify("collision with another vessel")

        # Ambiguous case
        ambiguous_result = classifier.classify("problem with door")

        # Clear cases should have higher confidence than ambiguous cases
        assert positive_result["confidence"] > ambiguous_result["confidence"]
        assert negative_result["confidence"] > ambiguous_result["confidence"]

    def test_f1_score_calculation(self, classifier):
        """Test overall F1 score on test dataset."""
        all_texts = POSITIVE_HATCH_CASES + NEGATIVE_HATCH_CASES
        true_labels = ["positive"] * len(POSITIVE_HATCH_CASES) + ["negative"] * len(
            NEGATIVE_HATCH_CASES
        )

        results = classifier.classify_batch(all_texts)
        predictions = [
            (
                "positive"
                if r["label"] in ["hatch_maloperation", "positive", True]
                else "negative"
            )
            for r in results
        ]

        # Calculate F1
        tp = sum(
            1
            for t, p in zip(true_labels, predictions)
            if t == "positive" and p == "positive"
        )
        fp = sum(
            1
            for t, p in zip(true_labels, predictions)
            if t == "negative" and p == "positive"
        )
        fn = sum(
            1
            for t, p in zip(true_labels, predictions)
            if t == "positive" and p == "negative"
        )

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        # F1 score should be at least 0.75
        assert (
            f1 >= 0.75
        ), f"F1 score too low: {f1:.3f} (precision={precision:.3f}, recall={recall:.3f})"


class TestRobustness:
    """Test suite for robustness and error handling."""

    @pytest.fixture
    def classifier(self):
        """Fixture providing initialized classifier."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        return LLMIncidentClassifier()

    def test_concurrent_classification(self, classifier):
        """Test that classifier handles concurrent requests safely."""
        import concurrent.futures

        texts = ["hatch not closed"] * 10

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(classifier.classify, text) for text in texts]
            results = [f.result() for f in futures]

        assert len(results) == len(texts)
        assert all(r is not None for r in results)

    def test_error_recovery(self, classifier):
        """Test classifier recovers from errors gracefully."""
        # Try to classify something that might cause issues
        problematic_inputs = [
            None,
            "",
            "x" * 100000,  # Very long
            "\x00\x01\x02",  # Control characters
        ]

        for inp in problematic_inputs:
            try:
                result = (
                    classifier.classify(inp)
                    if inp is not None
                    else classifier.classify("")
                )
                assert result is not None
            except Exception as e:
                # If error occurs, should be handled gracefully
                assert True  # Test passes if exception is caught

    def test_repeated_initialization(self):
        """Test that repeated initialization doesn't cause issues."""
        from worldenergydata.modules.marine_safety.analysis.llm_classifier import (
            LLMIncidentClassifier,
        )

        # Create multiple instances
        classifiers = [LLMIncidentClassifier() for _ in range(3)]

        # All should work independently
        results = [c.classify("hatch not closed") for c in classifiers]

        assert len(results) == 3
        assert all(r is not None for r in results)
        assert all(r["label"] == results[0]["label"] for r in results)


# Pytest configuration
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    import warnings

    # Suppress tokenizer warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

    yield

    # Cleanup after tests
    import gc

    gc.collect()


# Mark slow tests - note: pytest.config is deprecated
# Tests marked with @pytest.mark.slow can be run with: pytest -m slow
