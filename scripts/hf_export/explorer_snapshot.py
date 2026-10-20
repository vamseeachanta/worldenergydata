#!/usr/bin/env python3
"""Build and validate versioned, data-only Explorer snapshots (issue #1045).

No network, clock, environment, or filesystem writes in the builder. Publication
uses an injected backend; only a completely verified readback yields a receipt.
JSON rules follow RFC 8259 (2017), sections 4, 6 and 8.1. Digest computation uses
Python hashlib.sha256, with no engineering coefficients or inferred licence grant.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlsplit

# Protocol identifiers and widths follow the issue #1045 reviewed contract;
# shard bounds are mandatory caller inputs, never inferred scale limits.
SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"
PROJECTION = "field_explorer_browser"
MANIFEST = "browser/manifest.json"
COLLECTIONS = ("fields", "wells", "countries", "parametric_economics")
ROLES = ("explorer", "atlas", "performance", "parametric", "registry")
KEYS = {
    "fields": ["field_id"],
    "wells": ["well_id"],
    "countries": ["country"],
    "parametric_economics": ["field_id", "discount_rate", "wti_price_multiplier"],
}
# Explicit projections discard presentation structures, rather than guessing at
# stripping tags. Retained strings still undergo fail-closed HTML/URL validation.
FIELD_COLUMNS = (
    "operator",
    "region",
    "host",
    "treeType",
    "currentPhase",
    "metrics",
    "reservoir",
    "provenance",
)
WELL_COLUMNS = (
    "api",
    "slot",
    "spud_date",
    "td_date",
    "drilling_rig_days",
    "completion_rig_days",
    "max_tvd_ft",
    "mud_weight_ppg",
    "first_oil",
    "workovers",
    "cum_oil_mmbbl",
    "uptime_pct",
    "status",
)
PERFORMANCE_COLUMNS = (
    "wells",
    "economics_status",
    "economics_basis",
    "npv_mm",
    "breakeven_wti",
    "sens_mm_per_dollar",
    "eur_mmbbl",
    "eur_source",
    "eur_confidence",
    "cum_oil_mmbbl",
    "avg_uptime_pct",
    "avg_decline_pct_yr",
    "interventions",
)
COUNTRY_COLUMNS = ("country", "fields", "facilities", "badge", "module")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value):
    """Project-specific canonical JSON; not a claim of RFC 8785 compliance."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def strict_json(raw):
    def reject(_):
        raise ValueError("non-finite JSON number")

    return json.loads(
        raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=reject
    )


def safe_path(path):
    require(isinstance(path, str) and bool(path), "missing artifact path")
    require(
        all(
            re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", p)
            for p in path.split("/")
        ),
        "unsafe artifact path",
    )
    require(not path.startswith(".git/"), "unsafe artifact path")
    return path


def exact_sha(value):
    # HF commit IDs use full Git SHA-1 hex; HF download guide, revision section.
    require(
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{40}", value)
        and value != "0" * 40,
        "exact Git commit SHA required",
    )
    return value


def _text(value):
    require(isinstance(value, str) and bool(value.strip()), "nonempty string required")
    return value


def _safe_data(value):
    if isinstance(value, dict):
        for key, child in value.items():
            _safe_data(key)
            _safe_data(child)
    elif isinstance(value, list):
        for child in value:
            _safe_data(child)
    elif isinstance(value, str):
        decoded = value
        # Decode until stable: nested entities must not hide markup.
        while html.unescape(decoded) != decoded:
            decoded = html.unescape(decoded)
        require(
            not re.search(
                r"<\s*[A-Za-z/!?]|(?:javascript|vbscript)\s*:|data\s*:\s*(?:text/|image/|application/|[;,])",
                decoded,
                re.IGNORECASE,
            ),
            "unsafe browser string",
        )
        # RFC 8259 (2017), section 7: U+0000 through U+001F controls.
        require(
            not any(ord(c) < 32 and c not in "\n\r\t" for c in value),
            "control character in browser string",
        )
    elif isinstance(value, float):
        require(math.isfinite(value), "non-finite number")
    else:
        require(
            value is None or isinstance(value, (int, bool)), "unsupported data type"
        )


def _positive_int(value):
    require(type(value) is int and value > 0, "positive integer bound required")
    return value


