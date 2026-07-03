"""
FDAS Fiscal-Terms strict loader + validator.

The only supported way to obtain a :class:`FiscalTerms` is
:func:`get_fiscal_terms`, which reads a versioned YAML deck shipped as package
data and validates it fail-closed. Strictness is deliberate — a mis-authored
deck must raise, never silently degrade to a wrong royalty:

* unknown top-level or royalty fields are rejected (typo guard);
* ``royalty.model`` must be ``flat`` or ``none``; ``sliding_scale`` is rejected
  with an explicit pointer to #718 (the seam it needs does not exist yet);
* a ``flat`` model must carry ``rate_by_dev_system`` with *exactly* the four
  canonical dev systems, each rate in ``[0.0, 1.0]``;
* provenance fields (``source_url``, ``source_ref``, ``revision``,
  ``effective_date``, ``schema_version``) are required and non-empty;
* ``price_marker`` / ``currency`` are validated but *declarative* in v1.

Author: WorldEnergyData Team
Issue:  https://github.com/vamseeachanta/worldenergydata/issues/714
"""

from __future__ import annotations

from importlib import resources
from typing import Any, Dict

import yaml

from .terms import (
    DEV_SYSTEMS,
    RESERVED_ROYALTY_MODELS,
    SUPPORTED_PRICE_MARKERS,
    SUPPORTED_ROYALTY_MODELS,
    FiscalTerms,
    FiscalTermsNotFoundError,
    FiscalTermsValidationError,
    RoyaltyTerms,
)

# Current deck schema version. Bump when the deck contract changes; the loader
# rejects decks whose declared schema_version is not understood.
SCHEMA_VERSION = 1

_DECKS_PACKAGE = "worldenergydata.fdas.fiscal.decks"
_DECK_SUFFIX = ".yml"

# Allowed keys — anything else is a typo and must fail closed.
_ALLOWED_TOP = {
    "country",
    "royalty",
    "currency",
    "price_marker",
    "discount_rate",
    "income_tax",
    "notes",
    "source_url",
    "source_ref",
    "revision",
    "effective_date",
    "schema_version",
}
_ALLOWED_ROYALTY = {"model", "rate_by_dev_system"}
_REQUIRED_PROVENANCE = ("source_url", "source_ref", "revision", "effective_date")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise FiscalTermsValidationError(msg)


def _validate_royalty(raw: Any) -> RoyaltyTerms:
    _require(isinstance(raw, dict), "royalty: must be a mapping")
    unknown = set(raw) - _ALLOWED_ROYALTY
    _require(not unknown, f"royalty: unknown field(s) {sorted(unknown)}")

    model = raw.get("model")
    _require(isinstance(model, str), "royalty.model: required string")
    if model in RESERVED_ROYALTY_MODELS:
        raise FiscalTermsValidationError(
            f"royalty.model {model!r} is reserved but not yet supported: it "
            "needs a production-rate seam calculate_royalty does not expose. "
            "Tracked in https://github.com/vamseeachanta/worldenergydata/issues/718"
        )
    _require(
        model in SUPPORTED_ROYALTY_MODELS,
        f"royalty.model {model!r} not in {SUPPORTED_ROYALTY_MODELS}",
    )

    rate_map = raw.get("rate_by_dev_system")
    if model == "none":
        _require(
            rate_map is None,
            "royalty.rate_by_dev_system must be omitted when model is 'none'",
        )
        return RoyaltyTerms(model="none", rate_by_dev_system=None)

    # model == "flat"
    _require(
        isinstance(rate_map, dict),
        "royalty.rate_by_dev_system: required mapping for model 'flat'",
    )
    keys = set(rate_map)
    _require(
        keys == set(DEV_SYSTEMS),
        f"royalty.rate_by_dev_system keys must be exactly {sorted(DEV_SYSTEMS)}, "
        f"got {sorted(keys)}",
    )
    normalized: Dict[str, float] = {}
    for k in DEV_SYSTEMS:
        v = rate_map[k]
        _require(
            isinstance(v, (int, float)) and not isinstance(v, bool),
            f"royalty.rate_by_dev_system[{k!r}]: must be a number",
        )
        v = float(v)
        _require(
            0.0 <= v <= 1.0,
            f"royalty.rate_by_dev_system[{k!r}]={v}: must be in [0.0, 1.0]",
        )
        normalized[k] = v
    return RoyaltyTerms(model="flat", rate_by_dev_system=normalized)


