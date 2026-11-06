"""Bounded WAR bundle tests; examples are synthetic, never federal evidence."""

import hashlib
import json

import pytest

CSV = b"ACTIVITY_CATEGORY,OPERATOR\ndrilling,withheld\nintervention,withheld\ndrilling,withheld\n"


def evidence(payload=CSV):
    return {
        "dataset_id": "synthetic-war-test",
        "version": "test-v1",
        "source_url": "https://www.data.bsee.gov/Well/WellActivity/Default.aspx",
        "source_class": "public-federal",
        "license": "public-domain",
        "review_state": "reviewed",
        "readiness": "ready",
        "data_as_of": "2026-01-01",
        "retrieved_at": "2026-01-02T00:00:00+00:00",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "derivation": "reviewed-enriched-war",
    }


def build(payload=CSV, source=None):
    from worldenergydata.bsee.analysis.intervention.insight_workflow import build_bundle

    return build_bundle(
        payload,
        source=evidence(payload) if source is None else source,
        code_ref="a" * 40,
        catalog_ref="b" * 64,
    )


def test_aggregate_counts_and_no_raw_identity():
    """Hand count: D, I, D gives N=3, D=2, I=1, other=3-2-1=0.

    Counting basis: ComprehensiveActivityAnalyzer._analyze_cross_activity.
    No unique-well, duration, risk or population inference follows from rows.
    """
    result = build()
    assert result["metrics"] == {
        "record_count": 3,
        "drilling_records": 2,
        "intervention_records": 1,
        "other_records": 0,
    }
    assert "withheld" not in json.dumps(result)
    assert "OPERATOR" not in json.dumps(result)
    assert result["checks"]["hse"] == "NOT_EVALUATED"
    assert result["publication_state"] == "blocked_pending_bundle_review"
    assert result["source"]["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert result["findings"]
    assert result["limitations"]
    assert result["next_probes"]
    assert set(result["upstream_issues"]) == {450, 451}


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_class", "private"),
        ("license", "unknown"),
        ("readiness", "stale"),
        ("review_state", "pending"),
        ("sha256", "0" * 64),
        ("source_url", "https://example.org/data"),
        ("source_url", "https://www.data.bsee.gov/?token=hidden"),
        ("source_url", "https://user:password@www.data.bsee.gov/data"),
        ("dataset_id", "../restricted"),
        ("data_as_of", "unknown"),
        ("retrieved_at", "2026-01-02"),
        ("retrieved_at", "2025-01-01T00:00:00+00:00"),
    ],
)
def test_invalid_evidence_fails_closed(key, value):
    source = evidence()
    source[key] = value
    with pytest.raises(ValueError):
        build(source=source)


@pytest.mark.parametrize("key", list(evidence()))
def test_missing_evidence_fails_closed(key):
    source = evidence()
    del source[key]
    with pytest.raises(ValueError):
        build(source=source)


@pytest.mark.parametrize("payload", [b"", b"ACTIVITY_CATEGORY\n", b"wrong\ndrilling\n"])
def test_empty_or_wrong_schema_is_not_zero_activity(payload):
    with pytest.raises(ValueError):
        build(payload)


def test_unknown_and_missing_activity_are_other_records():
    """Hand count: completion and blank are 2 other rows; D=I=0."""
    result = build(b"ACTIVITY_CATEGORY,EXTRA\ncompletion,x\n,x\n")
    assert result["metrics"]["other_records"] == 2
    assert result["metrics"]["drilling_records"] == 0
    assert result["metrics"]["intervention_records"] == 0


def test_determinism_and_new_directory_only(tmp_path):
    from worldenergydata.bsee.analysis.intervention.insight_workflow import write_bundle

    bundle = build()
    assert bundle == build()
    target = tmp_path / "bundle"
    write_bundle(bundle, target)
    manifest = json.loads((target / "manifest.json").read_text())
    saved = (target / "insights.json").read_bytes()
    assert json.loads(saved) == bundle
    assert manifest["outputs"]["insights.json"] == hashlib.sha256(saved).hexdigest()
    html = (target / "findings.html").read_bytes()
    assert manifest["outputs"]["findings.html"] == hashlib.sha256(html).hexdigest()
    assert b"Revision history" in html
    assert b"NOT_EVALUATED" in html
    with pytest.raises(FileExistsError):
        write_bundle(bundle, target)
    assert saved == (target / "insights.json").read_bytes()


