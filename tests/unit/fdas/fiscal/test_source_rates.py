"""Rate consistency with the shipped decks' source notes, not current law.

Sources: fiscal/decks/{us_gom,uk,norway}.yml, original revision-1 source_ref
notes retained by the corrected Gulf deck at revision 2.
Percent conversion: NIST SP 811 (2008), section 7.10.2.
Independent hand calculation: percent means per hundred, so the Gulf note's
12.5% / 100 = 0.125 and 18.75% / 100 = 0.1875. The UK note says royalty
was abolished; the Norway note says no production royalty, both implying zero.
The UK and Norway income-tax fractions are checked against the same notes;
the Gulf federal_cit metadata has no source-note percentage and is not qualified.
External legal applicability and effective dates remain NOT_EVALUATED (#736).
"""

import re
from decimal import Decimal

import pytest

from worldenergydata.fdas.fiscal import (
    DEV_SYSTEMS,
    available_countries,
    get_fiscal_terms,
)


@pytest.mark.parametrize("country", available_countries())
@pytest.mark.parametrize("dev_system", (*DEV_SYSTEMS, "unmapped"))
def test_royalty_rate_equals_its_source_note(country, dev_system):
    """Check every shipped royalty key and the default fallback exactly."""
    terms = get_fiscal_terms(country)
    note = terms.source_ref
    if country == "us_gom":
        label = "shallow-water" if dev_system == "dry" else "deepwater"
        match = re.search(rf"(\d+(?:\.\d+)?)% {label}", note)
        assert match is not None, f"Missing {label} percentage in source_ref"
        # Percent conversion, hand calculation documented above.
        expected = Decimal(match.group(1)) / Decimal(100)
    elif country == "uk":
        assert "royalty abolished" in note
        expected = Decimal(0)  # uk.yml, revision 1, source_ref.
    elif country == "norway":
        assert "no production royalty" in note
        expected = Decimal(0)  # norway.yml, revision 1, source_ref.
    else:
        pytest.fail(f"Add a source-note royalty mapping for {country}")

    assert Decimal(str(terms.royalty.rate_for(dev_system))) == expected


def test_corrected_us_gom_deck_has_distinct_provenance():
    """A corrected royalty set must not retain the original revision identity."""
    terms = get_fiscal_terms("us_gom")
    assert terms.revision == "2"
    assert "0.188" in terms.notes and "0.1875" in terms.notes


@pytest.mark.parametrize(
    "country, tax_key, note_pattern",
    [
        ("uk", "ring_fence_cit", r"RFCT \((\d+(?:\.\d+)?)%\)"),
        ("uk", "supplementary_charge", r"Supplementary Charge \((\d+(?:\.\d+)?)%\)"),
        ("uk", "energy_profits_levy", r"Energy Profits Levy \((\d+(?:\.\d+)?)%\)"),
        ("norway", "ordinary_cit", r"(\d+(?:\.\d+)?)% CIT"),
        ("norway", "special_petroleum_tax", r"(\d+(?:\.\d+)?)% special petroleum tax"),
        ("norway", "marginal_rate", r"(\d+(?:\.\d+)?)% marginal regime"),
    ],
)
def test_income_tax_rate_equals_its_source_note(country, tax_key, note_pattern):
    """Percentages are read from shipped notes, without qualifying current law."""
    terms = get_fiscal_terms(country)
    match = re.search(note_pattern, terms.source_ref)
    assert match is not None, f"Missing {tax_key} percentage in source_ref"
    expected = Decimal(match.group(1)) / Decimal(100)
    assert Decimal(str(terms.income_tax[tax_key])) == expected
