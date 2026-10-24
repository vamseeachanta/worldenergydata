"""Lookup-key regressions with synthetic supplier records."""

from __future__ import annotations

import pytest

from worldenergydata.subsea import ManifoldSupplierLoader


@pytest.mark.parametrize("key", ["", " ", "\t\r\n", "\u2003"])
@pytest.mark.parametrize("catalogue", ["populated", "empty", "missing"])
def test_get_rejects_blank_key(tmp_path, key, catalogue):
    """Issue #1305 requires rejection, independently of available records.

    Python Language Reference, Membership test operations:
    https://docs.python.org/3/reference/expressions.html#membership-test-operations
    An empty substring belongs to every string, so it cannot identify a record.
    Python Library Reference, str.strip:
    https://docs.python.org/3/library/stdtypes.html#str.strip
    Each whitespace-only input strips to the empty string.
    """
    csv_path = tmp_path / "suppliers.csv"
    if catalogue != "missing":
        rows = "COMPANY\n"
        if catalogue == "populated":
            rows += "Synthetic Alpha\nSynthetic Beta\n"
        csv_path.write_text(rows, encoding="utf-8")
    loader = ManifoldSupplierLoader(csv_path)

    with pytest.raises(
        ValueError, match="company must contain non-whitespace characters"
    ):
        loader.get(key)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("aLpHa", "Synthetic Alpha"),
        ("BETA", "Synthetic Beta"),
        ("Synthetic", "Synthetic Alpha"),
        ("absent", None),
        (" Alpha ", None),
    ],
)
def test_get_preserves_nonblank_lookup(tmp_path, key, expected):
    """Hand check: lowercase substring comparison in CSV order.

    'alpha' belongs only to 'synthetic alpha'; 'beta' only to 'synthetic beta'.
    'synthetic' belongs to both, so the first row wins. Neither 'absent' nor
    ' alpha ' belongs to either row. Source: Python Language Reference,
    Membership test operations (URL above); existing get() docstring contract.
    These are synthetic string examples, not engineering input data.
    """
    csv_path = tmp_path / "suppliers.csv"
    csv_path.write_text("COMPANY\nSynthetic Alpha\nSynthetic Beta\n", encoding="utf-8")
    result = ManifoldSupplierLoader(csv_path).get(key)

    assert (result.COMPANY if result is not None else None) == expected
