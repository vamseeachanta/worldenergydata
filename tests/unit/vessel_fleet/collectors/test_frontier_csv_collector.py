"""Tests for the Frontier heavy-lift / pipelay CSV collector.

Uses inline CSV fixtures written to a tmp dir -- no off-repo dependency, so
these run in CI without the client share mounted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.collectors import frontier_csv_collector as fc

_HEAVY_LIFT_HEADER = (
    "contractor,vessel_name,vessel_type,operating_region,loa_ft,beam_ft,"
    "draft_ft,deck_capacity_t,classification,crane_model,"
    "primary_lift_capacity_t,primary_lift_radius_ft,secondary_lift_capacity_t,"
    "secondary_lift_radius_ft,max_hook_height_ft,mooring_system,dp_class,"
    "notes,needs_review,imo_number,current_owner,current_status,status_year,"
    "renamed_to,source_url,archival_year"
)

_PIPELAY_HEADER = (
    "contractor,vessel_name,vessel_type,operating_region,loa_ft,beam_ft,"
    "draft_load_ft,draft_light_ft,accommodation_persons,mooring_system,"
    "dp_class,lay_method,min_pipe_dia_in,max_pipe_dia_in,max_water_depth_ft,"
    "burial_capable,notes,needs_review,imo_number,current_owner,"
    "current_status,status_year,renamed_to,source_url,archival_year"
)


def _write(tmp_path: Path, name: str, header: str, rows: list[str]) -> None:
    (tmp_path / name).write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


class TestFtToM:
    def test_basic_conversion(self):
        # 100 ft = 30.48 m
        assert fc._ft_to_m("100") == 30.5

    def test_none(self):
        assert fc._ft_to_m(None) is None

    def test_empty(self):
        assert fc._ft_to_m("") is None


class TestHeavyLiftMapping:
    def test_maps_core_fields(self):
        row = {
            "vessel_name": "HAPPY BUCCANEER",
            "vessel_type": "Heavylift",
            "contractor": "BIGLIFT SHIPPING",
            "current_owner": "BigLift Shipping",
            "imo_number": "8300389",
            "classification": "DNV",
            "current_status": "scrapped",
            "source_url": "https://example.com/happy",
            "loa_ft": "479",
            "beam_ft": "93",
            "draft_ft": "20",
            "dp_class": "DP2",
            "primary_lift_capacity_t": "675.0",
            "primary_lift_radius_ft": "100",
            "secondary_lift_capacity_t": "2755.0",
            "deck_capacity_t": "5000",
        }
        out = fc._map_heavy_lift_row(row)
        assert out["VESSEL_NAME"] == "HAPPY BUCCANEER"
        assert out["VESSEL_CATEGORY"] == "construction"
        assert out["VESSEL_TYPE"] == "heavy_lift"
        assert out["IMO_NUMBER"] == "8300389"
        assert out["OWNER"] == "BigLift Shipping"
        assert out["DATA_SOURCE"] == fc.DATA_SOURCE_HEAVY_LIFT
        # ft -> m
        assert out["LOA_M"] == round(479 * 0.3048, 1)
        assert out["BEAM_M"] == round(93 * 0.3048, 1)
        # DP parse
        assert out["DP_CLASS"] == 2
        assert out["MAIN_CRANE_CAPACITY_T"] == 675.0
        assert out["AUX_CRANE_CAPACITY_T"] == 2755.0

    def test_blank_name_dropped(self):
        assert fc._map_heavy_lift_row({"vessel_name": "  "}) is None

    def test_missing_imo_is_none(self):
        out = fc._map_heavy_lift_row({"vessel_name": "X", "imo_number": ""})
        assert out["IMO_NUMBER"] is None


class TestPipelayMapping:
    def test_maps_core_fields(self):
        row = {
            "vessel_name": "SOLITAIRE",
            "vessel_type": "DP pipelay vessel",
            "contractor": "ALLSEAS GROUP, S.A.",
            "current_owner": "Allseas Group",
            "imo_number": "7129049",
            "current_status": "active",
            "source_url": "https://example.com/sol",
            "loa_ft": "984.0",
            "beam_ft": "131.0",
            "draft_load_ft": "79.0",
            "draft_light_ft": "28.0",
            "accommodation_persons": "420",
            "dp_class": "DP3",
            "lay_method": "S-lay",
            "max_pipe_dia_in": "60.0",
            "max_water_depth_ft": "10000.0",
        }
        out = fc._map_pipelay_row(row)
        assert out["VESSEL_TYPE"] == "pipelay_vessel"
        assert out["DP_CLASS"] == 3
        assert out["PIPELAY_METHOD"] == "S-lay"
        assert out["PIPELAY_CAPACITY_IN"] == 60.0
        assert out["QUARTERS_CAPACITY"] == 420
        assert out["DATA_SOURCE"] == fc.DATA_SOURCE_PIPELAY
        # prefers loaded draft
        assert out["DRAFT_M"] == round(79.0 * 0.3048, 1)

    def test_draft_falls_back_to_light(self):
        out = fc._map_pipelay_row(
            {"vessel_name": "X", "draft_load_ft": "", "draft_light_ft": "20"}
        )
        assert out["DRAFT_M"] == round(20 * 0.3048, 1)


class TestCollectFrontierVessels:
    def test_env_unset_returns_empty(self, monkeypatch):
        monkeypatch.delenv(fc.FRONTIER_ENV_VAR, raising=False)
        assert fc.collect_frontier_vessels() == []

    def test_missing_dir_returns_empty(self, tmp_path):
        assert fc.collect_frontier_vessels(tmp_path / "nope") == []

    def test_reads_both_files(self, tmp_path):
        _write(
            tmp_path,
            "heavy-lift-vessels-current.csv",
            _HEAVY_LIFT_HEADER,
            [
                "BIGLIFT,HAPPY BUCCANEER,Heavylift,WW,479,93,,,,,675.0,,2755.0,,300.0,8 Point,,,False,8300389,BigLift,scrapped,2024,,https://x,2010"
            ],
        )
        _write(
            tmp_path,
            "pipelay-contractors-current.csv",
            _PIPELAY_HEADER,
            [
                "ALLSEAS,SOLITAIRE,DP pipelay,,984.0,131.0,79.0,28.0,420,,DP3,S-lay,,60.0,10000.0,True,,False,7129049,Allseas,active,2024,,https://y,2011"
            ],
        )
        out = fc.collect_frontier_vessels(tmp_path)
        names = {r["VESSEL_NAME"] for r in out}
        assert names == {"HAPPY BUCCANEER", "SOLITAIRE"}

    def test_uses_env_var(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "heavy-lift-vessels-current.csv",
            _HEAVY_LIFT_HEADER,
            [
                "C,VESSEL X,Heavylift,WW,100,30,,,,,500.0,,,,,,DP2,,False,1234567,Owner,active,2024,,https://z,2010"
            ],
        )
        monkeypatch.setenv(fc.FRONTIER_ENV_VAR, str(tmp_path))
        out = fc.collect_frontier_vessels()
        assert len(out) == 1
        assert out[0]["VESSEL_NAME"] == "VESSEL X"
