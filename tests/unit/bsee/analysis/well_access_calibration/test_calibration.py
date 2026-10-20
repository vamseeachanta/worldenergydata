"""Independent hand calculations; all fixture numbers are synthetic inputs.

Rate: CDC Principles of Epidemiology (2012), lesson 3, section 2,
incidence rate = events / observed time. With a deliberately selected 100-day
model year, one well observed for 200 days contributes 1 year in each of
[0, 1), [1, 2). Two overlapping WAR windows [10, 20), [15, 25)
represent one event and 15 observed resource-days, not 20 days.
"""

import copy
from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.bsee.analysis.well_access_calibration import (
    build_calibration,
    run_calibration,
)


@pytest.fixture
def inputs():
    return {
        "wells": pd.DataFrame(
            [
                {
                    "API_WELL_NUMBER": "123456789012",
                    "LEASE_NUMBER": "L1",
                    "tree_type": "SPAR",
                    "first_production": "2020-01-01",
                },
                {
                    "API_WELL_NUMBER": "123456789013",
                    "LEASE_NUMBER": "L2",
                    "tree_type": "SUBSEA",
                    "first_production": "2020-01-01",
                },
            ]
        ),
        "war": pd.DataFrame(
            [
                {
                    "SN_WAR": "1",
                    "API_WELL_NUMBER": "12345678901200",
                    "WELL_ACTIVITY_CD": "WO",
                    "INTERVENTION_TYPE": "workover",
                    "CLASSIFICATION_BASIS": "Synthetic event label",
                    "WAR_START_DT": "2020-01-11",
                    "WAR_END_DT": "2020-01-21",
                },
                {
                    "SN_WAR": "2",
                    "API_WELL_NUMBER": "12345678901200",
                    "WELL_ACTIVITY_CD": "WO",
                    "INTERVENTION_TYPE": "workover",
                    "CLASSIFICATION_BASIS": "Synthetic event label",
                    "WAR_START_DT": "2020-01-16",
                    "WAR_END_DT": "2020-01-26",
                },
            ]
        ),
        "production": pd.DataFrame(
            [
                {
                    "API_WELL_NUMBER": "12345678901200",
                    "LEASE_NUMBER": "L1",
                    "PRODUCTION_DATE": "202002",
                    "DAYS_ON_PROD": 29,
                },
                {
                    "API_WELL_NUMBER": "12345678901200",
                    "LEASE_NUMBER": "L1",
                    "PRODUCTION_DATE": "202003",
                    "DAYS_ON_PROD": 0,
                },
            ]
        ),
        "parameters": {
            "observation_start": "2020-01-01",
            "observation_end": "2020-07-19",
            "band_edges_yr": [0, 1, 2],
            "days_per_year": 100,
            "event_gap_days": 2,
            "min_events": 2,
            "min_exposure_years": 1,
            "dry_tree_codes": ["SPAR", "TLP", "MTLP"],
            "coverage_basis": "Synthetic complete observation",
            "analog_basis": "Synthetic verified well tree types",
        },
    }


def test_hand_calculation(inputs):
    result = build_calibration(**inputs)
    rate = result["base_rates"]["workover"]
    assert [b["rate_per_well_year"] for b in rate["age_curve"]] == [1, 0]
    assert rate["duration_days"] == 15
    assert rate["low_confidence"] is True
    assert result["diagnostics"]["workover"]["event_count"] == 1
    assert result["meta"]["analog_wells"] == 1
    # Day-weighted availability = (29 + 0) / (29 + 31) = 29/60.
    assert result["uptime"]["facility_availability_suggested"] == pytest.approx(29 / 60)
    assert result["uptime"]["n_well_months"] == 2
    assert result["diagnostics"]["recompletion"]["status"] == "NOT_EVALUATED"
    assert "recompletion" not in result["base_rates"]


def test_duplicate_reports_and_order_do_not_change_result(inputs):
    expected = build_calibration(**inputs)
    inputs["war"] = pd.concat([inputs["war"].iloc[::-1], inputs["war"]])
    inputs["production"] = pd.concat([inputs["production"], inputs["production"]])
    assert build_calibration(**inputs) == expected


def test_gap_boundary(inputs):
    # [10,20), [22,25): gap=2 merges, covered duration=10+3=13 days.
    inputs["war"].loc[1, "WAR_START_DT"] = "2020-01-23"
    assert build_calibration(**inputs)["base_rates"]["workover"]["duration_days"] == 13
    inputs["parameters"]["event_gap_days"] = 1
    r = build_calibration(**inputs)
    assert r["diagnostics"]["workover"]["event_count"] == 2
    assert r["base_rates"]["workover"]["duration_days"] == 6.5