def _url(value):
    parsed = urlsplit(_text(value))
    require(
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and not parsed.fragment,
        "public HTTPS evidence required",
    )
    return value


def route_key(stable_id):
    """route-id-v1 from the reviewed plan; RFC 4648 (2006), section 7."""
    require(unicodedata.normalize("NFC", stable_id) == stable_id, "non-NFC identity")
    return "r1-" + base64.b32hexencode(stable_id.encode()).decode().lower().rstrip("=")


def _pick(value, columns):
    return {key: value.get(key) for key in columns}


def _unique(rows, keys):
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in keys)
        require(key not in seen, "duplicate primary key")
        seen.add(key)


def _admission(config, expected_dataset):
    require(config["schema_version"] == SCHEMA_VERSION, "unknown schema")
    require(config["generator_version"] == GENERATOR_VERSION, "unknown generator")
    require(config["dataset_id"] == expected_dataset, "dataset identity mismatch")
    require(
        re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", expected_dataset),
        "invalid dataset identity",
    )
    exact_sha(config["source_git_sha"])
    _url(config["source_repository"])
    license_id = _text(config["license"])
    require(
        license_id == license_id.strip().lower()
        and license_id not in ("other", "unknown", "pending", "none", "not_evaluated"),
        "unresolved license",
    )
    require(
        re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", license_id),
        "invalid license identifier",
    )
    _positive_int(config["shard_max_records"])
    _positive_int(config["shard_max_bytes"])
    require(set(config["inputs"]) == set(ROLES), "complete source roles required")
    for entry in config["inputs"].values():
        safe_path(entry["path"])
        require(
            entry["classification"] == "public"
            and entry["redistribution"] == "confirmed",
            "source not admitted",
        )
        require(entry["license"] == config["license"], "conflicting source license")
        _url(entry["evidence"])
        require(re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), "invalid source digest")


def _load_inputs(config, read):
    inputs = {}
    for role, entry in config["inputs"].items():
        raw = read(entry["path"])
        require(digest(raw) == entry["sha256"], "stale source hash")
        if entry["path"].endswith((".yml", ".yaml")):
            # The canonical repository registry is YAML; all other inputs are JSON.
            require(role == "registry", "only registry YAML is supported")
            import yaml

            inputs[role] = yaml.safe_load(raw)
        else:
            inputs[role] = strict_json(raw)
        # Even discarded source values must not hide non-finite numbers. HTML in
        # known presentation structures is discarded by the explicit projection.
        canonical_json(inputs[role])
    return inputs


def _registry(source):
    rows = source["fields"]
    _unique(rows, ["canonical_id"])
    registry = {r["canonical_id"]: r for r in rows}
    aliases = {}
    slugs = set()
    for fid, row in registry.items():
        require(re.fullmatch(r"[a-z][a-z0-9_]*", fid), "invalid canonical field ID")
        slug = row["fdp_slug"]
        require(
            re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) and slug not in slugs,
            "invalid or duplicate slug",
        )
        slugs.add(slug)
        require(isinstance(row["aliases"], list), "alias list required")
        for name in [row["display_name"], *row["aliases"]]:
            key = re.sub(r"[\W_]+", "", _text(name).casefold())
            require(key and aliases.get(key, fid) == fid, "conflicting alias")
            aliases[key] = fid
    return registry


