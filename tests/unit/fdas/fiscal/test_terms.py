"""Suite 4 — fiscal-terms strict schema validation (fail-closed).

Covers the loader/validator contract for the source-agnostic fiscal-terms deck
layer (#714): all shipped decks validate; unknown countries and malformed decks
fail closed; `sliding_scale` is rejected with a #718 pointer; provenance fields
are mandatory.
"""

import copy

import pytest

from worldenergydata.fdas.fiscal import (
    DEV_SYSTEMS,
    FiscalTerms,
    FiscalTermsNotFoundError,
    FiscalTermsValidationError,
    available_countries,
    get_fiscal_terms,
    validate_deck,
)


def _valid_deck():
    """A minimal schema-valid deck dict (flat royalty)."""
    return {
        "schema_version": 1,
        "country": "testland",
        "currency": "USD",
        "price_marker": "wti",
        "royalty": {
            "model": "flat",
            "rate_by_dev_system": {
                "dry": 0.10,
                "subsea15": 0.15,
                "subsea20": 0.20,
                "default": 0.15,
            },
        },
        "source_url": "https://example.gov/terms",
        "source_ref": "Example regulator",
        "revision": "1",
        "effective_date": "2026-07-03",
    }


# --- shipped decks all validate -------------------------------------------


def test_all_shipped_decks_validate():
    countries = available_countries()
    assert set(countries) >= {"us_gom", "norway", "uk"}, countries
    for country in countries:
        terms = get_fiscal_terms(country)
        assert isinstance(terms, FiscalTerms)
        assert terms.country
        assert terms.source_url and terms.revision and terms.effective_date


def test_us_gom_royalty_matches_legacy_config():
    """us_gom deck must reproduce fdas.core.config ROYALTY_RATE exactly."""
    from worldenergydata.fdas.core.config import DEFAULT_ASSUMPTIONS

    dev = DEFAULT_ASSUMPTIONS["DEV_SYSTEM"]
    rates = DEFAULT_ASSUMPTIONS["ROYALTY_RATE"]
    legacy = dict(zip(dev, rates))

    terms = get_fiscal_terms("us_gom")
    assert terms.royalty.model == "flat"
    for ds in DEV_SYSTEMS:
        assert terms.royalty.rate_for(ds) == legacy[ds], ds


def test_norway_is_none_model():
    terms = get_fiscal_terms("norway")
    assert terms.royalty.model == "none"
    for ds in DEV_SYSTEMS:
        assert terms.royalty.rate_for(ds) == 0.0


def test_uk_is_flat_zero():
    terms = get_fiscal_terms("uk")
    assert terms.royalty.model == "flat"
    for ds in DEV_SYSTEMS:
        assert terms.royalty.rate_for(ds) == 0.0


# --- fail-closed paths -----------------------------------------------------


def test_unknown_country_raises_with_available_list():
    with pytest.raises(FiscalTermsNotFoundError) as exc:
        get_fiscal_terms("atlantis")
    assert "us_gom" in exc.value.available
    assert "atlantis" in str(exc.value)


def test_unknown_top_level_field_rejected():
    d = _valid_deck()
    d["royaltyy"] = 0.1  # typo
    with pytest.raises(FiscalTermsValidationError, match="unknown field"):
        validate_deck(d)


def test_unknown_royalty_field_rejected():
    d = _valid_deck()
    d["royalty"]["rate"] = 0.1  # not an allowed royalty key
    with pytest.raises(FiscalTermsValidationError, match="unknown field"):
        validate_deck(d)


def test_sliding_scale_rejected_with_718_pointer():
    d = _valid_deck()
    d["royalty"] = {"model": "sliding_scale"}
    with pytest.raises(FiscalTermsValidationError) as exc:
        validate_deck(d)
    assert "718" in str(exc.value)


def test_flat_requires_exact_four_dev_systems():
    d = _valid_deck()
    del d["royalty"]["rate_by_dev_system"]["subsea20"]
    with pytest.raises(FiscalTermsValidationError, match="exactly"):
        validate_deck(d)

    d2 = _valid_deck()
    d2["royalty"]["rate_by_dev_system"]["extra"] = 0.1
    with pytest.raises(FiscalTermsValidationError, match="exactly"):
        validate_deck(d2)


def test_royalty_rate_bounds_enforced():
    for bad in (-0.01, 1.01, 2.0):
        d = _valid_deck()
        d["royalty"]["rate_by_dev_system"]["dry"] = bad
        with pytest.raises(FiscalTermsValidationError, match=r"\[0.0, 1.0\]"):
            validate_deck(d)


def test_none_model_must_not_carry_rate_map():
    d = _valid_deck()
    d["royalty"] = {"model": "none", "rate_by_dev_system": {"dry": 0.1}}
    with pytest.raises(FiscalTermsValidationError):
        validate_deck(d)


@pytest.mark.parametrize(
    "field", ["source_url", "source_ref", "revision", "effective_date"]
)
def test_provenance_fields_required_nonempty(field):
    d = _valid_deck()
    d[field] = "   "
    with pytest.raises(FiscalTermsValidationError, match=field):
        validate_deck(d)


def test_missing_provenance_field_rejected():
    d = _valid_deck()
    del d["source_url"]
    with pytest.raises(FiscalTermsValidationError, match="source_url"):
        validate_deck(d)


def test_wrong_schema_version_rejected():
    d = _valid_deck()
    d["schema_version"] = 99
    with pytest.raises(FiscalTermsValidationError, match="schema_version"):
        validate_deck(d)


def test_bad_price_marker_rejected():
    d = _valid_deck()
    d["price_marker"] = "diesel"
    with pytest.raises(FiscalTermsValidationError, match="price_marker"):
        validate_deck(d)


def test_fiscal_terms_is_frozen():
    terms = get_fiscal_terms("us_gom")
    with pytest.raises(Exception):
        terms.country = "changed"  # frozen dataclass


def test_validate_deck_is_pure_roundtrip():
    d = _valid_deck()
    snapshot = copy.deepcopy(d)
    validate_deck(d)
    assert d == snapshot  # validation must not mutate its input
