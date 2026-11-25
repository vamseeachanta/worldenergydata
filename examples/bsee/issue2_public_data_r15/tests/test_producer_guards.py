"""Failure cases for the r15 source selection and reconciliation."""
import sys
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

BSEE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BSEE))
from issue2_public_data_r15 import derive_r15 as derive
from issue2_public_data_r15.tests.input_fixtures import write_synthetic_archives


def test_partition_rejects_negative_kept_even_if_it_balances():
    with pytest.raises(ValueError, match="APD.*-1 kept"):
        derive.partition("APD", 1, "first_permit_in_period", -1, {"outside_years": 2})


def qualifying_borehole(depth):
    return pd.DataFrame([{
        "REGION_CODE": "G", "WELL_NAME_SUFFIX": "ST00BP00", "BOREHOLE_STAT_CD": "",
        "API_WELL_NUMBER": "001", "WELL_SPUD_DATE": "01/01/2015", "WATER_DEPTH": depth,
        "SURF_LATITUDE": "26", "SURF_LONGITUDE": "-90",
    }])


def test_qualifying_well_with_missing_depth_is_rejected():
    with pytest.raises(ValueError, match="missing water depth"):
        derive.map_data(qualifying_borehole(""), derive.derive_r12.WTI)


def test_unlisted_well_band_is_rejected_before_annual_counts(monkeypatch):
    # Model a new label from the classifier used to build the annual map.
    classifier = derive.derive_r12.load_r9()
    monkeypatch.setattr(classifier, "band_from_feet", lambda depth: "New depth band")
    monkeypatch.setattr(derive.derive_r12, "load_r9", lambda: classifier)
    with pytest.raises(ValueError, match="New depth band"):
        derive.map_data(qualifying_borehole("50"), derive.derive_r12.WTI)


def test_annual_counts_must_include_every_mapped_well(tmp_path, monkeypatch):
    write_synthetic_archives(tmp_path)
    yearly_counts = derive.derive_r12.yearly_counts
    monkeypatch.setattr(derive.derive_r12, "yearly_counts",
                        lambda wells, bands: yearly_counts(wells.iloc[1:], bands))
    with pytest.raises(ValueError, match="1 annual starts, 2 mapped wells, 2 drilling rows"):
        derive.build_tables(tmp_path, pd.DataFrame())


def test_drilling_rows_must_match_mapped_wells_even_if_partition_balances(tmp_path, monkeypatch):
    write_synthetic_archives(tmp_path)
    prepare = derive.r9.prepare_boreholes

    def exclude_one_from_drilling(bore):
        # One fewer qualified spud and one additional exclusion still reconcile to raw.
        bore = bore.copy()
        bore.loc[bore.API_WELL_NUMBER.eq("001"), "BOREHOLE_STAT_CD"] = "CNL"
        return prepare(bore)

    monkeypatch.setattr(derive.r9, "prepare_boreholes", exclude_one_from_drilling)
    with pytest.raises(ValueError, match="2 annual starts, 2 mapped wells, 1 drilling rows"):
        derive.build_tables(tmp_path, pd.DataFrame())


@pytest.mark.parametrize("member", ["mv_apd_main_all", "mv_apddata_all"])
@pytest.mark.parametrize("column", ["Est_Days", "Est_Duration"])
def test_apd_rejects_duration_columns_regardless_of_case(tmp_path, member, column):
    write_apd_member_case(tmp_path, member, column)
    with pytest.raises(ValueError, match=f"{member}/{column}"):
        derive.permit_data(tmp_path, [])


@pytest.mark.parametrize("member", ["mv_apd_main_all", "mv_apddata_all"])
def test_header_only_apd_member_is_rejected(tmp_path, member):
    write_apd_member_case(tmp_path, member, extra_column=None)
    with pytest.raises(ValueError, match=f"{member}.*no data rows"):
        derive.permit_data(tmp_path, [])


def write_apd_member_case(directory, member, extra_column):
    write_synthetic_archives(directory)
    path = directory / derive.APD
    with ZipFile(path) as archive:
        members = {name: archive.read(name).decode() for name in archive.namelist()}
    name = member + ".txt"
    header, *rows = members[name].splitlines()
    if extra_column is None:
        members[name] = header + "\n"
    else:
        members[name] = f"{header},{extra_column}\n" + "".join(f"{row},5\n" for row in rows)
    with ZipFile(path, "w") as archive:
        for name, contents in members.items():
            archive.writestr(name, contents)
