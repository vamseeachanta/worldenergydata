"""Tests for the HSE Risk Index Data Assembler.

Validates that the DataAssembler correctly loads, classifies, and aggregates
incident data from multiple HSE sources (BSEE, OSHA, Marine Safety, PHMSA,
EPA TRI) into per-activity metrics suitable for risk scoring.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.safety_analysis.risk_index.data_assembler import (
    DataAssembler,
)
from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
    IncidentClassifier,
)

# ---------------------------------------------------------------------------
# Synthetic data fixtures matching real column schemas
# ---------------------------------------------------------------------------


@pytest.fixture
def bsee_incidents_df() -> pd.DataFrame:
    """Synthetic BSEE accident investigation data (pipe-delimited source)."""
    return pd.DataFrame(
        {
            "DATE_OCCURRED": [
                "01/15/2020",
                "03/22/2020",
                "06/10/2020",
                "07/05/2020",
                "08/18/2020",
                "09/01/2020",
                "10/12/2020",
                "11/25/2020",
                "12/03/2020",
                "12/15/2020",
                "01/20/2021",
                "02/14/2021",
            ],
            "MILITARY_TIME": [
                "8:00",
                "14:30",
                "9:15",
                "11:00",
                "7:45",
                "16:20",
                "10:00",
                "13:30",
                "8:45",
                "15:00",
                "9:30",
                "11:15",
            ],
            "LEASE_NUMBER": [f"G{10000+i}" for i in range(12)],
            "AREA_BLOCK": [f"GC {700+i}" for i in range(12)],
            "ACCIDENT_TYPE": [
                "- Fire ",
                "- Explosion ",
                "- Injury ",
                "- LTA (>3 days) ",
                "- Pollution ",
                "- Fire ",
                "- Crane ",
                "- Blowout ",
                "- Fatality ",
                "- Fire ",
                "- Injury ",
                "- Explosion ",
            ],
            "PANEL_DISTRICT": ["DISTRICT"] * 12,
            "STATUS": ["Complete"] * 12,
            "fatalities": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
            "injuries": [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1],
        }
    )


@pytest.fixture
def bsee_incs_df() -> pd.DataFrame:
    """Synthetic BSEE INCs (incidents of non-compliance) data."""
    return pd.DataFrame(
        {
            "INC_DATE": [
                "8/21/2020 2:12:53 PM",
                "10/26/2020 2:58:41 PM",
                "11/5/2020 1:57:31 PM",
                "11/13/2020 12:58:22 PM",
                "12/01/2020 10:30:00 AM",
            ],
            "REGION": ["G", "G", "G", "G", "G"],
            "BUS_ASC_CODE": ["03295"] * 5,
            "BUS_ASC_NAME": ["Test Operator LLC"] * 5,
            "WARNING_INCS": [0, 1, 1, 0, 2],
            "COMP_SHUTIN_INCS": [1, 1, 1, 1, 0],
            "FAC_SHUTIN_INCS": [0, 0, 0, 1, 0],
        }
    )


@pytest.fixture
def bsee_inspections_df() -> pd.DataFrame:
    """Synthetic BSEE inspection data for INC rate computation."""
    return pd.DataFrame(
        {
            "INS_DATE": [
                "8/15/2020 10:30:00 AM",
                "10/20/2020 2:00:00 PM",
                "11/01/2020 10:51:00 AM",
                "11/10/2020 6:32:00 AM",
                "12/01/2020 9:00:00 AM",
                "12/10/2020 11:00:00 AM",
                "12/15/2020 8:30:00 AM",
                "12/20/2020 10:00:00 AM",
                "12/22/2020 14:00:00 PM",
                "12/28/2020 9:15:00 AM",
            ],
            "REGION": ["G"] * 10,
            "BUS_ASC_CODE": ["03295"] * 10,
            "BUS_ASC_NAME": ["Test Operator LLC"] * 10,
            "FACILITIES_INSPECTED": [1, 2, 1, 1, 1, 2, 1, 1, 1, 1],
            "INSPECTION_RECORDS": [1, 2, 1, 1, 1, 2, 1, 1, 1, 1],
            "INSPECTION_TYPES": [1, 2, 1, 1, 1, 2, 1, 1, 1, 1],
        }
    )


@pytest.fixture
def osha_accidents_df() -> pd.DataFrame:
    """Synthetic OSHA accident data matching osha_accident.csv schema."""
    return pd.DataFrame(
        {
            "summary_nr": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            "report_id": [200 + i for i in range(12)],
            "event_date": [
                "2020-01-10 00:00:00",
                "2020-02-15 00:00:00",
                "2020-03-20 00:00:00",
                "2020-04-05 00:00:00",
                "2020-05-12 00:00:00",
                "2020-06-18 00:00:00",
                "2020-07-22 00:00:00",
                "2020-08-14 00:00:00",
                "2020-09-03 00:00:00",
                "2020-10-19 00:00:00",
                "2020-11-08 00:00:00",
                "2020-12-25 00:00:00",
            ],
            "event_desc": [
                "WORKER FELL FROM DRILLING RIG DERRICK",
                "EXPLOSION AT WELLHEAD DURING PRODUCTION",
                "CRANE DROPPED LOAD ON PLATFORM",
                "PIPELINE RUPTURE AND GAS RELEASE",
                "WORKER STRUCK BY FALLING OBJECT ON RIG",
                "FIRE AT GAS PROCESSING FACILITY",
                "WORKER FELL FROM SCAFFOLD ON PLATFORM",
                "CHEMICAL RELEASE DURING TANK CLEANING",
                "WORKER CAUGHT IN ROTATING EQUIPMENT",
                "VEHICLE COLLISION ON WELL PAD",
                "WORKER SLIPPED ON WET DRILLING FLOOR",
                "ELECTRICAL SHOCK DURING MAINTENANCE",
            ],
            "event_keyword": [
                "FALL,DERRICK,DRILLING",
                "EXPLOSION,WELLHEAD,PRODUCTION",
                "CRANE,DROPPED,LOAD",
                "PIPELINE,RUPTURE,GAS",
                "STRUCK BY,FALLING OBJECT",
                "FIRE,GAS,PROCESSING",
                "FALL,SCAFFOLD,PLATFORM",
                "CHEMICAL,RELEASE,TANK",
                "CAUGHT IN,ROTATING",
                "VEHICLE,COLLISION",
                "SLIP,WET,DRILLING",
                "ELECTRICAL,SHOCK,MAINTENANCE",
            ],
            "sic_list": [
                "1381",
                "1311",
                "1794",
                "4612",
                "1381",
                "1311",
                "1629",
                "4959",
                "1381",
                "1311",
                "1381",
                "1731",
            ],
            "fatality": ["X", "", "", "", "X", "", "", "", "", "", "", ""],
            "state_flag": [""] * 12,
            "abstract_text": [""] * 12,
            "load_dt": ["2020-12-31"] * 12,
            "fatalities": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            "injuries": [0, 1, 1, 0, 0, 2, 1, 0, 1, 0, 1, 1],
        }
    )


@pytest.fixture
def osha_injuries_df() -> pd.DataFrame:
    """Synthetic OSHA injury details matching osha_accident_injury.csv schema."""
    return pd.DataFrame(
        {
            "summary_nr": [100, 101, 102, 104, 105, 105, 106, 108, 110, 111],
            "rel_insp_nr": [10000 + i for i in range(10)],
            "age": [35, 42, 28, 50, 33, 45, 38, 29, 41, 55],
            "sex": ["M", "M", "M", "M", "M", "M", "M", "M", "M", "M"],
            "nature_of_inj": [21, 10, 10, 21, 3, 3, 21, 10, 10, 12],
            "part_of_body": [4, 19, 12, 4, 10, 10, 4, 19, 12, 15],
            "src_of_injury": [19, 42, 15, 19, 24, 24, 42, 15, 42, 24],
            "event_type": [8, 5, 13, 8, 2, 2, 5, 13, 5, 2],
            "evn_factor": [18, 13, 18, 18, 3, 3, 13, 18, 13, 3],
            "hum_factor": [1, 9, 1, 1, 1, 1, 9, 1, 9, 1],
            "occ_code": [0] * 10,
            "degree_of_inj": [1, 2, 2, 1, 2, 2, 2, 2, 2, 2],
            "task_assigned": [1] * 10,
            "hazsub": [""] * 10,
            "const_op": [0] * 10,
            "const_op_cause": [0] * 10,
            "fat_cause": [0] * 10,
            "fall_distance": [""] * 10,
            "fall_ht": [""] * 10,
            "injury_line_nr": list(range(1, 11)),
            "load_dt": ["2020-12-31"] * 10,
        }
    )


@pytest.fixture
def marine_incidents_df() -> pd.DataFrame:
    """Synthetic marine safety incidents matching the SQLite schema."""
    return pd.DataFrame(
        {
            "incident_id": list(range(1, 16)),
            "source_agency": ["USCG"] * 15,
            "source_incident_id": [f"USCG-{1000+i}" for i in range(15)],
            "incident_date": pd.date_range("2020-01-01", periods=15, freq="ME"),
            "incident_type": [
                "COLLISION",
                "FIRE",
                "GROUNDING",
                "CAPSIZING",
                "POLLUTION",
                "FIRE",
                "COLLISION",
                "FLOODING",
                "EXPLOSION",
                "PERSONNEL_INJURY",
                "COLLISION",
                "FIRE",
                "GROUNDING",
                "OTHER",
                "PERSONNEL_INJURY",
            ],
            "severity_level": [3, 4, 2, 5, 1, 3, 2, 4, 5, 2, 3, 3, 2, 1, 2],
            "status": ["CLOSED"] * 15,
            "title": [f"Incident {i}" for i in range(1, 16)],
            "description": [
                "Vessel collision in channel",
                "Engine room fire on tanker",
                "Grounding on reef",
                "Small vessel capsized",
                "Oil sheen observed",
                "Galley fire on cargo vessel",
                "Allision with dock",
                "Flooding in cargo hold",
                "Explosion on chemical tanker",
                "Crew member injured on deck",
                "Vessel collision at anchor",
                "Electrical fire on bridge",
                "Soft grounding in shallow water",
                "Minor equipment damage",
                "Worker fell on wet deck",
            ],
            "fatalities": [0, 1, 0, 2, 0, 0, 0, 1, 3, 0, 0, 0, 0, 0, 0],
            "injuries": [2, 3, 1, 1, 0, 1, 0, 2, 5, 1, 1, 0, 0, 0, 1],
        }
    )


@pytest.fixture
def phmsa_incidents_df() -> pd.DataFrame:
    """Synthetic PHMSA pipeline incident data matching Excel schema."""
    return pd.DataFrame(
        {
            "REPORT_NUMBER": [f"20200001{i}" for i in range(12)],
            "IYEAR": [2020] * 12,
            "LOCAL_DATETIME": pd.date_range("2020-01-01", periods=12, freq="ME"),
            "FATAL": [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            "INJURE": [0, 1, 0, 2, 0, 1, 0, 0, 1, 0, 0, 0],
            "CAUSE": [
                "CORROSION",
                "EQUIPMENT FAILURE",
                "EXCAVATION DAMAGE",
                "INCORRECT OPERATION",
                "MATERIAL FAILURE OF PIPE OR WELD",
                "NATURAL FORCE DAMAGE",
                "OTHER OUTSIDE FORCE DAMAGE",
                "ALL OTHER CAUSES",
                "CORROSION",
                "EQUIPMENT FAILURE",
                "CORROSION",
                "MATERIAL FAILURE OF PIPE OR WELD",
            ],
            "CAUSE_DETAILS": [
                "External corrosion",
                "Control valve failure",
                "Third party excavation",
                "Valve left open",
                "Seam weld failure",
                "Flooding",
                "Vehicle impact",
                "Unknown",
                "Internal corrosion",
                "Pump failure",
                "Atmospheric corrosion",
                "Girth weld failure",
            ],
            "MAP_EIGHT_CAUSE": [
                "CORROSION",
                "EQUIPMENT FAILURE",
                "EXCAVATION DAMAGE",
                "INCORRECT OPERATION",
                "MATERIAL FAILURE OF PIPE OR WELD",
                "NATURAL FORCE DAMAGE",
                "OTHER OUTSIDE FORCE DAMAGE",
                "ALL OTHER CAUSES",
                "CORROSION",
                "EQUIPMENT FAILURE",
                "CORROSION",
                "MATERIAL FAILURE OF PIPE OR WELD",
            ],
            "MAP_EIGHT_SUBCAUSE": [
                "External",
                "Control/Relief",
                "Third party",
                "Valve",
                "Seam weld",
                "Flooding",
                "Vehicle",
                "Other",
                "Internal",
                "Pump/compressor",
                "Atmospheric",
                "Girth weld",
            ],
            "NARRATIVE": [
                "Pipeline corroded externally",
                "Control valve malfunctioned",
                "Excavator struck pipeline",
                "Operator left valve open",
                "Seam weld failed",
                "Flood waters exposed pipeline",
                "Vehicle struck above-ground pipe",
                "Cause not determined",
                "Internal corrosion at low point",
                "Pump seal failed",
                "Atmospheric corrosion on riser",
                "Girth weld cracked",
            ],
        }
    )


@pytest.fixture
def epa_tri_df() -> pd.DataFrame:
    """Synthetic EPA TRI chemical release data matching real CSV schema."""
    return pd.DataFrame(
        {
            "year": [
                2020,
                2020,
                2020,
                2021,
                2021,
                2021,
                2022,
                2022,
                2022,
                2022,
                2022,
                2022,
            ],
            "trifd": ["FAC001"] * 6 + ["FAC002"] * 6,
            "facility name": ["Test Refinery"] * 6 + ["Test Plant"] * 6,
            "st": ["TX"] * 6 + ["LA"] * 6,
            "primary naics": ["211120"] * 6 + ["324110"] * 6,
            "chemical": [
                "Benzene",
                "Toluene",
                "Ethylbenzene",
                "Benzene",
                "Xylene",
                "n-Hexane",
                "Benzene",
                "Naphthalene",
                "Methanol",
                "Hydrogen sulfide",
                "Ammonia",
                "Formaldehyde",
            ],
            "carcinogen": [
                "YES",
                "NO",
                "NO",
                "YES",
                "NO",
                "NO",
                "YES",
                "YES",
                "NO",
                "NO",
                "NO",
                "YES",
            ],
            "on-site release total": [
                1246.76,
                500.0,
                200.0,
                1100.0,
                300.0,
                150.0,
                980.0,
                250.0,
                100.0,
                50.0,
                75.0,
                120.0,
            ],
            "unit of measure": ["Pounds"] * 12,
            "5.1 - fugitive air": [
                78.3,
                50.0,
                20.0,
                65.0,
                30.0,
                15.0,
                55.0,
                25.0,
                10.0,
                5.0,
                7.5,
                12.0,
            ],
            "5.2 - stack air": [
                1168.46,
                450.0,
                180.0,
                1035.0,
                270.0,
                135.0,
                925.0,
                225.0,
                90.0,
                45.0,
                67.5,
                108.0,
            ],
        }
    )


@pytest.fixture
def classifier() -> IncidentClassifier:
    """Shared IncidentClassifier instance."""
    return IncidentClassifier()


@pytest.fixture
def assembler(classifier: IncidentClassifier) -> DataAssembler:
    """DataAssembler with real classifier for integration-style tests."""
    return DataAssembler(classifier=classifier)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAssembleFromDataFrames:
    """Test assembling and classifying incidents from pre-loaded DataFrames."""

    def test_assemble_from_single_source(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """Given a BSEE DataFrame, assemble classifies and produces output."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "activity_code" in result.columns
        assert "activity_name" in result.columns
        assert "total_incidents" in result.columns
        assert "fatalities" in result.columns
        assert "injuries" in result.columns

    def test_assemble_from_multiple_sources(
        self,
        assembler: DataAssembler,
        bsee_incidents_df: pd.DataFrame,
        osha_accidents_df: pd.DataFrame,
        marine_incidents_df: pd.DataFrame,
        phmsa_incidents_df: pd.DataFrame,
        epa_tri_df: pd.DataFrame,
    ):
        """Given DataFrames from all sources, assemble produces combined output."""
        sources = {
            "bsee": bsee_incidents_df,
            "osha": osha_accidents_df,
            "marine_safety": marine_incidents_df,
            "phmsa": phmsa_incidents_df,
            "epa_tri": epa_tri_df,
        }
        result = assembler.assemble(sources)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        # Must have all expected columns
        expected_cols = {
            "activity_code",
            "activity_name",
            "total_incidents",
            "fatalities",
            "injuries",
            "fatality_rate",
            "injury_rate",
            "tri_carcinogen_lbs",
            "inc_rate",
            "confidence",
            "sources",
            "weighted_incident_count",
        }
        assert expected_cols.issubset(set(result.columns))

    def test_assemble_preserves_all_activities(
        self,
        assembler: DataAssembler,
        bsee_incidents_df: pd.DataFrame,
        osha_accidents_df: pd.DataFrame,
    ):
        """Each unique activity from classification appears in the output."""
        sources = {
            "bsee": bsee_incidents_df,
            "osha": osha_accidents_df,
        }
        result = assembler.assemble(sources)

        # At least 2 different activity codes should appear
        assert result["activity_code"].nunique() >= 2


