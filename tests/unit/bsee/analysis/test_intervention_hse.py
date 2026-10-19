"""Reusable intake tests; all rows are synthetic and remain test-local."""

import hashlib
import sqlite3

import pytest

from worldenergydata.bsee.analysis import intervention_hse as hse


@pytest.fixture
def database(tmp_path):
    """Minimal schema from Phase 1A exploration's hse_incidents_profile queries."""
    path = tmp_path / "incidents # sample.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE hse_incidents "
            "(id INTEGER PRIMARY KEY, description TEXT, incident_type TEXT, "
            "operator TEXT, lease_number TEXT)"
        )
        connection.executemany(
            "INSERT INTO hse_incidents VALUES (?, ?, ?, ?, ?)",
            [
                (2, None, "injury", "private label", "private key"),
                (1, "wireline work", "violation", "private label", "private key"),
            ],
        )
    return path


def test_loader_is_read_only_ordered_and_projects_only_classifier_fields(database):
    """Hand inventory: two inserted IDs sort as 1, 2; private columns excluded."""
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    rows = hse.load_hse_incidents(database)
    assert [row.record_id for row in rows] == ["1", "2"]
    assert rows[0].classifier_fields() == {
        "description": "wireline work",
        "incident_type": "violation",
    }
    assert rows[1].classifier_fields() == {"incident_type": "injury"}
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        hse.load_hse_incidents(path)
    assert not path.exists()


def test_missing_table_is_not_an_empty_dataset(tmp_path):
    path = tmp_path / "empty.db"
    sqlite3.connect(path).close()
    with pytest.raises(ValueError, match="schema"):
        hse.load_hse_incidents(path)


def test_missing_required_column_is_not_silently_dropped(tmp_path):
    path = tmp_path / "wrong.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE hse_incidents (id INTEGER)")
    with pytest.raises(ValueError, match="schema"):
        hse.load_hse_incidents(path)


def test_empty_valid_table_returns_empty_tuple(database):
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM hse_incidents")
    assert hse.load_hse_incidents(database) == ()


def test_accident_type_keeps_distinct_source_semantics(database):
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE hse_incidents ADD COLUMN accident_type TEXT")
        connection.execute(
            "UPDATE hse_incidents SET accident_type='Blowout' WHERE id=1"
        )
    row = hse.load_hse_incidents(database)[0]
    assert row.classifier_fields()["accident_type"] == "Blowout"
    assert row.classifier_fields()["incident_type"] == "violation"


def test_bridge_uses_existing_direct_mapping_without_exposing_raw_text():
    """Taxonomy activity_definitions.py (2026), DRILL maps BLOWOUT.

    Expected confidence is the existing heuristic CONFIDENCE_DIRECT_CODE,
    not an independently validated probability or a population regression.
    """
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        CONFIDENCE_DIRECT_CODE,
        IncidentClassifier,
    )

    incident = hse.HseIncident("a", None, "violation", "Blowout")
    results = hse.classify_incidents(
        [incident], source="bsee", classifier=IncidentClassifier()
    )
    assert len(results) == 1
    assert results[0].record_id == "a"
    assert results[0].activity == "DRILL"
    assert results[0].confidence == CONFIDENCE_DIRECT_CODE
    assert results[0].match_method == "bsee_accident_type"
    assert "Blowout" not in repr(results[0])


def test_bridge_keeps_empty_text_as_unknown():
    """Existing classifier default maps a record without evidence to OTHER."""
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        IncidentClassifier,
    )

    results = hse.classify_incidents(
        [hse.HseIncident("a", None, None)],
        source="bsee",
        classifier=IncidentClassifier(),
    )
    assert results[0].activity == "OTHER"
    assert results[0].match_method == "default"


def test_bridge_rejects_unknown_source_even_for_empty_input():
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        IncidentClassifier,
    )

    with pytest.raises(ValueError, match="source"):
        hse.classify_incidents([], source="unverified", classifier=IncidentClassifier())


def test_bridge_rejects_duplicate_records():
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        IncidentClassifier,
    )

    row = hse.HseIncident("same", None, None)
    with pytest.raises(ValueError, match="unique"):
        hse.classify_incidents(
            [row, row], source="bsee", classifier=IncidentClassifier()
        )


def classified_rows(activity, size):
    """Synthetic labels; confidence unused, not an engineering input."""
    return [
        hse.ClassifiedIncident(str(i), activity, "unknown", 0.0, "default")
        for i in range(size)
    ]


@pytest.mark.parametrize(
    "size, expected", [(0, ()), (4, ()), (5, (("DRILL", 5),)), (6, (("DRILL", 6),))]
)
def test_activity_counts_suppress_small_cells(size, expected):
    """Hand calculation: N repeated DRILL records give count N.

    For N=0 or 4 publish nothing; N=5 or 6 publish N. Threshold source:
    docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md,
    Operator Aggregation Contract, rule 2 (2026). No rates are calculated.
    """
    result = hse.count_activity_patterns(classified_rows("DRILL", size))
    assert tuple((cell.activity, cell.count) for cell in result) == expected


def test_counts_expose_neither_suppressed_labels_nor_population_totals():
    """Hand count: five DRILL + four PERS; release only DRILL=5, not total=9."""
    rows = classified_rows("DRILL", 5) + [
        hse.ClassifiedIncident(f"p{i}", "PERS", "unknown", 0.0, "default")
        for i in range(4)
    ]
    result = hse.count_activity_patterns(rows)
    assert len(result) == 1
    assert vars(result[0]) == {"activity": "DRILL", "count": 5}


def test_counts_reject_non_taxonomy_labels():
    with pytest.raises(ValueError, match="activity"):
        hse.count_activity_patterns(classified_rows("private label", 5))


def test_counts_reject_duplicate_ids():
    row = classified_rows("DRILL", 1)[0]
    with pytest.raises(ValueError, match="unique"):
        hse.count_activity_patterns([row] * 5)


def test_loader_rejects_null_and_duplicate_ids(tmp_path):
    path = tmp_path / "ids.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE hse_incidents (id, description, incident_type)"
        )
        connection.execute("INSERT INTO hse_incidents VALUES (NULL, NULL, NULL)")
    with pytest.raises(ValueError, match="present"):
        hse.load_hse_incidents(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM hse_incidents")
        connection.executemany(
            "INSERT INTO hse_incidents VALUES (?, NULL, NULL)", [("same",), ("same",)]
        )
    with pytest.raises(ValueError, match="unique"):
        hse.load_hse_incidents(path)


def test_intake_classifier_and_counts_work_together(database):
    """Hand inventory: five distinct Blowout rows map to DRILL, count=5.

    Mapping source: taxonomy/activity_definitions.py (2026), DRILL's BSEE
    accident types. Release minimum: Operator Aggregation Contract rule 2,
    issue-416 plan (2026). This checks plumbing, not classifier accuracy.
    """
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        IncidentClassifier,
    )

    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM hse_incidents")
        connection.execute("ALTER TABLE hse_incidents ADD COLUMN accident_type TEXT")
        connection.executemany(
            "INSERT INTO hse_incidents (id, accident_type) VALUES (?, 'Blowout')",
            [(i,) for i in range(5)],
        )
    classified = hse.classify_incidents(
        hse.load_hse_incidents(database), source="bsee", classifier=IncidentClassifier()
    )
    assert hse.count_activity_patterns(classified) == (hse.ActivityCount("DRILL", 5),)
