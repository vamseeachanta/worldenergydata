"""Unit tests for the Kansas KGS ingest (#725).

Fixtures reproduce the verified quirks of the real files: the wrapped header
fragment on line 2 of the proration file, Oracle DD-Mon-YYYY dates in the
wells master, zero-pressure "not tested" rows, and wells missing from the
wells master.
"""

import textwrap

import pandas as pd
import pytest

from worldenergydata.modules.state_regulators.kansas_kgs.parsers import (
    read_proration_pressures,
    read_wells_master,
)
from worldenergydata.modules.state_regulators.kansas_kgs.pipeline import (
    build_coverage_stats,
    build_pressure_observations,
)

PRORATION_FIXTURE = textwrap.dedent(
    """\
    WELL_KID, LEASE, API_NUMBER, OPERATOR, TOWNSHIP, TWN_DIR, RANGE, RANGE_DIR, SECTION, LATITUDE, LONGITUDE, YEAR, ACREAGE, SHUT_IN_PRESS, WORKING_PRES,DAILY_RATE, OPEN_FLOW, ADJ_DELIVER, WATER_PROD,METER_PRES, DIFFERENT, COEFF
    RES","DIFFERENT","COEFF"
    "1001232609","POWELL 2-31","15-067-20048","MESA PETROLEUM C","29","S","37","W","31","37.4789143","-101.4114608","1996","636","0","0","0","0","1297","0","0","0","0"
    "1001232609","POWELL 2-31","15-067-20048","MESA PETROLEUM C","29","S","37","W","31","37.4789143","-101.4114608","1997","636","47.3","38.8","337.26","1022","645","0","38.3","10.58","12.1"
    "1001232609","POWELL 2-31","15-067-20048","MESA PETROLEUM C","29","S","37","W","31","37.4789143","-101.4114608","1999","636","29.8","25.2","126.79","458","342","0","25","2","12.1"
    "1001232610","MCCLAREN 2-5","15-067-20049","MESA PETROLEUM CO.","30","S","37","W","5","37.4711805","-101.3932762","2002","640","","","0","0","171","","","0","0"
    "1001232610","MCCLAREN 2-5","15-067-20049","MESA PETROLEUM CO.","30","S","37","W","5","37.4711805","-101.3932762","2003","640","42.3","33.3","188.21","506","283","0","33.1","3.64","12.1"
    "9999999999","ORPHAN 1","15-189-11111","UNKNOWN OP","33","S","38","W","2","37.1","-101.2","2005","640","61.5","50.0","100.0","400","200","0","49","1","12.0"
    """
)

WELLS_FIXTURE = textwrap.dedent(
    """\
    "KID","API_NUMBER","API_NUM_NODASH","LEASE","WELL","FIELD","LATITUDE","LONGITUDE","LONG_LAT_SOURCE","TOWNSHIP","TWN_DIR","RANGE","RANGE_DIR","SECTION","SPOT","FEET_NORTH","FEET_EAST","FOOT_REF","ORIG_OPERATOR","CURR_OPERATOR","ELEVATION","ELEV_REF","SURFACE_ELEVATION_LIDAR","DEPTH","FORMATION_AT_TOTAL_DEPTH","PRODUCE_FORM","IP_OIL","IP_GAS","IP_WATER","PERMIT","SPUD","COMPLETION","PLUGGING","MODIFIED","OIL_KID","OIL_DOR_ID","GAS_KID","GAS_DOR_ID","KCC_PERMIT","STATUS","STATUS2","COMMENTS","LEASE_WELL_NAME"
    "1001232609","15-067-20048","15067200480000","POWELL","2-31","HUGOTON","37.4789143","-101.4114608","Calc. from footages","29","S","37","W","31","NE","4620","-3300","SE","MESA PETROLEUM C","unavailable","3341"," KB","3340.1","2800","CHASE","CHASE","","","","01-MAR-1960","12-MAR-1960","20-APR-1960","","13-JUN-2014","","","","","","GAS","Producing","","POWELL 2-31"
    "1001232610","15-067-20049","15067200490000","MCCLAREN","2-5","HUGOTON","37.4711805","-101.3932762","Calc. from footages","30","S","37","W","5","NW","1480","2130","NW","MESA PETROLEUM CO.","unavailable","3350"," TOPO","3350.5","0","CHASE","CHASE","","","","06-APR-1961","17-APR-1961","28-APR-1961","","18-APR-2014","","","","","","GAS","Producing","","MCCLAREN 2-5"
    """
)

