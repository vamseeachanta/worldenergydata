"""Validate curated-table citations and report unresolved source evidence.

The citation fields follow issue #1262: document, edition, and table or clause.
This audit reads metadata only. It cannot verify correspondence to an extraction
or grant permission to redistribute values. No engineering equations are used.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data/modules/metocean"
CITATION_FIELDS = ("source_document", "edition", "table_or_clause")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_mapping(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "Metadata has duplicate mapping keys")
        result[key] = value
    return result


class _UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of discarding earlier declarations."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        pairs = [
            (
                self.construct_object(key, deep=deep),
                self.construct_object(value, deep=deep),
            )
            for key, value in node.value
        ]
        try:
            return _unique_mapping(pairs)
        except TypeError as error:
            raise ValueError("Invalid metadata mapping key") from error


def _read_json(path: Path) -> object:
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_unique_mapping
    )


def _entries(content: object, key: str) -> list[dict]:
    _require(isinstance(content, dict), "Invalid catalogue object")
    entries = content.get(key)
    _require(isinstance(entries, list), "Invalid catalogue inventory")
    _require(all(isinstance(row, dict) for row in entries), "Invalid catalogue entry")
    return entries


def _validate_record(record: object) -> list[str]:
    _require(isinstance(record, dict), "Invalid source record")
    _require(
        _text(record.get("source_document")), "Missing source document attribution"
    )
    for field in CITATION_FIELDS:
        value = record.get(field)
        _require(field in record, "Missing citation field")
        _require(value is None or _text(value), "Invalid citation field")
    missing = [field for field in CITATION_FIELDS if record[field] is None]
    evidence = record.get("evidence")
    _require(isinstance(evidence, list) and bool(evidence), "Missing source evidence")
    for item in evidence:
        _require(isinstance(item, dict), "Invalid source evidence")
        _require(
            all(_text(item.get(key)) for key in ("path", "revision", "scope")),
            "Incomplete source evidence",
        )
        path = item["path"]
        _require(
            "\\" not in path
            and ":" not in path
            and all(part not in ("", ".", "..") for part in path.split("/")),
            "Evidence must use a forward-slash repository-relative path",
        )
        _require(
            re.fullmatch(r"[0-9a-f]{40}", item["revision"]) is not None,
            "Evidence requires a full repository revision",
        )
    status = record.get("verification_status")
    _require(status in ("NOT_EVALUATED", "VERIFIED"), "Unknown verification status")
    if status == "VERIFIED":
        _require(not missing, "Verified citation is incomplete")
        _require(
            record.get("attribution_status") == "publication_citation"
            and record.get("decision_status") == "resolved",
            "Verified citation requires publication attribution and a resolved decision",
        )
    else:
        _require(
            record.get("attribution_status")
            in ("repository_attribution_only", "publication_citation"),
            "Unknown attribution status",
        )
        _require(
            record.get("decision_status") == "maintainer_decision_required",
            "Unevaluated source requires a maintainer decision",
        )
        _require(
            _text(record.get("reason")) and _text(record.get("required_evidence")),
            "Unevaluated source requires a reason and required evidence",
        )
    return missing


def audit_sources(data_dir: Path = DEFAULT_DATA) -> dict:
    """Return a deterministic decision queue, rejecting inconsistent metadata.

    VERIFIED is a recorded human assessment, never inferred from filled fields.
    CITATIONS_RECORDED describes metadata, not engineering or rights approval.
    """
    sidecar = _read_json(data_dir / "table_sources.json")
    _require(isinstance(sidecar, dict), "Invalid source sidecar")
    tables = sidecar.get("tables")
    _require(
        isinstance(tables, dict) and bool(tables), "Empty or invalid source inventory"
    )
    _require(
        all(
            _text(name) and Path(name).name == name and name.endswith(".csv")
            for name in tables
        ),
        "Invalid source inventory filename",
    )
    metadata = _read_json(data_dir / "_metadata.json")
    loader = _UniqueLoader((data_dir / "schema.yaml").read_text(encoding="utf-8"))
    try:
        schema = loader.get_single_data()
    finally:
        loader.dispose()
    external = _entries(metadata, "external_datasets")
    datasets = [
        row for row in _entries(schema, "datasets") if row.get("distributed") is False
    ]
    for entries in (external, datasets):
        names = [row.get("name") for row in entries]
        _require(all(_text(name) for name in names), "Invalid catalogue name")
        _require(len(names) == len(set(names)), "Catalogue has duplicate names")
        _require(set(names) == set(tables), "Catalogue and source inventory differ")
        for row in entries:
            _require(
                row.get("source_record") == f"table_sources.json#/tables/{row['name']}",
                "Catalogue source_record does not resolve to its table",
            )
    decisions = []
    for name, record in sorted(tables.items()):
        missing = _validate_record(record)
        if record["verification_status"] == "NOT_EVALUATED":
            decisions.append({**record, "name": name, "missing_fields": missing})
    return {
        "status": "NOT_EVALUATED" if decisions else "CITATIONS_RECORDED",
        "table_count": len(tables),
        "verified_citation_count": len(tables) - len(decisions),
        "maintainer_decisions": decisions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--require-citations", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit_sources(args.data_dir)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError):
        # Parser exceptions may contain source values or absolute input paths.
        print(
            json.dumps(
                {
                    "status": "INVALID",
                    "error": "Source metadata is unreadable or inconsistent",
                }
            )
        )
        return 2
    print(json.dumps(report, indent=2))
    return int(args.require_citations and bool(report["maintainer_decisions"]))


if __name__ == "__main__":
    raise SystemExit(main())