def test_cli_reads_local_inputs_without_changing_them(tmp_path):
    from worldenergydata.bsee.analysis.intervention.insight_workflow import main

    csv_path = tmp_path / "war.csv"
    source_path = tmp_path / "source.json"
    csv_path.write_bytes(CSV)
    original_source = json.dumps(evidence()).encode()
    source_path.write_bytes(original_source)
    target = tmp_path / "analysis"
    assert (
        main(
            [
                "--input",
                str(csv_path),
                "--source",
                str(source_path),
                "--output",
                str(target),
                "--code-ref",
                "a" * 40,
                "--catalog-ref",
                "b" * 64,
            ]
        )
        == 0
    )
    assert (
        json.loads((target / "insights.json").read_text())["metrics"]["record_count"]
        == 3
    )
    assert csv_path.read_bytes() == CSV
    assert source_path.read_bytes() == original_source


def test_cli_fails_before_writing_for_unclassified_input(tmp_path):
    from worldenergydata.bsee.analysis.intervention.insight_workflow import main

    csv_path = tmp_path / "war.csv"
    csv_path.write_bytes(CSV)
    source_path = tmp_path / "source.json"
    source_path.write_text("{}")
    target = tmp_path / "analysis"
    with pytest.raises(ValueError):
        main(
            [
                "--input",
                str(csv_path),
                "--source",
                str(source_path),
                "--output",
                str(target),
                "--code-ref",
                "a" * 40,
                "--catalog-ref",
                "b" * 64,
            ]
        )
    assert not target.exists()


def test_annual_counts_preserve_unknown_year_without_inference():
    """Hand counts: 2024 D,I -> (2,1,1); 2025 D -> (1,1,0).

    A blank year with completion contributes one undated other record.
    Sum of year buckets 2+1+1=4 equals total rows. Years are labels from
    input, not inferred operational dates or exposure denominators.
    """
    result = build(
        b"ACTIVITY_CATEGORY,YEAR\ndrilling,2024\nintervention,2024\n"
        b"drilling,2025\ncompletion,\n"
    )
    assert result["by_year"] == [
        {
            "year": "2024",
            "record_count": 2,
            "drilling_records": 1,
            "intervention_records": 1,
            "other_records": 0,
        },
        {
            "year": "2025",
            "record_count": 1,
            "drilling_records": 1,
            "intervention_records": 0,
            "other_records": 0,
        },
        {
            "year": None,
            "record_count": 1,
            "drilling_records": 0,
            "intervention_records": 0,
            "other_records": 1,
        },
    ]


def test_absent_years_remain_undated():
    assert build()["by_year"][0]["year"] is None
    assert build()["by_year"][0]["record_count"] == 3


def test_invalid_year_is_undated_and_not_echoed():
    result = build(b"ACTIVITY_CATEGORY,YEAR\ndrilling,restricted-label\n")
    assert result["by_year"][0]["year"] is None
    assert "restricted-label" not in json.dumps(result)


def test_manifest_links_upstream_contracts(tmp_path):
    from worldenergydata.bsee.analysis.intervention.insight_workflow import write_bundle

    target = tmp_path / "bundle"
    write_bundle(build(), target)
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["upstream_links"] == {
        "run_manifest": "https://github.com/vamseeachanta/worldenergydata/issues/450",
        "source_readiness": "https://github.com/vamseeachanta/worldenergydata/issues/451",
    }


def test_extra_source_metadata_is_not_projected():
    source = {
        **evidence(),
        "local_path": "restricted-location",
        "notes": "restricted-note",
    }
    output = json.dumps(build(source=source))
    assert "restricted-location" not in output
    assert "restricted-note" not in output
