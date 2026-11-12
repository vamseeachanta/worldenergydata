"""Keep production district names separate from unqualified numeric IDs."""

from collections.abc import Iterable

from .validators import TexasDataValidator

# The wellbore client accepts integer district parameters in the range 1-10.
# Suffix districts have no qualified mapping to that interface.
WELLBORE_DISTRICT_PARAMETERS = {
    "01": 1,
    "02": 2,
    "03": 3,
    "04": 4,
    "05": 5,
    "06": 6,
    "08": 8,
    "09": 9,
    "10": 10,
}
NUMERIC_DISTRICT_COLUMNS = frozenset({"DISTRICT_NO", "OG_DIST_NO", "DIST_NO"})


def wellbore_district_parameter(district: str) -> int:
    """Resolve a supported name, rejecting unqualified mappings before I/O."""
    normalized = TexasDataValidator().normalize_district(district)
    if normalized not in WELLBORE_DISTRICT_PARAMETERS:
        raise ValueError(
            f"well download district mapping is not qualified for {district!r}; "
            "omit districts to download the bulk well dataset"
        )
    return WELLBORE_DISTRICT_PARAMETERS[normalized]


def require_district_names(columns: Iterable[str]) -> None:
    """Reject numeric-ID schemas, even if a name column is also supplied."""
    numeric_columns = [
        str(column)
        for column in columns
        if str(column).strip().upper().replace(" ", "_").replace("-", "_")
        in NUMERIC_DISTRICT_COLUMNS
    ]
    if numeric_columns:
        raise ValueError(
            "Unqualified numeric district IDs in columns "
            f"{', '.join(numeric_columns)}; production input requires district "
            "names in district or DISTRICT_NAME. Numeric-ID conversion must be "
            "qualified upstream; renaming an ID column is not a conversion."
        )
