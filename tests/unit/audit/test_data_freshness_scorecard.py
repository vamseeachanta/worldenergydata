"""Tests for data freshness scorecard generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "audit"))

from data_freshness_scorecard import build_scorecard, main, write_markdown


def _write_project(root: Path, scheduler_status: str = "success") -> None:
    (root / "data" / "modules" / "bsee").mkdir(parents=True)
    (root / "data" / "modules" / "bsee" / "_metadata.json").write_text(
        json.dumps(
            {
                "last_refresh": "2026-06-01",
                "record_count": 12,
                "file_count": 2,
                "total_size_bytes": 100,
            }
        )
    )
    (root / "data" / "modules" / "bsee" / "manifest.json").write_text(
        json.dumps(
            {
                "last_success_ts": "2026-06-07T00:00:00+00:00",
                "refresh_interval_days": 7,
                "records_updated": 12,
                "status": scheduler_status,
            }
        )
    )
    (root / "module-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "modules": [
                    {
                        "id": "bsee",
                        "catalog_status": "sample",
                        "in_scheduler": True,
                        "public_cli": True,
                    },
                    {
                        "id": "texas_rrc",
                        "catalog_status": "runtime_fetched",
                        "in_scheduler": False,
                        "public_cli": True,
                    },
                ]
            }
        )
    )
    (root / "data" / "catalog.yaml").write_text(
        yaml.safe_dump(
            {
                "modules": {
                    "bsee": {
                        "datasets": [
                            {"name": "a", "row_count": 5},
                            {"name": "b", "row_count": 7},
                        ]
                    }
                }
            }
        )
    )


def test_build_scorecard_combines_manifest_catalog_and_metadata(tmp_path: Path):
    _write_project(tmp_path)

    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")

    bsee = scorecard["modules"]["bsee"]
    assert bsee["catalog_status"] == "sample"
    assert bsee["dataset_count"] == 2
    assert bsee["record_count"] == 12
    assert bsee["scheduler_last_success_ts"] == "2026-06-07T00:00:00+00:00"
    assert bsee["freshness_status"] == "fresh"

    texas = scorecard["modules"]["texas_rrc"]
    assert texas["dataset_count"] == 0
    assert texas["freshness_status"] == "missing"


def test_build_scorecard_rejects_non_success_scheduler_manifest(tmp_path: Path):
    _write_project(tmp_path, scheduler_status="failure")

    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")

    assert scorecard["modules"]["bsee"]["freshness_status"] == "stale"


def test_main_writes_json_and_markdown_outputs(tmp_path: Path):
    _write_project(tmp_path)
    report_path = tmp_path / "docs" / "reports" / "scorecard.md"
    json_path = tmp_path / "data" / "freshness-scorecard.json"

    rc = main(
        [
            "--project-root",
            str(tmp_path),
            "--date",
            "2026-06-08",
            "--report-output",
            str(report_path),
            "--json-output",
            str(json_path),
        ]
    )

    assert rc == 0
    assert json_path.exists()
    assert report_path.exists()
    assert "| bsee | sample | fresh | 2 | 12 |" in report_path.read_text()


def _declare_fixture(root: Path, module_id: str = "texas_rrc") -> Path:
    manifest_path = root / "module-manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    entry = next(row for row in manifest["modules"] if row["id"] == module_id)
    entry["fixture_catalog"] = "fixtures/synthetic.json"
    manifest_path.write_text(yaml.safe_dump(manifest))
    return root / entry["fixture_catalog"]


def _assert_fixture_consistency(root: Path, scorecard: dict) -> None:
    manifest = yaml.safe_load((root / "module-manifest.yaml").read_text())
    declarations = {
        row["id"]: row.get("fixture_catalog") for row in manifest["modules"]
    }
    for module_id, entry in scorecard["modules"].items():
        readiness = entry["fixture_readiness"]
        declaration = declarations.get(module_id)
        assert readiness == ("packaged" if declaration else "none"), module_id
        if readiness == "packaged":
            path = root / declaration
            assert path.exists(), module_id
            nonempty = (
                path.stat().st_size > 0 if path.is_file() else any(path.iterdir())
            )
            assert nonempty, module_id
    for module_id, declaration in declarations.items():
        if declaration:
            assert (
                scorecard["modules"][module_id]["fixture_readiness"] == "packaged"
            ), module_id


def test_fixture_readiness_is_independent_of_statuses_and_counts(tmp_path: Path):
    without = tmp_path / "without"
    with_fixture = tmp_path / "with"
    _write_project(without)
    _write_project(with_fixture)
    fixture = _declare_fixture(with_fixture)
    fixture.parent.mkdir()
    fixture.write_text('{"synthetic": true}\n')

    baseline = build_scorecard(without, report_date="2026-06-08")["modules"]
    packaged = build_scorecard(with_fixture, report_date="2026-06-08")["modules"]

    assert packaged["texas_rrc"]["fixture_readiness"] == "packaged"
    assert baseline["texas_rrc"]["fixture_readiness"] == "none"
    for module_id, entry in baseline.items():
        assert {k: v for k, v in entry.items() if k != "fixture_readiness"} == {
            k: v for k, v in packaged[module_id].items() if k != "fixture_readiness"
        }
    _assert_fixture_consistency(with_fixture, {"modules": packaged})


def test_packaged_synthetic_fixture_keeps_live_freshness_missing(tmp_path: Path):
    _write_project(tmp_path)
    fixture = _declare_fixture(tmp_path)
    fixture.parent.mkdir()
    fixture.write_text('{"synthetic": true}\n')
    manifest_path = tmp_path / "module-manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["modules"][1]["catalog_status"] = "not_applicable"
    manifest_path.write_text(yaml.safe_dump(manifest))

    entry = build_scorecard(tmp_path, report_date="2026-06-08")["modules"]["texas_rrc"]

    assert entry["fixture_readiness"] == "packaged"
    assert entry["catalog_status"] == "not_applicable"
    assert entry["freshness_status"] == "missing"
    assert entry["dataset_count"] == entry["record_count"] == 0


def test_missing_declared_fixture_consistency_names_module(tmp_path: Path):
    _write_project(tmp_path)
    _declare_fixture(tmp_path)
    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")

    assert scorecard["modules"]["texas_rrc"]["fixture_readiness"] == "none"
    with pytest.raises(AssertionError, match="texas_rrc"):
        _assert_fixture_consistency(tmp_path, scorecard)


@pytest.mark.parametrize("kind", ["file", "directory"])
@pytest.mark.parametrize("nonempty", [False, True])
def test_fixture_readiness_requires_nonempty_path(
    tmp_path: Path, kind: str, nonempty: bool
):
    _write_project(tmp_path)
    fixture = _declare_fixture(tmp_path)
    fixture.parent.mkdir()
    if kind == "directory":
        fixture.mkdir()
        if nonempty:
            (fixture / "synthetic.json").write_text("{}\n")
    else:
        fixture.write_text("{}\n" if nonempty else "")

    entry = build_scorecard(tmp_path, report_date="2026-06-08")["modules"]["texas_rrc"]

    assert entry["fixture_readiness"] == ("packaged" if nonempty else "none")


def _write_synthetic_landman_project(root: Path, declaration: dict) -> None:
    (root / "data").mkdir(parents=True)
    (root / "module-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "modules": [
                    {"id": "landman", "catalog_status": "not_applicable", **declaration}
                ]
            }
        )
    )
    (root / "data" / "catalog.yaml").write_text(
        yaml.safe_dump({"modules": {"landman": {"datasets": []}}})
    )
    fixture = root / "fixtures" / "synthetic.json"
    fixture.parent.mkdir()
    fixture.write_text('{"synthetic": true}\n')


@pytest.mark.parametrize(
    ("kind", "expected_readiness"),
    [
        ("absent", "none"),
        ("empty", "none"),
        ("null", "none"),
        ("boolean", "none"),
        ("list", "none"),
        ("mapping", "none"),
        ("missing", "none"),
        ("absolute-file", "none"),
        ("absolute-directory", "none"),
        ("parent-traversal", "none"),
        ("embedded-parent-traversal", "none"),
        ("relative", "packaged"),
    ],
)
def test_landman_fixture_declarations_keep_live_freshness_missing(
    tmp_path: Path, kind: str, expected_readiness: str
) -> None:
    """Use the date from test_packaged_synthetic_fixture_keeps_live_freshness_missing."""
    root = tmp_path / "repository"
    sentinel = tmp_path / "sibling" / "synthetic.json"
    sentinel.parent.mkdir()
    sentinel.write_text('{"synthetic": true}\n')
    relative = Path("fixtures") / "synthetic.json"
    traversal = Path("..") / sentinel.relative_to(tmp_path)
    declarations = {
        "empty": "",
        "null": None,
        "boolean": True,
        "list": [str(relative)],
        "mapping": {"path": str(relative)},
        "missing": str(relative.with_name("missing.json")),
        "absolute-file": str(sentinel),
        "absolute-directory": str(sentinel.parent),
        "parent-traversal": str(traversal),
        "embedded-parent-traversal": str(Path("fixtures") / ".." / traversal),
        "relative": str(relative),
    }
    declaration = {} if kind == "absent" else {"fixture_catalog": declarations[kind]}
    _write_synthetic_landman_project(root, declaration)
    if kind in {
        "absolute-file",
        "absolute-directory",
        "parent-traversal",
        "embedded-parent-traversal",
        "relative",
    }:
        target = root / declaration["fixture_catalog"]
        assert target.exists()
        assert target.read_bytes() if target.is_file() else list(target.iterdir())

    entry = build_scorecard(root, report_date="2026-06-08")["modules"]["landman"]

    assert entry["fixture_readiness"] == expected_readiness
    assert entry["catalog_status"] == "not_applicable"
    assert entry["freshness_status"] == "missing"
    # Hand calculation: no datasets and the sum of no row counts both yield zero.
    assert entry["dataset_count"] == entry["record_count"] == 0


def test_generated_scorecard_fixture_consistency(tmp_path: Path):
    """Repository inputs are read; generated output stays in the temporary tree."""
    root = Path(__file__).resolve().parents[3]
    scorecard = build_scorecard(root, report_date="2026-06-08")
    write_markdown(scorecard, tmp_path / "scorecard.md")

    for module_id, entry in scorecard["modules"].items():
        assert entry["fixture_readiness"] in {"packaged", "none"}, module_id
    _assert_fixture_consistency(root, scorecard)


def test_committed_scorecard_row_schema_and_fixture_consistency():
    """Legacy row keys match scorecard commit 632f2a93e0cd0d38d15d0da7314cc87ce783b306."""
    root = Path(__file__).resolve().parents[3]
    scorecard = json.loads((root / "data/freshness-scorecard.json").read_text())
    legacy_keys = frozenset(
        {
            "module",
            "catalog_status",
            "freshness_status",
            "in_scheduler",
            "public_cli",
            "dataset_count",
            "record_count",
            "last_refresh",
            "scheduler_last_success_ts",
            "refresh_interval_days",
        }
    )
    fixture_keys = legacy_keys | {"fixture_readiness"}
    row_schemas = {frozenset(entry) for entry in scorecard["modules"].values()}

    assert row_schemas in ({legacy_keys}, {fixture_keys})
    if row_schemas == {fixture_keys}:
        _assert_fixture_consistency(root, scorecard)


def test_markdown_has_fixture_readiness_value_per_row(tmp_path: Path):
    _write_project(tmp_path)
    fixture = _declare_fixture(tmp_path)
    fixture.parent.mkdir()
    fixture.write_text("{}\n")
    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")
    output = tmp_path / "scorecard.md"

    write_markdown(scorecard, output)

    rows = [
        line.split("|")[1:-1]
        for line in output.read_text().splitlines()
        if line.startswith("|")
    ]
    headers = [cell.strip() for cell in rows[0]]
    assert "Fixture Readiness" in headers
    index = headers.index("Fixture Readiness")
    assert len(rows[2:]) == scorecard["module_count"]
    for row, module_id in zip(rows[2:], sorted(scorecard["modules"])):
        assert len(row) == len(headers)
        assert (
            row[index].strip() == scorecard["modules"][module_id]["fixture_readiness"]
        )


def test_markdown_defaults_legacy_rows_to_none(tmp_path: Path) -> None:
    """Rows without fixture readiness render none in the last column."""
    scorecard = {
        "report_date": "2026-06-08",
        "modules": {
            module: {
                "catalog_status": "sample",
                "freshness_status": "missing",
                "dataset_count": 0,
                "record_count": 0,
            }
            for module in ("alpha", "beta")
        },
    }
    output = tmp_path / "legacy.md"

    write_markdown(scorecard, output)

    rows = output.read_text().splitlines()[4:]
    assert len(rows) == len(scorecard["modules"])
    assert all(row.split("|")[-2].strip() == "none" for row in rows)


def test_markdown_writes_committed_scorecard(tmp_path: Path) -> None:
    """The committed scorecard is rendered without rewriting its source."""
    root = Path(__file__).resolve().parents[3]
    scorecard = json.loads((root / "data/freshness-scorecard.json").read_text())
    output = tmp_path / "committed.md"

    write_markdown(scorecard, output)

    rows = output.read_text().splitlines()[4:]
    assert len(rows) == len(scorecard["modules"])
    for row, module in zip(rows, sorted(scorecard["modules"])):
        expected = scorecard["modules"][module].get("fixture_readiness", "none")
        assert row.split("|")[-2].strip() == expected


def test_markdown_preserves_packaged_readiness(tmp_path: Path) -> None:
    """An explicit packaged value remains packaged in the last column."""
    _write_project(tmp_path)
    fixture = _declare_fixture(tmp_path)
    fixture.parent.mkdir()
    fixture.write_text("{}\n")
    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")
    output = tmp_path / "packaged.md"

    write_markdown(scorecard, output)

    rows = output.read_text().splitlines()[4:]
    row = next(row for row in rows if row.split("|")[1].strip() == "texas_rrc")
    assert row.split("|")[-2].strip() == "packaged"