def _tables(inputs):
    explorer = inputs["explorer"]
    registry = _registry(inputs["registry"])
    fields = []
    for fid, data in explorer["fields"].items():
        require(fid in registry and data["id"] == fid, "field registry mismatch")
        identity = registry[fid]
        perf = inputs["performance"]["fields"].get(fid)
        if perf is None:
            require(
                type(data.get("wellsCount")) is int and data["wellsCount"] == 0,
                "missing performance needs explicit zero-well coverage",
            )
            perf = {"wells": 0, "economics_status": "not_evaluated"}
        fields.append(
            {
                **_pick(data, FIELD_COLUMNS),
                **_pick(perf, PERFORMANCE_COLUMNS),
                "id": fid,
                "field_id": fid,
                "field_route_key": route_key(fid),
                "display_name": identity["display_name"],
                "aliases": sorted(identity["aliases"]),
                "slug": identity["fdp_slug"],
            }
        )
    require(fields, "empty field snapshot")
    field_ids = {r["field_id"] for r in fields}
    wells = []
    for well in explorer["wells"]["wells"]:
        require(well["field_id"] in field_ids, "orphan well")
        api = well["api"]
        # bsee-api12 identity format is specified by the reviewed issue plan;
        # no conversion from display slot or rounded numeric API is permitted.
        require(
            isinstance(api, str) and re.fullmatch(r"[0-9]{12}", api), "API12 required"
        )
        wid = "bsee-api12:" + api
        wells.append(
            {
                **_pick(well, WELL_COLUMNS),
                "well_id": wid,
                "well_route_key": route_key(wid),
                "parent_field_id": well["field_id"],
            }
        )
    for field in fields:
        count = sum(w["parent_field_id"] == field["field_id"] for w in wells)
        require(
            type(field["wells"]) is int and field["wells"] == count,
            "field/well count disagreement",
        )
        field["well_count"] = count
        field["readiness"] = "drilldown_ready" if count else "zero_well_ready"
    countries = [_pick(c, COUNTRY_COLUMNS) for c in inputs["atlas"]["countries"]]
    economics = []
    for fid, data in inputs["parametric"]["fields"].items():
        if data["economics_status"] != "surfaced":
            continue
        require(fid in field_ids, "unknown economics field")
        require(
            inputs["performance"]["fields"][fid]["economics_status"] == "surfaced",
            "conflicting economics admission",
        )
        for row in data["grid"]:
            economics.append(
                {
                    **_pick(row, ("wti_price_multiplier", "discount_rate", "npv_musd")),
                    "field_id": fid,
                    "field": fid,
                    "economics_basis": "life_to_date_pretax_npv",
                    "breakeven_multiplier": data["breakeven_multiplier_by_rate"][
                        f"{row['discount_rate']:g}"
                    ],
                }
            )
    tables = dict(zip(COLLECTIONS, (fields, wells, countries, economics)))
    for name, rows in tables.items():
        _validate_rows(name, rows)
        _safe_data(rows)
        _unique(rows, KEYS[name])
        rows.sort(key=lambda r: tuple(r[k] for k in KEYS[name]))
    return tables


def _shards(rows, max_records, max_bytes):
    current = []
    for row in rows:
        require(
            len(canonical_json([row])) <= max_bytes, "single record exceeds byte bound"
        )
        if current and (
            len(current) >= max_records
            or len(canonical_json(current + [row])) > max_bytes
        ):
            yield current
            current = []
        current.append(row)
    # An empty shard declares the schema and explicit zero coverage.
    if current or not rows:
        require(
            len(canonical_json(current)) <= max_bytes, "empty shard exceeds byte bound"
        )
        yield current


RECORD_COLUMNS = {
    "fields": sorted(
        {
            *FIELD_COLUMNS,
            *PERFORMANCE_COLUMNS,
            "id",
            "field_id",
            "field_route_key",
            "display_name",
            "aliases",
            "slug",
            "well_count",
            "readiness",
        }
    ),
    "wells": sorted({*WELL_COLUMNS, "well_id", "well_route_key", "parent_field_id"}),
    "countries": sorted(COUNTRY_COLUMNS),
    "parametric_economics": sorted(
        {
            "field_id",
            "field",
            "wti_price_multiplier",
            "discount_rate",
            "npv_musd",
            "breakeven_multiplier",
            "economics_basis",
        }
    ),
}
MANIFEST_COLUMNS = {
    "schema_version",
    "projection",
    "dataset_id",
    "source_repository",
    "source_git_sha",
    "generator",
    "sources",
    "counts",
    "artifacts",
    "license",
    "readiness",
    "route_key_encoding",
    "relationship",
    "sharding",
    "compatibility",
    "card",
}


