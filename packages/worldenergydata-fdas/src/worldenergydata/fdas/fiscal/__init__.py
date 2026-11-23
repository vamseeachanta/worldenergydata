"""FDAS fiscal-terms layer (source-agnostic country royalty/tax decks).

Public surface:
    get_fiscal_terms(country) -> FiscalTerms   # fail-closed deck loader
    available_countries() -> list[str]
    FiscalTerms, RoyaltyTerms                    # frozen domain types
    FiscalTermsError / *NotFoundError / *ValidationError

v1 consumes only the royalty layer in ``CashflowEngine.calculate_royalty``;
all other fields are declarative metadata. See ``fdas/fiscal/README`` in the
member README for the consumed-vs-declarative table.
"""

from .schema import (
    SCHEMA_VERSION,
    available_countries,
    get_fiscal_terms,
    validate_deck,
)
from .terms import (
    DEV_SYSTEMS,
    FiscalTerms,
    FiscalTermsError,
    FiscalTermsNotFoundError,
    FiscalTermsValidationError,
    RoyaltyTerms,
)

__all__ = [
    "SCHEMA_VERSION",
    "DEV_SYSTEMS",
    "FiscalTerms",
    "RoyaltyTerms",
    "FiscalTermsError",
    "FiscalTermsNotFoundError",
    "FiscalTermsValidationError",
    "get_fiscal_terms",
    "available_countries",
    "validate_deck",
]
