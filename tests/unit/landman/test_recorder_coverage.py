"""Offline feasibility tests; expected decisions follow issue #914's categories.

Truth-table cases below are independent hand evaluations: an explicit ban wins;
unknown search access blocks automation; required attendance means in-person;
payment or registration means gated; free index plus free images means public;
an online index without established free images requires manual follow-up.
These are policy cases, not numerical engineering acceptance limits.
"""

import json
import runpy
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.landman.recorder_coverage import (
    CoverageCatalog,
    RecorderCoverage,
    load_catalog,
    main,
)


@pytest.fixture
def row():
    return {
        "state": "TX",
        "county": "Example",
        "recorder_url": "https://example.org/recorder",
        "priority_basis": "Synthetic policy fixture; no real county assertion.",
        "readiness_evidence": ["Issue #911, state regulator separation."],
        "regulator_readiness": "configured-only",
        "search_capabilities": "NOT_EVALUATED",
        "document_types": ["deed"],
        "cost_constraints": "NOT_EVALUATED",
        "coverage_limits": "NOT_EVALUATED",
        "legal_caveats": "Terms and title completeness require review.",
        "next_action": "Review recorder terms without creating an account.",
        "sources": [
            {
                "url": "https://example.org/recorder",
                "title": "Synthetic evidence",
                "observed_on": "2026-10-20",
                "status": "opened",
                "finding": "Synthetic fixture, not a public-source claim.",
            }
        ],
    }


@pytest.mark.parametrize(
    "facts, expected",
    [
        ({}, "do-not-automate"),
        ({"online_search": True}, "do-not-automate"),
        ({"in_person_required": True}, "in-person-only"),
        ({"online_search": True, "account_required": True}, "paid-gated"),
        ({"online_search": True, "payment_required": True}, "paid-gated"),
        (
            {
                "online_search": True,
                "account_required": False,
                "payment_required": False,
            },
            "manual-download",
        ),
        (
            {
                "online_search": True,
                "free_images": True,
                "account_required": False,
                "payment_required": False,
            },
            "public-online",
        ),
        (
            {
                "online_search": True,
                "free_images": True,
                "account_required": False,
                "payment_required": False,
                "automation_terms": "prohibited",
            },
            "do-not-automate",
        ),
        ({"in_person_required": True, "payment_required": True}, "in-person-only"),
    ],
)
def test_classification_truth_table(row, facts, expected):
    assert RecorderCoverage(**(row | facts)).classification == expected


def test_public_access_is_not_automation_permission(row):
    facts = {
        "online_search": True,
        "free_images": True,
        "account_required": False,
        "payment_required": False,
    }
    record = RecorderCoverage(**(row | facts))
    assert record.classification == "public-online"
    assert record.automation_feasibility == "NOT_EVALUATED"
    assert record.title_chain_status == "NOT_EVALUATED"
    assert record.source_family == "county-recorder"
    permitted = record.model_copy(
        update={"automation_terms": "allowed", "bulk_available": True}
    )
    assert permitted.automation_feasibility == "candidate-for-review"


def test_unavailable_evidence_does_not_establish_access(row):
    row.update(
        online_search=True,
        free_images=True,
        account_required=False,
        payment_required=False,
        automation_terms="allowed",
        bulk_available=True,
    )
    row["sources"][0]["status"] = "unavailable"
    record = RecorderCoverage(**row)
    assert record.classification == "do-not-automate"
    assert record.automation_feasibility == "blocked"


@pytest.mark.parametrize(
    "field,value",
    [
        ("sources", []),
        ("priority_basis", " "),
        ("readiness_evidence", []),
        ("recorder_url", "file:records"),
        ("online_search", "yes"),
        ("source_family", "state-regulator"),
        ("automation_terms", "assumed"),
    ],
)
def test_invalid_evidence_rejected(row, field, value):
    with pytest.raises(ValidationError):
        RecorderCoverage(**(row | {field: value}))


def test_exact_lookup_and_duplicate_rejection(row):
    catalog = CoverageCatalog(counties=[RecorderCoverage(**row)])
    assert catalog.get(" tx ", " example county ").county == "EXAMPLE"
    with pytest.raises(KeyError):
        catalog.get("TX", "Exam")
    with pytest.raises(ValidationError, match="Duplicate"):
        CoverageCatalog(counties=[RecorderCoverage(**row), RecorderCoverage(**row)])


def test_priority_order_is_readiness_then_identity(row):
    """Hand sort: downloaded CO precedes configured TX; no production score."""
    configured = RecorderCoverage(**row)
    downloaded = RecorderCoverage(
        **(
            row
            | {"state": "CO", "county": "Other", "regulator_readiness": "downloaded"}
        )
    )
    catalog = CoverageCatalog(counties=[configured, downloaded])
    assert [r.state for r in catalog.priority_counties()] == ["CO", "TX"]
    assert catalog.priority_counties(states=[" tx "]) == [configured]


def test_packaged_catalog_and_serialization(tmp_path):
    catalog = load_catalog()
    assert {(r.state, r.county) for r in catalog.counties} == {
        ("TX", "MIDLAND"),
        ("OK", "CANADIAN"),
        ("CO", "WELD"),
        ("KS", "STEVENS"),
    }
    for record in catalog.counties:
        assert record.sources
        assert all(s.observed_on <= date(2026, 10, 20) for s in record.sources)
        assert record.title_chain_status == "NOT_EVALUATED"
        assert record.automation_feasibility != "candidate-for-review"
    # Serialized computed answers must remain loadable and be recomputed.
    path = tmp_path / "coverage.json"
    path.write_text(catalog.model_dump_json())
    assert load_catalog(path) == catalog
    assert json.loads(path.read_text())["counties"][0]["classification"]
    tampered = json.loads(path.read_text())
    tampered["counties"][0]["classification"] = "public-online"
    tampered["counties"][0]["automation_feasibility"] = "candidate-for-review"
    path.write_text(json.dumps(tampered))
    assert load_catalog(path) == catalog


def test_missing_custom_catalog_is_not_silently_replaced(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_catalog(tmp_path / "missing.json")


def test_export_filters_and_recomputes_answers(capsys):
    main(["--state", "ok"])
    payload = json.loads(capsys.readouterr().out)
    assert [r["county"] for r in payload["counties"]] == ["CANADIAN"]
    assert payload["counties"][0]["classification"] == "paid-gated"
    main(["--state", "AR"])
    assert json.loads(capsys.readouterr().out) == {"counties": []}


def test_worked_example(capsys):
    """Hand evaluation of the source facts, without calling the classifier.

    Weld's explicit automation ban wins over copy purchase availability;
    Canadian's required image login means gated. Neither the Stevens nor
    Midland page establishes online search rights, so both stay excluded.
    Equal reported readiness sorts alphabetically by state: CO, KS, OK, TX.
    """
    root = Path(__file__).resolve().parents[3]
    runpy.run_path(
        str(root / "examples/landman/recorder_coverage.py"), run_name="__main__"
    )
    assert capsys.readouterr().out.splitlines() == [
        "CO/WELD: do-not-automate; automation=blocked; title=NOT_EVALUATED",
        "KS/STEVENS: do-not-automate; automation=blocked; title=NOT_EVALUATED",
        "OK/CANADIAN: paid-gated; automation=blocked; title=NOT_EVALUATED",
        "TX/MIDLAND: do-not-automate; automation=blocked; title=NOT_EVALUATED",
    ]
