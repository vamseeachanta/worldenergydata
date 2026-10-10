"""Shared catalog contract fixtures and evidence constructors."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "catalog_integration",
    ROOT / "src/worldenergydata/field_development/catalog_integration.py",
)


@pytest.fixture
def api():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def tamper_persisted_bundle(api, bundle, output):
    """Replace existing disposable fixture bytes and pins to probe reader semantics."""
    if not output.is_dir():
        raise ValueError("tampering requires an already validated fixture")
    for name, raw in api.storage._serialized_files(bundle).items():
        (output / name).write_bytes(raw)


@pytest.fixture
def inputs(tmp_path):
    legacy = tmp_path / "fields.csv"
    legacy.write_text(
        "FIELD_ID,FIELD_NAME,COUNTRY,BLOCK\n1,Cameia,Angola,Block 21\n"
        "2,Dalia,Angola,17\n2,Dalia,Angola,17\n"
        "2,Other,Angola,17\n3,Tombua Landana,Angola,Block 14\n",
        encoding="utf-8",
        newline="\n",  # LF on every OS: frozen catalog digests hash these bytes
    )
    parent = tmp_path / "sanctioned.csv"
    parent.write_text(
        "PROJECT,SOURCE_URL\nDalia,https://example.org/dalia\n",
        encoding="utf-8",
        newline="\n",
    )
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    rows = field_rows()
    tables = evidence_tables(rows)
    for name, records in tables.items():
        write_json(snapshot / (name + ".json"), records)
    manifest = {
        "dataset_id": "angola-field-development-evidence",
        "as_of": "2026-10-02",
        "files": [
            {
                "path": name + ".json",
                "record_count": len(records),
                "sha256": hashlib.sha256(
                    (snapshot / (name + ".json")).read_bytes()
                ).hexdigest(),
            }
            for name, records in tables.items()
        ],
        "inherited_cost_input": {
            "sha256": hashlib.sha256(parent.read_bytes()).hexdigest()
        },
    }
    write_json(snapshot / "manifest.json", manifest)
    return snapshot, legacy, parent


def reviewed_matrix(bundle):
    return [
        dict(
            row,
            decision="eligible_factual_derivative",
            basis="test factual derivative",
            reviewer="Vamsee",
            approval_ref="test owner decision",
            reviewed_sha256=row["sha256"],
        )
        for row in bundle["eligibility"]
    ]


def repin(out, name):
    path = out / "integration_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["output_hashes"][name] = hashlib.sha256(
        (out / name).read_bytes()
    ).hexdigest()
    write_json(path, manifest)


def field_rows():
    common = {
        "entity_type": "field",
        "country": "Angola",
        "development": "Unassigned",
        "current_configuration_verified": False,
        "source_ref": "s1",
        "source_vintage": "2004",
        "water_depth_scope": "development envelope",
    }
    rows = [
        dict(
            common,
            entity_id="ao-cameia",
            name="Cameia",
            block="20/11",
            water_depth_m=1700,
        ),
        dict(
            common,
            entity_id="ao-dalia",
            name="Dalia",
            block="17",
            water_depth_m={"min": 600, "max": 1200},
        ),
        dict(common, entity_id="ao-tombua", name="Tombua", block="14"),
        dict(
            common,
            entity_id="ao-phase",
            name="Mafumeira Sul",
            block="0",
            entity_type="development_phase",
        ),
    ]
    return rows


def evidence_tables(rows):
    tables = {
        "field_observations": rows,
        "sources": [{"source_ref": "s1", "url": "https://example.org/s1"}],
        "cost_observations": [
            {
                "cost_id": "c1",
                "entity_or_scope": "Dalia",
                "source_ref": "s1",
                "scope_type": "project",
                "unit": "USD billion",
                "value": 3.4,
                "field_allocation_permitted": False,
            }
        ],
        "milestone_observations": [
            {
                "subject": "Dalia",
                "event_date": "2004-01-01",
                "precision": "upper_bound_day",
                "source_ref": "s1",
                "scope": "field",
            },
            {
                "subject": "Landana North #1",
                "event_date": "2029-H1",
                "precision": "half_year",
                "source_ref": "s1",
                "scope": "well",
            },
        ],
        "inherited_cost_records": [
            {"project": "Dalia", "source_url": "https://example.org/dalia"}
        ],
    }
    return tables
