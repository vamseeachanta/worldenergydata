#!/usr/bin/env python3
"""Regenerate the single field-economics report for every producing Lower
Tertiary field, on the latest window (auto-detected newest OGOR-A month) with
the verified first-oil corrections applied.

One process loops over all fields so the heavy package import / .bin-loader
patch / latest-month detection are paid once, not per field. Each field's
leases are auto-derived (multi-lease fields handled).

Usage:
    uv run python scripts/lower_tertiary/regenerate_all_field_reports.py
"""

from __future__ import annotations

import argparse
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_field_economics_report as gen  # noqa: E402
from worldenergydata.lower_tertiary import (  # noqa: E402
    v30_financial_reproducer as _fin,
)
from worldenergydata.lower_tertiary import v30_reproducer as _rep  # noqa: E402
from worldenergydata.lower_tertiary.latest_runner import (  # noqa: E402
    FIRST_OIL_CORRECTIONS,
)


def _install_batch_caches() -> None:
    """Memoize the heavy/identical loaders for the batch run.

    OGOR .bin production and WTI prices are identical across every field, so
    reading them once (then copying on use to stay mutation-safe) turns dozens
    of ~300MB disk reads / network WTI fetches into one each. Also memoizes the
    all-fields V30 financials (recomputed inside every build_report otherwise).
    Must run AFTER gen._ensure_ogor_loader() so the .bin loader is the target.
    """

    def _df_cache_keyed(raw):
        cache: dict = {}

        def f(*args, **kwargs):
            key = (
                tuple(str(a) for a in args),
                tuple(sorted((k, str(v)) for k, v in kwargs.items())),
            )
            if key not in cache:
                cache[key] = raw(*args, **kwargs)
            return cache[key].copy()

        return f

    # OGOR loader (currently gen._load_ogor_from_bin via _ensure_ogor_loader).
    ogor = _df_cache_keyed(_fin.load_ogor_production)
    _rep.load_ogor_production = ogor
    _fin.load_ogor_production = ogor

    # WTI: frozen V30 xlsx + extended EIA/FRED (network).
    v30_wti = _df_cache_keyed(_fin.load_v30_wti_prices)
    _rep.load_v30_wti_prices = v30_wti
    _fin.load_v30_wti_prices = v30_wti
    # load_extended_wti_prices is imported LOCALLY inside build_field_npv_timeline
    # from the wti_prices module, so patch it at the source module.
    from worldenergydata.lower_tertiary import wti_prices as _wti

    _wti.load_extended_wti_prices = _df_cache_keyed(_wti.load_extended_wti_prices)
    if hasattr(_wti, "load_v30_wti_prices"):
        _wti.load_v30_wti_prices = _df_cache_keyed(_wti.load_v30_wti_prices)

    # Small reference tables, reloaded repeatedly across fields.
    for name in ("load_v30_leases", "load_v30_drilling", "load_v30_assumptions"):
        raw = getattr(_fin, name, None) or getattr(_rep, name, None)
        if raw is not None:
            cached = _df_cache_keyed(raw)
            setattr(_rep, name, cached)
            setattr(_fin, name, cached)

    # reproduce_v30_production runs a heavy groupby over the FULL OGOR set and
    # is called ~3x per report (timeline, stackup, financials) with the same
    # end_date — the dominant cost. Memoize by call signature. Returns a dict of
    # per-dev frames; callers .copy() the frames before mutating, so this is safe.
    _raw_prod = _fin.reproduce_v30_production
    _prod_cache: dict = {}

    def _prod_memo(*args, **kwargs):
        key = (
            tuple(str(a) for a in args),
            tuple(sorted((k, str(v)) for k, v in kwargs.items())),
        )
        if key not in _prod_cache:
            _prod_cache[key] = _raw_prod(*args, **kwargs)
        return _prod_cache[key]

    _rep.reproduce_v30_production = _prod_memo
    _fin.reproduce_v30_production = _prod_memo

    # All-fields V30 financials are window-independent and read-only here.
    _raw_fin = _fin.reproduce_v30_financials
    _fin_cache: dict = {}

    def _fin_memo():
        if "v" not in _fin_cache:
            _fin_cache["v"] = _raw_fin()
        return _fin_cache["v"]

    _fin.reproduce_v30_financials = _fin_memo

# Producing Lower Tertiary fields (display names as in the golden baseline).
# Pre-production fields (North Platte, Kaskida, Tiber) have no NPV timeline.
PRODUCING_FIELDS = [
    "Jack St Malo",
    "Stones",
    "Julia",
    "Big Foot",
    "Cascade Chinook",
    "Anchor",
    "Shenandoah",
]

REPORTS_DIR = gen.PROJECT_ROOT / "reports" / "lower_tertiary"
_NPV_RE = re.compile(r"Terminal cumulative NPV = \*\*\$([-\d,.]+) M\*\*")


def _slug(dev_name: str) -> str:
    return dev_name.lower().replace(" ", "_").replace("/", "_")


def _terminal_npv(report_md: str) -> str:
    m = _NPV_RE.search(report_md)
    return f"${m.group(1)} M" if m else "n/a"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fields",
        nargs="+",
        default=None,
        help="Subset of field display names to generate (default: all "
        "producing fields). Useful for chunking heavy fields into separate runs.",
    )
    args = parser.parse_args(argv)

    fields = args.fields if args.fields else PRODUCING_FIELDS

    gen._ensure_ogor_loader()
    _install_batch_caches()
    latest_month = gen.detect_latest_ogor_month()
    latest_end = gen._month_end_str(latest_month)
    print(
        f"Latest OGOR-A month: {latest_month.strftime('%Y-%m')} (end {latest_end})",
        flush=True,
    )
    print(flush=True)

    results: list[tuple[str, str, str, str]] = []  # field, window, status, detail
    for dev in fields:
        label = f"{dev} [latest]"
        try:
            report = gen.build_report(
                dev,
                None,
                end_date=latest_end,
                first_oil_overrides=FIRST_OIL_CORRECTIONS,
            )
            out = REPORTS_DIR / f"field_economics_{_slug(dev)}.md"
            out.write_text(report, encoding="utf-8")
            npv = _terminal_npv(report)
            results.append((dev, "latest", "OK", f"NPV {npv} -> {out.name}"))
            print(f"  OK   {label:<34} NPV {npv}", flush=True)
        except Exception as exc:  # noqa: BLE001 - want a per-field summary
            results.append((dev, "latest", "FAIL", str(exc)))
            print(f"  FAIL {label:<34} {exc}", flush=True)
            traceback.print_exc()

    print()
    print("=== SUMMARY ===")
    ok = sum(1 for r in results if r[2] == "OK")
    for dev, win, status, detail in results:
        print(f"  [{status:<4}] {dev} [{win}]: {detail}")
    print(f"\n{ok}/{len(results)} reports generated.")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
