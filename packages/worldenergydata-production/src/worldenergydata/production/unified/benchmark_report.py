"""Cross-country field-development benchmark report (#723).

Provenance-badged benchmark across the unified production regions, REUSING the
tested analytics: ``cross_basin.compare_peak_rates`` / ``fiscal_sensitivity``
(per-country ``_FISCAL_REGIMES``, illustrative), ``router.RegionRouter``, and
``fdas.core.config.classify_dev_system_by_depth``.

Design (Option A — never label mock as real). Only US/GoM has a real data path
today; other adapters return MOCK rows. Provenance is FAIL-CLOSED: a region is
"real" only when every source is in :data:`_REAL_SOURCES`; anything else is
"seed". Seed rows carry ``data-provenance="seed"`` and the seed badge, so a
seed row can never render as real. Empty-data regions are SKIPPED with a
warning (never a fabricated zero row, the #715-B1 lesson); fields with no depth
bucket as "unknown" (depth never fabricated). Fiscal coefficients are
simplified public approximations — NOT legal or financial advice.
"""

from __future__ import annotations

import html
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.production.unified.cross_basin import (
    _DISCOUNT_RATE,
    compare_peak_rates,
    fiscal_sensitivity,
)
from worldenergydata.production.unified.query import (
    ProductionQuery,
    ProductionResult,
)

logger = logging.getLogger(__name__)

_CONCEPT_BUCKETS = ("dry", "subsea15", "subsea20", "unknown")

# Fail-CLOSED provenance: a region is "real" ONLY when every one of its source
# tags is in this allowlist of known real-data adapter paths. Anything else —
# a ``*_mock`` tag, a blank/NaN source, or any unrecognised string — is "seed"
# by construction, so unknown provenance can never be upgraded to real by
# naming luck (#723 review Finding 1). Compared case-insensitively.
_REAL_SOURCES = frozenset(
    {"bsee", "sodir", "cores", "ukcs", "brazil_anp",
     "eia_us", "mexico_cnh", "texas_rrc", "canada"}
)

# Repo root: benchmark_report.py -> unified -> production -> worldenergydata
# -> src -> worldenergydata-production -> packages -> ROOT
_REPO_ROOT = Path(__file__).resolve().parents[6]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def provenance_by_region(result: ProductionResult) -> dict[str, str]:
    """Classify each region's data as ``"real"`` or ``"seed"`` — FAIL CLOSED.

    A region is ``"real"`` only when EVERY one of its ``source`` values is in
    the :data:`_REAL_SOURCES` allowlist (compared case-insensitively). ANY
    unrecognised, blank, NaN, or ``*_mock`` source — or a missing ``source``
    column — makes the region ``"seed"``. Unknown provenance is never upgraded
    to real (#723 review Finding 1); mixed-source regions are seed.

    Args:
        result: A ``ProductionResult`` whose ``data`` frame carries the
            ``region`` (and normally ``source``) columns.

    Returns:
        Mapping ``{region: "real" | "seed"}``.
    """
    df = result.data
    out: dict[str, str] = {}
    if df is None or df.empty or "region" not in df.columns:
        return out
    if "source" not in df.columns:
        # No provenance information at all -> cannot prove real -> seed.
        return {str(r): "seed" for r in df["region"].unique()}
    for region, group in df.groupby("region"):
        sources = group["source"].astype("string").fillna("")
        norm = sources.str.strip().str.lower()
        # Real iff there is at least one row AND every source is known-real.
        all_real = bool(len(norm)) and bool(norm.isin(_REAL_SOURCES).all())
        out[str(region)] = "real" if all_real else "seed"
    return out


# ---------------------------------------------------------------------------
# Concept mix
# ---------------------------------------------------------------------------


def concept_mix_by_region(depth_by_field: dict) -> dict[str, dict[str, int]]:
    """Aggregate dev-system concept counts per region from field water depths.

    Args:
        depth_by_field: Nested mapping ``{region: {field_name: water_depth_ft}}``.
            A depth of ``None`` (or missing) classifies the field as
            ``"unknown"`` — depth is never fabricated.

    Returns:
        ``{region: {"dry": n, "subsea15": n, "subsea20": n, "unknown": n}}``.
    """
    from worldenergydata.fdas.core.config import classify_dev_system_by_depth

    mix: dict[str, dict[str, int]] = {}
    for region, fields in (depth_by_field or {}).items():
        counts = {bucket: 0 for bucket in _CONCEPT_BUCKETS}
        for _field, depth in (fields or {}).items():
            concept = classify_dev_system_by_depth(depth)
            if concept not in counts:
                concept = "unknown"
            counts[concept] += 1
        mix[str(region)] = counts
    return mix


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _single_region_result(region: str, df: pd.DataFrame) -> ProductionResult:
    return ProductionResult(
        query=ProductionQuery(regions=[region]),
        data=df,
        summary=pd.DataFrame(),
        sources_used=sorted(df["source"].dropna().unique().tolist())
        if "source" in df.columns
        else [],
        coverage_gaps=[],
    )