SETTINGS = {
    "atmospheric_psi": 14.696,
    "test_type": "KS_PRORATION",
    "pressure_kind": "WHP_shut_in",
    "gradient_method": "whp_shutin_over_td_lower_bound",
    "min_pressure_psig": 0.0,
}


@pytest.fixture
def proration(tmp_path):
    path = tmp_path / "kansas_proration_pressures.txt"
    path.write_text(PRORATION_FIXTURE, encoding="utf-8")
    return read_proration_pressures(path)


@pytest.fixture
def wells(tmp_path):
    path = tmp_path / "ks_wells.txt"
    path.write_text(WELLS_FIXTURE, encoding="utf-8")
    return read_wells_master(path)


class TestParsers:
    def test_mangled_header_continuation_skipped(self, proration):
        assert len(proration) == 6
        assert list(proration["WELL_KID"].iloc[:2]) == ["1001232609", "1001232609"]

    def test_numeric_typing_and_blanks(self, proration):
        row_1997 = proration[proration["YEAR"] == 1997].iloc[0]
        assert row_1997["SHUT_IN_PRESS"] == pytest.approx(47.3)
        blank = proration[proration["YEAR"] == 2002].iloc[0]
        assert pd.isna(blank["SHUT_IN_PRESS"])

    def test_wells_oracle_dates_parsed(self, wells):
        assert wells["SPUD"].iloc[0] == pd.Timestamp("1960-03-12")
        assert wells["DEPTH"].iloc[0] == pytest.approx(2800.0)


class TestObservations:
    def test_zero_and_blank_pressures_excluded(self, proration, wells):
        obs = build_pressure_observations(proration, wells, SETTINGS)
        # 6 fixture rows: one zero (1996), one blank (2002) -> 4 observations
        assert len(obs) == 4
        assert (obs["pressure_psig_reported"] > 0).all()

    def test_gradient_only_with_positive_depth(self, proration, wells):
        obs = build_pressure_observations(proration, wells, SETTINGS)
        powell = obs[obs["well_key"] == "1001232609"]
        expected = (47.3 + 14.696) / 2800.0
        assert powell[powell["test_year"] == 1997]["gradient_psi_ft"].iloc[
            0
        ] == pytest.approx(expected)
        # MCCLAREN has DEPTH == 0 -> no gradient, no method
        mcclaren = obs[obs["well_key"] == "1001232610"]
        assert mcclaren["gradient_psi_ft"].isna().all()
        assert mcclaren["gradient_method"].isna().all()

    def test_earliest_observation_flag(self, proration, wells):
        obs = build_pressure_observations(proration, wells, SETTINGS)
        powell = obs[obs["well_key"] == "1001232609"].set_index("test_year")
        assert bool(powell.loc[1997, "is_earliest_observation"])
        assert not bool(powell.loc[1999, "is_earliest_observation"])

    def test_unmatched_well_kept_with_null_wells_fields(self, proration, wells):
        obs = build_pressure_observations(proration, wells, SETTINGS)
        orphan = obs[obs["well_key"] == "9999999999"]
        assert len(orphan) == 1
        assert orphan["api14"].isna().all()
        assert orphan["county_code"].iloc[0] == "189"

    def test_join_key_is_kid_not_api(self, proration, wells):
        obs = build_pressure_observations(proration, wells, SETTINGS)
        assert obs[obs["well_key"] == "1001232609"]["field"].eq("HUGOTON").all()


class TestCoverage:
    def test_coverage_stats_shape(self, proration, wells):
        obs = build_pressure_observations(proration, wells, SETTINGS)
        stats = build_coverage_stats(proration, obs, len(wells))
        assert stats["proration_rows_total"] == 6
        assert stats["proration_rows_with_pressure"] == 4
        assert stats["wells_with_pressure_observation"] == 3
        assert stats["wells_unmatched_in_wells_master"] == 1
        assert stats["test_year_range"] == [1997, 2005]
        assert stats["wells_by_field_top20"]["HUGOTON"] == 2