def _validate_rows(name, rows):
    measurements = {
        "fields": (
            "npv_mm",
            "breakeven_wti",
            "sens_mm_per_dollar",
            "eur_mmbbl",
            "cum_oil_mmbbl",
            "avg_uptime_pct",
            "avg_decline_pct_yr",
            "interventions",
        ),
        "wells": (
            "drilling_rig_days",
            "completion_rig_days",
            "max_tvd_ft",
            "mud_weight_ppg",
            "cum_oil_mmbbl",
            "uptime_pct",
        ),
    }
    for row in rows:
        for key in measurements.get(name, ()):
            value = row[key]
            require(
                value is None or (type(value) in (int, float) and math.isfinite(value)),
                "finite measurement or null required",
            )
        if name == "fields" and row["economics_status"] != "surfaced":
            require(
                all(
                    row[k] is None
                    for k in ("npv_mm", "breakeven_wti", "sens_mm_per_dollar")
                ),
                "withheld economics must remain null",
            )
        for key in KEYS[name]:
            if key in ("discount_rate", "wti_price_multiplier"):
                require(
                    type(row[key]) in (int, float) and math.isfinite(row[key]),
                    "numeric scenario key required",
                )
            else:
                _text(row[key])
        if name == "parametric_economics":
            for key in ("npv_musd", "breakeven_multiplier"):
                require(
                    type(row[key]) in (int, float) and math.isfinite(row[key]),
                    "finite scenario value required",
                )
        if name == "countries":
            require(
                type(row["fields"]) is int and row["fields"] >= 0,
                "nonnegative catalog count required",
            )
        if name == "fields":
            _text(row["display_name"])
            require(
                isinstance(row["aliases"], list)
                and all(isinstance(a, str) and a for a in row["aliases"]),
                "invalid aliases",
            )


def _schema(name, rows):
    # Every analytical/browser record has exactly the declared columns. Nested
    # data is JSON-only and subjected to recursive string/number safety checks.
    columns = RECORD_COLUMNS[name]
    require(all(set(row) == set(columns) for row in rows), "record schema disagreement")
    return {
        "id": f"{PROJECTION}/{SCHEMA_VERSION}/{name}",
        "columns": sorted(columns),
        "primary_key": KEYS[name],
    }


def build_snapshot(config, read_source, expected_dataset):
    """Build in memory from hash-admitted bytes; use build_from_git for release."""
    _admission(config, expected_dataset)
    inputs = _load_inputs(config, read_source)
    tables = _tables(inputs)
    source_ids = {
        "fields": ["explorer", "registry", "performance"],
        "wells": ["explorer", "registry"],
        "countries": ["atlas"],
        "parametric_economics": ["parametric", "registry", "performance"],
    }
    files, artifacts = {}, []
    for name, rows in tables.items():
        schema = _schema(name, rows)
        parts = [(f"{name}.json", "analytical", rows)]
        parts.extend(
            (f"browser/{name}/part-{i:05}.json", "browser", part)
            for i, part in enumerate(
                _shards(rows, config["shard_max_records"], config["shard_max_bytes"])
            )
        )
        for path, kind, part in parts:
            data = canonical_json(part)
            files[path] = data
            artifacts.append(
                {
                    "path": path,
                    "kind": kind,
                    "collection": name,
                    "sha256": digest(data),
                    "byte_count": len(data),
                    "media_type": "application/json",
                    "record_count": len(part),
                    "schema": schema,
                    "sort": KEYS[name],
                    "provenance": source_ids[name],
                    "license": config["license"],
                    "redistribution": "confirmed",
                }
            )
    counts = {name: len(rows) for name, rows in tables.items()}
    counts["catalog_fields"] = len(inputs["atlas"]["fields"])
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "projection": PROJECTION,
        "dataset_id": config["dataset_id"],
        "source_repository": config["source_repository"],
        "source_git_sha": config["source_git_sha"],
        "generator": {"id": "explorer_snapshot", "version": GENERATOR_VERSION},
        "sources": config["inputs"],
        "counts": counts,
        "artifacts": artifacts,
        "license": config["license"],
        "readiness": "manifest_ready",
        "route_key_encoding": "route-id-v1",
        "relationship": {"wells.parent_field_id": "fields.field_id"},
        "sharding": {
            "max_records": config["shard_max_records"],
            "max_bytes": config["shard_max_bytes"],
        },
        "compatibility": {
            "status": "versioned_migration_required",
            "analytical_format": "json",
            "analytical_schema_version": "2.0.0",
            "replaces": "legacy_parquet",
        },
    }
    # HF datasets supports JSON analytical configs; explicit format migration
    # prevents claiming legacy Parquet consumers are compatible without evidence.
    card = ["---", f"license: {config['license']}", "configs:"]
    for name in COLLECTIONS:
        card.extend([f"- config_name: {name}", f"  data_files: {name}.json"])
    card.extend(
        [
            "---",
            "",
            "# Explorer snapshot",
            "",
            "Analytical JSON migration; browser contract is declared in browser/manifest.json.",
        ]
    )
    files["README.md"] = ("\n".join(card) + "\n").encode()
    manifest["card"] = {
        "path": "README.md",
        "sha256": digest(files["README.md"]),
        "byte_count": len(files["README.md"]),
    }
    files[MANIFEST] = canonical_json(manifest)
    validate_snapshot(files)
    return files


