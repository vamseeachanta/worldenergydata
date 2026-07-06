"""KC-deepwater ingest fidelity (#842).

The canonical FDAS extractor (``docs/modules/bsee/analysis/production/FDAS_V30/
extract_drilling_completion_days.py``) now reads the raw BSEE WAR ``.bin``
pickles on the data share directly, and the lease list gained Buckskin's six
Keathley Canyon leases (``leases_v21_kc.csv``).

Two fidelity anchors pin that ingest:

* **Anchor** must reproduce the frozen V30 workbook exactly (821 drilling /
  1,004 completion days) — proving the ``.bin`` code path is bit-for-bit
  faithful to the canonical extraction on an already-matched field.
* **Buckskin** must land at 25 bores / 2,056 D&C days — the recovered field
  the shelf-only extract dropped (World Oil April 2026 article: 24 / 2,004).

Runs the real extractor against the real share; skipped when /mnt/ace is not
mounted (e.g., CI).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FDAS_DIR = (
    REPO_ROOT / "docs" / "modules" / "bsee" / "analysis" / "production" / "FDAS_V30"
)
SCRIPT = FDAS_DIR / "extract_drilling_completion_days.py"
LEASES = FDAS_DIR / "leases_v21_kc.csv"

WAR_BIN_DIR = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin/war")
WAR_MAIN = WAR_BIN_DIR / "mv_war_main.bin"
WAR_BOREHOLES = WAR_BIN_DIR / "mv_war_boreholes_view.bin"
WAR_REMARKS = WAR_BIN_DIR / "mv_war_main_prop_remark.bin"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not WAR_MAIN.exists(),
        reason="raw WAR .bin share not mounted at /mnt/ace",
    ),
]

BUCKSKIN_LEASES = {"G25806", "G25813", "G25814", "G25815", "G25823", "G32650"}


@pytest.fixture(scope="module")
def extract(tmp_path_factory):
    """Run the canonical extractor once against the raw .bin share."""
    out = tmp_path_factory.mktemp("kc_ingest") / "dc_days_candidate.xlsx"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--leases",
            str(LEASES),
            "--war-main",
            str(WAR_MAIN),
            "--war-boreholes",
            str(WAR_BOREHOLES),
            "--war-remarks",
            str(WAR_REMARKS),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        cwd=FDAS_DIR,
    )
    df = pd.read_excel(out, sheet_name="Sheet1")
    leases = pd.read_csv(LEASES)
    leases["_KEY"] = leases["LEASE_NUM"].str.upper()
    df["_KEY"] = df["SURF_LEASE_NUM"].str.upper()
    return df.merge(leases[["_KEY", "DEV_NAME"]], on="_KEY", how="left")


def _dev(df, name):
    return df[df["DEV_NAME"] == name]


def test_leases_file_is_v20_plus_buckskin():
    leases = pd.read_csv(LEASES)
    assert len(leases) == 26
    assert (
        set(leases.loc[leases["DEV_NAME"] == "Buckskin", "LEASE_NUM"])
        == BUCKSKIN_LEASES
    )


def test_anchor_reproduces_frozen_v30_exactly(extract):
    anchor = _dev(extract, "Anchor")
    assert int(anchor["DRILLING_DAYS"].sum()) == 821
    assert int(anchor["COMPLETION_DAYS"].sum()) == 1004


def test_buckskin_recovered(extract):
    buckskin = _dev(extract, "Buckskin")
    assert buckskin["API_WELL_NUMBER"].nunique() == 25
    dc = int(buckskin["DRILLING_DAYS"].sum() + buckskin["COMPLETION_DAYS"].sum())
    assert dc == 2056  # World Oil April 2026 article: 24 bores / 2,004 D&C


def test_all_wells_map_to_a_development(extract):
    assert extract["DEV_NAME"].notna().all()
    assert len(extract) == 253
