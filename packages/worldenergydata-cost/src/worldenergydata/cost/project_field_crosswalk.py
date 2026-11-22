"""Offline cost-register locators joined to held field-development identities.

Identity links retain the original project scope. They neither allocate costs
nor establish equivalence between project and field accounting boundaries.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

COST = Path("data/modules/cost")
CURATED = COST / "curated"
CROSSWALK = CURATED / "project_field_crosswalk.csv"
MANIFEST = CURATED / "project_field_crosswalk.manifest.json"
CATALOG = Path("src/worldenergydata/field_development/past_projects.yml")
FIELD_IDENTITIES = Path("config/fields.yml")
IDENTITIES = CURATED / "cost_project_identity.csv"
REGISTER_TABLES = (
    "sanctioned_projects.csv",
    "contract_awards.csv",
    "project_cost_statements.csv",
    "cost_revision_trails.csv",
)
COLUMNS = (
    "PROJECT_ID",
    "COST_PROJECT_ID",
    "PROJECT",
    "CATALOG_FIELD_ID",
    "MATCH_METHOD",
    "CONFIDENCE",
    "PROVENANCE",
    "EVIDENCE",
    "REASON",
)
LIMITATION = "Field identity only; project scope retained; no cost allocation or scope equivalence."


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _norm(value):
    return " ".join((value or "").split()).casefold()


def read_csv(path):
    """Decode BOM-tolerant CSV and reject ambiguous headers or row widths."""
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            header, rows = reader.fieldnames, list(reader)
    except csv.Error as error:
        raise ValueError(f"invalid CSV: {Path(path).name}") from error
    _require(header and len(header) == len(set(header)), "invalid CSV header")
    _require(all(h and h == h.strip() for h in header), "invalid CSV header")
    _require(
        all(None not in r and None not in r.values() for r in rows),
        "invalid CSV row width",
    )
    _require(
        all(
            re.sub(r"[^A-Z0-9]", "", h.upper())
            not in {"PROJECT", "PROJECTID", "PROJECTNAME"}
            or h in {"PROJECT", "PROJECT_ID"}
            for h in header
        ),
        "invalid CSV PROJECT header",
    )
    return header, rows


def _project_tables(root):
    tables = {}
    for lane in ("curated", "staging"):
        for path in sorted((root / COST / lane).rglob("*.csv")):
            relative = path.relative_to(root)
            if relative == CROSSWALK:
                continue
            header, rows = read_csv(path)
            if {"PROJECT", "PROJECT_ID"} & set(header):
                tables[relative.as_posix()] = (header, rows)
    return tables


def _controlled_names(root, tables):
    """Resolve active opaque references using curated source locators only."""
    path = root / IDENTITIES
    if not path.exists():
        return {}
    _, rows = read_csv(path)
    result, names = {}, set()
    for row in rows:
        if not (
            row.get("ACTIVE") == "true"
            and row.get("STATE") == "active"
            and row.get("ENTITY_KIND") == "project"
            and not row.get("TOMBSTONED_BY_ID")
        ):
            continue
        table, locator, identity = (
            row.get(k, "")
            for k in ("SOURCE_TABLE", "SOURCE_RECORD_LOCATOR", "OPAQUE_ID")
        )
        _require(
            table
            and Path(table).name == table
            and "/" not in table
            and "\\" not in table,
            "invalid project identity source table",
        )
        _require(
            locator.startswith("PROJECT=") and identity,
            "invalid project identity locator",
        )
        name = locator.removeprefix("PROJECT=")
        source = tables.get((CURATED / table).as_posix(), ([], []))[1]
        _require(
            any(r.get("PROJECT") == name for r in source),
            "missing project identity source",
        )
        _require(
            identity not in result and name not in names, "duplicate project identity"
        )
        result[identity] = name
        names.add(name)
    return result


def _blocks(value):
    blocks = {b.strip().upper() for b in (value or "").split(";") if b.strip()}
    _require(
        all(re.fullmatch(r"[A-Z]{2}\d{3}", b) for b in blocks),
        "invalid structured block",
    )
    return blocks


def load_cost_projects(root):
    """Inventory all curated/staging projects using exact PROJECT natural keys.

    PROJECT:<label> is a source locator, not an issued opaque identity. A rename
    changes it. Repeated observations share the exact label, as in portfolio_trace.
    Controlled references are decoded before the same natural-key grouping.
    """
    root = Path(root)
    tables = _project_tables(root)
    controlled = _controlled_names(root, tables)
    controlled_by_name = {name: identity for identity, name in controlled.items()}
    projects = {}
    for table, (header, rows) in tables.items():
        for row in rows:
            name, reference = row.get("PROJECT"), row.get("PROJECT_ID", "")
            if "PROJECT" in header:
                _require(name and name.strip() == name, "invalid CSV project name")
            if reference:
                _require(
                    reference in controlled,
                    "unknown project ID reference: " + reference,
                )
                _require(
                    name is None or name == controlled[reference],
                    "project ID/name mismatch",
                )
                name = controlled[reference]
            _require(name, "invalid CSV empty project reference")
            project = projects.setdefault(
                name,
                dict(
                    project_id="PROJECT:" + name,
                    cost_project_id=controlled_by_name.get(name, ""),
                    name=name,
                    sources=[],
                    operators=set(),
                    blocks=set(),
                ),
            )
            key = "PROJECT" if "PROJECT" in header else "PROJECT_ID"
            project["sources"].append(f"{table}#{key}={row[key]}")
            if row.get("OPERATOR"):
                project["operators"].add(_norm(row["OPERATOR"]))
            single, multiple = (
                _blocks(row.get("BLOCK", "")),
                _blocks(row.get("BLOCKS", "")),
            )
            _require(
                not single or not multiple or single == multiple,
                "conflicting structured blocks",
            )
            project["blocks"].update(multiple or single)
    for project in projects.values():
        operators = project.pop("operators")
        project["operator"] = next(iter(operators)) if len(operators) == 1 else ""
        project["blocks"] = sorted(project["blocks"])
        project["sources"] = sorted(set(project["sources"]))
    return [projects[name] for name in sorted(projects)]


def load_catalog(root):
    """Use catalog IDs/attributes and canonical held aliases; reject YAML drift."""
    import yaml

    root = Path(root)
    identities = yaml.safe_load((root / FIELD_IDENTITIES).read_text(encoding="utf-8"))[
        "fields"
    ]
    raw_catalog = yaml.safe_load((root / CATALOG).read_text(encoding="utf-8"))
    canonical = {r["canonical_id"]: r for r in identities}
    _require(len(canonical) == len(identities), "duplicate canonical field ID")
    fields = []
    for region in raw_catalog["regions"].values():
        for row in region.get("projects") or []:
            identity = canonical.get(row["project_id"])
            _require(identity is not None, "unknown catalog field ID")
            _require(
                identity["display_name"] == row["display_name"],
                "catalog field name drift",
            )
            _require(
                set(identity["bsee"]["area_blocks"]) == set(row["bsee_area_blocks"]),
                "catalog field blocks drift",
            )
            fields.append(
                dict(
                    field_id=row["project_id"],
                    name=row["display_name"],
                    aliases=identity.get("aliases") or [],
                    operator=row["operator"],
                    blocks=sorted(_blocks(";".join(row["bsee_area_blocks"]))),
                )
            )
    _unique_index(fields, "field_id", "field")
    _require(
        {f["field_id"] for f in fields} == set(canonical), "catalog field ID set drift"
    )
    return fields


def match_project(project, fields):
    """Return one deterministic candidate or an explicit unresolved reason.

    Matching is intentionally stricter than canonical punctuation-insensitive
    field resolution: scope-bearing project labels are not rewritten.
    """
    name = _norm(project["name"])
    rules = (
        ("exact_name", "high", lambda f: name == _norm(f["name"])),
        ("alias", "high", lambda f: name in {_norm(a) for a in f.get("aliases", [])}),
    )
    for method, confidence, predicate in rules:
        candidates = [f["field_id"] for f in fields if name and predicate(f)]
        if candidates:
            return _match_result(candidates, method, confidence, project["name"])
    operator, blocks = _norm(project.get("operator")), set(project.get("blocks", []))
    scope_label = re.search(r"\b(phase|cluster|bundle|infill)\b|[/+&]", name)
    if operator and blocks and not scope_label:
        candidates = [
            f["field_id"]
            for f in fields
            if operator == _norm(f.get("operator"))
            and blocks == set(f.get("blocks", []))
        ]
        if candidates:
            return _match_result(
                candidates, "operator_block", "medium", project["name"]
            )
    return _match_result([], "unmatched", "low", project["name"])


def _match_result(candidates, method, confidence, name):
    if len(candidates) == 1:
        return dict(
            field_ids=candidates, method=method, confidence=confidence, reason=""
        )
    reason = (
        "Ambiguous catalog candidates; manual evidence required: "
        + ", ".join(sorted(candidates))
        if candidates
        else "No exact name, held alias or unique operator/full-block match in catalog for "
        + name
    )
    return dict(field_ids=[], method="unmatched", confidence="low", reason=reason)


def _unique_index(rows, key, kind):
    index = {}
    for row in rows:
        identity = row[key]
        _require(
            identity and identity not in index, "duplicate or empty " + kind + " ID"
        )
        index[identity] = row
    return index


def _evidence(row, project):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "duplicate evidence key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("non-finite evidence constant: " + value)

    try:
        evidence = json.loads(
            row["EVIDENCE"],
            object_pairs_hook=unique_pairs,
            parse_constant=reject_constant,
        )
    except (ValueError, TypeError) as error:
        raise ValueError("invalid evidence JSON") from error
    _require(isinstance(evidence, dict), "invalid evidence object")
    _require(
        evidence.get("project_sources") == sorted(project.get("sources", [])),
        "evidence project source mismatch",
    )
    expected = [row["CATALOG_FIELD_ID"]] if row["CATALOG_FIELD_ID"] else []
    _require(evidence.get("catalog_fields") == expected, "evidence field mismatch")
    _require(
        isinstance(evidence.get("basis"), str) and evidence["basis"].strip(),
        "missing evidence basis",
    )
    if expected:
        _require(
            isinstance(evidence.get("limitation"), str)
            and evidence["limitation"].startswith(LIMITATION),
            "missing evidence scope limitation",
        )
    unmapped = evidence.get("unmapped_scope", [])
    _require(
        isinstance(unmapped, list)
        and all(isinstance(s, str) and s.strip() for s in unmapped),
        "invalid evidence unmapped scope",
    )
    if unmapped and expected:
        _require(
            all(s in evidence["limitation"] for s in unmapped),
            "unmapped scope missing from limitation",
        )
    return evidence


def validate_crosswalk(rows, projects, fields):
    """Reject invalid joins and require a mapping or explanation for every project."""
    project_index = _unique_index(projects, "project_id", "project")
    field_index = _unique_index(fields, "field_id", "field")
    groups, seen, partial = defaultdict(list), set(), set()
    for row in rows:
        _require(set(COLUMNS) <= row.keys(), "missing crosswalk columns")
        pid, fid = row["PROJECT_ID"], row["CATALOG_FIELD_ID"]
        _require(pid in project_index, "unknown project ID: " + pid)
        _require(row["PROJECT"] == project_index[pid]["name"], "project name mismatch")
        _require(
            row["COST_PROJECT_ID"] == project_index[pid].get("cost_project_id", ""),
            "controlled cost project ID mismatch",
        )
        _require(not fid or fid in field_index, "unknown catalog field ID: " + fid)
        _require((pid, fid) not in seen, "duplicate project/field link")
        seen.add((pid, fid))
        _require(row["PROVENANCE"] == "derived", "invalid crosswalk provenance")
        _require(row["CONFIDENCE"] in {"high", "medium", "low"}, "invalid confidence")
        method = row["MATCH_METHOD"]
        _require(
            method in {"exact_name", "alias", "operator_block", "manual", "unmatched"},
            "invalid match method",
        )
        _require(
            (method == "unmatched") == (not fid), "unmatched method/field contradiction"
        )
        _require(
            bool(row["REASON"].strip()) == (not fid), "missing or contradictory reason"
        )
        if not fid:
            _require(row["CONFIDENCE"] == "low", "unmatched confidence must be low")
        elif method == "manual":
            match = match_project(project_index[pid], fields)
            _require(
                fid not in match["field_ids"], "manual relabels deterministic match"
            )
        else:
            match = match_project(project_index[pid], fields)
            _require(
                fid in match["field_ids"]
                and method == match["method"]
                and row["CONFIDENCE"] == match["confidence"],
                "unsupported deterministic match",
            )
        evidence = _evidence(row, project_index[pid])
        if fid and evidence.get("unmapped_scope"):
            partial.add(pid)
        groups[pid].append(row)
    _require(
        set(groups) == set(project_index),
        "missing crosswalk projects: "
        + ", ".join(sorted(set(project_index) - set(groups))),
    )
    mapped = 0
    for pid, links in groups.items():
        ids = {r["CATALOG_FIELD_ID"] for r in links}
        _require(not ("" in ids and len(ids) > 1), "mixed mapped/unmapped project")
        expected = set(match_project(project_index[pid], fields)["field_ids"])
        _require(
            not expected or expected <= ids,
            "manual/unmatched override omits deterministic match",
        )
        mapped += bool(ids - {""})
    return dict(
        projects=len(projects),
        mapped=mapped,
        explained=len(projects) - mapped,
        accounted_for=len(groups),
        links=sum(bool(r["CATALOG_FIELD_ID"]) for r in rows),
        partial=len(partial),
    )


def read_crosswalk(path, projects, fields):
    """Revalidate hand-editable crosswalk rows on every read."""
    _, rows = read_csv(path)
    validate_crosswalk(rows, projects, fields)
    return rows


def text_digest(path):
    """SHA-256 domain utf8-lf: BOM removed; CRLF and lone CR become LF."""
    raw = Path(path).read_text(encoding="utf-8-sig")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def input_paths(root):
    root = Path(root)
    paths = set(_project_tables(root)) | {
        CATALOG.as_posix(),
        FIELD_IDENTITIES.as_posix(),
    }
    if (root / IDENTITIES).exists():
        paths.add(IDENTITIES.as_posix())
    return sorted(paths)


def build_manifest(root, crosswalk=None):
    """Pin the input set and the exact crosswalk in the declared text domain."""
    root = Path(root)
    return dict(
        schema_version=1,
        dataset_id="cost-project-field-crosswalk",
        digest_domain="utf8-lf",
        units="identity links; no monetary quantities",
        inputs={p: text_digest(root / p) for p in input_paths(root)},
        crosswalk_sha256=text_digest(crosswalk or root / CROSSWALK),
    )


def verify_manifest(root, manifest, crosswalk=None):
    expected = build_manifest(root, crosswalk)
    _require(manifest == expected, "manifest input set, metadata or digest mismatch")


def validate_repository(root, crosswalk=None):
    root = Path(root)
    for table in REGISTER_TABLES:
        _require(
            (root / CURATED / table).is_file(),
            "missing required cost register table: " + table,
        )
    projects, fields = load_cost_projects(root), load_catalog(root)
    _require(projects and fields, "empty register or catalog")
    rows = read_crosswalk(crosswalk or root / CROSSWALK, projects, fields)
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    # Candidates are validated against pinned inputs; the held output retains
    # its independent digest check.
    verify_manifest(root, manifest)
    return validate_crosswalk(rows, projects, fields)


def build_crosswalk(projects, fields):
    """Generate deterministic candidate rows; manual scope decisions remain explicit."""
    rows = []
    for project in projects:
        match = match_project(project, fields)
        fid = next(iter(match["field_ids"]), "")
        evidence = dict(
            project_sources=project["sources"],
            catalog_fields=[fid] if fid else [],
            basis="Held catalog " + match["method"] + " comparison.",
            limitation=LIMITATION,
            unmapped_scope=[],
        )
        rows.append(
            dict(
                PROJECT_ID=project["project_id"],
                COST_PROJECT_ID=project.get("cost_project_id", ""),
                PROJECT=project["name"],
                CATALOG_FIELD_ID=fid,
                MATCH_METHOD=match["method"],
                CONFIDENCE=match["confidence"],
                PROVENANCE="derived",
                EVIDENCE=json.dumps(evidence, sort_keys=True),
                REASON=match["reason"],
            )
        )
    validate_crosswalk(rows, projects, fields)
    return rows