def test_observation_clipping_and_age_boundary(inputs):
    # Observation starts at age 1: only 100 days / 100 = 1 year exposed.
    inputs["parameters"]["observation_start"] = "2020-04-10"
    inputs["war"]["WAR_START_DT"] = ["2020-04-10", "2020-04-11"]
    inputs["war"]["WAR_END_DT"] = ["2020-04-12", "2020-04-13"]
    r = build_calibration(**inputs)
    assert r["diagnostics"]["exposure_years"] == [0, 1]
    assert r["base_rates"]["workover"]["age_curve"] == [
        {"age_min_yr": 1.0, "age_max_yr": 2.0, "rate_per_well_year": 1.0}
    ]


def test_subsea_excluded_even_with_war_events(inputs):
    wet = inputs["war"].copy()
    wet["API_WELL_NUMBER"] = "12345678901300"
    inputs["war"] = pd.concat([inputs["war"], wet])
    assert build_calibration(**inputs)["diagnostics"]["workover"]["event_count"] == 1


@pytest.mark.parametrize("code", ["REC", "ST"])
def test_normalized_recompletion_types(inputs, code):
    inputs["war"]["WELL_ACTIVITY_CD"] = code
    inputs["war"]["INTERVENTION_TYPE"] = "recompletion"
    r = build_calibration(**inputs)
    assert r["diagnostics"]["recompletion"]["event_count"] == 1
    assert r["base_rates"]["recompletion"]["resource_class"] == "modu"


def test_suffix_transition_only_when_prior_suffix_observed(inputs):
    inputs["war"]["WELL_ACTIVITY_CD"] = "COM"
    inputs["war"]["INTERVENTION_TYPE"] = ""
    inputs["war"].loc[1, "API_WELL_NUMBER"] = "12345678901201"
    r = build_calibration(**inputs)
    assert r["diagnostics"]["recompletion"]["event_count"] == 1
    inputs["war"] = inputs["war"].iloc[1:]
    assert (
        build_calibration(**inputs)["diagnostics"]["recompletion"]["event_count"] == 0
    )


def test_light_mapping(inputs):
    inputs["war"]["WELL_ACTIVITY_CD"] = "OTHER"
    inputs["war"]["INTERVENTION_TYPE"] = ""
    inputs["war"]["RIG_NAME"] = "WIRELINE UNIT"
    r = build_calibration(**inputs)
    assert r["base_rates"]["light_well_intervention"]["resource_class"] == "lwi_vessel"
    assert r["base_rates"]["light_well_intervention"]["low_confidence"] is True


@pytest.mark.parametrize(
    "key,value",
    [
        ("days_per_year", 0),
        ("event_gap_days", -1),
        ("band_edges_yr", [0, 2, 1]),
        ("min_events", 0),
        ("min_exposure_years", 0),
        ("dry_tree_codes", ["SUBSEA"]),
        ("observation_end", "2019-01-01"),
        ("coverage_basis", ""),
    ],
)
def test_invalid_parameters(inputs, key, value):
    inputs["parameters"][key] = value
    with pytest.raises(ValueError):
        build_calibration(**inputs)


@pytest.mark.parametrize("days", [-1, 30, float("nan")])
def test_invalid_production_days(inputs, days):
    inputs["production"].loc[0, "DAYS_ON_PROD"] = days
    with pytest.raises(ValueError):
        build_calibration(**inputs)


def test_conflicting_months_rejected(inputs):
    other = inputs["production"].iloc[[0]].copy()
    other["DAYS_ON_PROD"] = 10
    inputs["production"] = pd.concat([inputs["production"], other])
    with pytest.raises(ValueError, match="Conflicting"):
        build_calibration(**inputs)


def test_censored_event_not_a_complete_duration(inputs):
    inputs["parameters"]["observation_end"] = "2020-01-24"
    r = build_calibration(**inputs)
    assert r["diagnostics"]["workover"]["event_count"] == 1
    assert r["diagnostics"]["workover"]["status"] == "NOT_EVALUATED"
    assert "workover" not in r["base_rates"]


def test_empty_data_not_zero_calibration(inputs):
    inputs["war"] = inputs["war"].iloc[:0]
    inputs["production"] = inputs["production"].iloc[:0]
    r = build_calibration(**inputs)
    assert r["base_rates"] == {}
    assert r["uptime"]["status"] == "NOT_EVALUATED"
    assert r["uptime"]["facility_availability_suggested"] is None


def test_consumer_contract(inputs):
    """digitalmodel build_intervention_types at revision 84aa1f6 (2026).

    Mirror its float/str/bool conversions without importing the other package.
    """
    for spec in build_calibration(**inputs)["base_rates"].values():
        assert float(spec["duration_days"]) >= 0
        assert spec["resource_class"] in ("modu", "lwi_vessel")
        assert isinstance(spec["low_confidence"], bool)
        for band in spec["age_curve"]:
            assert float(band["age_min_yr"]) < float(band["age_max_yr"])
            assert float(band["rate_per_well_year"]) >= 0


