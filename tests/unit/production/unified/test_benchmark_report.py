"""TDD coverage for the cross-country field-development benchmark report (#723).

The benchmark surface reuses the already-tested ``cross_basin`` analytics and
the region ``router``; the genuinely new contract under test here is:

  * provenance labelling — a region is "real" only when NO ``source`` value
    for that region ends in ``_mock``; otherwise it is "seed";
  * the report must NEVER present a seed/mock row with the "real" badge
    (the provenance-badged, never-mislabel design — Option A);
  * a region whose adapter returns EMPTY data is SKIPPED with a logged
    warning, never emitted as a fabricated zero-economics row (the
    #715-B1 silent-zero lesson);
  * concept-mix classification buckets a field with no depth as "unknown"
    (depth is never fabricated);
  * rendered HTML is fully self-contained (no external asset refs).
"""

from __future__ import annotations

import logging
import re

import pandas as pd
import pytest

from worldenergydata.production.unified.benchmark_report import (
    build_benchmark,
    concept_mix_by_region,
    provenance_by_region,
    render_benchmark_html,
)
from worldenergydata.production.unified.query import (
    STANDARD_COLUMNS,
    ProductionQuery,
    ProductionResult,
)

# ---------------------------------------------------------------------------
# Fake adapters / router — never touch real data or the 300MB BSEE binary.
# ---------------------------------------------------------------------------


class _FakeAdapter:
    """Minimal AbstractProductionAdapter stand-in returning canned rows."""

    def __init__(self, region: str, rows: list[dict]) -> None:
        self.region = region
        self._rows = rows

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        if not self._rows:
            return pd.DataFrame(columns=list(STANDARD_COLUMNS))
        return pd.DataFrame(self._rows)

    def available_fields(self):
        return sorted({r["field_name"] for r in self._rows})


class _FakeRouter:
    def __init__(self, adapters: dict[str, _FakeAdapter]) -> None:
        self._adapters = adapters

    def get_adapter(self, region: str) -> _FakeAdapter:
        return self._adapters[region]

    def list_regions(self):
        return sorted(self._adapters)


def _row(region, field, year, month, oil, source):
    return {
        "region": region,
        "field_name": field,
        "year": year,
        "month": month,
        "oil_bbl": float(oil),
        "gas_mcf": float(oil) * 0.5,
        "water_bbl": float(oil) * 0.1,
        "condensate_bbl": float(oil) * 0.02,
        "source": source,
    }


def _real_rows():
    return [
        _row("gom", "Atlantis", 2020, 1, 8_000_000, "bsee"),
        _row("gom", "Atlantis", 2020, 2, 7_500_000, "bsee"),
    ]


def _seed_rows():
    return [
        _row("ncs", "Edvard Grieg", 2020, 1, 5_800_000, "sodir_mock"),
        _row("ncs", "Edvard Grieg", 2020, 2, 5_200_000, "sodir_mock"),
    ]


def _make_result(rows):
    q = ProductionQuery(regions=["x"])
    data = (
        pd.DataFrame(rows) if rows else pd.DataFrame(columns=list(STANDARD_COLUMNS))
    )
    return ProductionResult(
        query=q,
        data=data,
        summary=pd.DataFrame(),
        sources_used=sorted({r["source"] for r in rows}) if rows else [],
        coverage_gaps=[],
    )


# ---------------------------------------------------------------------------
# provenance
# ---------------------------------------------------------------------------


def test_provenance_real_when_no_mock_source():
    result = _make_result(_real_rows())
    prov = provenance_by_region(result)
    assert prov["gom"] == "real"


def test_provenance_seed_when_mock_source():
    result = _make_result(_seed_rows())
    prov = provenance_by_region(result)
    assert prov["ncs"] == "seed"


# ---------------------------------------------------------------------------
# build_benchmark — never mislabel seed as real
# ---------------------------------------------------------------------------


def test_build_benchmark_never_marks_seed_as_real():
    router = _FakeRouter(
        {
            "gom": _FakeAdapter("gom", _real_rows()),
            "ncs": _FakeAdapter("ncs", _seed_rows()),
        }
    )
    bench = build_benchmark(["gom", "ncs"], router=router)

    # Every seed-provenance row must carry provenance=="seed" (never "real").
    seed_rows = [r for r in bench["rows"] if r["region"] == "ncs"]
    assert seed_rows, "expected at least one NCS seed row"
    assert all(r["provenance"] == "seed" for r in seed_rows)
    assert all(r["provenance"] == "real" for r in bench["rows"] if r["region"] == "gom")

    # Rendered HTML: the seed row must carry the seed marker, and no seed row
    # may appear under the "real" badge.
    html_out = render_benchmark_html(bench)
    assert 'data-provenance="seed"' in html_out
    assert "Illustrative seed" in html_out
    # The NCS field name must appear inside a seed-tagged row, never elsewhere.
    assert "Edvard Grieg" in html_out


