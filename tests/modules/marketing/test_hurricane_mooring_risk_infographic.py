"""Contract tests for the hurricane mooring risk-avoidance infographic."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.marketing.generate_hurricane_mooring_risk_infographic import (
    CAVEAT,
    build_stats,
    generate_artifacts,
    preserve_prior_draft,
    render_html,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = REPO_ROOT / "data" / "modules" / "marine_safety" / "input"
REPORT_DIR = REPO_ROOT / "reports" / "modules" / "marketing"
DOCX_NAME = "Hurricane Planning and Mooring R0-4revisions.docx"


def test_stats_recomputed_from_source_csvs():
    stats = build_stats(INPUT_DIR, DOCX_NAME)

    assert stats["dataset_total_records"] == 65
    assert stats["dataset_total_fatalities"] == 60
    assert stats["source_row_counts"] == {
        "fatality_incidents.csv": 20,
        "foundering_incidents.csv": 15,
        "hatch_incidents.csv": 30,
    }
    assert stats["source_fatality_sums"] == {
        "fatality_incidents.csv": 22,
        "foundering_incidents.csv": 38,
    }


def test_metric_contract_separates_pathways():
    stats = build_stats(INPUT_DIR, DOCX_NAME)

    assert stats["foundering_pathway_records"] == 15
    assert stats["foundering_pathway_fatalities"] == 38
    assert len(stats["matched_incident_ids"]["foundering_pathway"]) == 15
    assert stats["hatch_watertight_event_records"] == 20
    assert len(stats["matched_incident_ids"]["hatch_watertight_events"]) == 20
    assert stats["explicit_weather_wave_water_ingress_pathway_events"] == 21
    assert stats["explicit_weather_wave_water_ingress_pathway_fatalities"] == 30
    assert stats["explicit_weather_wave_water_ingress_pathway_pct_of_event_records"] == 38.2
    assert (
        stats["denominators"][
            "explicit_weather_wave_water_ingress_pathway_pct_of_event_records"
        ]
        == "21 explicit weather/wave/water-ingress pathway events / 55 incident/event rows excluding hatch controls"
    )
    assert len(
        stats["matched_incident_ids"]["explicit_weather_wave_water_ingress_pathway_events"]
    ) == 21
    assert not set(stats["matched_incident_ids"]["foundering_pathway"]) & set(
        stats["matched_incident_ids"]["hatch_watertight_events"]
    )


def test_legacy_direct_exposure_contract_removed():
    stats = build_stats(INPUT_DIR, DOCX_NAME)
    html = render_html(stats)
    serialized_stats = json.dumps(stats)

    legacy_tokens = [
        "direct_weather_or_water_exposure",
        "Direct weather/water exposure",
    ]
    for token in legacy_tokens:
        assert token not in serialized_stats
        assert token not in html


def test_committed_infographic_artifacts_remove_legacy_direct_exposure_claims():
    html_path = REPORT_DIR / "hurricane_mooring_risk_avoidance_infographic.html"
    stats_path = REPORT_DIR / "hurricane_mooring_risk_avoidance_infographic_stats.json"
    html = html_path.read_text(encoding="utf-8")
    stats_text = stats_path.read_text(encoding="utf-8")

    assert "Explicit storm/wave/water-ingress pathway events" in html
    assert "21 / 55 event rows" in html
    assert "explicit_weather_wave_water_ingress_pathway_events" in stats_text
    legacy_tokens = [
        "direct_weather_or_water_exposure",
        "Direct weather/water exposure",
        "26 / 55 event rows",
    ]
    for token in legacy_tokens:
        assert token not in html
        assert token not in stats_text


def test_weather_water_false_positive_controls_excluded():
    stats = build_stats(INPUT_DIR, DOCX_NAME)

    matched_ids = set(
        stats["matched_incident_ids"][
            "explicit_weather_wave_water_ingress_pathway_events"
        ]
    )
    generic_outcome_false_positives = {
        "FA013",  # overboard/drowning without storm or water-ingress pathway
        "FA016",  # mooring-operation overboard outcome, not weather exposure
        "F009",  # fire/power-loss vessel sinking outcome
        "F010",  # reef collision/foundered outcome
        "F015",  # grounding/tow sinking outcome
        "H016",  # Weather deck hatch seal text; not weather-driven incident
    }

    assert stats["hatch_control_records"] == 10
    assert "NI002" in stats["excluded_incident_ids"]["hatch_controls"]
    assert "NI010" in stats["excluded_incident_ids"]["hatch_controls"]
    assert "NI010" in stats["excluded_incident_ids"]["preventive_or_control_rows"]
    assert not generic_outcome_false_positives & matched_ids


def test_hatch_severity_counts_are_exact():
    stats = build_stats(INPUT_DIR, DOCX_NAME)

    assert stats["hatch_severity_counts"] == {
        "Critical": 6,
        "High": 6,
        "Medium": 7,
        "Low": 1,
        "None": 10,
    }
    assert stats["critical_high_hatch_events"] == 12
    assert stats["critical_high_hatch_event_pct"] == 60.0
    assert stats["critical_high_hatch_all_hatch_pct"] == 40.0
    assert (
        stats["denominators"]["critical_high_hatch_event_pct"]
        == "12 critical/high hatch events / 20 hatch event rows excluding severity=None controls"
    )
    assert (
        stats["denominators"]["critical_high_hatch_all_hatch_pct"]
        == "12 critical/high hatch events / 30 all hatch CSV records including controls"
    )


def test_stats_json_has_traceability_and_timestamp(tmp_path: Path):
    result = generate_artifacts(
        output_dir=tmp_path, input_dir=INPUT_DIR, docx_name=DOCX_NAME
    )
    stats = json.loads(result["stats_path"].read_text(encoding="utf-8"))

    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stats["generated_utc"])
    assert stats["source_files"] == [
        "data/modules/marine_safety/input/fatality_incidents.csv",
        "data/modules/marine_safety/input/foundering_incidents.csv",
        "data/modules/marine_safety/input/hatch_incidents.csv",
    ]
    assert (
        stats["document_provenance"]["filename"]
        == "Hurricane Planning and Mooring R0-4revisions.docx"
    )
    assert stats["caveat"] == CAVEAT
    assert stats["matched_incident_ids"]["explicit_weather_wave_water_ingress_pathway_events"]
    assert stats["excluded_incident_ids"]["hatch_controls"]


def test_rendered_html_contains_required_positioning():
    html = render_html(build_stats(INPUT_DIR, DOCX_NAME))

    assert (
        "Hurricane mooring analysis turns marine incident pathways into avoidable planning decisions"
        in html
    )
    assert "Port / refuge decision tree" in html
    assert "Bollard, fender, and mooring-line capacity checks" in html
    assert "storm-category survivability" in html
    assert CAVEAT in html
    assert "hurricane-only" in html


def test_rendered_html_is_interactive_and_provenanced(tmp_path: Path):
    result = generate_artifacts(
        output_dir=tmp_path, input_dir=INPUT_DIR, docx_name=DOCX_NAME
    )
    html = result["html_path"].read_text(encoding="utf-8")

    assert "<details" in html
    assert "<summary" in html
    assert "Generated UTC" in html
    assert "data/modules/marine_safety/input/fatality_incidents.csv" in html
    assert "data/modules/marine_safety/input/foundering_incidents.csv" in html
    assert "data/modules/marine_safety/input/hatch_incidents.csv" in html
    assert "Hurricane Planning and Mooring R0-4revisions.docx" in html


def test_reference_artifact_preservation_is_idempotent(tmp_path: Path):
    original_html = tmp_path / "hurricane_mooring_safety_infographic.html"
    original_stats = tmp_path / "hurricane_mooring_safety_infographic_stats.json"
    original_html.write_text("<html>prior</html>", encoding="utf-8")
    original_stats.write_text('{"prior": true}', encoding="utf-8")

    first = preserve_prior_draft(tmp_path)
    second = preserve_prior_draft(tmp_path)

    reference_html = (
        tmp_path / "reference_hurricane_mooring_safety_infographic_prior_draft.html"
    )
    reference_stats = (
        tmp_path
        / "reference_hurricane_mooring_safety_infographic_prior_draft_stats.json"
    )
    assert reference_html.read_text(encoding="utf-8") == "<html>prior</html>"
    preserved_stats = json.loads(reference_stats.read_text(encoding="utf-8"))
    assert preserved_stats["prior"] is True
    assert not original_html.exists()
    assert not original_stats.exists()
    assert first["preserved_html"] == str(reference_html)
    assert second["preserved_html"] == str(reference_html)


def test_reference_stats_sanitizes_absolute_paths(tmp_path: Path):
    original_stats = tmp_path / "hurricane_mooring_safety_infographic_stats.json"
    original_stats.write_text(
        json.dumps(
            {
                "output": "/mnt/local-analysis/workspace-hub/worldenergydata/reports/modules/marketing/hurricane_mooring_safety_infographic.html",
                "source_files": [
                    "/mnt/local-analysis/workspace-hub/worldenergydata/data/modules/marine_safety/input/fatality_incidents.csv"
                ],
            }
        ),
        encoding="utf-8",
    )

    preserve_prior_draft(tmp_path)

    reference_stats = json.loads(
        (
            tmp_path
            / "reference_hurricane_mooring_safety_infographic_prior_draft_stats.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        reference_stats["output"]
        == "reports/modules/marketing/hurricane_mooring_safety_infographic.html"
    )
    assert reference_stats["source_files"] == [
        "data/modules/marine_safety/input/fatality_incidents.csv"
    ]
    assert "local absolute paths were sanitized" in reference_stats["reference_note"]


def test_binary_exports_are_policy_gated(tmp_path: Path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "hurricane_mooring_safety_infographic.png").write_bytes(b"PNG")
    (assets / "hurricane_mooring_safety_infographic.pdf").write_bytes(b"PDF")

    result = generate_artifacts(
        output_dir=tmp_path, input_dir=INPUT_DIR, docx_name=DOCX_NAME
    )

    assert result["binary_exports"] == "skipped"
    assert result["html_path"].exists()
    assert result["stats_path"].exists()
    assert not (
        assets / "reference_hurricane_mooring_safety_infographic_prior_draft.png"
    ).exists()
    assert not (
        assets / "reference_hurricane_mooring_safety_infographic_prior_draft.pdf"
    ).exists()


def test_html_avoids_hurricane_causation_claims():
    html = render_html(build_stats(INPUT_DIR, DOCX_NAME)).lower()

    banned_phrases = [
        "65 hurricane incidents",
        "hurricane-caused incidents",
        "all incidents were caused by hurricanes",
    ]
    for phrase in banned_phrases:
        assert phrase not in html