class TestAggregateMetrics:
    """Test per-activity metric aggregation."""

    def test_total_incidents_per_activity(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """total_incidents sums correctly per activity."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        total = result["total_incidents"].sum()
        assert total == len(bsee_incidents_df)

    def test_fatalities_per_activity(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """Fatalities are summed correctly per activity."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        total_fatalities = result["fatalities"].sum()
        assert total_fatalities == bsee_incidents_df["fatalities"].sum()

    def test_injuries_per_activity(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """Injuries are summed correctly per activity."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        total_injuries = result["injuries"].sum()
        assert total_injuries == bsee_incidents_df["injuries"].sum()

    def test_fatality_rate_computation(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """fatality_rate = fatalities / total_incidents for each activity."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        for _, row in result.iterrows():
            if row["total_incidents"] > 0:
                expected_rate = row["fatalities"] / row["total_incidents"]
                assert abs(row["fatality_rate"] - expected_rate) < 1e-9

    def test_injury_rate_computation(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """injury_rate = injuries / total_incidents for each activity."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        for _, row in result.iterrows():
            if row["total_incidents"] > 0:
                expected_rate = row["injuries"] / row["total_incidents"]
                assert abs(row["injury_rate"] - expected_rate) < 1e-9


class TestTriCarcinogenAggregation:
    """Test EPA TRI carcinogen-specific aggregation."""

    def test_carcinogen_lbs_summed_per_activity(
        self, assembler: DataAssembler, epa_tri_df: pd.DataFrame
    ):
        """EPA TRI carcinogen pounds are summed for YES-carcinogen records."""
        result = assembler.assemble({"epa_tri": epa_tri_df})

        # All EPA TRI records classify to ENV activity
        total_carcinogen = result["tri_carcinogen_lbs"].sum()

        # Expected: sum of on-site release total where carcinogen == YES
        expected = epa_tri_df.loc[
            epa_tri_df["carcinogen"].str.upper() == "YES",
            "on-site release total",
        ].sum()
        assert abs(total_carcinogen - expected) < 0.01

    def test_non_carcinogen_records_excluded(
        self, assembler: DataAssembler, epa_tri_df: pd.DataFrame
    ):
        """Non-carcinogen records do not contribute to tri_carcinogen_lbs."""
        # Make all records non-carcinogen
        modified = epa_tri_df.copy()
        modified["carcinogen"] = "NO"

        result = assembler.assemble({"epa_tri": modified})
        assert result["tri_carcinogen_lbs"].sum() == 0.0


class TestComplianceMetrics:
    """Test INC rate computation from BSEE data."""

    def test_inc_rate_from_bsee(
        self,
        assembler: DataAssembler,
        bsee_incs_df: pd.DataFrame,
        bsee_inspections_df: pd.DataFrame,
    ):
        """INC rate = (WARNING_INCS + COMP_SHUTIN_INCS) / total_inspections."""
        inc_rate = assembler.compute_inc_rate(bsee_incs_df, bsee_inspections_df)

        total_warnings = bsee_incs_df["WARNING_INCS"].sum()
        total_comp_shutins = bsee_incs_df["COMP_SHUTIN_INCS"].sum()
        total_violations = total_warnings + total_comp_shutins
        total_inspections = len(bsee_inspections_df)

        expected_rate = total_violations / total_inspections
        assert abs(inc_rate - expected_rate) < 1e-9

    def test_inc_rate_zero_inspections(
        self,
        assembler: DataAssembler,
        bsee_incs_df: pd.DataFrame,
    ):
        """INC rate returns 0.0 when no inspections exist."""
        empty_inspections = pd.DataFrame(
            columns=[
                "INS_DATE",
                "REGION",
                "BUS_ASC_CODE",
                "BUS_ASC_NAME",
                "FACILITIES_INSPECTED",
                "INSPECTION_RECORDS",
                "INSPECTION_TYPES",
            ]
        )
        inc_rate = assembler.compute_inc_rate(bsee_incs_df, empty_inspections)
        assert inc_rate == 0.0


class TestSourceWeighting:
    """Test that source reliability weights are applied correctly."""

    def test_weighted_incident_count(
        self,
        assembler: DataAssembler,
        bsee_incidents_df: pd.DataFrame,
        osha_accidents_df: pd.DataFrame,
    ):
        """Weighted incident count applies source-specific weights."""
        sources = {
            "bsee": bsee_incidents_df,
            "osha": osha_accidents_df,
        }
        result = assembler.assemble(sources)

        # The weighted count should differ from raw total_incidents
        # because different sources contribute with different weights
        assert "weighted_incident_count" in result.columns
        # For any activity, weighted_incident_count should be <= total_incidents
        # (since all weights are <= 1.0)
        for _, row in result.iterrows():
            assert row["weighted_incident_count"] <= row["total_incidents"] + 1e-9

    def test_source_weights_are_correct(self):
        """Validate the predefined source weight values."""
        assert DataAssembler.SOURCE_WEIGHTS == {
            "bsee": 0.30,
            "marine_safety": 0.25,
            "osha": 0.20,
            "phmsa": 0.15,
            "epa_tri": 0.10,
        }

    def test_single_source_weighting(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """Single source: weighted count = total_incidents * source_weight."""
        result = assembler.assemble({"bsee": bsee_incidents_df})

        for _, row in result.iterrows():
            expected = row["total_incidents"] * DataAssembler.SOURCE_WEIGHTS["bsee"]
            assert abs(row["weighted_incident_count"] - expected) < 1e-9

    def test_sources_list_populated(
        self,
        assembler: DataAssembler,
        bsee_incidents_df: pd.DataFrame,
        osha_accidents_df: pd.DataFrame,
    ):
        """The sources column lists all contributing sources per activity."""
        sources = {
            "bsee": bsee_incidents_df,
            "osha": osha_accidents_df,
        }
        result = assembler.assemble(sources)

        # At least one activity should have data from both sources
        for _, row in result.iterrows():
            assert isinstance(row["sources"], list)
            assert len(row["sources"]) >= 1
            for s in row["sources"]:
                assert s in {"bsee", "osha"}


class TestMinimumIncidentThreshold:
    """Test confidence flagging for low-count activities."""

    def test_low_count_flagged_low_confidence(self, assembler: DataAssembler):
        """Activities with < MINIMUM_INCIDENT_THRESHOLD flagged as low confidence."""
        # Create a small dataset with very few incidents
        small_df = pd.DataFrame(
            {
                "DATE_OCCURRED": ["01/15/2020"] * 3,
                "ACCIDENT_TYPE": ["- Fire "] * 3,
                "fatalities": [0, 0, 0],
                "injuries": [0, 1, 0],
            }
        )
        result = assembler.assemble({"bsee": small_df})

        # With only 3 incidents, should be flagged as "low"
        for _, row in result.iterrows():
            if row["total_incidents"] < DataAssembler.MINIMUM_INCIDENT_THRESHOLD:
                assert row["confidence"] == "low"

    def test_high_count_not_flagged_low(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """Activities at or above threshold are not flagged as low confidence."""
        # Create enough incidents in one category
        many = pd.concat([bsee_incidents_df] * 5, ignore_index=True)
        result = assembler.assemble({"bsee": many})

        for _, row in result.iterrows():
            if row["total_incidents"] >= DataAssembler.MINIMUM_INCIDENT_THRESHOLD:
                assert row["confidence"] in ("high", "medium")

    def test_threshold_value(self):
        """The minimum incident threshold is 10."""
        assert DataAssembler.MINIMUM_INCIDENT_THRESHOLD == 10


class TestEmptySourceHandling:
    """Test graceful handling of missing or empty data sources."""

    def test_empty_sources_dict(self, assembler: DataAssembler):
        """Empty sources dict returns empty DataFrame with correct columns."""
        result = assembler.assemble({})

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        expected_cols = {
            "activity_code",
            "activity_name",
            "total_incidents",
            "fatalities",
            "injuries",
            "fatality_rate",
            "injury_rate",
            "tri_carcinogen_lbs",
            "inc_rate",
            "confidence",
            "sources",
            "weighted_incident_count",
        }
        assert expected_cols.issubset(set(result.columns))

    def test_empty_dataframe_source(self, assembler: DataAssembler):
        """A source with an empty DataFrame is silently skipped."""
        empty = pd.DataFrame(columns=["ACCIDENT_TYPE", "fatalities", "injuries"])
        result = assembler.assemble({"bsee": empty})

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_mix_of_empty_and_populated(
        self,
        assembler: DataAssembler,
        bsee_incidents_df: pd.DataFrame,
    ):
        """Empty sources alongside populated ones are handled without error."""
        empty_osha = pd.DataFrame(
            columns=[
                "event_date",
                "event_desc",
                "sic_list",
                "fatality",
                "fatalities",
                "injuries",
            ]
        )
        sources = {
            "bsee": bsee_incidents_df,
            "osha": empty_osha,
        }
        result = assembler.assemble(sources)

        assert len(result) > 0
        total = result["total_incidents"].sum()
        assert total == len(bsee_incidents_df)

    def test_none_source_raises_error(self, assembler: DataAssembler):
        """Passing None as a source value raises TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            assembler.assemble({"bsee": None})

    def test_unknown_source_key_raises_error(self, assembler: DataAssembler):
        """Unknown source keys are rejected with ValueError."""
        fake_df = pd.DataFrame({"col": [1, 2, 3]})
        with pytest.raises(ValueError, match="Unknown source"):
            assembler.assemble({"unknown_source": fake_df})


class TestClassifySource:
    """Test the internal _classify_source method."""

    def test_classify_adds_activity_columns(
        self, assembler: DataAssembler, bsee_incidents_df: pd.DataFrame
    ):
        """_classify_source adds activity/subactivity/confidence columns."""
        classified = assembler._classify_source(bsee_incidents_df, "bsee")

        assert "activity" in classified.columns
        assert "activity_name" in classified.columns
        assert "subactivity" in classified.columns
        assert "classification_confidence" in classified.columns
        assert "source" in classified.columns
        assert len(classified) == len(bsee_incidents_df)

    def test_classify_bsee_maps_fire_to_psafe(self, assembler: DataAssembler):
        """BSEE fire incidents classify to PSAFE (Process Safety)."""
        df = pd.DataFrame(
            {
                "ACCIDENT_TYPE": ["- Fire "],
                "fatalities": [0],
                "injuries": [1],
            }
        )
        classified = assembler._classify_source(df, "bsee")
        assert classified.iloc[0]["activity"] == "PSAFE"

    def test_classify_epa_tri_maps_to_env(
        self, assembler: DataAssembler, epa_tri_df: pd.DataFrame
    ):
        """All EPA TRI records classify to ENV (Environmental)."""
        classified = assembler._classify_source(epa_tri_df, "epa_tri")
        assert (classified["activity"] == "ENV").all()


class TestComputeConfidence:
    """Test confidence level computation."""

    def test_low_confidence_below_threshold(self, assembler: DataAssembler):
        """Below threshold incident count yields low confidence."""
        row = pd.Series({"total_incidents": 5, "avg_classification_confidence": 0.9})
        assert assembler._compute_confidence(row) == "low"

    def test_high_confidence_many_incidents(self, assembler: DataAssembler):
        """Many incidents with high classification confidence yields high."""
        row = pd.Series({"total_incidents": 100, "avg_classification_confidence": 0.85})
        assert assembler._compute_confidence(row) == "high"

    def test_medium_confidence_moderate_data(self, assembler: DataAssembler):
        """Moderate incident count or moderate confidence yields medium."""
        row = pd.Series({"total_incidents": 15, "avg_classification_confidence": 0.50})
        assert assembler._compute_confidence(row) == "medium"
