"""Run a synthetic exact-ID catalog example in a new, caller-chosen directory."""

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "catalog_integration",
    ROOT / "src/worldenergydata/field_development/catalog_integration.py",
)
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


def write_json(path, value):
    path.write_text(API.canonical(value) + "\n", encoding="utf-8")


def synthetic_tables():
    """Authored inputs only: no research observations or physical coefficients.

    Types and the upper-bound date interpretation follow issue 1144, final
    dispositions, and data/modules/offshore_assets/schema.yaml. The example date
    is a synthetic calendar value, not an asserted production date.
    """
    common = {
        "country": "Angola",
        "development": "Example development",
        "source_ref": "example",
        "block": "",
        "current_configuration_verified": False,
    }
    return {
        "sources": [
            {"source_ref": "example", "url": "https://example.org/catalog-evidence"}
        ],
        "field_observations": [
            dict(
                common,
                entity_id="example-field",
                name="Example field",
                entity_type="field",
            ),
            dict(
                common,
                entity_id="example-phase",
                name="Example phase",
                entity_type="phase",
            ),
        ],
        "milestone_observations": [
            {
                "subject": "Example field",
                "scope": "field",
                "source_ref": "example",
                "event_date": "2004-01-01",
                "precision": "upper_bound_day",
            }
        ],
        "cost_observations": [],
        "inherited_cost_records": [],
    }


def create_inputs(directory):
    snapshot = directory / "snapshot"
    snapshot.mkdir()
    tables = synthetic_tables()
    for table, rows in tables.items():
        write_json(snapshot / (table + ".json"), rows)
    legacy, parent = directory / "fields.csv", directory / "parents.csv"
    legacy.write_text(
        "FIELD_ID,FIELD_NAME,COUNTRY,BLOCK\nexample,Example field,Angola,\n",
        encoding="utf-8",
        newline="\n",
    )
    parent.write_text("PROJECT,SOURCE_URL\n", encoding="utf-8", newline="\n")
    write_json(
        snapshot / "manifest.json",
        {
            "dataset_id": "angola-field-development-evidence",
            "files": [
                {
                    "path": table + ".json",
                    "record_count": len(rows),
                    "sha256": API.digest_bytes(
                        (snapshot / (table + ".json")).read_bytes()
                    ),
                }
                for table, rows in tables.items()
            ],
            "inherited_cost_input": {"sha256": API.digest_bytes(parent.read_bytes())},
        },
    )
    return snapshot, legacy, parent


def run(directory):
    directory = Path(directory)
    directory.mkdir(parents=True)  # Existing destinations must never be overwritten.
    inputs = create_inputs(directory)
    API.write_bundle(API.build_integration(*inputs), directory / "bundle")
    bundle = API.read_bundle(directory / "bundle")
    reader = API.CatalogEvidence(bundle)
    view = reader.entity("angola-field-development-evidence:example-field")
    write_json(directory / "field-evidence.json", view)
    milestone = next(
        r for r in view["records"] if r["table"] == "milestone_observations"
    )
    fields = sum(e["entity_type"] == "field" for e in bundle["entities"])
    result = {
        "state": bundle["manifest"]["state"],
        "registered_fields": fields,
        "registered_nonfields": len(bundle["entities"]) - fields,
        "accepted_legacy_groups": len(view["legacy_groups"]),
        "field_record_groups": len(view["records"]),
        "milestone_precision": milestone["observation"]["precision"],
        "source_urls": [s["url"] for s in view["sources"]],
    }
    write_json(directory / "answer.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))


if __name__ == "__main__":
    main()
