"""Synthetic BSEE raw archives and manifest for the interventions example.

Two Gulf wells, four approved permits and one end-of-operations report, in
the archive and member layout the example reads. The manifest carries the
real size and SHA-256 of each archive, so a test can omit a receipt, mark it
failed or change an archive after the manifest was written.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pandas as pd

BOREHOLE = "BoreholeRawData.zip"
APM = "eWellAPMRawData.zip"
EOR = "eWellEORRawData.zip"
WAR = "eWellWARRawData.zip"
PAGE_UPDATED = "11/13/2026 4:31:20 AM"
FIRST_SPUD = "03/01/2006"


def boreholes(first_spud=FIRST_SPUD):
    return pd.DataFrame(
        [
            # Development well in 1,524 m of water, still producing.
            (
                "608174000100",
                "G",
                "5000",
                "ST00BP00",
                first_spud,
                "COM",
                "01/01/2007",
                "D",
            ),
            # Exploration well on the shelf, permanently abandoned in 2025.
            (
                "608174000200",
                "G",
                "300",
                "ST00BP00",
                "01/10/2008",
                "PA",
                "03/01/2025",
                "E",
            ),
        ],
        columns=[
            "API_WELL_NUMBER",
            "REGION_CODE",
            "WATER_DEPTH",
            "WELL_NAME_SUFFIX",
            "WELL_SPUD_DATE",
            "BOREHOLE_STAT_CD",
            "BOREHOLE_STAT_DT",
            "WELL_TYPE_CODE",
        ],
    )


def _members_apm():
    main = pd.DataFrame(
        [
            ("1", "608174000100", "01/15/2024", "WORKOVER", "G00001", "R1", "5"),
            ("2", "608174000200", "03/01/2025", "ABANDON", "G00002", "R2", "10"),
            ("3", "608174000100", "06/01/2025", "WORKOVER", "G00001", "R2", "3"),
            ("4", "608174000100", "11/01/2026", "ENHANCE", "G00001", "R1", "2"),
        ],
        columns=[
            "SN_APM",
            "API_WELL_NUMBER",
            "ACC_STATUS_DATE",
            "APM_OP_CD",
            "SURF_LEASE_NUM",
            "RIG_ID_NUM",
            "EST_OPERATION_DAYS",
        ],
    )
    return {
        "mv_apm_main": main,
        "mv_apm_suboperations": pd.DataFrame(
            {"SN_APM_FK": ["2"], "APM_SUBOP_CD": ["PERMABAN"]}
        ),
        "mv_apm_main_prop": pd.DataFrame(
            {
                "SN_APM": ["1", "2", "3", "4"],
                "APM_OP_DESC": [
                    "Replace tubing.",
                    "Permanently abandon the well.",
                    "Recomplete.",
                    "Acidize.",
                ],
            }
        ),
        "mv_apm_rig_view": pd.DataFrame(
            {
                "RIG_ID_NUM": ["R1", "R2"],
                "RIG_NAME": ["WIRELINE UNIT", "DRILLSHIP"],
                "RIG_TYPE_CODE": ["WL", "DS"],
            }
        ),
        "mv_apm_primary_op_codes": pd.DataFrame(
            {
                "VALUE": ["WORKOVER", "ABANDON", "ENHANCE"],
                "DESCRIP": ["Workover", "Abandon", "Enhance"],
            }
        ),
        "mv_apm_suboperation_codes": pd.DataFrame(
            {"VALUE": ["PERMABAN"], "DESCRIP": ["Permanent Abandonment"]}
        ),
    }


def _members_eor():
    return {
        "mv_eor_mainquery": pd.DataFrame(
            {
                "SN_EOR": ["E1"],
                "API_WELL_NUMBER": ["608174000100"],
                "EOR_OPERATION_CD": ["W"],
                "BOREHOLE_STAT_DT": ["06/10/2025"],
                "SURF_LEASE_NUMBER": ["G00001"],
                "SUBSEA_COMPLETION_FLAG": ["YES"],
            }
        )
    }


def _members_war():
    # One workover by a named drillship on the development well in 2025.
    return {
        "mv_war_main": pd.DataFrame(
            {
                "SN_WAR": ["W1"],
                "API_WELL_NUMBER": ["608174000100"],
                "WAR_START_DT": ["06/01/2025"],
                "WAR_END_DT": ["06/05/2025"],
                "RIG_NAME": ["DRILLSHIP"],
                "SURF_LEASE_NUM": ["G00001"],
            }
        ),
        "mv_war_main_prop": pd.DataFrame(
            {"SN_WAR": ["W1"], "WELL_ACTIVITY_CD": ["WO"]}
        ),
    }


def write_archive(path, members):
    with zipfile.ZipFile(path, "w") as z:
        for member, frame in members.items():
            buffer = io.StringIO()
            frame.to_csv(buffer, index=False, lineterminator="\n")
            z.writestr(f"{member}.txt", buffer.getvalue().encode("cp1252"))


def write_borehole(data_dir, first_spud=FIRST_SPUD):
    write_archive(
        Path(data_dir) / BOREHOLE, {"mv_boreholes_all": boreholes(first_spud)}
    )


def receipt(data_dir, name, status="downloaded", page_updated=PAGE_UPDATED):
    path = Path(data_dir) / name
    return dict(
        name=name,
        url=f"https://www.data.bsee.gov/Well/Files/{name}",
        page_last_updated=page_updated,
        download_utc="2026-11-13T16:17:33+00:00",
        bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        status=status,
    )


def build(data_dir, eor="downloaded", war=None, page_updated=PAGE_UPDATED):
    """Write the three archives and a manifest.

    eor: "downloaded" (verified receipt), "failed" (receipt marked failed) or
    "omitted" (no receipt). The EOR archive is on disk in every case.
    war: None (no WAR archive) or one of the eor states; the optional WAR
    archive is then on disk with that receipt state.
    page_updated: the raw-page update date of every receipt, which sets the
    snapshot file date.
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    write_borehole(data_dir)
    write_archive(data_dir / APM, _members_apm())
    write_archive(data_dir / EOR, _members_eor())
    files = [
        receipt(data_dir, BOREHOLE, page_updated=page_updated),
        receipt(data_dir, APM, page_updated=page_updated),
    ]
    if eor != "omitted":
        files.append(receipt(data_dir, EOR, eor, page_updated))
    if war is not None:
        write_archive(data_dir / WAR, _members_war())
        if war != "omitted":
            files.append(receipt(data_dir, WAR, war, page_updated))
    manifest = dict(source_id="bsee-data-center", files=files)
    (data_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return data_dir
