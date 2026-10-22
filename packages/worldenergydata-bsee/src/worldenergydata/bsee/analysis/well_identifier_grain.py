"""BSEE identifier keys and distinct population counts.

Source: NTL 2009-G33, Well Naming and Numbering Standards (2009), attachment
pp. 3-5, API Well Number and Producing Interval Code:
https://www.bsee.gov/sites/bsee.gov/files/notices-to-lessees-ntl/notices-to-lessees/09-g33.pdf

This validates format, not agency assignment or historical renumbering. A WB
code does not classify a bore as a geologic sidetrack versus a bypass.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable


def normalize_bsee_api12(value: object) -> str:
    """Return a complete BSEE bore key or raise for ambiguous input.

    Strip surrounding whitespace and an all-zero decimal tail introduced by
    numeric table loading. Never pad missing digits, remove punctuation, or
    truncate a family/event identifier. Errors omit source values so logs do
    not inadvertently disclose unrelated input data.
    """
    text = re.sub(r"\.0+$", "", str(value).strip())
    # NTL 2009-G33 (2009), attachment p. 3: 2+3+5+2 ASCII decimal digits.
    if re.fullmatch(r"[0-9]{12}", text) is None:
        raise ValueError("BSEE bore key requires a complete API-12 identifier")
    return text


def summarize_bore_population(values: Iterable[object]) -> dict:
    """Count distinct API-12 bores and API-10 families in the supplied extract.

    Duplicate source rows count once. Invalid identifiers fail the audit rather
    than silently reducing the population. No count of completions, producers,
    or sidetracks can be inferred from these bore keys alone.
    """
    bores = {normalize_bsee_api12(value) for value in values}
    # NTL 2009-G33 (2009), attachment p. 3: family = state+county+well
    # sequence (2+3+5 digits); final two digits identify the wellbore.
    family_sizes = Counter(bore[:10] for bore in bores)
    histogram = Counter(family_sizes.values())
    return {
        "bore_count": len(bores),
        "well_family_count": len(family_sizes),
        "family_size_histogram": dict(sorted(histogram.items())),
        "wellbore_codes": sorted({bore[10:] for bore in bores}),
    }
