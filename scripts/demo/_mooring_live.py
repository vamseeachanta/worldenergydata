#!/usr/bin/env python3
# ABOUTME: Live-wires the mooring grounded-card engineering panel to a real digitalmodel run (#768).
# ABOUTME: Runs digitalmodel.mooring_fatigue as a SUBPROCESS in its own venv (repos stay decoupled).

"""Produce the mooring grounded-card's engineering panel from a LIVE digitalmodel run.

digitalmodel is NOT a worldenergydata dependency (separate repo, separate venv, heavy
deps). So the engineering result crosses the repo boundary **as data**: we run
``digitalmodel.mooring_fatigue`` via a subprocess in digitalmodel's own venv and read
back its summary CSV. This keeps both repos independently deployable — the loose
coupling the two-repo architecture is designed for (#764 engineering↔asset circle).

Inputs: the mooring component catalog (``data/modules/subsea/curated/mooring_components.csv``)
supplies real chain geometry + MBL. The catalog does NOT carry cyclic loading, so the
per-line tension scatter is a representative spectrum scaled to the line MBL (labelled
as illustrative loading in the card ``basis``). The solver, S-N curve, Miner damage and
fatigue life are all live digitalmodel.
"""

from __future__ import annotations

import csv
import glob
import math
import os
import subprocess
import tempfile
from pathlib import Path

import yaml

from worldenergydata.hse.grounding_card import AnalysisSummary

REPO = Path(__file__).resolve().parents[2]
COMPONENTS = REPO / "data/modules/subsea/curated/mooring_components.csv"
DM_ROOT = Path(os.environ.get("DIGITALMODEL_ROOT", "/mnt/local-analysis/digitalmodel"))
DM_PY = DM_ROOT / ".venv/bin/python"

DESIGN_LIFE_YEARS = 25.0
DFF = 3.0
N_LINES = 8


def pick_chain_component(path: Path = COMPONENTS) -> dict:
    """Largest-MBL steel chain in the catalog = a representative deepwater bottom line."""
    with open(path, newline="") as fh:
        chains = [r for r in csv.DictReader(fh) if r["COMPONENT_TYPE"] == "chain"]
    if not chains:
        raise RuntimeError(f"no chain components in {path}")
    return max(chains, key=lambda r: float(r["MBL_KN"]))


def _tension_bins(mbl_kn: float) -> list[dict]:
    """Representative fatigue loading scaled to the line MBL (illustrative scatter —
    the catalog carries geometry/MBL, not the cyclic tension history)."""
    return [
        {"tension_range_kN": round(0.05 * mbl_kn, 1), "n_cycles": 1.0e6},
        {"tension_range_kN": round(0.09 * mbl_kn, 1), "n_cycles": 2.0e5},
        {"tension_range_kN": round(0.14 * mbl_kn, 1), "n_cycles": 1.0e4},
    ]


def build_cfg(comp: dict, out_dir: Path) -> dict:
    d_mm = float(comp["SIZE_MM"])
    mbl = float(comp["MBL_KN"])
    area_mm2 = round(2 * math.pi / 4 * d_mm**2, 1)  # twin-bar studless chain
    bins = _tension_bins(mbl)
    lines = [
        {
            "id": f"Line {i + 1}",
            "material": "CHAIN",
            "area_mm2": area_mm2,
            "tension_range_bins": bins,
        }
        for i in range(N_LINES)
    ]
    return {
        "basename": "mooring_fatigue",
        "mooring_fatigue": {
            "design_life_years": DESIGN_LIFE_YEARS,
            "dff": DFF,
            "sn_curve": {"curve": "D", "environment": "seawater_cp"},
            "output_dir": str(out_dir),
            "lines": lines,
        },
    }


def run_dm_mooring_fatigue(comp: dict) -> list[dict]:
    """Run digitalmodel mooring_fatigue in its own venv; return the per-line summary rows."""
    if not DM_PY.exists():
        raise RuntimeError(
            f"digitalmodel venv not found at {DM_PY}; set DIGITALMODEL_ROOT"
        )
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out_dir = td / "out"
        out_dir.mkdir()
        cfg = build_cfg(comp, out_dir)
        inp = td / "mooring_fatigue.yml"
        inp.write_text(yaml.safe_dump(cfg))
        subprocess.run(
            [str(DM_PY), "-m", "digitalmodel", str(inp)],
            cwd=str(DM_ROOT),
            check=True,
            capture_output=True,
            timeout=300,
        )
        summ = glob.glob(str(out_dir / "*_mooring_fatigue_summary.csv"))
        if not summ:
            raise RuntimeError("digitalmodel produced no mooring_fatigue summary CSV")
        with open(summ[0], newline="") as fh:
            return list(csv.DictReader(fh))


def build_live_analysis() -> AnalysisSummary:
    """Run the live digitalmodel mooring-fatigue and map it to the card's AnalysisSummary."""
    comp = pick_chain_component()
    rows = run_dm_mooring_fatigue(comp)
    gov = max(
        rows, key=lambda r: float(r["total_damage"])
    )  # governing = min fatigue life
    life = float(gov["fatigue_life_years"])
    rel = "above" if life >= DESIGN_LIFE_YEARS else "below"
    return AnalysisSummary(
        title=f"Mooring Fatigue — {N_LINES}-line {comp['GRADE']} {comp['SIZE_MM']}mm chain (deepwater spread)",
        headline=(
            f"Minimum fatigue life {life:,.0f} yr at {gov['line_id']} — "
            f"{rel} the {DESIGN_LIFE_YEARS:.0f}-yr design basis."
        ),
        metrics=[
            (f"{life:,.0f} yr", "Min fatigue life"),
            (f"{float(gov['total_damage']):.3f}", "Max damage / line"),
            (gov["line_id"], "Governing line"),
            (f"{DESIGN_LIFE_YEARS:.0f} yr", "Design basis"),
        ],
        method=(
            "Live digitalmodel mooring_fatigue — T-N screening (DNV-RP-C203 S-N curve D, "
            f"seawater with CP), Miner's-rule damage across the tension scatter, DFF {DFF:g}"
        ),
        basis=(
            f"LIVE digitalmodel mooring_fatigue run (subprocess, dm's own venv). Component "
            f"{comp['COMPONENT_ID']} — MBL {comp['MBL_KN']} kN, {comp['DATA_SOURCE']}; geometry + MBL "
            f"from the mooring component catalog. Tension scatter is a representative spectrum scaled "
            f"to MBL (illustrative loading; the catalog carries no cyclic history). #768."
        ),
    )
