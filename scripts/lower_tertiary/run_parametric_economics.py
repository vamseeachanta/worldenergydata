#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "pandas", "numpy"]
# ///
"""ABOUTME: YAML-driven parametric batch runner for LT field economics.
ABOUTME: Sweeps WTI price multiplier x discount rate over the sanctioned
ABOUTME: V30/V50 cashflow model and emits an HF-ready results grid.

Batch/parametric strategy
-------------------------
NPV is exact (affine) in a uniform WTI price multiplier (revenue and royalty
scale with price; opex, D&C, facilities and discounting do not — see the
"Run it yourself" note in the committed field economics reports). The runner
therefore takes TWO anchor runs of the sanctioned model per field
(:func:`build_field_npv_timeline`), then evaluates the full multiplier grid
exactly. Discount-rate variants are re-derived from each anchor's
*undiscounted* monthly cashflow using the model's own per-month discount
convention (recovered from the net/discounted column ratio, so no assumption
about the t0 convention is made). One extra direct model run verifies the
affine reconstruction end-to-end.

Publication gating follows the committed baseline `_performance.json`
(#971/#976): fields whose economics_status != "surfaced" have economics
withheld (null) in the publication CSV; the JSON keeps the full grid with an
explicit economics_status on every row.

    PYTHONPATH="src:packages/worldenergydata-core/src:packages/worldenergydata-bsee/src" \
    uv run --no-sync python scripts/lower_tertiary/run_parametric_economics.py \
        config/parametric/lt_economics_sweep.yml
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "worldenergydata-bsee" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "worldenergydata-core" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.lower_tertiary.latest_runner import (  # noqa: E402
    FIRST_OIL_CORRECTIONS,
)
from worldenergydata.lower_tertiary.ops_timeline import (  # noqa: E402
    detect_latest_ogor_month,
    ensure_ogor_loader,
    month_end_str,
)
from worldenergydata.lower_tertiary.v30_financial_reproducer import (  # noqa: E402
    build_field_npv_timeline,
)


def _slug(field: str) -> str:
    return field.strip().lower().replace(" ", "_").replace("/", "_")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _npv_at_rates(timeline, r0: float, rates: list[float]) -> dict[float, float]:
    """Terminal NPV of one anchor run at each requested annual discount rate.

    Recovers the model's per-month discount exponent t_i (in years) from the
    ratio net/discounted at the base rate r0, then re-discounts the same
    undiscounted monthly cashflow at each rate. Months with zero net cashflow
    contribute zero at every rate.
    """
    net = timeline["net_cashflow_usd"].to_numpy(dtype=float)
    disc = timeline["discounted_cashflow_usd"].to_numpy(dtype=float)
    nz = net != 0.0
    t_years = np.zeros_like(net)
    t_years[nz] = np.log(net[nz] / disc[nz]) / np.log(1.0 + r0)
    out: dict[float, float] = {}
    for r in rates:
        if abs(r - r0) < 1e-12:
            out[r] = float(disc.sum())
        else:
            out[r] = float((net[nz] / (1.0 + r) ** t_years[nz]).sum())
    return out


def main() -> int:
    cfg_path = Path(sys.argv[1] if len(sys.argv) > 1 else
                    PROJECT_ROOT / "config" / "parametric" / "lt_economics_sweep.yml").resolve()
    cfg = yaml.safe_load(cfg_path.read_text())

    source_desc = ensure_ogor_loader()
    end_date = cfg["end_date"]
    if end_date == "latest":
        end_date = month_end_str(detect_latest_ogor_month())

    multipliers = [float(m) for m in cfg["wti_price_multipliers"]]
    m1, m2 = (float(m) for m in cfg["anchor_multipliers"])
    rates = [float(r) for r in cfg["discount_rates"]]

    baseline = json.loads(
        (PROJECT_ROOT / cfg["baseline_performance"]).read_text()
    )["fields"]

    print(f"sweep={cfg['sweep_name']} source={source_desc} end_date={end_date}")
    fields_out: dict[str, dict] = {}
    coeffs: dict[str, dict[float, tuple[float, float]]] = {}
    matches: list[dict] = []

    for spec in cfg["fields"]:
        dev = spec["name"]
        input_set = spec.get("input_set", "v30")
        slug = _slug(dev)
        anchors = {}
        for m in (m1, m2):
            res = build_field_npv_timeline(
                dev,
                end_date=end_date,
                wti_price_multiplier=m,
                first_oil_overrides=FIRST_OIL_CORRECTIONS,
                input_set=input_set,
            )
            anchors[m] = {
                "npv_by_rate": _npv_at_rates(
                    res["timeline"], res["discount_rate_annual"], rates
                ),
                "terminal_npv_usd": res["terminal_npv_usd"],
                "r0": res["discount_rate_annual"],
            }
            print(f"  {dev}: anchor m={m} NPV ${res['terminal_npv_usd']/1e6:,.1f}M")

        status = baseline.get(slug, {}).get("economics_status", "unlisted")
        # Affine coefficients per rate: npv_r(m) = A_r + B_r * m
        grid = []
        breakeven = {}
        coeffs[slug] = {}
        for r in rates:
            n1, n2 = anchors[m1]["npv_by_rate"][r], anchors[m2]["npv_by_rate"][r]
            b = (n2 - n1) / (m2 - m1)
            a = n1 - b * m1
            coeffs[slug][r] = (a, b)
            breakeven[f"{r:g}"] = round(-a / b, 4) if b > 0 else None
            for m in multipliers:
                grid.append(
                    {
                        "wti_price_multiplier": m,
                        "discount_rate": r,
                        "npv_musd": round((a + b * m) / 1e6, 1),
                        "economics_status": status,
                    }
                )

        # Match-up against the committed baseline (m=1.0, r=r0).
        base_npv = baseline.get(slug, {}).get("npv_mm")
        r0 = anchors[m1]["r0"]
        a0, b0 = coeffs[slug][r0]
        run_npv = round((a0 + b0 * 1.0) / 1e6, 1)
        match = {
            "field": slug,
            "baseline_npv_mm": base_npv,
            "parametric_npv_mm_at_1x_r0": run_npv,
            "delta_mm": None if base_npv is None else round(run_npv - base_npv, 2),
            "economics_status": status,
        }
        matches.append(match)
        fields_out[slug] = {
            "display": dev,
            "input_set": input_set,
            "economics_status": status,
            "discount_rate_base": r0,
            "breakeven_multiplier_by_rate": breakeven,
            "grid": grid,
        }

    # Affinity verification: one direct run vs the affine prediction.
    v = cfg["verify"]
    vdev, vm = v["field"], float(v["wti_price_multiplier"])
    vslug = _slug(vdev)
    vres = build_field_npv_timeline(
        vdev,
        end_date=end_date,
        wti_price_multiplier=vm,
        first_oil_overrides=FIRST_OIL_CORRECTIONS,
        input_set="v50_kc" if vdev == "Buckskin" else "v30",
    )
    r0 = vres["discount_rate_annual"]
    va, vb = coeffs[vslug][r0]
    predicted_usd = va + vb * vm  # unrounded affine prediction
    delta_usd = abs(vres["terminal_npv_usd"] - predicted_usd)
    verify_ok = delta_usd <= float(v["tolerance_usd"])
    print(
        f"verify {vdev} m={vm}: direct ${vres['terminal_npv_usd']/1e6:,.1f}M "
        f"vs affine ${predicted_usd/1e6:,.1f}M -> delta ${delta_usd:,.2f} "
        f"({'OK' if verify_ok else 'FAIL'})"
    )

    out = {
        "sweep_name": cfg["sweep_name"],
        "schema_version": "1.0.0",
        "provenance": {
            "code_revision": _git_rev(),
            "config_path": str(cfg_path.relative_to(PROJECT_ROOT)),
            "config_sha256": _sha256(cfg_path),
            "data_source": source_desc,
            "end_date": end_date,
            "model": "worldenergydata.lower_tertiary.v30_financial_reproducer."
                     "build_field_npv_timeline",
            "economics_basis": "life_to_date_pretax_npv",
            "gating": "economics withheld in CSV unless baseline "
                      "economics_status == 'surfaced' (#971/#976)",
        },
        "verification": {
            "field": vdev,
            "wti_price_multiplier": vm,
            "delta_usd": round(delta_usd, 2),
            "ok": verify_ok,
        },
        "baseline_match": matches,
        "fields": fields_out,
    }

    json_path = PROJECT_ROOT / cfg["outputs"]["json"]
    csv_path = PROJECT_ROOT / cfg["outputs"]["csv"]
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(out, indent=2) + "\n")

    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["field", "economics_status", "wti_price_multiplier",
             "discount_rate", "npv_musd", "breakeven_multiplier"]
        )
        for slug, f in fields_out.items():
            for g in f["grid"]:
                surfaced = f["economics_status"] == "surfaced"
                w.writerow([
                    slug,
                    f["economics_status"],
                    g["wti_price_multiplier"],
                    g["discount_rate"],
                    g["npv_musd"] if surfaced else "",
                    f["breakeven_multiplier_by_rate"][f"{g['discount_rate']:g}"]
                    if surfaced else "",
                ])

    print(f"wrote {json_path.relative_to(PROJECT_ROOT)}")
    print(f"wrote {csv_path.relative_to(PROJECT_ROOT)}")
    return 0 if verify_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
