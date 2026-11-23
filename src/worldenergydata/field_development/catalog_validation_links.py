"""Evidence dependencies and exact content closure."""

import importlib.util
from pathlib import Path

if __package__:
    from . import catalog_validation_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_validation_common",
        Path(__file__).with_name("catalog_validation_common.py"),
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)

require = common.require
unique = common.unique
fingerprint = common.fingerprint


def validate_parent_reference(row, parent_ids, parents):
    require(
        row.get("link_status") == "parent_reference"
        and row.get("parent_record_id") in parent_ids
        and row["parent_record_id"] in row["dependencies"],
        "inherited cost missing parent reference",
    )
    parent = parents[row["parent_record_id"]]
    require(
        parent.get("table") == "parent_reference"
        and row.get("parent_row_fingerprint") == parent.get("sha256")
        and parent["record_id"] == "sanctioned_projects:row:" + parent["sha256"],
        "inherited parent fingerprint mismatch",
    )


def validate_links(bundle, entity_ids, source_ids):
    records = bundle["links"]["records"]
    ids = unique(records, "record_id")
    parent_ids = unique(bundle["links"]["parent_references"], "record_id")
    parents = {r["record_id"]: r for r in bundle["links"]["parent_references"]}
    for row in records:
        require(
            row.get("entity_id") is None or row["entity_id"] in entity_ids,
            "dangling entity foreign key",
        )
        require(set(row["dependencies"]) <= ids | parent_ids, "dangling dependency")
        require(
            type(row["multiplicity"]) is int and row["multiplicity"] > 0,
            "invalid record multiplicity",
        )
        if row["table"] == "inherited_cost_records":
            validate_parent_reference(row, parent_ids, parents)
        elif row["table"] != "sources":
            require(
                any(
                    d in ids
                    and d.startswith(bundle["manifest"]["dataset_id"] + ":sources:")
                    for d in row["dependencies"]
                ),
                "missing source dependency",
            )
    for entity in bundle["entities"]:
        require(
            entity["evidence_record_id"] in ids and entity["source_ref"] in source_ids,
            "dangling entity evidence/source",
        )
    return ids


def expected_records(bundle):
    expected = {}
    dataset = bundle["manifest"]["dataset_id"]
    for table, rows in bundle["evidence"].items():
        for row in rows:
            explicit = next(
                (
                    row[k]
                    for k in ("entity_id", "cost_id", "source_ref")
                    if k in row and (k != "source_ref" or table == "sources")
                ),
                None,
            )
            identifier = f"{dataset}:{table}:{explicit or fingerprint(row)}"
            digest = fingerprint(row)
            prior, count = expected.get(identifier, (digest, 0))
            require(prior == digest, "evidence identity collision")
            expected[identifier] = (digest, count + 1)
    return expected


def validate_record_closure(bundle):
    expected = expected_records(bundle)
    records = bundle["links"]["records"]
    actual = {r["record_id"]: (r["sha256"], r["multiplicity"]) for r in records}
    require(actual == expected, "evidence/link content closure mismatch")
    require(
        bundle["manifest"]["supplemental_entity_count"]
        == sum(bool(e.get("supplemental")) for e in bundle["entities"]),
        "supplemental count mismatch",
    )
    require(
        bundle["manifest"]["legacy_row_count"]
        == sum(r["multiplicity"] for r in bundle["ledger"]),
        "legacy count mismatch",
    )
    require(
        bundle["manifest"]["decision_sha256"] == fingerprint(bundle["match_decisions"]),
        "decision digest mismatch",
    )
    require(
        bundle["manifest"]["eligibility_sha256"] == fingerprint(bundle["eligibility"]),
        "eligibility digest mismatch",
    )
