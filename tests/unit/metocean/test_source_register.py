"""Offline source-register and legacy-catalog contract tests."""

import hashlib
import json
from dataclasses import asdict
from importlib.resources import files

from worldenergydata.metocean.extrapolation.source_catalog import NearestSourceFinder


def test_register_is_a_packaged_resource():
    resource = files("worldenergydata.metocean").joinpath("data/source_register.json")
    register = json.loads(resource.read_text(encoding="utf-8"))
    assert register["schema_version"] == 1
    identifiers = [row["id"] for row in register["sources"]]
    assert len(identifiers) == len(set(identifiers))
    for row in register["sources"]:
        assert row["publisher"]
        assert row["terms_quote"]
        assert row["access_status"]
        assert row["test_fetch"]["outcome"]
        if row["update_enabled"]:
            assert row["terms_rechecked"]
            assert row["test_fetch"]["http_status"] == 200
            assert row["test_fetch"]["bytes"] > 0
            assert row["test_fetch"]["content_validated"]
            assert row["account_required"] is False


def test_catalog_matches_frozen_pre_migration_output():
    rows = [asdict(row) for row in NearestSourceFinder().list_sources()]
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    # Digest of the complete ordered catalog before migration, not new JSON.
    assert hashlib.sha256(encoded).hexdigest() == (
        "cac7095c06248a2118f0f488c9af6ac132decd70ed77a8d85cfa2dddce79efc9"
    )
