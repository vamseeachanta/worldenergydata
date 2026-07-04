"""Tests for production Colorado ECMC FacilityDetail/Form 5A ingest (#751)."""

from urllib.error import HTTPError

import pandas as pd
import pytest

from worldenergydata.modules.state_regulators.colorado_ecmc import (
    facility_detail_ingest,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_ingest import (
    build_facility_detail_source_list,
)


def test_build_source_list_derives_facility_detail_keys_from_raw_wells():
    wells = pd.DataFrame(
        [
            {
                "API": "12332498",
                "API_County": "123",
                "API_Seq": "32498",
                "API_Label": "05-123-32498",
                "Facil_Id": 420193,
                "Field_Name": "WATTENBERG",
                "Max_MD": 14829,
                "Max_TVD": 7041,
                "Latitude": 40.1,
                "Longitude": -104.8,
            }
        ]
    )

    source_list, quality = build_facility_detail_source_list(
        wells, {"allow_full_source_list": True, "max_requests": 1}
    )

    row = source_list.iloc[0]
    assert row["api_fragment"] == "12332498"
    assert row["api10"] == "0512332498"
    assert pd.isna(row["api12"])
    assert row["facility_id"] == "420193"
    assert row["field"] == "WATTENBERG"
    assert row["max_md_ft"] == 14829
    assert row["max_tvd_ft"] == 7041
    assert quality["source_rows"] == 1
    assert quality["request_rows"] == 1


def test_build_source_list_fails_closed_without_full_list_approval():
    wells = pd.DataFrame(
        [
            {
                "API": "12332498",
                "API_County": "123",
                "API_Seq": "32498",
                "API_Label": "05-123-32498",
                "Facil_Id": 420193,
                "Field_Name": "WATTENBERG",
                "Max_MD": 14829,
                "Max_TVD": 7041,
            },
            {
                "API": "12324638",
                "API_County": "123",
                "API_Seq": "24638",
                "API_Label": "05-123-24638",
                "Facil_Id": 288652,
                "Field_Name": "WATTENBERG",
                "Max_MD": 10201,
                "Max_TVD": 7300,
            },
        ]
    )

    capped, quality = build_facility_detail_source_list(wells, {"max_requests": 1})
    assert list(capped["api_fragment"]) == ["12332498"]
    assert quality["request_rows"] == 1
    assert quality["allow_full_source_list"] is False

    with pytest.raises(ValueError, match="allow_full_source_list"):
        build_facility_detail_source_list(wells, {"max_requests": 2})


def test_fetch_facility_detail_pages_uses_user_agent_and_writes_status(
    tmp_path, monkeypatch
):
    source_list = pd.DataFrame([{"api_fragment": "12332498", "facility_id": "420193"}])
    payload = b"<html>API# 05-123-32498 FacilityID: 420193 Initial Test Data</html>"
    seen = {}

    class FakeResponse:
        headers = {"ETag": "abc"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            return payload if size != 0 else b""

        def getcode(self):
            return 200

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["user_agent"] = request.headers["User-agent"]
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(facility_detail_ingest, "urlopen", fake_urlopen)
    monkeypatch.setattr(facility_detail_ingest, "sleep", lambda _: None)

    result = facility_detail_ingest.fetch_facility_detail_pages(
        source_list,
        {
            "storage": {"base_dir": str(tmp_path)},
            "facility_detail": {
                "base_url": "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx",
                "timeout_seconds": 30,
                "request_delay_seconds": 0,
                "user_agent": "worldenergydata-test/1.0",
                "max_retries": 0,
            },
        },
    )

    raw_path = tmp_path / "raw" / "facility_detail" / "html" / "12332498.html"
    fetched_path = tmp_path / "raw" / "facility_detail" / "status" / "fetched.jsonl"
    assert seen == {
        "url": "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12332498",
        "user_agent": "worldenergydata-test/1.0",
        "timeout": 30,
    }
    assert raw_path.read_bytes() == payload
    assert fetched_path.read_text(encoding="utf-8").count("\n") == 1
    assert result["fetched"][0]["api_fragment"] == "12332498"
    assert result["fetched"][0]["status_code"] == 200
    assert result["fetched"][0]["raw_path"] == str(raw_path)


def test_fetch_facility_detail_pages_treats_403_as_terminal_failure(
    tmp_path, monkeypatch
):
    source_list = pd.DataFrame([{"api_fragment": "12332498", "facility_id": "420193"}])
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        raise HTTPError(request.full_url, 403, "Forbidden", hdrs={}, fp=None)

    monkeypatch.setattr(facility_detail_ingest, "urlopen", fake_urlopen)

    result = facility_detail_ingest.fetch_facility_detail_pages(
        source_list,
        {
            "storage": {"base_dir": str(tmp_path)},
            "facility_detail": {
                "base_url": "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx",
                "timeout_seconds": 30,
                "request_delay_seconds": 0,
                "user_agent": "worldenergydata-test/1.0",
                "max_retries": 3,
            },
        },
    )

    failed_path = tmp_path / "raw" / "facility_detail" / "status" / "failed.jsonl"
    assert calls["count"] == 1
    assert result["failed"][0]["status_code"] == 403
    assert result["failed"][0]["error_class"] == "HTTPError"
    assert result["failed"][0]["retryable"] is False
    assert failed_path.read_text(encoding="utf-8").count("\n") == 1


def test_fetch_facility_detail_pages_excludes_identity_mismatch(tmp_path, monkeypatch):
    source_list = pd.DataFrame([{"api_fragment": "12332498", "facility_id": "420193"}])
    payload = b"<html>API# 05-123-00001 FacilityID: 999999 Initial Test Data</html>"

    class FakeResponse:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            return payload

        def getcode(self):
            return 200

    monkeypatch.setattr(
        facility_detail_ingest,
        "urlopen",
        lambda request, timeout: FakeResponse(),
    )

    result = facility_detail_ingest.fetch_facility_detail_pages(
        source_list,
        {
            "storage": {"base_dir": str(tmp_path)},
            "facility_detail": {
                "base_url": "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx",
                "timeout_seconds": 30,
                "request_delay_seconds": 0,
                "user_agent": "worldenergydata-test/1.0",
                "max_retries": 0,
                "stop_on_identity_mismatch": True,
            },
        },
    )

    assert result["fetched"] == []
    assert result["failed"][0]["status"] == "identity_mismatch"
    assert result["failed"][0]["retryable"] is False


def test_build_form5a_pressure_candidates_converts_initial_test_pressures():
    classified = pd.DataFrame(
        [
            {
                "api10": "0512332498",
                "facility_id": "420193",
                "field": "WATTENBERG",
                "test_date": pd.Timestamp("2017-05-19"),
                "test_type": "CASING_PRESS",
                "measure_value": 1700,
                "source_section": "initial_test_data",
                "pressure_role": "candidate_pressure_observation",
                "interval_bottom_ft": 14700,
                "vertical_td_ft": 7041,
                "max_tvd_ft": 7041,
                "max_md_ft": 14829,
                "source_url": "https://ecmc.example/facility?api=12332498",
                "raw_path": "/mnt/ace/raw/12332498.html",
                "sha256": "abc123",
            },
            {
                "api10": "0512332498",
                "facility_id": "420193",
                "field": "WATTENBERG",
                "test_date": pd.Timestamp("2017-05-19"),
                "test_type": "TUBING_PRESS",
                "measure_value": 1300,
                "source_section": "initial_test_data",
                "pressure_role": "candidate_pressure_observation",
                "interval_bottom_ft": 14700,
                "vertical_td_ft": 7041,
                "max_tvd_ft": 7041,
                "max_md_ft": 14829,
                "source_url": "https://ecmc.example/facility?api=12332498",
                "raw_path": "/mnt/ace/raw/12332498.html",
                "sha256": "abc123",
            },
        ]
    )

    candidates, quality = facility_detail_ingest.build_form5a_pressure_candidates(
        classified, {"pressure_observations": {"atmospheric_psi": 14.7}}
    )
    by_type = candidates.set_index("test_type")

    casing = by_type.loc["CASING_PRESS"]
    tubing = by_type.loc["TUBING_PRESS"]
    assert casing["well_key"] == "CO_ECMC_FACILITY:420193"
    assert casing["state"] == "CO"
    assert casing["pressure_kind"] == "initial_test_casing_pressure_unverified"
    assert casing["pressure_psig"] == 1700
    assert casing["pressure_psia"] == pytest.approx(1714.7)
    assert casing["reference_depth_ft"] == 14700
    assert casing["reference_depth_source"] == "interval_bottom_ft"
    assert casing["era"] == "completion_initial_test"
    assert casing["source_name"] == "colorado_ecmc_form5a_facility_detail"
    assert casing["screen_promotable"] is False
    assert tubing["pressure_kind"] == "flowing_tubing_initial_test"
    assert tubing["screen_promotable"] is False
    assert quality["candidate_pressure_rows"] == 2
    assert quality["screen_promotable_rows"] == 0


def test_build_form5a_pressure_candidates_excludes_missing_field_or_depth():
    classified = pd.DataFrame(
        [
            {
                "api10": "0512332498",
                "facility_id": "420193",
                "field": None,
                "test_date": pd.Timestamp("2017-05-19"),
                "test_type": "CASING_PRESS",
                "measure_value": 1700,
                "source_section": "initial_test_data",
                "pressure_role": "candidate_pressure_observation",
                "interval_bottom_ft": 14700,
            },
            {
                "api10": "0512332499",
                "facility_id": "420194",
                "field": "WATTENBERG",
                "test_date": pd.Timestamp("2017-05-20"),
                "test_type": "TUBING_PRESS",
                "measure_value": 1300,
                "source_section": "initial_test_data",
                "pressure_role": "candidate_pressure_observation",
                "interval_bottom_ft": 0,
                "vertical_td_ft": None,
                "max_tvd_ft": None,
                "max_md_ft": None,
            },
        ]
    )

    candidates, quality = facility_detail_ingest.build_form5a_pressure_candidates(
        classified, {"pressure_observations": {"atmospheric_psi": 14.7}}
    )

    assert candidates.empty
    assert quality["candidate_pressure_rows"] == 2
    assert quality["excluded_missing_field"] == 1
    assert quality["excluded_missing_depth"] == 1
    assert quality["usable_candidate_rows"] == 0


def test_evaluate_screen_promotion_keeps_form5a_candidate_only():
    candidates = pd.DataFrame(
        [
            {
                "well_key": "CO_ECMC_FACILITY:420193",
                "pressure_kind": "flowing_tubing_initial_test",
                "screen_promotable": False,
            }
        ]
    )

    promotion = facility_detail_ingest.evaluate_screen_promotion(
        candidates, {"screen_promotable_rows": 0}, {}
    )

    assert promotion["status"] == "candidate_only"
    assert promotion["screen_promotable_rows"] == 0
