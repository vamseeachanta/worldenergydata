# ABOUTME: Detection module for hatch, door, and opening maloperation incidents.
# ABOUTME: Provides LLM-based and regex-based detection with hybrid mode support.

"""
Hatch Maloperation Detection Module

This module provides detection capabilities for hatch, door, and opening maloperation
incidents using:
- LLM-based detection (zero-shot classification)
- Regex pattern matching (fallback/primary)
- Hybrid detection mode combining both methods
"""

import logging
import re
from typing import Any, Dict, List, Optional, Pattern

from .hatch_patterns import HATCH_PATTERNS

# LLM classifier import (optional - graceful degradation if not installed)
try:
    from ..llm_classifier import LLMIncidentClassifier

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning(
        "LLM classifier not available. Install with: pip install transformers torch. "
        "Falling back to regex-only detection."
    )


class HatchDetector:
    """
    Detector for hatch, door, and opening maloperation incidents.

    Supports LLM-based detection with optional regex fallback for maximum
    accuracy and coverage.
    """

    def __init__(
        self,
        use_llm: bool = True,
        llm_confidence_threshold: float = 0.7,
        fallback_to_regex: bool = True,
        llm_model_name: Optional[str] = None,
    ):
        """
        Initialize the HatchDetector.

        Args:
            use_llm: Whether to use LLM-based detection (default: True if available)
            llm_confidence_threshold: Minimum confidence score for LLM classification
            fallback_to_regex: Use regex detection if LLM confidence is low
            llm_model_name: Custom LLM model name
        """
        # Compile regex patterns for better performance
        self.compiled_hatch_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE) for pattern in HATCH_PATTERNS
        ]

        # LLM configuration
        self.use_llm = use_llm and LLM_AVAILABLE
        self.llm_confidence_threshold = llm_confidence_threshold
        self.fallback_to_regex = fallback_to_regex

        # Initialize LLM classifier if enabled
        self.llm_classifier = None
        if self.use_llm:
            try:
                if llm_model_name:
                    self.llm_classifier = LLMIncidentClassifier(
                        model_name=llm_model_name
                    )
                else:
                    self.llm_classifier = LLMIncidentClassifier()
                logging.info("LLM-based hatch detection enabled")
            except Exception as e:
                logging.warning(
                    f"Failed to initialize LLM classifier: {e}. Falling back to regex."
                )
                self.use_llm = False
                self.llm_classifier = None
        else:
            if use_llm and not LLM_AVAILABLE:
                logging.info(
                    "LLM requested but not available. Using regex-only detection."
                )

        # Detection statistics
        self._detection_stats = {
            "llm_detections": 0,
            "regex_detections": 0,
            "hybrid_detections": 0,
            "total_analyzed": 0,
        }

    def is_hatch_maloperation_incident(
        self, incident: Dict[str, Any], return_details: bool = False
    ) -> bool | Dict[str, Any]:
        """
        Determine if an incident involves hatch/opening maloperation.

        Uses LLM-based detection (if enabled) with optional regex fallback for
        maximum accuracy and coverage.

        Args:
            incident: Incident dictionary with description field
            return_details: If True, return detailed detection information

        Returns:
            If return_details=False: Boolean indicating hatch incident
            If return_details=True: Dictionary with detection details
        """
        description = incident.get("description", "")
        if not description:
            return (
                False
                if not return_details
                else {
                    "is_hatch_incident": False,
                    "detection_method": "none",
                    "reason": "No description provided",
                }
            )

        self._detection_stats["total_analyzed"] += 1

        # Try LLM detection first (if enabled)
        llm_result = None
        llm_detected = False
        llm_confidence = 0.0

        if self.use_llm and self.llm_classifier:
            try:
                llm_result = self._detect_with_llm(description)
                llm_detected = llm_result["is_hatch_incident"]
                llm_confidence = llm_result["confidence"]
            except Exception as e:
                logging.warning(f"LLM detection failed: {e}. Falling back to regex.")
                llm_result = None

        # Try regex detection
        regex_detected = self._detect_with_regex(description)

        # Determine final result based on detection mode
        if llm_result and llm_confidence >= self.llm_confidence_threshold:
            # High-confidence LLM detection
            is_hatch = llm_detected
            method = "llm"
            self._detection_stats["llm_detections"] += 1

            # If regex also matches, it's a hybrid detection
            if regex_detected and llm_detected:
                method = "hybrid"
                self._detection_stats["hybrid_detections"] += 1
                self._detection_stats["llm_detections"] -= 1  # Don't double count

        elif self.fallback_to_regex or not self.use_llm:
            # Use regex (either as fallback or primary method)
            is_hatch = regex_detected
            method = "regex"
            if regex_detected:
                self._detection_stats["regex_detections"] += 1
        else:
            # Low confidence LLM, no regex fallback
            is_hatch = llm_detected if llm_result else False
            method = "llm" if llm_result else "none"

        # Return simple boolean or detailed result
        if not return_details:
            return is_hatch

        details = {
            "is_hatch_incident": is_hatch,
            "detection_method": method,
            "regex_matched": regex_detected,
        }

        if llm_result:
            details["llm_confidence"] = llm_confidence
            details["llm_reasoning"] = llm_result.get("reasoning", "")
            details["matched_phrases"] = llm_result.get("matched_phrases", [])

        return details

    def _detect_with_llm(self, description: str) -> Dict[str, Any]:
        """
        Use LLM to detect hatch maloperation incidents.

        Args:
            description: Incident description text

        Returns:
            Dictionary with LLM detection results
        """
        if not self.llm_classifier:
            raise RuntimeError("LLM classifier not initialized")

        return self.llm_classifier.detect_hatch_maloperation(description)

    def _detect_with_regex(self, description: str) -> bool:
        """
        Use regex patterns to detect hatch maloperation incidents.

        Args:
            description: Incident description text

        Returns:
            True if any hatch pattern matches, False otherwise
        """
        for pattern in self.compiled_hatch_patterns:
            if pattern.search(description):
                return True
        return False

    def extract_hatch_related_text(self, incident: Dict[str, Any]) -> Optional[str]:
        """
        Extract hatch-related text segments from incident description.

        Args:
            incident: Incident dictionary with description field

        Returns:
            Extracted hatch-related text or None if not found
        """
        description = incident.get("description", "")
        if not description:
            return None

        # Find sentences containing hatch-related terms
        sentences = re.split(r"[.!?]", description)
        relevant_sentences = []

        for sentence in sentences:
            for pattern in self.compiled_hatch_patterns:
                if pattern.search(sentence):
                    relevant_sentences.append(sentence.strip())
                    break

        if relevant_sentences:
            return " ".join(relevant_sentences)

        return None

    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detection methods used.

        Returns:
            Dictionary with detection statistics
        """
        stats = self._detection_stats.copy()
        stats["detection_mode"] = {
            "llm_enabled": self.use_llm,
            "regex_fallback": self.fallback_to_regex,
            "llm_threshold": self.llm_confidence_threshold,
        }

        # Calculate percentages
        total = stats["total_analyzed"]
        if total > 0:
            stats["llm_percentage"] = round(stats["llm_detections"] / total * 100, 2)
            stats["regex_percentage"] = round(
                stats["regex_detections"] / total * 100, 2
            )
            stats["hybrid_percentage"] = round(
                stats["hybrid_detections"] / total * 100, 2
            )

        return stats

    def reset_detection_statistics(self) -> None:
        """Reset detection statistics counters."""
        self._detection_stats = {
            "llm_detections": 0,
            "regex_detections": 0,
            "hybrid_detections": 0,
            "total_analyzed": 0,
        }