def validate_deck(raw: Any) -> FiscalTerms:
    """Strictly validate a parsed deck mapping into a :class:`FiscalTerms`.

    Raises :class:`FiscalTermsValidationError` on any deviation from the
    contract. Pure (no I/O) so it is unit-testable without shipping a file.
    """
    _require(isinstance(raw, dict), "deck: top level must be a mapping")
    unknown = set(raw) - _ALLOWED_TOP
    _require(not unknown, f"deck: unknown field(s) {sorted(unknown)}")

    sv = raw.get("schema_version")
    _require(sv == SCHEMA_VERSION, f"schema_version: expected {SCHEMA_VERSION}, got {sv!r}")

    country = raw.get("country")
    _require(
        isinstance(country, str) and country.strip(),
        "country: required non-empty string",
    )

    for key in _REQUIRED_PROVENANCE:
        val = raw.get(key)
        _require(
            isinstance(val, str) and val.strip(),
            f"{key}: required non-empty string",
        )

    price_marker = raw.get("price_marker", "wti")
    _require(
        price_marker in SUPPORTED_PRICE_MARKERS,
        f"price_marker {price_marker!r} not in {SUPPORTED_PRICE_MARKERS}",
    )
    currency = raw.get("currency", "USD")
    _require(isinstance(currency, str) and currency.strip(), "currency: non-empty string")

    discount_rate = raw.get("discount_rate")
    if discount_rate is not None:
        _require(
            isinstance(discount_rate, (int, float)) and not isinstance(discount_rate, bool),
            "discount_rate: must be a number when present",
        )
        discount_rate = float(discount_rate)

    income_tax = raw.get("income_tax", {})
    _require(isinstance(income_tax, dict), "income_tax: must be a mapping when present")
    notes = raw.get("notes", "")
    _require(isinstance(notes, str), "notes: must be a string when present")

    royalty = _validate_royalty(raw.get("royalty"))

    return FiscalTerms(
        country=country,
        royalty=royalty,
        source_url=raw["source_url"],
        source_ref=raw["source_ref"],
        revision=str(raw["revision"]),
        effective_date=raw["effective_date"],
        schema_version=int(sv),
        currency=currency,
        price_marker=price_marker,
        discount_rate=discount_rate,
        income_tax=income_tax,
        notes=notes,
    )


def available_countries() -> list:
    """List the country codes for which a deck ships as package data."""
    out = []
    for entry in resources.files(_DECKS_PACKAGE).iterdir():
        name = entry.name
        if name.endswith(_DECK_SUFFIX) and not name.startswith("_"):
            out.append(name[: -len(_DECK_SUFFIX)])
    return sorted(out)


def get_fiscal_terms(country: str) -> FiscalTerms:
    """Load and strictly validate the fiscal-terms deck for ``country``.

    Args:
        country: deck stem, e.g. ``"us_gom"``, ``"norway"``, ``"uk"``.

    Raises:
        FiscalTermsNotFoundError: no deck ships for ``country``.
        FiscalTermsValidationError: the deck exists but violates the schema.
    """
    key = str(country).strip().lower()
    resource = resources.files(_DECKS_PACKAGE).joinpath(key + _DECK_SUFFIX)
    if not resource.is_file():
        raise FiscalTermsNotFoundError(country, available=available_countries())
    with resource.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    try:
        return validate_deck(raw)
    except FiscalTermsValidationError as exc:
        raise FiscalTermsValidationError(f"deck {key!r}: {exc}") from exc
