"""Source-neutral intake controls; all test entities are synthetic."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.hse.importers.offshore_importer import OffshoreImporter
from worldenergydata.hse.offshore import Event, SourceDocument, check_privacy


def event(**changes):
    row = dict(
        event_id="test-event",
        event_date="2024-02-01",
        country="GB",
        basin_or_area="test basin",
        installation_name="test installation",
        installation_aliases=["test alias"],
        installation_type="semisubmersible",
        operation="riser or BOP handling",
        equipment=["riser"],
        failure_mode="separation",
        failure_summary="riser separated during handling",
        organisations=["test organisation"],
    )
    row.update(changes)
    return row


def source(**changes):
    row = dict(
        event_id="test-event",
        source="uk_hse",
        source_ref="test-notice",
        title="test notice",
        doc_type="improvement notice",
        issue_date="2024-03-21",
        status="complied with",
        url="https://resources.hse.gov.uk/notices/test",
        access_date="2026-10-17",
        licence="OGL-3.0",
        evidence_level="regulator",
        access_status="public",
        summary="assembly instructions required clarification",
    )
    row.update(changes)
    return row


def reviewed_strings(value):
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return set().union(*(reviewed_strings(v) for v in value)) if value else set()
    if isinstance(value, dict):
        return (
            set().union(*(reviewed_strings(v) for v in value.values()))
            if value
            else set()
        )
    return set()


def packet(events=None, sources=None, **changes):
    rows = dict(events=events or [event()], sources=sources or [source()])
    rows["reviewed_text"] = sorted(reviewed_strings(rows))
    rows.update(changes)
    return rows


def approve_test_pilot(importer):
    importer.ingest(
        packet(
            sources=[
                source(access_status="public"),
                source(
                    source="opred",
                    source_ref="test-release",
                    access_status="public",
                    url="https://itportal.energysecurity.gov.uk/test",
                ),
                source(
                    source="iadc",
                    source_ref="test-alert",
                    access_status="public",
                    url="https://iadc.org/test",
                    evidence_level="industry alert",
                ),
            ]
        )
    )
    review = {
        "verdict": "pass",
        "reviewer_role": "independent_agent",
        "reviewed_event_ids": ["test-event"],
        "dataset_sha256": importer.content_digest(),
    }
    importer.approve_pilot("test-event", review)
    return review


def test_global_coordinates_and_unknown_counts():
    row = Event.model_validate(event(lat=60.380755, lon=-4.098893))
    assert row.injuries is None and row.fatalities is None
    assert row.event_date.isoformat() == "2024-02-01"


@pytest.mark.parametrize(
    "changes",
    [
        {"lat": 91},
        {"lon": -181},
        {"injuries": -1},
        {"operation": "unknown"},
        {"failure_summary": "word " * 51},
        {"injured_person_name": "redacted"},
        {"release_quantity": 1},
        {"event_date": "2024-02-01T06:45:00"},
    ],
)
def test_invalid_event(changes):
    with pytest.raises(ValidationError):
        Event.model_validate(event(**changes))


def test_utc_time_is_preserved():
    row = Event.model_validate(event(event_date="2024-02-01T06:45:00Z"))
    assert row.event_date.isoformat().endswith("+00:00")


def test_source_citation_and_ogl_attribution():
    row = SourceDocument.model_validate(source())
    assert "test-notice" in row.citation
    assert "accessed 2026-10-17" in row.citation
    assert "Contains public sector information" in row.citation


@pytest.mark.parametrize(
    "changes",
    [
        {"url": "https://unofficial.invalid/test"},
        {"source": "social_media"},
        {"evidence_level": "lead"},
        {"access_status": "blocked"},
        {"url": "https://resources.hse.gov.uk\x40unofficial.invalid/test"},
        {"access_date": "2024-01-01"},
        {"licence": ""},
    ],
)
def test_unverified_source_cannot_be_admitted(changes):
    with pytest.raises(ValidationError):
        SourceDocument.model_validate(source(**changes))


def test_privacy_fails_closed_for_unreviewed_text():
    rows = packet()
    rows["events"][0]["failure_summary"] = "redacted individual was involved"
    with pytest.raises(ValueError, match="privacy"):
        check_privacy(rows["events"], rows["reviewed_text"])


@pytest.mark.parametrize("value", ["contact\x40example.invalid", "+44 1234 567890"])
def test_contact_data_rejected_even_if_reviewed(value):
    with pytest.raises(ValueError, match="privacy"):
        check_privacy([value], [value])


def test_import_is_idempotent_and_logs_planted_duplicate(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    rows = packet()
    assert importer.ingest(rows)["sources_added"] == 1
    assert importer.ingest(rows)["sources_added"] == 0
    with sqlite3.connect(importer.database) as db:
        assert db.execute("select count(*) from events").fetchone()[0] == 1
        assert db.execute("select count(*) from sources").fetchone()[0] == 1
        assert (
            db.execute("select rule from dedup_log order by id desc").fetchone()[0]
            == "source_ref"
        )


def test_alias_date_country_matches_one_event(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    rows = packet(
        [
            event(
                event_id="another",
                installation_name="TEST ALIAS",
                event_date="2024-02-03",
            )
        ],
        [source(event_id="another", source_ref="second")],
    )
    result = importer.ingest(rows)
    assert result["events_added"] == 0 and result["sources_added"] == 1
    with sqlite3.connect(importer.database) as db:
        assert db.execute("select distinct event_id from sources").fetchall() == [
            ("test-event",)
        ]


@pytest.mark.parametrize("changes", [{"country": "NO"}, {"event_date": "2024-02-04"}])
def test_country_and_date_required_for_match(tmp_path, changes):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    approve_test_pilot(importer)
    rows = packet(
        [event(event_id="another", **changes)],
        [source(event_id="another", source_ref="second")],
    )
    assert importer.ingest(rows, stage="candidate")["events_added"] == 1


def test_existing_event_is_linked_without_copying(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    existing = [
        dict(
            module="hse",
            record_id="42",
            event_date="2024-02-01",
            country="GB",
            installation_name="test installation",
            block_or_lease="204/20",
        )
    ]
    result = importer.ingest(packet(), existing=existing)
    assert result["linked_existing"] == 1 and result["events_added"] == 0
    assert importer.ingest(packet())["events_added"] == 0
    with sqlite3.connect(importer.database) as db:
        assert db.execute("select count(*) from events").fetchone()[0] == 0
        assert db.execute("select module,record_id from external_links").fetchall() == [
            ("hse", "42")
        ]


def test_bsee_date_and_block_link_without_installation_match(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    existing = [
        dict(
            module="hse",
            record_id="42",
            event_date="2024-02-01",
            country="US",
            installation_name="",
            block_or_lease="MC807",
        )
    ]
    rows = packet([event(country="US", block_or_lease="MC-807; G12345")])
    assert importer.ingest(rows, existing=existing)["linked_existing"] == 1


def test_conflicting_source_or_ambiguous_match_rolls_back(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    bad = packet([event(event_date="2025-01-01")])
    with pytest.raises(ValueError, match="conflicting"):
        importer.ingest(bad)
    with sqlite3.connect(importer.database) as db:
        assert db.execute("select count(*) from sources").fetchone()[0] == 1


def test_no_orphans_or_unused_event_rows(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    with pytest.raises(ValueError, match="event"):
        importer.ingest(packet(sources=[source(event_id="missing")]))


def test_manifest_digests_and_bulk_gate(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    manifest = importer.export(tmp_path / "exports")
    assert manifest["event_count"] == 1
    assert manifest["bulk_admitted"] is False
    assert manifest["digest_format"] == "canonical-sqlite-evidence-v2"
    for name, digest in manifest["sha256"].items():
        assert (
            hashlib.sha256((tmp_path / "exports" / name).read_bytes()).hexdigest()
            == digest
        )


def test_pilot_gate_needs_three_independent_sources(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    with pytest.raises(ValueError, match="pilot"):
        importer.approve_pilot(
            "test-event", {"verdict": "pass", "reviewed_event_ids": ["test-event"]}
        )


def test_bulk_intake_requires_pilot_review(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    with pytest.raises(ValueError, match="pilot"):
        importer.ingest(packet(), stage="candidate")


def test_pilot_intake_cannot_silently_collect_many_events(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    rows = packet(
        [
            event(
                event_id="second",
                installation_name="different",
                installation_aliases=[],
            )
        ],
        [source(event_id="second", source_ref="second")],
    )
    with pytest.raises(ValueError, match="pilot"):
        importer.ingest(rows)


def test_review_is_bound_to_actual_data(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    review = approve_test_pilot(importer)
    assert review["dataset_sha256"] == importer.content_digest()
    review["dataset_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        importer.approve_pilot("test-event", review)


def test_privacy_inventory_itself_is_checked():
    with pytest.raises(ValueError, match="privacy"):
        check_privacy(["valid"], ["valid", "contact\x40example.invalid"])


def test_full_gate_requires_consumed_indexes_and_frozen_independent_review(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    approve_test_pilot(importer)
    events = [
        event(
            event_id=f"event-{n}",
            installation_name=f"test installation {n}",
            installation_aliases=[],
        )
        for n in range(49)
    ]
    sources = [
        source(event_id=f"event-{n}", source_ref=f"notice-{n}") for n in range(49)
    ]
    importer.ingest(packet(events, sources), stage="candidate")
    review = dict(
        verdict="pass",
        reviewer_role="independent_agent",
        reviewed_event_ids=[f"event-{n}" for n in range(5)],
        dataset_sha256=importer.content_digest(),
    )
    with pytest.raises(ValueError, match="index"):
        importer.approve_bulk(review, {})
    indexes = {
        module: {"complete": True, "records": []} for module in ("hse", "marine_safety")
    }
    indexes["hse"]["records"] = [
        dict(
            record_id="unrelated",
            event_date="2020-01-01",
            country="US",
            installation_name="test unrelated",
        )
    ]
    importer.reconcile_existing(indexes)
    importer.approve_bulk(review, indexes)
    assert importer.export(tmp_path / "accepted")["bulk_admitted"] is True
    short_review = dict(review, reviewed_event_ids=["event-0"])
    with pytest.raises(ValueError, match="10%"):
        importer.approve_bulk(short_review, indexes)
    # A changed evidence packet invalidates previous bulk acceptance.
    importer.ingest(
        packet(
            [
                event(
                    event_id="extra", installation_name="extra", installation_aliases=[]
                )
            ],
            [source(event_id="extra", source_ref="extra")],
        ),
        stage="candidate",
    )
    assert importer.export(tmp_path / "changed")["bulk_admitted"] is False
    with pytest.raises(ValueError, match="digest"):
        importer.approve_bulk(review, indexes)


def test_reconciliation_links_both_existing_modules_and_invalidates_review(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    indexes = {
        module: {
            "complete": True,
            "records": [
                dict(
                    record_id="42",
                    event_date="2024-02-01",
                    country="GB",
                    installation_name="test installation",
                )
            ],
        }
        for module in ("hse", "marine_safety")
    }
    importer.reconcile_existing(indexes)
    with sqlite3.connect(importer.database) as db:
        assert db.execute("select count(*) from events").fetchone()[0] == 0
        assert db.execute("select count(*) from external_links").fetchone()[0] == 2
        assert db.execute("select count(*) from sources").fetchone()[0] == 1


def test_review_receipt_refuses_unbounded_text(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    review = approve_test_pilot(importer)
    with pytest.raises(ValidationError):
        importer.approve_pilot(
            "test-event", dict(review, notes="contact\x40example.invalid")
        )


def test_changed_pilot_evidence_requires_new_review(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    approve_test_pilot(importer)
    importer.ingest(packet(sources=[source(source_ref="additional-pilot-notice")]))
    with pytest.raises(ValueError, match="pilot"):
        importer.ingest(packet(), stage="candidate")


def test_pilot_limit_applies_to_external_links(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    rows = packet(
        [
            event(),
            event(
                event_id="second",
                installation_name="different",
                installation_aliases=[],
            ),
        ],
        [source(), source(event_id="second", source_ref="second")],
    )
    existing = [
        dict(
            module="hse",
            record_id=str(n),
            event_date="2024-02-01",
            country="GB",
            installation_name=name,
        )
        for n, name in enumerate(("test installation", "different"))
    ]
    with pytest.raises(ValueError, match="pilot"):
        importer.ingest(rows, existing=existing)


def test_reconciliation_checks_other_module_for_prelinked_event(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    identity = dict(
        record_id="42",
        event_date="2024-02-01",
        country="GB",
        installation_name="test installation",
    )
    importer.ingest(packet(), existing=[dict(identity, module="hse")])
    indexes = {
        module: {"complete": True, "records": [identity]}
        for module in ("hse", "marine_safety")
    }
    importer.reconcile_existing(indexes)
    with sqlite3.connect(importer.database) as db:
        assert db.execute("select count(*) from external_links").fetchone()[0] == 2
    indexes["hse"]["records"] = [dict(identity, event_date="2025-01-01")]
    with pytest.raises(ValueError, match="existing link"):
        importer.reconcile_existing(indexes)


def test_evidence_level_must_match_agency():
    with pytest.raises(ValidationError):
        SourceDocument.model_validate(
            source(source="iadc", url="https://iadc.org/test")
        )


def test_export_collision_leaves_existing_evidence_unchanged(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(packet())
    importer.export(tmp_path / "export")
    before = {p.name: p.read_bytes() for p in (tmp_path / "export").iterdir()}
    importer.ingest(packet())  # audit log changes, event/source content does not
    with pytest.raises(FileExistsError):
        importer.export(tmp_path / "export")
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "export").iterdir()}


def test_source_labels_are_truthful():
    root = Path(__file__).resolve().parents[3]
    contract = json.loads(
        (root / "data/source-refresh-acceptance-contract.json").read_text()
    )
    row = next(s for s in contract["sources"] if s["module_id"] == "hse")
    assert all(agency in row["source_authority"] for agency in ("BSEE", "OSHA", "EPA"))
    assert row["uk_hse_offshore_statistics_status"] == "not_acquired"
    assert "offshore/statistics.htm" not in row["source_url_or_api"]


def test_cached_notice_cannot_satisfy_pilot_gate(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    rows = packet(
        sources=[
            source(access_status="cached"),
            source(
                source="opred",
                source_ref="release",
                access_status="public",
                url="https://itportal.energysecurity.gov.uk/test",
            ),
            source(
                source="iadc",
                source_ref="alert",
                access_status="public",
                evidence_level="industry alert",
                url="https://iadc.org/test",
            ),
        ]
    )
    importer.ingest(rows)
    review = dict(
        verdict="pass",
        reviewer_role="independent_agent",
        reviewed_event_ids=["test-event"],
        dataset_sha256=importer.content_digest(),
    )
    with pytest.raises(ValueError, match="public"):
        importer.approve_pilot("test-event", review)


def test_linked_identity_participates_in_same_packet_matching(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    approve_test_pilot(importer)
    rows = packet(
        [
            event(
                event_id="linked",
                installation_name="external installation",
                installation_aliases=["shared alias"],
            ),
            event(
                event_id="alias",
                installation_name="shared alias",
                installation_aliases=[],
            ),
            event(
                event_id="original",
                installation_name="external installation",
                installation_aliases=[],
            ),
        ],
        [
            source(event_id="linked", source_ref="linked-notice"),
            source(event_id="alias", source_ref="alias-notice"),
            source(event_id="original", source_ref="original-notice"),
        ],
    )
    identity = dict(
        module="hse",
        record_id="42",
        event_date="2024-02-01",
        country="GB",
        installation_name="external installation",
    )
    result = importer.ingest(rows, existing=[identity], stage="candidate")
    assert result["events_added"] == 0
    with importer.connect() as db:
        assert db.execute(
            "SELECT DISTINCT event_id FROM sources WHERE event_id != 'test-event'"
        ).fetchall() == [("linked",)]


@pytest.mark.parametrize("entry_point", ["ingest", "reconcile"])
def test_external_identity_contacts_rejected_before_persistence(tmp_path, entry_point):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    row = dict(
        record_id="contact\x40example.invalid",
        event_date="2024-02-01",
        country="GB",
        installation_name="test installation",
    )
    with pytest.raises(ValueError, match="privacy"):
        if entry_point == "ingest":
            importer.ingest(packet(), existing=[dict(row, module="hse")])
        else:
            importer.ingest(packet())
            importer.reconcile_existing(
                {
                    module: dict(complete=True, records=[row])
                    for module in ("hse", "marine_safety")
                }
            )
    with importer.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM external_links").fetchone()[0] == 0


@pytest.mark.parametrize(
    "identity_change",
    [
        {"module": "unrecognized"},
        {"event_id": "injected-canonical-id"},
    ],
)
def test_external_identity_cannot_inject_internal_metadata(tmp_path, identity_change):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    row = dict(
        module="hse",
        record_id="42",
        event_date="2024-02-01",
        country="GB",
        installation_name="test installation",
    )
    row.update(identity_change)
    with pytest.raises(ValueError, match="identity|module"):
        importer.ingest(packet(), existing=[row])


@pytest.mark.parametrize("route", ["ingest", "reconcile"])
@pytest.mark.parametrize("alias", ["legacy alias", "new alias"])
def test_link_aliases_survive_reopening_database(tmp_path, route, alias):
    database = tmp_path / "offshore.db"
    importer = OffshoreImporter(database)
    approve_test_pilot(importer)
    identity = dict(
        record_id="42",
        event_date="2024-02-01",
        country="GB",
        installation_name="external installation",
        installation_aliases=["legacy alias"],
    )
    rows = packet(
        [
            event(
                event_id="linked",
                installation_name="external installation",
                installation_aliases=["shared alias"],
            )
        ],
        [source(event_id="linked", source_ref="linked-notice")],
    )
    if route == "ingest":
        importer.ingest(
            rows, existing=[dict(identity, module="hse")], stage="candidate"
        )
    else:
        importer.ingest(rows, stage="candidate")
        importer.reconcile_existing(
            {
                "hse": dict(complete=True, records=[identity]),
                "marine_safety": dict(complete=True, records=[]),
            }
        )
    importer.ingest(
        packet(
            [
                event(
                    event_id="learned",
                    installation_name="shared alias",
                    installation_aliases=["new alias"],
                )
            ],
            [source(event_id="learned", source_ref="learned-notice")],
        ),
        stage="candidate",
    )
    reopened = OffshoreImporter(database)
    result = reopened.ingest(
        packet(
            [
                event(
                    event_id="reopened",
                    installation_name=alias,
                    installation_aliases=[],
                )
            ],
            [source(event_id="reopened", source_ref="reopened-notice")],
        ),
        stage="candidate",
    )
    assert result["events_added"] == 0


def test_canonical_alias_chain_is_persistent_and_idempotent(tmp_path):
    database = tmp_path / "offshore.db"
    importer = OffshoreImporter(database)
    approve_test_pilot(importer)
    rows = packet(
        [
            event(
                event_id="chain-a",
                installation_name="installation-a",
                installation_aliases=["installation-b"],
            ),
            event(
                event_id="chain-b",
                installation_name="installation-b",
                installation_aliases=["installation-c"],
            ),
            event(
                event_id="chain-c",
                installation_name="installation-c",
                installation_aliases=[],
            ),
        ],
        [
            source(event_id=f"chain-{letter}", source_ref=f"notice-{letter}")
            for letter in "abc"
        ],
    )
    assert importer.ingest(rows, stage="candidate")["events_added"] == 1
    reopened = OffshoreImporter(database)
    rerun = reopened.ingest(rows, stage="candidate")
    assert rerun["events_added"] == rerun["sources_added"] == 0
    result = reopened.ingest(
        packet(
            [
                event(
                    event_id="later",
                    installation_name="installation-c",
                    installation_aliases=[],
                )
            ],
            [source(event_id="later", source_ref="later-notice")],
        ),
        stage="candidate",
    )
    assert result["events_added"] == 0


@pytest.mark.parametrize("route", ["ingest", "reconcile"])
def test_link_preserves_classification_and_binds_export_digest(tmp_path, route):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    identity = dict(
        record_id="42",
        event_date="2024-02-01",
        country="GB",
        installation_name="test installation",
    )
    if route == "ingest":
        importer.ingest(packet(), existing=[dict(identity, module="hse")])
    else:
        importer.ingest(packet())
        importer.reconcile_existing(
            {
                "hse": {"complete": True, "records": [identity]},
                "marine_safety": {"complete": True, "records": []},
            }
        )
    importer = OffshoreImporter(importer.database)
    importer.export(tmp_path / "export")
    link = json.loads((tmp_path / "export/external_links.json").read_text())[0]
    expected = {
        key: event()[key]
        for key in ("operation", "failure_mode", "failure_summary", "equipment")
    }
    assert link["annotations"] == expected
    digest = importer.content_digest()
    with importer.connect() as db:
        db.execute("UPDATE external_links SET annotations='{}'")
    assert importer.content_digest() != digest


@pytest.mark.parametrize("stage", ["pilot", "candidate"])
@pytest.mark.parametrize(
    "changes",
    [
        {"operation": "lifting"},
        {"failure_mode": "equipment failure"},
        {"failure_summary": "equipment failed during handling"},
        {"equipment": ["hoist"]},
    ],
)
def test_linked_classification_conflict_rolls_back_reviewed_pilot(
    tmp_path, stage, changes
):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(
        packet(),
        existing=[
            dict(
                module="hse",
                record_id="42",
                event_date="2024-02-01",
                country="GB",
                installation_name="test installation",
            )
        ],
    )
    approve_test_pilot(importer)
    importer = OffshoreImporter(importer.database)
    with importer.connect() as db:
        before = list(db.iterdump())
    with pytest.raises(
        ValueError,
        match="conflicting event classification; explicit review required",
    ):
        importer.ingest(packet([event(**changes)]), stage=stage)
    with importer.connect() as db:
        assert list(db.iterdump()) == before


def test_legacy_link_migration_exports_empty_annotations_and_accepts_intake(tmp_path):
    database = tmp_path / "offshore.db"
    identity = dict(
        event_date="2024-02-01",
        country="GB",
        installation_name="test installation",
        installation_aliases=["test alias"],
        block_or_lease=None,
    )
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE external_links("
            "event_id TEXT NOT NULL, module TEXT NOT NULL, record_id TEXT NOT NULL, "
            "identity TEXT NOT NULL, UNIQUE(module,record_id))"
        )
        db.execute(
            "INSERT INTO external_links VALUES (?,?,?,?)",
            ("test-event", "hse", "42", json.dumps(identity, sort_keys=True)),
        )
    importer = OffshoreImporter(database)
    importer.export(tmp_path / "legacy-export")
    legacy_link = json.loads(
        (tmp_path / "legacy-export/external_links.json").read_text()
    )[0]
    assert legacy_link["identity"] == identity
    assert legacy_link["annotations"] == {}
    assert importer.ingest(packet()) == dict(
        events_added=0, sources_added=1, linked_existing=0
    )
    importer = OffshoreImporter(database)
    manifest = importer.export(tmp_path / "export")
    assert manifest["linked_existing_count"] == 1
    link = json.loads((tmp_path / "export/external_links.json").read_text())[0]
    assert link["identity"] == identity
    assert link["annotations"] == {
        key: event()[key]
        for key in ("operation", "failure_mode", "failure_summary", "equipment")
    }
    digest = importer.content_digest()
    assert importer.ingest(packet())["sources_added"] == 0
    assert importer.content_digest() == digest


@pytest.mark.parametrize(
    "agency,host",
    [
        ("iogp", "data.iogp.org"),
        ("nopsema", "www.nopsema.gov.au"),
        ("csb", "www.csb.gov"),
    ],
)
def test_metadata_only_sources_refuse_summary_and_allow_omission(agency, host):
    row = source(
        source=agency,
        url=f"https://{host}/test",
        evidence_level="industry alert" if agency == "iogp" else "regulator",
    )
    with pytest.raises(ValidationError, match="metadata"):
        SourceDocument.model_validate(row)
    row.pop("summary")
    assert SourceDocument.model_validate(row).summary is None


@pytest.mark.parametrize("field", ["summary", "status"])
def test_source_text_is_limited_to_fifty_words(field):
    with pytest.raises(ValidationError, match="50 words"):
        SourceDocument.model_validate(source(**{field: "word " * 51}))
    SourceDocument.model_validate(source(**{field: "word " * 50}))


def test_bulk_gate_refuses_fewer_than_fifty_with_valid_prior_pilot(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    review = approve_test_pilot(importer)
    with pytest.raises(ValueError, match="50 events"):
        importer.approve_bulk(review, {})


def test_pilot_gate_counts_agencies_not_public_documents(tmp_path):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(
        packet(sources=[source(source_ref=f"notice-{n}") for n in range(3)])
    )
    review = dict(
        verdict="pass",
        reviewer_role="independent_agent",
        reviewed_event_ids=["test-event"],
        dataset_sha256=importer.content_digest(),
    )
    with pytest.raises(ValueError, match="three public sources"):
        importer.approve_pilot("test-event", review)


def test_empty_hse_index_is_refused():
    with pytest.raises(ValueError, match="hse"):
        OffshoreImporter._index_evidence(
            {
                "hse": {"complete": True, "records": []},
                "marine_safety": {"complete": True, "records": []},
            }
        )


def test_committed_packets_exclude_cached_evidence():
    root = Path(__file__).resolve().parents[3] / "data/modules/hse/offshore"
    for name in ("pilot.json", "sample.json"):
        rows = json.loads((root / name).read_text())
        assert all(row["access_status"] == "public" for row in rows["sources"])


@pytest.mark.parametrize("stage", ["pilot", "candidate"])
@pytest.mark.parametrize(
    "changes",
    [
        {"operation": "lifting"},
        {"failure_mode": "equipment failure"},
        {"failure_summary": "equipment failed during handling"},
        {"equipment": ["hoist"]},
    ],
)
def test_stored_classification_conflict_rolls_back_reviewed_pilot(
    tmp_path, stage, changes
):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    approve_test_pilot(importer)
    importer = OffshoreImporter(importer.database)
    with importer.connect() as db:
        before = list(db.iterdump())
    rows = packet(
        [event(event_id="another", **changes)],
        [source(event_id="another", source_ref="second")],
    )
    with pytest.raises(
        ValueError,
        match="conflicting event classification; explicit review required",
    ):
        importer.ingest(rows, stage=stage)
    with importer.connect() as db:
        assert list(db.iterdump()) == before


@pytest.mark.parametrize("route", ["stored", "linked"])
@pytest.mark.parametrize(
    "changes",
    [
        {"operation": "lifting"},
        {"failure_mode": "equipment failure"},
        {"failure_summary": "equipment failed during handling"},
        {"equipment": ["hoist"]},
    ],
)
def test_same_packet_classification_conflict_rolls_back(tmp_path, route, changes):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    existing = []
    if route == "linked":
        existing = [
            dict(
                module="hse",
                record_id="42",
                event_date="2024-02-01",
                country="GB",
                installation_name="test installation",
            )
        ]
    with importer.connect() as db:
        before = list(db.iterdump())
    rows = packet(
        [event(), event(event_id="another", **changes)],
        [source(), source(event_id="another", source_ref="second")],
    )
    with pytest.raises(
        ValueError,
        match="conflicting event classification; explicit review required",
    ):
        importer.ingest(rows, existing=existing)
    with importer.connect() as db:
        assert list(db.iterdump()) == before


@pytest.mark.parametrize("module", ["hse", "marine_safety"])
@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"operation": "lifting"},
        {"failure_mode": "equipment failure"},
        {"failure_summary": "equipment failed during handling"},
        {"equipment": ["hoist"]},
    ],
)
def test_existing_event_id_cannot_gain_second_intake_link(tmp_path, module, changes):
    importer = OffshoreImporter(tmp_path / "offshore.db")
    importer.ingest(
        packet(),
        existing=[
            dict(
                module="hse",
                record_id="42",
                event_date="2024-02-01",
                country="GB",
                installation_name="test installation",
            )
        ],
    )
    approve_test_pilot(importer)
    importer = OffshoreImporter(importer.database)
    rows = packet(
        [
            event(
                event_date="2024-03-01",
                installation_name="different installation",
                installation_aliases=[],
                **changes,
            )
        ]
    )
    with importer.connect() as db:
        before = list(db.iterdump())
    with pytest.raises(ValueError, match="conflicting event ID"):
        importer.ingest(
            rows,
            existing=[
                dict(
                    module=module,
                    record_id="43",
                    event_date="2024-03-01",
                    country="GB",
                    installation_name="different installation",
                )
            ],
            stage="candidate",
        )
    with importer.connect() as db:
        assert list(db.iterdump()) == before