def test_workflow_determinism_and_offline_report(inputs, tmp_path):
    cfg = copy.deepcopy(inputs["parameters"])
    for key in ("wells", "war", "production"):
        path = tmp_path / f"{key}.csv"
        inputs[key].to_csv(path, index=False)
        cfg[f"{key}_csv"] = str(path)
    cfg["outputs"] = {
        "calibration_yml": str(tmp_path / "calibration.yml"),
        "report_html": str(tmp_path / "report.html"),
    }
    r = run_calibration(cfg)
    before = Path(cfg["outputs"]["calibration_yml"]).read_bytes()
    run_calibration(cfg)
    assert before == Path(cfg["outputs"]["calibration_yml"]).read_bytes()
    assert yaml.safe_load(before) == r
    html = Path(cfg["outputs"]["report_html"]).read_text()
    assert "NOT_EVALUATED" in html
    assert "src=" not in html and "href=" not in html
    assert "Revision history" in html
    assert "48.3%" in html


def test_router_bypasses_generic_group_loading(monkeypatch):
    from worldenergydata.bsee.analysis import well_access_calibration
    from worldenergydata.bsee.bsee import bsee

    calls = []
    monkeypatch.setattr(
        well_access_calibration,
        "run_calibration",
        lambda cfg: calls.append(cfg) or {"base_rates": {}},
    )
    cfg = {
        "basename": "bsee",
        "analysis": {"flag": True, "type": "well_access_calibration"},
        "well_access_calibration": {"sentinel": True},
    }
    assert bsee().router(cfg)["bsee"]["well_access_calibration"] == {"base_rates": {}}
    assert calls == [{"sentinel": True}]


def test_observed_well_lifetime_limits_exposure(inputs):
    # Last observation at age 0.5: 50 / 100 = 0.5 well-years.
    inputs["wells"]["last_observed"] = "2020-02-20"
    r = build_calibration(**inputs)
    assert r["diagnostics"]["exposure_years"] == [0.5, 0]
    assert r["base_rates"]["workover"]["age_curve"][0]["rate_per_well_year"] == 2


def test_partial_production_month_omitted(inputs):
    inputs["parameters"]["observation_start"] = "2020-02-15"
    r = build_calibration(**inputs)
    assert r["uptime"]["n_well_months"] == 1
    assert r["uptime"]["partial_months_omitted"] == 1
    assert r["uptime"]["facility_availability_suggested"] == 0


def test_missing_production_months_remain_unknown(inputs):
    # Complete months January through June: six eligible, two observed.
    r = build_calibration(**inputs)
    assert r["uptime"]["expected_well_months"] == 6
    assert r["uptime"]["missing_well_months"] == 4
    assert r["uptime"]["coverage_complete"] is False


def test_html_escapes_evidence(inputs):
    from worldenergydata.bsee.analysis.well_access_calibration.report import render_html

    inputs["parameters"]["coverage_basis"] = "<script>unsafe</script>"
    html = render_html(build_calibration(**inputs))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_real_export_smoke(tmp_path):
    """Enable with WED_DATA_ROOT holding reviewed well_access_calibration CSVs.

    The manifest must contain verified dry-tree identities, full first-production
    dates and coverage_basis in parameters.yml. Raw binary presence alone cannot
    establish the required joins or coverage; no automatic unverified cohort.
    """
    from worldenergydata.common.data_resolver import get_module_data_safe

    data = get_module_data_safe("bsee")
    if data is None:
        pytest.skip("BSEE data root unavailable")
    root = data / "well_access_calibration"
    parameters = root / "parameters.yml"
    if not parameters.is_file():
        pytest.skip("Reviewed BSEE calibration exports are not available")
    config = yaml.safe_load(parameters.read_text())
    for key in ("wells", "war", "production"):
        config[f"{key}_csv"] = str(root / f"{key}.csv")
    config["outputs"] = {"calibration_yml": str(tmp_path / "calibration.yml")}
    result = run_calibration(config)
    assert result["meta"]["analog_wells"] > 0
    assert result["base_rates"]


def test_saved_example_through_engine(tmp_path):
    """Exercise the actual saved input through the engine dispatch.

    Same independent synthetic arithmetic as test_hand_calculation. Embedded
    execution directs application-manager results into the temporary folder.
    """
    from worldenergydata.engine import engine

    cfg = yaml.safe_load(Path("config/input/well_access_calibration.yml").read_text())
    cfg["well_access_calibration"]["outputs"] = {
        "calibration_yml": str(tmp_path / "calibration.yml"),
        "report_html": str(tmp_path / "report.html"),
    }
    result = engine(cfg=cfg, embed=True, root_folder=str(tmp_path), log_to_file=False)[
        "bsee"
    ]["well_access_calibration"]
    assert result["base_rates"]["workover"]["duration_days"] == 15
    assert result["uptime"]["facility_availability_suggested"] == pytest.approx(29 / 60)
    assert (tmp_path / "report.html").is_file()


