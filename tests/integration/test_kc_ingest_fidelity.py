"""KC-deepwater ingest fidelity (#842).

The canonical FDAS extractor (``docs/modules/bsee/analysis/production/FDAS_V30/
extract_drilling_completion_days.py``) now reads the raw BSEE WAR ``.bin``
pickles on the data share directly, and the lease list gained Buckskin's six
Keathley Canyon leases (``leases_v21_kc.csv``).

Two fidelity anchors pin that ingest:

* **Anchor** — 731 drilling / 399 completion days.
* **Buckskin** — 25 bores / 1,171 D&C days.

.. note:: These values changed with the basis (#1075).

   They previously read 821 / 1,004 and 2,056, reproducing the frozen V30
   workbook. Those were *reproducibility* pins: they asserted that the ``.bin``
   code path reproduced an earlier extraction, not that either was correct.
   Both encoded the calendar spud-to-TD rule, in which drilling days measure
   elapsed time rather than rig time and completion days accrue after TD
   without bound.

   Days now come from ``war_rig_days`` on BSEE WAR activity codes, so these
   pins *had* to move; leaving them would have pinned the defect. They are
   updated here deliberately, in the same commit as the basis change, and not
   weakened — each still asserts an exact figure. The direction is uniform
   (every development falls, −35.3% overall) and the cause is documented in
   #1063.

   Note these anchors remain *reproducibility* pins against our own output.
   The only external check on the basis is well 608124009500, covered by
   ``tests/unit/bsee/analysis/test_war_rig_days.py`` against the domain
   owner's hand-worked numbers.

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

pytestmark = pytest.mark.slow

# Only the extraction tests need the share; the leases-CSV integrity test
# must keep running in CI where /mnt/ace is absent.
requires_share = pytest.mark.skipif(
    not WAR_MAIN.exists(),
    reason="raw WAR .bin share not mounted at /mnt/ace",
)

BUCKSKIN_LEASES = {"G25806", "G25813", "G25814", "G25815", "G25823", "G32650"}


@pytest.fixture(scope="module")
def extract(tmp_path_factory):
    """Run the canonical extractor once against the raw .bin share."""
    out = tmp_path_factory.mktemp("kc_ingest") / "dc_days_candidate.xlsx"
    proc = subprocess.run(
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
        capture_output=True,
        cwd=FDAS_DIR,
    )
    assert proc.returncode == 0, proc.stderr.decode()
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


@requires_share
def test_anchor_reproduces_frozen_v30_exactly(extract):
    # Was 821 / 1,004 on the calendar basis; see the module docstring.
    anchor = _dev(extract, "Anchor")
    assert int(anchor["DRILLING_DAYS"].sum()) == 731
    assert int(anchor["COMPLETION_DAYS"].sum()) == 399


@requires_share
def test_buckskin_recovered(extract):
    buckskin = _dev(extract, "Buckskin")
    assert buckskin["API_WELL_NUMBER"].nunique() == 25
    dc = int(buckskin["DRILLING_DAYS"].sum() + buckskin["COMPLETION_DAYS"].sum())
    # Was 2,056 on the calendar basis. The World Oil April 2026 article's
    # 24 bores / 2,004 D&C is not an independent check on this figure --
    # that table is itself this repository's model output.
    assert dc == 1171


@requires_share
def test_all_wells_map_to_a_development(extract):
    assert extract["DEV_NAME"].notna().all()
    assert len(extract) == 253
