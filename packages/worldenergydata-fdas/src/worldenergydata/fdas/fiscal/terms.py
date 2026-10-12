"""
FDAS Fiscal-Terms domain model.

Frozen, source-agnostic representations of a country's field-economics fiscal
regime. In v1 only the *royalty* layer is consumed by the cashflow engine
(``CashflowEngine.calculate_royalty``); every other field is declarative
metadata that documents provenance and reserves seams for later slices
(revenue/NPV price-marker + discount in #716, sliding-scale royalty in #718).

The types here carry no I/O and no validation logic beyond dataclass field
typing — construction and strict validation live in ``schema.py`` so that the
only supported way to obtain a ``FiscalTerms`` is through the fail-closed
loader (``get_fiscal_terms``). This keeps every in-memory ``FiscalTerms``
provably schema-valid.

Author: WorldEnergyData Team
Issue:  https://github.com/vamseeachanta/worldenergydata/issues/714
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

# Development systems the royalty map is keyed by — must match the columns of
# ``fdas.core.config.DEFAULT_ASSUMPTIONS['DEV_SYSTEM']`` exactly so that a
# ``flat`` deck can reproduce the legacy per-dev-system ROYALTY_RATE vector.
DEV_SYSTEMS = ("dry", "subsea15", "subsea20", "default")

# Additive royalty models retain the version-1 shipped deck contract.
SUPPORTED_ROYALTY_MODELS = ("flat", "none", "sliding_scale")
RESERVED_ROYALTY_MODELS = ()

# Declarative price markers (not consumed in v1 — revenue seam is #716).
SUPPORTED_PRICE_MARKERS = ("wti", "brent", "gas_hh", "gas_ttf")


class FiscalTermsError(Exception):
    """Base class for fiscal-terms failures."""


class FiscalTermsValidationError(FiscalTermsError):
    """Raised when a deck fails strict schema validation (fail-closed)."""


class FiscalTermsNotFoundError(FiscalTermsError):
    """Raised when no deck ships for the requested country.

    Carries the list of available country decks so the caller (and test
    output) sees exactly what *is* shippable rather than a bare KeyError.
    """

    def __init__(self, country: str, available: Optional[list] = None):
        self.country = country
        self.available = sorted(available or [])
        super().__init__(
            f"No fiscal-terms deck for country {country!r}. "
            f"Available: {self.available}"
        )


@dataclass(frozen=True)
class RoyaltyTerms:
    """Royalty sub-model.

    Attributes:
        model: ``"flat"`` (per-dev-system fixed rate), ``"none"`` (zero royalty),
            or ``"sliding_scale"`` (production-rate bands).
        rate_by_dev_system: for ``model == "flat"``, an exact mapping over
            ``DEV_SYSTEMS`` with each rate in ``[0.0, 1.0]``. ``None`` for
            ``model == "none"``.
    """

    model: str
    rate_by_dev_system: Optional[Dict[str, float]] = None

    bands: tuple[tuple[Optional[float], float], ...] = ()

    def rate_for(
        self, dev_system: str, *, production_rate_bpd: Optional[float] = None
    ) -> float:
        """Resolve the royalty rate for a development system.

        ``sliding_scale`` requires a finite, non-negative daily production rate
        and selects the first inclusive threshold, ending with an unbounded band.
        ``none`` → 0.0. ``flat`` → the mapped rate, falling back to the
        ``default`` dev-system entry when ``dev_system`` is unknown — mirroring
        ``AssumptionsManager.get``'s default-row fallback so parity holds for
        dev systems outside the canonical four.
        """
        if self.model == "none":
            return 0.0
        if self.model == "sliding_scale":
            if (
                not isinstance(production_rate_bpd, (int, float))
                or isinstance(production_rate_bpd, bool)
                or not math.isfinite(production_rate_bpd)
                or production_rate_bpd < 0
            ):
                raise ValueError("production rate must be finite, non-negative bpd")
            for threshold, rate in self.bands:
                if threshold is None or production_rate_bpd <= threshold:
                    return rate
            raise ValueError("production rate has no validated royalty band")
        assert self.rate_by_dev_system is not None  # guaranteed by validation
        if dev_system in self.rate_by_dev_system:
            return self.rate_by_dev_system[dev_system]
        return self.rate_by_dev_system["default"]


@dataclass(frozen=True)
class FiscalTerms:
    """Country fiscal regime (v1: royalty consumed, rest declarative).

    Consumed in v1:
        country, royalty

    Declarative metadata (readable, provably *not* consumed — see Suite 6):
        currency, price_marker, discount_rate, income_tax, notes

    Provenance (machine-verifiable, required non-empty by the loader):
        source_url, source_ref, revision, effective_date, schema_version
    """

    country: str
    royalty: RoyaltyTerms
    # provenance
    source_url: str
    source_ref: str
    revision: str
    effective_date: str
    schema_version: int
    # declarative metadata (not consumed in v1)
    currency: str = "USD"
    price_marker: str = "wti"
    discount_rate: Optional[float] = None
    income_tax: Dict[str, object] = field(default_factory=dict)
    notes: str = ""