def test_workflow_join_properties_and_input_digest(inputs, tmp_path):
    import hashlib

    cfg = copy.deepcopy(inputs["parameters"])
    for key in ("wells", "war", "production"):
        frame = inputs[key]
        if key == "war":
            props = frame[["SN_WAR", "WELL_ACTIVITY_CD"]]
            path = tmp_path / "properties.csv"
            props.to_csv(path, index=False)
            cfg["war_properties_csv"] = str(path)
            frame = frame.drop(columns=["WELL_ACTIVITY_CD"])
        path = tmp_path / f"{key}.csv"
        frame.to_csv(path, index=False)
        cfg[f"{key}_csv"] = str(path)
    result = run_calibration(cfg)
    assert result["diagnostics"]["workover"]["event_count"] == 1
    assert (
        result["meta"]["input_sha256"]["war"]
        == hashlib.sha256(Path(cfg["war_csv"]).read_bytes()).hexdigest()
    )
    # Conflicting properties cannot multiply event rows silently.
    props.loc[1, "SN_WAR"] = props.loc[0, "SN_WAR"]
    props.loc[1, "WELL_ACTIVITY_CD"] = "ST"
    props.to_csv(cfg["war_properties_csv"], index=False)
    with pytest.raises(pd.errors.MergeError):
        run_calibration(cfg)


def test_outputs_cannot_overwrite_inputs(inputs, tmp_path):
    cfg = copy.deepcopy(inputs["parameters"])
    for key in ("wells", "war", "production"):
        path = tmp_path / f"{key}.csv"
        inputs[key].to_csv(path, index=False)
        cfg[f"{key}_csv"] = str(path)
    original = Path(cfg["wells_csv"]).read_bytes()
    cfg["outputs"] = {"calibration_yml": cfg["wells_csv"]}
    with pytest.raises(ValueError, match="overwrite"):
        run_calibration(cfg)
    assert Path(cfg["wells_csv"]).read_bytes() == original


@pytest.mark.parametrize("code", ["WO", "REC", "ST"])
def test_raw_activity_codes_are_not_definitions(inputs, code):
    """Canonical war_activity_codes.yml (2026) forbids guessing meanings."""
    inputs["war"]["WELL_ACTIVITY_CD"] = code
    inputs["war"] = inputs["war"].drop(
        columns=["INTERVENTION_TYPE", "CLASSIFICATION_BASIS"]
    )
    assert build_calibration(**inputs)["base_rates"] == {}


def test_classification_evidence_required(inputs):
    inputs["war"]["CLASSIFICATION_BASIS"] = ""
    with pytest.raises(ValueError, match="classification evidence"):
        build_calibration(**inputs)


def test_no_qualified_analogs_is_not_a_calibration(inputs):
    inputs["wells"]["tree_type"] = "SUBSEA"
    r = build_calibration(**inputs)
    assert r["base_rates"] == {}
    assert r["meta"]["analog_wells"] == 0
    assert r["uptime"]["status"] == "NOT_EVALUATED"


def test_zero_exposure_in_all_age_bands(inputs):
    inputs["parameters"]["band_edges_yr"] = [0, 1]
    inputs["parameters"]["observation_start"] = "2020-04-10"
    r = build_calibration(**inputs)
    assert r["diagnostics"]["exposure_years"] == [0]
    assert r["base_rates"] == {}


def test_left_censored_events_excluded(inputs):
    # Event starts at day 10, before observation day 15; no new start observed.
    inputs["parameters"]["observation_start"] = "2020-01-16"
    assert build_calibration(**inputs)["diagnostics"]["workover"]["event_count"] == 0


def test_unlabelled_reports_force_low_confidence(inputs):
    inputs["parameters"]["min_events"] = 1
    assert (
        build_calibration(**inputs)["base_rates"]["workover"]["low_confidence"] is False
    )
    unknown = inputs["war"].iloc[[0]].copy()
    unknown["SN_WAR"] = "3"
    unknown["INTERVENTION_TYPE"] = ""
    unknown["CLASSIFICATION_BASIS"] = ""
    inputs["war"] = pd.concat([inputs["war"], unknown])
    r = build_calibration(**inputs)
    assert r["meta"]["unlabelled_reports"] == 1
    assert r["base_rates"]["workover"]["low_confidence"] is True
