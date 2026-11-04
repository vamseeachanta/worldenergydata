#!/usr/bin/env python3
"""Synthetic, write-free worked example for the Explorer snapshot contract.

Inputs: two registry fields, one API well belonging to the first field, one
country covering both fields, and no surfaced economics. By hand enumeration,
fields=2, wells=1, countries=1, catalog_fields=2, parametric_economics=0. The
second field has explicit zero-well coverage. Shard size 1 is a chosen example
input, not a production limit; its byte bound is derived from the input size.
No financial results, real licences or real repository identity are asserted.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/hf_export"))
from explorer_snapshot import (
    GENERATOR_VERSION,
    SCHEMA_VERSION,
    build_snapshot,
    canonical_json,
    digest,
    publish_snapshot,
)


def example():
    documents = {
        "explorer": {
            "fields": {
                "alpha": {"id": "alpha", "name": "Alpha", "provenance": "Synthetic"},
                "beta": {
                    "id": "beta",
                    "name": "Beta",
                    "wellsCount": 0,
                    "provenance": "Synthetic",
                },
            },
            "wells": {
                "wells": [{"api": "123456789012", "field_id": "alpha", "slot": "A"}]
            },
        },
        "performance": {
            "fields": {"alpha": {"wells": 1, "economics_status": "not_evaluated"}}
        },
        "atlas": {
            "countries": [{"country": "Example", "fields": 2}],
            "fields": [{"catalog_id": "alpha"}, {"catalog_id": "beta"}],
        },
        "parametric": {"fields": {}},
        "registry": {
            "fields": [
                {
                    "canonical_id": fid,
                    "display_name": fid.title(),
                    "aliases": [],
                    "fdp_slug": fid,
                }
                for fid in ("alpha", "beta")
            ]
        },
    }
    sources = {
        f"{role}.json": canonical_json(value) for role, value in documents.items()
    }
    config = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "dataset_id": "namespace/dataset",
        "source_repository": "https://example.org/energy.git",
        "source_git_sha": "a" * 40,  # Synthetic identity; not a real Git release.
        "license": "cc-by-4.0",
        "shard_max_records": 1,
        "shard_max_bytes": sum(map(len, sources.values())),
        "inputs": {
            role: {
                "path": f"{role}.json",
                "sha256": digest(sources[f"{role}.json"]),
                "classification": "public",
                "redistribution": "confirmed",
                "license": "cc-by-4.0",
                "evidence": "https://example.org/synthetic",
            }
            for role in documents
        },
    }
    return build_snapshot(config, sources.__getitem__, "namespace/dataset")


if __name__ == "__main__":
    sys.stdout.buffer.write(
        canonical_json(publish_snapshot(example(), None, None, dry_run=True))
    )