def validate_snapshot(files):
    """Re-parse staged/read-back bytes, checking full inventory and relational parity."""
    m = strict_json(files[MANIFEST])
    require(set(m) == MANIFEST_COLUMNS, "unknown manifest member")
    require(
        m["schema_version"] == SCHEMA_VERSION and m["projection"] == PROJECTION,
        "unknown manifest schema",
    )
    exact_sha(m["source_git_sha"])
    require(
        m["generator"] == {"id": "explorer_snapshot", "version": GENERATOR_VERSION},
        "unknown generator",
    )
    _admission(
        {
            "schema_version": m["schema_version"],
            "dataset_id": m["dataset_id"],
            "generator_version": m["generator"]["version"],
            "source_git_sha": m["source_git_sha"],
            "source_repository": m["source_repository"],
            "license": m["license"],
            "inputs": m["sources"],
            "shard_max_records": m["sharding"]["max_records"],
            "shard_max_bytes": m["sharding"]["max_bytes"],
        },
        m["dataset_id"],
    )
    require(
        m["readiness"] == "manifest_ready"
        and m["route_key_encoding"] == "route-id-v1"
        and m["relationship"] == {"wells.parent_field_id": "fields.field_id"},
        "unsupported relational contract",
    )
    require(
        set(m["counts"]) == {*COLLECTIONS, "catalog_fields"}
        and all(type(v) is int and v >= 0 for v in m["counts"].values()),
        "invalid counts",
    )
    require(
        m["compatibility"]
        == {
            "status": "versioned_migration_required",
            "analytical_format": "json",
            "analytical_schema_version": "2.0.0",
            "replaces": "legacy_parquet",
        },
        "unknown analytical migration",
    )
    _safe_data(m)
    expected = {MANIFEST, "README.md"}
    card = m["card"]
    require(
        card["path"] == "README.md"
        and digest(files["README.md"]) == card["sha256"]
        and len(files["README.md"]) == card["byte_count"],
        "card integrity mismatch",
    )
    combined = {k: [] for k in COLLECTIONS}
    analytical = {}
    for entry in m["artifacts"]:
        path = safe_path(entry["path"])
        require(path not in expected and path in files, "artifact missing or duplicate")
        expected.add(path)
        data = files[path]
        require(
            digest(data) == entry["sha256"] and len(data) == entry["byte_count"],
            "artifact integrity mismatch",
        )
        rows = strict_json(data)
        _safe_data(rows)
        require(
            isinstance(rows, list) and len(rows) == entry["record_count"],
            "artifact count mismatch",
        )
        name = entry["collection"]
        require(name in COLLECTIONS, "unknown collection")
        _validate_rows(name, rows)
        require(
            name in COLLECTIONS and entry["schema"] == _schema(name, rows),
            "unknown record schema",
        )
        require(
            entry["sort"] == KEYS[name] and entry["media_type"] == "application/json",
            "artifact contract mismatch",
        )
        require(
            entry["redistribution"] == "confirmed" and entry["license"] == m["license"],
            "artifact license mismatch",
        )
        require(
            all(p in m["sources"] for p in entry["provenance"]), "unknown provenance"
        )
        if entry["kind"] == "browser":
            require(path.startswith(f"browser/{name}/"), "browser path mismatch")
            require(
                len(rows) <= m["sharding"]["max_records"]
                and len(data) <= m["sharding"]["max_bytes"],
                "shard bound exceeded",
            )
            combined[name].extend(rows)
        else:
            require(
                entry["kind"] == "analytical"
                and path == f"{name}.json"
                and name not in analytical,
                "analytical inventory mismatch",
            )
            analytical[name] = rows
    require(
        set(files) == expected and set(analytical) == set(COLLECTIONS),
        "incomplete artifact inventory",
    )
    for name, rows in combined.items():
        require(
            rows == analytical[name] and len(rows) == m["counts"][name],
            "browser/analytical count or content mismatch",
        )
        _unique(rows, KEYS[name])
        require(
            rows == sorted(rows, key=lambda r: tuple(r[k] for k in KEYS[name])),
            "collection sorting mismatch",
        )
    require(bool(combined["fields"]), "empty field snapshot")
    _registry(
        {
            "fields": [
                {
                    "canonical_id": r["field_id"],
                    "display_name": r["display_name"],
                    "aliases": r["aliases"],
                    "fdp_slug": r["slug"],
                }
                for r in combined["fields"]
            ]
        }
    )
    field_ids = {r["field_id"] for r in combined["fields"]}
    for well in combined["wells"]:
        require(
            isinstance(well["api"], str) and re.fullmatch(r"[0-9]{12}", well["api"]),
            "API12 required",
        )
        require(well["parent_field_id"] in field_ids, "orphan well")
        require(
            well["well_id"] == "bsee-api12:" + well["api"]
            and well["well_route_key"] == route_key(well["well_id"]),
            "well identity mismatch",
        )
    for row in combined["parametric_economics"]:
        require(row["field_id"] in field_ids, "orphan economics record")
    for field in combined["fields"]:
        require(field["id"] == field["field_id"], "field ID disagreement")
        require(
            field["readiness"]
            == ("drilldown_ready" if field["well_count"] else "zero_well_ready"),
            "readiness disagreement",
        )
        count = sum(
            w["parent_field_id"] == field["field_id"] for w in combined["wells"]
        )
        require(
            field["well_count"] == count == field["wells"], "field/well count mismatch"
        )
        require(
            field["field_route_key"] == route_key(field["field_id"]),
            "field route mismatch",
        )
    return m


