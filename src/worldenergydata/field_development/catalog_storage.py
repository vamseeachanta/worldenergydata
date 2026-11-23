"""Catalog storage helpers."""

from __future__ import annotations

import copy
import csv
import importlib.util
import io
import os
import tempfile
from pathlib import Path

if __package__:
    from . import catalog_build_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_build_common", Path(__file__).with_name("catalog_build_common.py")
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)

TABLES = common.TABLES
input_contract = common.input_contract
validation = common.validation
canonical = common.canonical
digest_bytes = common.digest_bytes
validate_evidence = common.validate_evidence


def csv_bytes(rows):
    if not rows:
        return b""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=sorted(set().union(*(r.keys() for r in rows))),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(
        {k: canonical(v) if isinstance(v, (dict, list)) else v for k, v in r.items()}
        for r in rows
    )
    return stream.getvalue().encode("utf-8")


def write_bundle(bundle, out_dir):
    out = Path(out_dir)
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"catalog destination already exists: {out}")
    files = _validated_files(bundle)
    out.parent.mkdir(parents=True, exist_ok=True)
    _publish_files(files, out)


def _publish_files(files, out):
    out.mkdir()
    identity = _path_identity(out)
    owned = {}
    try:
        for name, raw in files.items():
            if name != "integration_manifest.json":
                _write_owned_file(out / name, raw, owned)
        if not all(_owned_matches(path, record) for path, record in owned.items()):
            raise OSError("catalog artifacts changed during publication")
        _write_owned_file(
            out / "integration_manifest.json", files["integration_manifest.json"], owned
        )
    except BaseException as error:
        residue = _rollback_owned(out, identity, owned)
        if residue:
            note = "publication rollback preserved residue: " + ", ".join(residue)
            add_note = getattr(error, "add_note", None)
            if callable(add_note):
                add_note(note)
            else:
                raise RuntimeError(f"{error}; {note}") from error
        raise


def _path_identity(path):
    stat = path.lstat()
    return stat.st_dev, stat.st_ino


def _write_owned_file(path, raw, owned):
    with path.open("xb", buffering=0) as stream:
        stat = os.fstat(stream.fileno())
        identity = stat.st_dev, stat.st_ino
        position = 0
        owned[path] = identity, digest_bytes(b"")
        while position < len(raw):
            count = stream.write(raw[position : position + 65536])
            if not count:
                raise OSError("catalog artifact write made no progress")
            position += count
            owned[path] = identity, digest_bytes(raw[:position])


def _owned_matches(path, record):
    try:
        identity, digest = record
        return (
            not path.is_symlink()
            and _path_identity(path) == identity
            and digest_bytes(path.read_bytes()) == digest
        )
    except OSError:
        return False


def _rollback_owned(out, identity, owned):
    try:
        if out.is_symlink() or _path_identity(out) != identity:
            return [str(out)]
    except OSError:
        return [str(out)]
    residue = []
    for path, record in reversed(list(owned.items())):
        if not path.exists() and not path.is_symlink():
            continue
        if _owned_matches(path, record):
            try:
                path.unlink()
                continue
            except OSError:
                pass
        residue.append(str(path))
    try:
        out.rmdir()
    except OSError:
        residue.append(str(out))
    return residue


def _validated_files(bundle):
    files = _serialized_files(bundle)
    with tempfile.TemporaryDirectory(prefix="catalog-validation-") as temporary:
        staged = Path(temporary) / "bundle"
        _write_files(files, staged)
        read_bundle(
            staged, public_only=bundle["manifest"]["state"] == "eligible_derived_export"
        )
    return files


def _write_files(files, out):
    out.mkdir()
    for name, raw in files.items():
        (out / name).write_bytes(raw)


def _serialized_files(bundle):
    files = {
        "entity_registry.csv": csv_bytes(bundle["entities"]),
        "legacy_entity_crosswalk.csv": csv_bytes(bundle["crosswalk"]),
        "legacy_catalog_ledger.csv": csv_bytes(bundle["ledger"]),
        "entity_relationships.csv": csv_bytes(bundle["relationships"]),
        "catalog_links.json": (canonical(bundle["links"]) + "\n").encode(),
        "publication_eligibility.json": (
            canonical(bundle["eligibility"]) + "\n"
        ).encode(),
        "catalog_match_decisions.json": (
            canonical(bundle["match_decisions"]) + "\n"
        ).encode(),
    }
    for table, rows in bundle["evidence"].items():
        files[table + ".json"] = (canonical(rows) + "\n").encode("utf-8")
    manifest = copy.deepcopy(bundle["manifest"])
    manifest["output_hashes"] = {
        name: digest_bytes(raw) for name, raw in sorted(files.items())
    }
    files["integration_manifest.json"] = (canonical(manifest) + "\n").encode("utf-8")
    return files


def read_bundle(out_dir, public_only=False):
    out = Path(out_dir)
    manifest = input_contract.strict_json(
        (out / "integration_manifest.json").read_bytes()
    )
    if public_only and manifest["state"] != "eligible_derived_export":
        raise ValueError("local draft is not a public dataset")
    pinned = _read_pinned_artifacts(out, manifest)
    tables = {t: input_contract.strict_json(pinned[t + ".json"]) for t in TABLES}
    validate_evidence(tables)
    entities = validation.parsed_csv(pinned["entity_registry.csv"])
    links = input_contract.strict_json(pinned["catalog_links.json"])
    ids = {row["entity_id"] for row in entities}
    if any(
        row.get("entity_id") and row["entity_id"] not in ids for row in links["records"]
    ):
        raise ValueError("dangling entity foreign key")

    def read_optional_csv(name):
        return validation.parsed_csv(pinned[name])

    bundle = dict(
        entities=entities,
        links=links,
        evidence=tables,
        manifest=manifest,
        eligibility=input_contract.strict_json(pinned["publication_eligibility.json"]),
        match_decisions=input_contract.strict_json(
            pinned["catalog_match_decisions.json"]
        ),
        crosswalk=read_optional_csv("legacy_entity_crosswalk.csv"),
        ledger=read_optional_csv("legacy_catalog_ledger.csv"),
        relationships=read_optional_csv("entity_relationships.csv"),
    )
    validation.validate_bundle(bundle)
    return bundle


def _read_pinned_artifacts(out, manifest):
    required = {t + ".json" for t in TABLES} | {
        "entity_registry.csv",
        "legacy_entity_crosswalk.csv",
        "legacy_catalog_ledger.csv",
        "entity_relationships.csv",
        "catalog_links.json",
        "publication_eligibility.json",
        "catalog_match_decisions.json",
    }
    validation.validate_manifest(manifest, required)
    pinned = {}
    for name, expected in manifest["output_hashes"].items():
        if Path(name).name != name:
            raise ValueError("unsafe artifact path")
        pinned[name] = (out / name).read_bytes()
        if digest_bytes(pinned[name]) != expected:
            raise ValueError("output digest mismatch or unsafe path")
    return pinned
