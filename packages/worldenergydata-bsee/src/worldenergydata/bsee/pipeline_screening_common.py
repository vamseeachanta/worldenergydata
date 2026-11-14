"""Per-cell provenance helpers for the screening inventory."""


def _put(row, field, value, source):
    row[field] = value
    row[field + "_source"] = source


def _known(row, field, value, source):
    _put(row, field, value, source if value is not None else "UNKNOWN:unavailable")