def build_from_git(root, config_path, source_sha, expected_dataset):
    """Require clean HEAD and read each input directly from that exact Git object."""
    exact_sha(source_sha)
    root = Path(root)

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True
        ).stdout

    require(
        not git("status", "--porcelain", "--untracked-files=all"),
        "snapshot requires a clean source tree",
    )
    require(
        git("rev-parse", "HEAD").decode().strip() == source_sha,
        "source SHA must equal clean HEAD",
    )

    def read(path):
        return git("show", f"{source_sha}:{safe_path(path)}")

    config = strict_json(read(config_path))
    require(
        "source_git_sha" not in config or config["source_git_sha"] == source_sha,
        "configuration source SHA mismatch",
    )
    # A committed configuration cannot name the commit containing itself. Bind
    # HEAD here, after verifying cleanliness, instead of creating a hash cycle.
    config["source_git_sha"] = source_sha
    return build_snapshot(config, read, expected_dataset)


def resolve_url(dataset_id, sha, path):
    exact_sha(sha)
    safe_path(path)
    require(
        re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", dataset_id),
        "invalid dataset identity",
    )
    return f"https://huggingface.co/datasets/{dataset_id}/resolve/{sha}/{quote(path, safe='/')}"


def publish_snapshot(files, expected_parent, backend, *, dry_run=False):
    """One expected-parent commit, then exact-SHA byte-for-byte readback.

    HF HfApi.create_commit documentation: parent_commit provides optimistic
    concurrency; CommitInfo.oid supplies the resulting commit. Readback failure
    can leave the remote head advanced, but no receipt is returned or promoted.
    """
    m = validate_snapshot(files)
    if dry_run:
        return {
            "publication": "not_published",
            "counts": m["counts"],
            "manifest_sha256": digest(files[MANIFEST]),
        }
    exact_sha(expected_parent)
    # Freeze mutable caller buffers before crossing a backend boundary.
    frozen = dict(files)
    sha = exact_sha(backend.commit(m["dataset_id"], expected_parent, dict(frozen)))
    returned = {}
    for path in [MANIFEST, *sorted(set(frozen) - {MANIFEST})]:
        returned[path] = backend.read(m["dataset_id"], sha, path)
        require(returned[path] == frozen[path], "exact-revision readback mismatch")
    validate_snapshot(returned)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": m["dataset_id"],
        "source_git_sha": m["source_git_sha"],
        "hf_commit_sha": sha,
        "expected_parent": expected_parent,
        "counts": m["counts"],
        "hashes": {p: digest(b) for p, b in sorted(returned.items())},
        "compatibility": m["compatibility"],
        "verification": "exact_bytes_verified",
    }
