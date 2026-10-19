"""Royalty consistency with the shipped decks' source notes, not current law.

Sources: fiscal/decks/{us_gom,uk,norway}.yml, revision 1, source_ref.
Percent conversion: NIST SP 811 (2008), section 7.10.2.
Independent hand calculation: percent means per hundred, so the Gulf note's
12.5% / 100 = 0.125 and 18.75% / 100 = 0.1875. The UK note says royalty
was abolished; the Norway note says no production royalty, both implying zero.
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