def build_benchmark(
    regions: list[str],
    *,
    oil_price_usd: float = 70.0,
    discount_rate: float = 0.10,
    router=None,
    depth_by_field: Optional[dict] = None,
) -> dict:
    """Build the cross-country benchmark structure.

    For each region: query its adapter, reuse ``compare_peak_rates`` and
    ``fiscal_sensitivity`` from :mod:`cross_basin`, attach per-region
    provenance and (optionally) a concept mix.  Regions whose adapter returns
    EMPTY data are skipped with a warning and never fabricated as zero rows.

    Args:
        regions: Region keys to benchmark (router aliases accepted).
        oil_price_usd: Oil price for the fiscal sensitivity model.
        discount_rate: Annual discount rate. ``cross_basin.fiscal_sensitivity``
            applies a fixed rate (:data:`cross_basin._DISCOUNT_RATE`); passing
            any other value raises ``ValueError`` rather than silently
            producing numbers at a different rate than reported (#723 review
            Finding 2). ``meta.discount_rate`` always reports the rate the
            numbers were actually computed at.
        router: Object exposing ``get_adapter(region)``.  Defaults to a real
            ``RegionRouter``.
        depth_by_field: Optional ``{region: {field: depth_ft}}`` for concept mix.

    Returns:
        ``{rows, provenance, generated_regions, skipped_empty, concept_mix, meta}``.
    """
    if discount_rate != _DISCOUNT_RATE:
        raise ValueError(
            f"discount_rate={discount_rate} unsupported; "
            f"cross_basin.fiscal_sensitivity fixes {_DISCOUNT_RATE}. "
            "Refusing to report a rate the numbers were not computed at."
        )

    if router is None:
        from worldenergydata.production.unified.router import RegionRouter

        router = RegionRouter()

    rows: list[dict] = []
    provenance: dict[str, str] = {}
    generated_regions: list[str] = []
    skipped_empty: list[str] = []

    for region in regions:
        adapter = router.get_adapter(region)
        df = adapter.fetch(ProductionQuery(regions=[region]))

        if df is None or df.empty:
            logger.warning(
                "Skipping region %r: adapter returned no production rows "
                "(no fabricated zero-economics row emitted).",
                region,
            )
            skipped_empty.append(region)
            continue

        result = _single_region_result(region, df)
        prov_map = provenance_by_region(result)
        peaks = compare_peak_rates(result)
        fiscal = fiscal_sensitivity(result, oil_price_usd)

        peak_lookup = {
            (r["region"], r["field_name"]): r["peak_oil_bbl"]
            for _, r in peaks.iterrows()
        }
        for _, fr in fiscal.iterrows():
            key = (fr["region"], fr["field_name"])
            region_prov = prov_map.get(str(fr["region"]), "seed")
            rows.append(
                {
                    "region": str(fr["region"]),
                    "field_name": str(fr["field_name"]),
                    "peak_oil_bbl": float(peak_lookup.get(key, 0.0)),
                    "govt_take": float(fr["effective_govt_take_pct"]),
                    # Discounted post-tax cash flow over HISTORICAL production
                    # only, excluding all capex — NOT an investment NPV. Named
                    # honestly per #723 review Finding 3.
                    "disc_posttax_cf_usd": float(fr["operator_npv_usd"]),
                    "provenance": region_prov,
                }
            )
        provenance.update(prov_map)
        generated_regions.append(region)

    concept_mix = concept_mix_by_region(depth_by_field) if depth_by_field else {}

    return {
        "rows": rows,
        "provenance": provenance,
        "generated_regions": generated_regions,
        "skipped_empty": skipped_empty,
        "concept_mix": concept_mix,
        "meta": {
            "oil_price_usd": oil_price_usd,
            # The rate the numbers were ACTUALLY computed at (guaranteed above).
            "discount_rate": _DISCOUNT_RATE,
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "n_rows": len(rows),
        },
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_BADGE = {
    "real": ("badge-real", "Real regulatory data"),
    "seed": ("badge-seed", "Illustrative seed — not yet ingested"),
}

_CSS = """
:root{--navy:#0B3D91;--teal:#0f8a7e;--bg:#eef3fa;--panel:#fff;--ink:#13233f;--muted:#5b6b86;--line:#dbe4f0;--soft:#f4f8fc;--warn:#b7791f}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5;padding:32px 20px 80px}
main{max-width:1080px;margin:0 auto}
h1{font-size:28px;font-weight:800;color:var(--navy);letter-spacing:-.4px}
.sub{color:var(--muted);font-size:16px;margin-top:8px;max-width:820px}
.disclaimer{margin-top:20px;background:#fffaf0;border:1px solid #f0dcae;border-left:4px solid var(--warn);border-radius:10px;padding:14px 16px;color:#7a5a12;font-size:14px}
table{width:100%;border-collapse:collapse;margin-top:26px;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:11px 14px;text-align:left;font-size:14px;border-bottom:1px solid var(--line)}
th{background:var(--soft);color:var(--navy);font-weight:700;font-size:12.5px;text-transform:uppercase;letter-spacing:.4px}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr[data-provenance="seed"]{background:#fffdf8}
tr:last-child td{border-bottom:none}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:700;white-space:nowrap}
.badge-real{background:#e6f6ec;color:#127a3e;border:1px solid #b7e3c6}
.badge-seed{background:#fdf3e0;color:#8a5a12;border:1px solid #f0dcae}
.concept{margin-top:34px}
.concept h2{font-size:18px;color:var(--navy);border-left:4px solid var(--teal);padding-left:12px}
.skip{margin-top:24px;color:var(--muted);font-size:13px}
footer{margin-top:40px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);padding-top:16px}
a.back{color:var(--teal);font-weight:700}
"""


def _fmt_int(v: float) -> str:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{v:,.0f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(v: float) -> str:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{v:.1f}%"
    except (TypeError, ValueError):
        return "—"


def render_benchmark_html(benchmark: dict) -> str:
    """Render the benchmark as a self-contained HTML document.

    Every row shows a visible provenance badge and, for seed rows, a
    ``data-provenance="seed"`` attribute — so a seed row can NEVER be presented
    with the "real" badge.  No external assets are referenced (inline CSS only).

    Args:
        benchmark: The structure returned by :func:`build_benchmark`.

    Returns:
        A complete ``<!DOCTYPE html>`` string.
    """
    meta = benchmark.get("meta", {})
    rows = benchmark.get("rows", [])

    body_rows = []
    for r in rows:
        prov = r.get("provenance", "seed")
        badge_cls, badge_txt = _BADGE.get(prov, _BADGE["seed"])
        body_rows.append(
            "<tr data-provenance=\"{prov}\">"
            "<td>{region}</td>"
            "<td>{field}</td>"
            "<td class=\"num\">{peak}</td>"
            "<td class=\"num\">{take}</td>"
            "<td class=\"num\">{npv}</td>"
            "<td><span class=\"badge {cls}\">{badge}</span></td>"
            "</tr>".format(
                prov=html.escape(prov),
                region=html.escape(str(r.get("region", ""))),
                field=html.escape(str(r.get("field_name", ""))),
                peak=_fmt_int(r.get("peak_oil_bbl", 0.0)),
                take=_fmt_pct(r.get("govt_take", 0.0)),
                npv=_fmt_int(r.get("disc_posttax_cf_usd", 0.0)),
                cls=badge_cls,
                badge=html.escape(badge_txt),
            )
        )

    # Concept-mix section (optional).
    concept_html = ""
    concept_mix = benchmark.get("concept_mix") or {}
    if concept_mix:
        crows = []
        for region, counts in sorted(concept_mix.items()):
            crows.append(
                "<tr><td>{r}</td><td class=\"num\">{d}</td><td class=\"num\">{s15}</td>"
                "<td class=\"num\">{s20}</td><td class=\"num\">{u}</td></tr>".format(
                    r=html.escape(str(region)),
                    d=counts.get("dry", 0),
                    s15=counts.get("subsea15", 0),
                    s20=counts.get("subsea20", 0),
                    u=counts.get("unknown", 0),
                )
            )
        concept_html = (
            "<section class=\"concept\"><h2>Development-concept mix by region</h2>"
            "<p class=\"sub\">Fields bucketed by water depth via "
            "<code>classify_dev_system_by_depth</code>; fields without a known "
            "depth are counted as <em>unknown</em> (depth is never fabricated).</p>"
            "<table><thead><tr><th>Region</th><th>Dry tree</th><th>Subsea (&lt;6000 ft)</th>"
            "<th>Subsea (&ge;6000 ft)</th><th>Unknown</th></tr></thead><tbody>"
            + "".join(crows)
            + "</tbody></table></section>"
        )

    skipped = benchmark.get("skipped_empty") or []
    skip_html = ""
    if skipped:
        skip_html = (
            "<p class=\"skip\">Regions skipped (adapter returned no rows — no "
            "fabricated economics emitted): <strong>"
            + html.escape(", ".join(skipped))
            + "</strong></p>"
        )

    generated = ", ".join(benchmark.get("generated_regions", [])) or "—"

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>worldenergydata — Cross-Country Field-Development Benchmark</title>
<style>{_CSS}</style>
</head>
<body>
<main>
  <p><a class="back" href="../capabilities/">&larr; Capabilities</a></p>
  <h1>Cross-country field-development benchmark</h1>
  <p class="sub">Peak production, effective government take and a discounted
     post-tax cash-flow proxy (historical, no capex) across offshore regions,
     each row badged with its data provenance. Fiscal coefficients are
     simplified public approximations — not legal or financial advice.</p>
  <div class="disclaimer">
    <strong>Provenance notice.</strong> Rows tagged
    <span class="badge badge-seed">Illustrative seed — not yet ingested</span>
    use <strong>synthetic mock data</strong> from the region adapter and must
    not be read as measured regulatory production. Only rows tagged
    <span class="badge badge-real">Real regulatory data</span> are sourced from
    ingested public regulatory records. The <strong>Discounted post-tax CF</strong>
    column is discounted post-tax cash flow over <strong>historical production
    only, excluding all capital expenditure</strong> — it is a backward-looking
    cash-flow proxy, not a forward-looking investment NPV.
  </div>
  <table>
    <thead>
      <tr>
        <th>Region</th><th>Field</th><th>Peak oil (bbl/mo)</th>
        <th>Govt take</th><th>Discounted post-tax CF (hist., no capex, USD)</th><th>Provenance</th>
      </tr>
    </thead>
    <tbody>
      {''.join(body_rows) if body_rows else '<tr><td colspan="6">No data.</td></tr>'}
    </tbody>
  </table>
  {skip_html}
  {concept_html}
  <footer>
    Generated {html.escape(str(meta.get('generated_utc', '')))} ·
    oil price ${html.escape(str(meta.get('oil_price_usd', '')))}/bbl ·
    discount {float(meta.get('discount_rate', 0.10)) * 100:.0f}% ·
    regions: {html.escape(generated)} ·
    Public regulatory data only. Source: worldenergydata unified production adapters.
  </footer>
</main>
</body>
</html>
"""
    return doc


# ---------------------------------------------------------------------------
# Report generation (CI-safe: uses mock adapters, no BSEE binary)
# ---------------------------------------------------------------------------

# Illustrative public water depths (ft) for the mock benchmark fields, used
# only to populate the concept-mix table.  Fields not listed classify as
# "unknown" — depth is never fabricated for the economics.
_ILLUSTRATIVE_DEPTHS_FT: dict[str, dict[str, Optional[float]]] = {
    "ncs": {"Edvard Grieg": 360.0, "Valhall": 230.0, "Ivar Aasen": 360.0},
    "gom": {"Atlantis": 7070.0, "Thunder Horse": 6300.0,
            "Mars-Ursa": 3000.0, "Na Kika": 6340.0},
    "brazil": {},
    "ukcs": {},
}


def generate_report(output_dir: Optional[Path] = None) -> dict:
    """Generate the benchmark report artifacts (``index.html`` + ``_facts.json``).

    Uses the default ``RegionRouter`` (mock adapters), so it runs in CI without
    the 300MB BSEE binary.  Every region resolves to synthetic data and is
    therefore badged as seed.

    Args:
        output_dir: Target directory.  Defaults to
            ``<repo>/reports/field_benchmark``.

    Returns:
        The benchmark dict that was rendered.
    """
    from worldenergydata.production.unified.router import RegionRouter

    router = RegionRouter()
    regions = router.list_regions()

    depth_by_field: dict[str, dict[str, Optional[float]]] = {}
    for region in regions:
        try:
            fields = router.get_adapter(region).available_fields()
        except Exception:  # pragma: no cover - defensive
            fields = []
        region_depths = _ILLUSTRATIVE_DEPTHS_FT.get(region, {})
        depth_by_field[region] = {f: region_depths.get(f) for f in fields}

    benchmark = build_benchmark(
        regions, router=router, depth_by_field=depth_by_field
    )

    out = Path(output_dir) if output_dir else (_REPO_ROOT / "reports" / "field_benchmark")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_benchmark_html(benchmark), encoding="utf-8")
    (out / "_facts.json").write_text(
        json.dumps(benchmark, indent=2, sort_keys=True), encoding="utf-8"
    )
    logger.info("Wrote benchmark report to %s", out)
    return benchmark


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    b = generate_report()
    print(
        f"generated_regions={b['generated_regions']} "
        f"skipped_empty={b['skipped_empty']} rows={len(b['rows'])}"
    )
