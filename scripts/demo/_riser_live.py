#!/usr/bin/env python3
# ABOUTME: Live-wires the riser grounded-card engineering panel to a real digitalmodel run (#771).
# ABOUTME: Runs digitalmodel.riser_fatigue as a SUBPROCESS in its own venv — the #768 pattern, per asset.

"""Produce the riser grounded-card's engineering panel from a LIVE digitalmodel run.

Second live arc of the engineering↔asset circle (#764), generalising the mooring
bridge (#768) to the riser asset. digitalmodel is NOT a worldenergydata dependency,
so the result crosses the repo boundary as data: we run
``digitalmodel.riser_fatigue.workflow.router`` via a subprocess in digitalmodel's own
venv and read back its summary CSV.

The riser *section* (OD / WT) and the wave+VIV scatter are a representative SCR spec
(labelled illustrative in the card ``basis``) — worldenergydata's field registers carry
riser *counts*, not per-riser stress histograms. The solver, DNV S-N curve, Miner damage
and fatigue life are all live digitalmodel.
"""

from __future__ import annotations

import csv
import glob
import os
import subprocess
import tempfile
from pathlib import Path

import yaml

from worldenergydata.hse.grounding_card import AnalysisSummary

DM_ROOT = Path(os.environ.get("DIGITALMODEL_ROOT", "/mnt/local-analysis/digitalmodel"))
DM_PY = DM_ROOT / ".venv/bin/python"

DESIGN_LIFE_YEARS = 25.0
DFF = 10.0  # DNV-OS-F201 riser fatigue design factor

# Representative steel catenary riser (SCR) in the touchdown zone — 10.75" x 22 mm
# API 5L X65, with an illustrative long-term wave stress histogram + a VIV case.
_SEGMENT = {
    "id": "SCR touchdown zone",
    "material": "API 5L X65",
    "outer_diameter_mm": 273.0,
    "wall_thickness_mm": 22.0,
    "wave": {
        "stress_ranges_MPa": [4.0, 8.0, 13.0, 20.0],
        "cycles": [1.2e7, 1.5e6, 6.0e4, 1.0e3],
        "scf": 1.15,
        "histogram_period_years": 1.0,
    },
    "viv_cases": [
        {"stress_range_MPa": 6.0, "frequency_hz": 0.2, "exposure_fraction": 0.05},
    ],
}


def build_cfg(out_dir: Path) -> dict:
    return {
        "basename": "riser_fatigue",
        "riser_fatigue": {
            "design_life_years": DESIGN_LIFE_YEARS,
            "dff": DFF,
            "sn_curve": {"curve": "F1", "environment": "seawater_cp"},
            "output_dir": str(out_dir),
            "segments": [_SEGMENT],
        },
    }


def run_dm_riser_fatigue() -> list[dict]:
    if not DM_PY.exists():
        raise RuntimeError(
            f"digitalmodel venv not found at {DM_PY}; set DIGITALMODEL_ROOT"
        )
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out_dir = td / "out"
        out_dir.mkdir()
        inp = td / "riser_fatigue.yml"
        inp.write_text(yaml.safe_dump(build_cfg(out_dir)))
        subprocess.run(
            [str(DM_PY), "-m", "digitalmodel", str(inp)],
            cwd=str(DM_ROOT),
            check=True,
            capture_output=True,
            timeout=300,
        )
        summ = glob.glob(str(out_dir / "*riser_fatigue*summary*.csv")) or glob.glob(
            str(out_dir / "*summary*.csv")
        )
        if not summ:
            raise RuntimeError("digitalmodel produced no riser_fatigue summary CSV")
        with open(summ[0], newline="") as fh:
            return list(csv.DictReader(fh))


def build_live_analysis() -> AnalysisSummary:
    rows = run_dm_riser_fatigue()
    gov = max(rows, key=lambda r: float(r["total_damage"]))
    life = float(gov["fatigue_life_years"])
    rel = "above" if life >= DESIGN_LIFE_YEARS else "below"
    return AnalysisSummary(
        title="Riser Fatigue — SCR touchdown zone, 10.75″ API 5L X65",
        headline=(
            f"Minimum fatigue life {life:,.0f} yr at the {gov['segment_id']} — "
            f"{rel} the {DESIGN_LIFE_YEARS:.0f}-yr design basis (DFF {DFF:g})."
        ),
        metrics=[
            (f"{life:,.0f} yr", "Min fatigue life"),
            (f"{float(gov['wave_damage']):.3f}", "Wave damage"),
            (f"{float(gov['viv_damage']):.3f}", "VIV damage"),
            (f"{DESIGN_LIFE_YEARS:.0f} yr", "Design basis"),
        ],
        method=(
            "Live digitalmodel riser_fatigue — DNV-RP-C203 S-N (curve F1, seawater w/ CP), "
            "wave-histogram + VIV Miner damage, DNV-OS-F201 DFF 10"
        ),
        basis=(
            "LIVE digitalmodel riser_fatigue run (subprocess, dm's own venv). Representative "
            "SCR section (273 mm × 22 mm, API 5L X65) + illustrative wave/VIV stress scatter; "
            "field registers carry riser counts, not per-riser stress histograms. Solver, S-N "
            "curve, Miner damage and life are live digitalmodel. #771."
        ),
    )
