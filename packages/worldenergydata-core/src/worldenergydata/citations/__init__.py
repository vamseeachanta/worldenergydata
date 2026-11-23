"""Immutable citation sidecars and fail-closed wiki metadata validation."""

from .schema import (
    Citation,
    CitationResolutionError,
    CitationValidationError,
    CitedValue,
    validate_citation,
)

__all__ = [
    "Citation",
    "CitedValue",
    "CitationResolutionError",
    "CitationValidationError",
    "validate_citation",
]
