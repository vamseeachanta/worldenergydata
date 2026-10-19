"""Check production-volume conservation through the public report exporter.

Equation source: OpenStax, College Algebra 2e (2021), section 9.4,
"Series and Their Notations", definition of a finite partial sum:
https://openstax.org/books/college-algebra-2e/pages/9-4-series-and-their-notations

For disjoint reporting periods already expressed in bbl, total volume is
V = sum(v_i). These synthetic inputs are period volumes, not daily rates;
no time multiplier, unit conversion, empirical coefficient or acceptance
tolerance is used. The expected values below are independent hand sums.
This checks export fidelity, not the upstream production calculation.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from worldenergydata.reporting import export_report


@pytest.mark.parametrize("fmt", ["csv", "json", "xlsx", "parquet"])
@pytest.mark.parametrize(
    ("volumes_bbl", "expected_total_bbl"),
    [
        # Hand calculation: 1200.25 + 0 + 349.5 + 50.25 = 1600 bbl.
        pytest.param([1200.25, 0.0, 349.5, 50.25], 1600.0, id="mixed-production"),
        # Hand calculation: 0 + 0 = 0 bbl (two shut-in periods).
        pytest.param([0.0, 0.0], 0.0, id="shut-in"),
        # Hand calculation: 1/8 + 1/4 + 1/2 = 7/8 = 0.875 bbl.
        # Binary-exact fractions permit exact equality without a tolerance.
        pytest.param([0.125, 0.25, 0.5], 0.875, id="fractional-production"),
        # Hand calculation: a single period contributes its 75.5 bbl unchanged.
        pytest.param([75.5], 75.5, id="single-period"),
    ],
)
def test_export_preserves_production_volume(
    tmp_path, fmt, volumes_bbl, expected_total_bbl
):
    """Read the artifact and compare its rows and total to the hand sums.

    Independent hand calculations (all values in bbl):
    mixed: 1200.25 + 0 + 349.5 + 50.25 = 1600;
    shut-in: 0 + 0 = 0;
    fractional: 1/8 + 1/4 + 1/2 = 7/8 = 0.875;
    single-period: 75.5 = 75.5.
    Neither the exporter nor a sum of the input DataFrame supplies the oracle.
    JSON and XLSX also carry a caller-supplied summary: its reported total must
    agree with the independently checked artifact rows. CSV and Parquet carry
    only the rows under the existing export contract.
    """
    result = SimpleNamespace(
        data=pd.DataFrame({"production_bbl": volumes_bbl}),
        summary={"total_production_bbl": expected_total_bbl},
    )
    manifest = export_report(
        result,
        formats=[fmt],
        output_dir=str(tmp_path),
        filename_prefix="production",
    )

    assert manifest.formats_failed == {}
    assert manifest.formats_succeeded == [fmt]
    assert set(manifest.files) == {fmt}
    artifact = Path(manifest.files[fmt])
    summary = None
    if fmt == "json":
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        exported = pd.DataFrame(payload["data"])
        summary = payload["summary"]
    elif fmt == "xlsx":
        exported = pd.read_excel(artifact, sheet_name="data")
        summary_rows = pd.read_excel(artifact, sheet_name="summary")
        summary = dict(zip(summary_rows["key"], summary_rows["value"]))
    elif fmt == "parquet":
        exported = pd.read_parquet(artifact)
    else:
        exported = pd.read_csv(artifact)

    assert list(exported.columns) == ["production_bbl"]
    assert exported["production_bbl"].tolist() == volumes_bbl
    assert exported["production_bbl"].sum() == expected_total_bbl
    if summary is not None:
        assert summary["total_production_bbl"] == expected_total_bbl
        assert summary["total_production_bbl"] == exported["production_bbl"].sum()
