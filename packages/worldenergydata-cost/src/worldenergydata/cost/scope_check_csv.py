"""Validate CSV structure before interpreting benchmark values."""

import csv
import io


def benchmark_rows(content, required):
    """Yield rows with unique stripped headings, converting CSV parser errors."""
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        headings = [key.strip() for key in (reader.fieldnames or ())]
        if len(headings) != len(set(headings)):
            raise ValueError("duplicate benchmark columns")
        if not required <= set(headings):
            raise ValueError("benchmark table is missing required columns")
        reader.fieldnames = headings
        for raw in reader:
            if any(value is None for value in raw.values()) or None in raw:
                raise ValueError("benchmark row has an invalid column count")
            yield {key: value.strip() for key, value in raw.items()}
    except csv.Error:
        raise ValueError("benchmark CSV could not be parsed") from None
