"""Rate consistency with the shipped decks' source notes, not current law.

Sources: fiscal/decks/us_gom.yml revision 2 (revision-1 percentages retained),
and fiscal/decks/{uk,norway}.yml revision 1, source_ref.
Percent conversion: NIST SP 811 (2008), section 7.10.2.
Independent hand calculation: percent means per hundred, so the Gulf note's
12.5% / 100 = 0.125 and 18.75% / 100 = 0.1875. The UK note says royalty
was abolished; the Norway note says no production royalty, both implying zero.
External legal applicability and effective dates remain NOT_EVALUATED (#736).
UK/Norway declarative income-tax percentages use the same conversion.
Gulf federal_cit has no cited percentage and remains outside source validation.
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


def test_corrected_gulf_deck_has_distinct_revision_and_correction_note():
    """Changed fractions need provenance distinct from rounded revision 1."""
    terms = get_fiscal_terms("us_gom")
    assert terms.revision == "2"
    assert "0.188 to 0.1875" in terms.notes
    assert "revision 1" in terms.notes


@pytest.mark.parametrize(
    "country, source_patterns",
    [
        (
            "uk",
            {
                "ring_fence_cit": r"RFCT \((\d+)%\)",
                "supplementary_charge": r"Supplementary Charge \((\d+)%\)",
                "energy_profits_levy": r"Energy Profits Levy \((\d+)%\)",
            },
        ),
        (
            "norway",
            {
                "ordinary_cit": r"(\d+)% CIT",
                "special_petroleum_tax": r"(\d+)% special petroleum tax",
                "marginal_rate": r"(\d+)% marginal regime",
            },
        ),
    ],
)
def test_income_tax_rates_equal_their_source_note(country, source_patterns):
    """Check every cited tax fraction; this does not qualify current tax law."""
    terms = get_fiscal_terms(country)
    assert set(terms.income_tax) == set(source_patterns)
    for field, pattern in source_patterns.items():
        match = re.search(pattern, terms.source_ref)
        assert match is not None, f"Missing {field} percentage in source_ref"
        expected = Decimal(match.group(1)) / Decimal(100)
        assert Decimal(str(terms.income_tax[field])) == expected, field
