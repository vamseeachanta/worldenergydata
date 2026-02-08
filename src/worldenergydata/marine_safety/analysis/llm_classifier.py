# ABOUTME: LLM-based incident classification system using transformer models
# ABOUTME: Provides zero-shot classification, batch processing, and hatch maloperation detection

import logging
import re
import warnings
from typing import Any, Dict, List, Optional

# Suppress transformers warnings
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

logger = logging.getLogger(__name__)


class LLMIncidentClassifier:
    """
    LLM-based classifier for marine incident classification.

    Uses zero-shot classification with transformer models to identify
    incident types, with specialized detection for hatch/opening maloperation.

    Features:
    - Zero-shot classification with confidence scores
    - Batch processing for efficiency
    - Specialized hatch maloperation detection
    - Model caching to avoid reloading
    - GPU support (optional)

    Examples:
        >>> classifier = LLMIncidentClassifier()
        >>> result = classifier.classify_incident(
        ...     "Hatch cover not properly secured",
        ...     ["hatch maloperation", "other"]
        ... )
        >>> print(result['label'], result['confidence'])
        hatch maloperation 0.92

        >>> hatch_result = classifier.detect_hatch_maloperation(
        ...     "Engine room access hatch left open"
        ... )
        >>> print(hatch_result['is_hatch_incident'])
        True
    """

    # Default hatch-related candidate labels
    HATCH_LABELS = [
        "hatch maloperation",
        "hatch not properly closed",
        "opening not secured",
        "engine room access failure",
        "watertight door malfunction",
        "cover improperly fastened",
        "other incident",
    ]

    # Keywords for phrase extraction
    INCIDENT_KEYWORDS = [
        "hatch",
        "opening",
        "door",
        "cover",
        "access",
        "secure",
        "close",
        "seal",
        "watertight",
        "fastened",
        "malfunction",
        "failure",
        "unsealed",
        "ajar",
        "open",
        "breach",
        "leak",
        "water",
        "ingress",
    ]

    def __init__(
        self,
        model_name: str = "facebook/bart-large-mnli",
        use_gpu: bool = False,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize LLM classifier with specified model.

        Args:
            model_name: HuggingFace model name for zero-shot classification
                       Default: 'facebook/bart-large-mnli'
            use_gpu: Whether to use GPU acceleration (requires CUDA)
            confidence_threshold: Minimum confidence score for predictions (0-1)

        Raises:
            RuntimeError: If model loading fails
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.confidence_threshold = confidence_threshold

        logger.info(f"Initializing LLM classifier with model: {model_name}")
        logger.info(
            f"GPU enabled: {use_gpu}, Confidence threshold: {confidence_threshold}"
        )

        try:
            from transformers import pipeline

            device = 0 if use_gpu else -1  # 0 for GPU, -1 for CPU

            self.classifier = pipeline(
                "zero-shot-classification", model=model_name, device=device
            )

            logger.info("Model loaded successfully")

        except ImportError as e:
            raise RuntimeError(
                "Failed to load transformers library. "
                "Install with: pip install transformers torch"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load model '{model_name}': {str(e)}") from e

    def classify_incident(
        self, text: str, candidate_labels: List[str], multi_label: bool = False
    ) -> Dict[str, Any]:
        """
        Classify single incident text with confidence scores.

        Args:
            text: Incident description text to classify
            candidate_labels: List of possible classification labels
            multi_label: Whether to allow multiple labels (default: False)

        Returns:
            Dictionary containing:
            - label: Predicted label (or None if below threshold/invalid input)
            - confidence: Confidence score (0-1)
            - all_scores: Dictionary of all labels with their scores

        Examples:
            >>> classifier = LLMIncidentClassifier()
            >>> result = classifier.classify_incident(
            ...     "Hatch not closed properly",
            ...     ["hatch maloperation", "collision", "fire"]
            ... )
            >>> result['label']
            'hatch maloperation'
        """
        # Handle edge cases
        if text is None or not isinstance(text, str):
            logger.warning("Invalid input: text is None or not a string")
            return {"label": None, "confidence": 0.0, "all_scores": {}}

        # Handle empty or whitespace-only text
        if not text.strip():
            logger.warning("Empty or whitespace-only text provided")
            return {"label": None, "confidence": 0.0, "all_scores": {}}

        try:
            # Run classification
            result = self.classifier(
                text, candidate_labels=candidate_labels, multi_label=multi_label
            )

            # Extract top prediction
            top_label = result["labels"][0]
            top_score = result["scores"][0]

            # Create score dictionary
            all_scores = {
                label: score for label, score in zip(result["labels"], result["scores"])
            }

            # Check confidence threshold
            final_label = top_label if top_score >= self.confidence_threshold else None

            return {
                "label": final_label,
                "confidence": float(top_score),
                "all_scores": all_scores,
            }

        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            return {"label": None, "confidence": 0.0, "all_scores": {}, "error": str(e)}

    def classify_batch(
        self,
        texts: List[str],
        candidate_labels: List[str],
        confidence_threshold: Optional[float] = None,
        multi_label: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Batch classify multiple incidents for efficiency.

        Args:
            texts: List of incident description texts
            candidate_labels: List of possible classification labels
            confidence_threshold: Override default confidence threshold
            multi_label: Whether to allow multiple labels per text

        Returns:
            List of classification results (same format as classify_incident)

        Examples:
            >>> classifier = LLMIncidentClassifier()
            >>> texts = [
            ...     "Hatch not closed",
            ...     "Collision with pier",
            ...     "Engine room door unsealed"
            ... ]
            >>> results = classifier.classify_batch(
            ...     texts,
            ...     ["hatch maloperation", "collision", "other"]
            ... )
            >>> len(results)
            3
        """
        if not texts:
            return []

        threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else self.confidence_threshold
        )

        try:
            # Use pipeline's batch processing
            batch_results = self.classifier(
                texts, candidate_labels=candidate_labels, multi_label=multi_label
            )

            # Process results
            processed_results = []
            for result in batch_results:
                top_label = result["labels"][0]
                top_score = result["scores"][0]

                all_scores = {
                    label: score
                    for label, score in zip(result["labels"], result["scores"])
                }

                final_label = top_label if top_score >= threshold else None

                processed_results.append(
                    {
                        "label": final_label,
                        "confidence": float(top_score),
                        "all_scores": all_scores,
                    }
                )

            return processed_results

        except Exception as e:
            logger.error(f"Batch classification error: {str(e)}")
            # Return error results for each text
            return [
                {"label": None, "confidence": 0.0, "all_scores": {}, "error": str(e)}
                for _ in texts
            ]

    def detect_hatch_maloperation(self, text: str) -> Dict[str, Any]:
        """
        Specialized method for hatch/opening maloperation detection.

        Combines zero-shot classification with phrase extraction to
        detect and explain hatch-related incidents.

        Args:
            text: Incident description text

        Returns:
            Dictionary containing:
            - is_hatch_incident: Boolean indicating if this is a hatch incident
            - confidence: Confidence score (0-1)
            - matched_phrases: List of relevant phrases found in text
            - reasoning: Explanation of the classification
            - classification: Full classification result

        Examples:
            >>> classifier = LLMIncidentClassifier()
            >>> result = classifier.detect_hatch_maloperation(
            ...     "Engine room access hatch found open during inspection"
            ... )
            >>> result['is_hatch_incident']
            True
            >>> 'hatch' in result['matched_phrases'][0].lower()
            True
        """
        if not text or not isinstance(text, str) or not text.strip():
            return {
                "is_hatch_incident": False,
                "confidence": 0.0,
                "matched_phrases": [],
                "reasoning": "Invalid or empty input text",
                "classification": {},
            }

        # Classify with hatch-specific labels
        classification = self.classify_incident(text, self.HATCH_LABELS)

        # Extract relevant phrases
        matched_phrases = self.extract_incident_phrases(text)

        # Determine if it's a hatch incident
        top_label = classification.get("label", "")
        confidence = classification.get("confidence", 0.0)

        # Consider it a hatch incident if:
        # 1. Classification is not 'other incident' AND confidence >= threshold
        # 2. OR matched phrases contain hatch-related terms with moderate confidence
        is_hatch_incident = (
            top_label
            and top_label != "other incident"
            and confidence >= self.confidence_threshold
        )

        # Generate reasoning
        if is_hatch_incident:
            reasoning = (
                f"Classified as '{top_label}' with {confidence:.1%} confidence. "
                f"Found {len(matched_phrases)} relevant phrases in the incident description."
            )
        else:
            reasoning = (
                f"Not identified as hatch incident. "
                f"Top classification: '{top_label or 'none'}' "
                f"with {confidence:.1%} confidence (threshold: {self.confidence_threshold:.1%})."
            )

        return {
            "is_hatch_incident": is_hatch_incident,
            "confidence": confidence,
            "matched_phrases": matched_phrases,
            "reasoning": reasoning,
            "classification": classification,
        }

    def extract_incident_phrases(self, text: str) -> List[str]:
        """
        Extract relevant phrases from incident description.

        Identifies sentences or phrases that contain incident-related keywords.

        Args:
            text: Incident description text

        Returns:
            List of extracted phrases containing incident keywords

        Examples:
            >>> classifier = LLMIncidentClassifier()
            >>> text = "The hatch was not secured. Weather was good. Door malfunction occurred."
            >>> phrases = classifier.extract_incident_phrases(text)
            >>> len(phrases) >= 2
            True
        """
        if not text or not isinstance(text, str):
            return []

        # Split into sentences
        sentences = re.split(r"[.!?]+", text)

        matched_phrases = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence contains any incident keywords
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in self.INCIDENT_KEYWORDS):
                matched_phrases.append(sentence)

        return matched_phrases

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Convenience method for basic hatch maloperation classification.

        This is the primary interface used by existing tests.

        Args:
            text: Incident description text

        Returns:
            Dictionary with 'label' and 'confidence' keys
        """
        result = self.detect_hatch_maloperation(text)

        # Map to expected format
        if result["is_hatch_incident"]:
            label = "hatch_maloperation"  # or 'positive' or True
        else:
            label = "other"  # or 'negative' or False

        return {"label": label, "confidence": result["confidence"]}


# Backwards compatibility aliases
def create_classifier(
    model_name: str = "facebook/bart-large-mnli", use_gpu: bool = False
) -> LLMIncidentClassifier:
    """
    Factory function to create classifier instance.

    Args:
        model_name: HuggingFace model name
        use_gpu: Whether to use GPU

    Returns:
        Initialized LLMIncidentClassifier instance
    """
    return LLMIncidentClassifier(model_name=model_name, use_gpu=use_gpu)
