"""Tests for Kansas KGS source catalog and raw manifest support."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def test_source_catalog_paths_stay_under_kansas_ace_root() -> None:
    from worldenergydata.kansas_kgs.raw_sources import (
        DEFAULT_KANSAS_KGS_ROOT,
        load_source_catalog,
    )

    catalog = load_source_catalog()

    assert str(DEFAULT_KANSAS_KGS_ROOT).endswith("/kansas_kgs")
    assert {"pressure_proration", "wells_master"}.issubset(catalog)
    for source in catalog.values():
        assert source.raw_path.is_relative_to(DEFAULT_KANSAS_KGS_ROOT)
        assert source.source_url.startswith("https://www.kgs.ku.edu/")


def test_source_catalog_rejects_out_of_root_path(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.raw_sources import load_source_catalog

    bad_catalog = tmp_path / "source_catalog.yml"
    bad_catalog.write_text(
        "\n".join(
            [
                "sources:",
                "  bad:",
                "    source_url: https://www.kgs.ku.edu/bad.txt",
                "    raw_path: /tmp/outside.txt",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="kansas_kgs"):
        load_source_catalog(bad_catalog)


def test_existing_raw_files_are_hashed_into_manifest(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.raw_sources import ensure_raw_sources

    pressure = tmp_path / "raw/pressure/kansas_proration_pressures.txt"
    wells = tmp_path / "raw/wells/ks_wells.zip"
    pressure.parent.mkdir(parents=True)
    wells.parent.mkdir(parents=True)
    pressure.write_text("pressure\n", encoding="utf-8")
    wells.write_bytes(b"zip-bytes")

    manifest = ensure_raw_sources(
        tmp_path,
        refresh=False,
        allow_non_ace_root=True,
        http_metadata={
            "pressure_proration": {"last_modified": "Thu, 27 Mar 2025 17:32:01 GMT"},
            "wells_master": {"last_modified": "Fri, 05 Jun 2026 19:31:21 GMT"},
        },
    )

    payload = json.loads((tmp_path / "raw/manifest.json").read_text())
    assert (
        manifest["pressure_proration"]["sha256"]
        == hashlib.sha256(b"pressure\n").hexdigest()
    )
    assert payload["sources"]["wells_master"]["size_bytes"] == len(b"zip-bytes")
    assert payload["sources"]["pressure_proration"]["http_metadata"][
        "last_modified"
    ].startswith("Thu")
    assert payload["sources"]["pressure_proration"]["observed_at"].endswith("Z")


def test_existing_raw_files_collect_head_metadata_when_requested(
    tmp_path: Path,
) -> None:
    from worldenergydata.kansas_kgs.raw_sources import ensure_raw_sources

    pressure = tmp_path / "raw/pressure/kansas_proration_pressures.txt"
    wells = tmp_path / "raw/wells/ks_wells.zip"
    pressure.parent.mkdir(parents=True)
    wells.parent.mkdir(parents=True)
    pressure.write_text("pressure\n", encoding="utf-8")
    wells.write_bytes(b"zip-bytes")

    def metadata_fetcher(source):
        return {
            "last_modified": f"{source.source_id}-last-modified",
            "content_length": "123",
        }

    ensure_raw_sources(
        tmp_path,
        refresh=False,
        allow_non_ace_root=True,
        metadata_fetcher=metadata_fetcher,
    )

    payload = json.loads((tmp_path / "raw/manifest.json").read_text())
    assert (
        payload["sources"]["pressure_proration"]["http_metadata"]["last_modified"]
        == "pressure_proration-last-modified"
    )
    assert (
        payload["sources"]["wells_master"]["http_metadata"]["content_length"] == "123"
    )


def test_refresh_not_called_when_raw_files_present(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.raw_sources import ensure_raw_sources

    (tmp_path / "raw/pressure").mkdir(parents=True)
    (tmp_path / "raw/wells").mkdir(parents=True)
    (tmp_path / "raw/pressure/kansas_proration_pressures.txt").write_text(
        "pressure\n", encoding="utf-8"
    )
    (tmp_path / "raw/wells/ks_wells.zip").write_bytes(b"zip-bytes")

    def fail_fetch(*_args, **_kwargs) -> None:
        raise AssertionError("fetcher should not be called")

    ensure_raw_sources(
        tmp_path,
        refresh=False,
        fetcher=fail_fetch,
        allow_non_ace_root=True,
    )


def test_kansas_county_mapping_covers_all_counties() -> None:
    from worldenergydata.kansas_kgs.raw_sources import load_kansas_counties

    counties = load_kansas_counties()

    assert len(counties) == 105
    assert counties["067"] == "Grant"
    assert counties["189"] == "Stevens"
