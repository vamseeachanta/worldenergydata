"""Validate optional per-field partner interests as reference data only.

Each paired development is one combined entry with one capital cost and one
plateau rate. No public per-field split of that cost or rate is established in
the opened sources; none is invented. Per-field shares are reference data, and
the flat partners list remains the sole calculation input.
"""

from collections.abc import Mapping
from numbers import Real

# Field names from issue 747's research note, discrepancy rows 3 and 9.
PARTNER_FIELD_NAMES = {
    "cascade_chinook": ("Cascade", "Chinook"),
    "jack_st_malo": ("Jack", "St. Malo"),
}


def _has_source_locator(source: object) -> bool:
    if isinstance(source, str):
        return bool(source.strip())
    if isinstance(source, Mapping):
        return all(
            isinstance(source.get(key), str) and source[key].strip()
            for key in ("key", "title", "url", "date")
        )
    return False


def validate_partners_by_field(field_id: str, partners_by_field: object) -> None:
    """Inspect optional reference metadata without changing it or enforcing totals."""
    if partners_by_field is None:
        return
    if not isinstance(partners_by_field, Mapping):
        raise ValueError("partners_by_field must be a mapping")
    allowed_names = PARTNER_FIELD_NAMES.get(field_id, ())
    for field_name, entries in partners_by_field.items():
        if field_name not in allowed_names:
            raise ValueError("partners_by_field contains an invalid field name")
        if not isinstance(entries, list):
            raise ValueError("partners_by_field entries must be a list")
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError("partners_by_field entries must be mappings")
            share = entry.get("share")
            if (
                isinstance(share, bool)
                or not isinstance(share, Real)
                or not 0 <= share <= 1
            ):
                raise ValueError("partners_by_field share must be a number in [0, 1]")
            if not _has_source_locator(entry.get("source")):
                raise ValueError("partners_by_field entry must have a non-empty source")