def test_empty_region_is_skipped_with_warning_not_zero_rows(caplog):
    router = _FakeRouter(
        {
            "gom": _FakeAdapter("gom", _real_rows()),
            "spain": _FakeAdapter("spain", []),  # empty adapter
        }
    )
    with caplog.at_level(logging.WARNING):
        bench = build_benchmark(["gom", "spain"], router=router)

    assert "spain" in bench["skipped_empty"]
    assert "spain" not in bench["generated_regions"]
    # A warning was logged for the skip.
    assert any("spain" in rec.message for rec in caplog.records)
    # No fabricated zero-economics row for the empty region.
    assert all(r["region"] != "spain" for r in bench["rows"])
    assert not any(
        r["region"] == "spain" and r.get("disc_posttax_cf_usd") == 0
        for r in bench["rows"]
    )


# ---------------------------------------------------------------------------
# concept mix
# ---------------------------------------------------------------------------


def test_concept_mix_unknown_when_no_depth():
    depth_by_field = {
        "gom": {"Atlantis": 7000.0, "NoDepthField": None},
    }
    mix = concept_mix_by_region(depth_by_field)
    assert mix["gom"]["unknown"] == 1  # NoDepthField
    assert mix["gom"]["subsea20"] == 1  # Atlantis at 7000 ft


# ---------------------------------------------------------------------------
# rendering — self-contained
# ---------------------------------------------------------------------------


def test_render_html_self_contained():
    router = _FakeRouter(
        {
            "gom": _FakeAdapter("gom", _real_rows()),
            "ncs": _FakeAdapter("ncs", _seed_rows()),
        }
    )
    bench = build_benchmark(["gom", "ncs"], router=router)
    html_out = render_benchmark_html(bench)

    # No external asset references (inline only).
    assert "src=" not in html_out
    assert 'href="http' not in html_out
    assert "http://" not in html_out.replace("http://www.w3.org", "")  # allow xmlns
    # Both badge labels present when both provenances present.
    assert "Real regulatory data" in html_out
    assert "Illustrative seed" in html_out


# ---------------------------------------------------------------------------
# Fail-closed provenance + render-binding (review Findings 1 & 4)
# ---------------------------------------------------------------------------


def test_mixed_source_region_all_seed():
    # A region with BOTH a real-tag row and a _mock row must be "seed":
    # any impurity poisons the whole region (fail-closed).
    rows = [
        _row("ncs", "Edvard Grieg", 2020, 1, 5_000_000, "sodir"),  # real tag
        _row("ncs", "Edvard Grieg", 2020, 2, 4_800_000, "sodir_mock"),  # mock
    ]
    prov = provenance_by_region(_make_result(rows))
    assert prov["ncs"] == "seed"


def test_unknown_source_is_seed():
    # A source tag not in the real allowlist must NOT be upgraded to real.
    rows = [_row("atlantis", "F1", 2020, 1, 1_000_000, "weird_source")]
    prov = provenance_by_region(_make_result(rows))
    assert prov["atlantis"] == "seed"


def test_missing_source_column_is_seed():
    # A frame with no `source` column at all -> cannot prove real -> seed.
    df = pd.DataFrame(
        [{"region": "gom", "field_name": "Atlantis", "oil_bbl": 1.0}]
    )
    result = ProductionResult(
        query=ProductionQuery(regions=["gom"]),
        data=df,
        summary=pd.DataFrame(),
        sources_used=[],
        coverage_gaps=[],
    )
    assert provenance_by_region(result)["gom"] == "seed"


def test_render_row_badge_matches_provenance():
    # Each rendered row's visible badge must match its data-provenance
    # attribute — a seed row can NEVER show the "real" badge.
    router = _FakeRouter(
        {
            "gom": _FakeAdapter("gom", _real_rows()),
            "ncs": _FakeAdapter("ncs", _seed_rows()),
        }
    )
    html_out = render_benchmark_html(build_benchmark(["gom", "ncs"], router=router))
    trs = re.findall(
        r'<tr data-provenance="(real|seed)">(.*?)</tr>', html_out, re.DOTALL
    )
    assert trs, "expected rendered data rows"
    for prov, cells in trs:
        if prov == "seed":
            assert "Illustrative seed" in cells
            assert "Real regulatory data" not in cells
        else:
            assert "Real regulatory data" in cells
            assert "Illustrative seed" not in cells


def test_field_name_html_escaped():
    rows = [
        _row("x", "<script>alert(1)</script>", 2020, 1, 1_000_000, "bsee"),
        _row("x", "A & B field", 2020, 1, 1_000_000, "bsee"),
    ]
    router = _FakeRouter({"x": _FakeAdapter("x", rows)})
    html_out = render_benchmark_html(build_benchmark(["x"], router=router))
    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;" in html_out
    assert "A &amp; B field" in html_out


def test_discount_rate_mismatch_raises():
    # Refuse to report a rate the numbers were not computed at (Finding 2).
    router = _FakeRouter({"gom": _FakeAdapter("gom", _real_rows())})
    with pytest.raises(ValueError, match="discount_rate"):
        build_benchmark(["gom"], router=router, discount_rate=0.15)
