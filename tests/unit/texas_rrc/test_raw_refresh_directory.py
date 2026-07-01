"""Tests for Texas RRC GoDrive directory raw refresh."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest


def fixed_clock() -> datetime:
    return datetime(2026, 6, 29, 20, 0, 0, tzinfo=timezone.utc)


def _entry(filename: str, page_first: int = 0):
    from worldenergydata.texas_rrc.godrive import GoDriveDirectoryEntry

    return GoDriveDirectoryEntry(
        filename=filename,
        command_id=f"fileTable:{page_first}:j_id_2f",
        modified_label="6/29/26 6:14:59 PM",
        size_label="1.00 KB",
        row_key=filename,
        page_first=page_first,
    )


def _page(entries, row_count: int | None = None):
    from worldenergydata.texas_rrc.godrive import GoDriveDirectoryPage

    return GoDriveDirectoryPage(
        entries=tuple(entries),
        view_state="state",
        row_count=row_count or len(entries),
        page_first=0,
        rows_per_page=1000,
    )


def _catalog_for(source_id: str, policy: str):
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()
    catalog[source_id] = {
        **catalog[source_id],
        "directory_refresh_policy": policy,
    }
    return catalog


class FakeDirectoryTransport:
    def __init__(self, pages, payloads: dict[str, bytes] | None = None):
        self.pages = tuple(pages)
        self.payloads = payloads or {}
        self.listed_urls: list[tuple[str, int]] = []
        self.downloads: list[tuple[str, str, Path]] = []

    def list_godrive_directory(self, url: str, rows_per_page: int = 1000):
        self.listed_urls.append((url, rows_per_page))
        return self.pages

    def download_godrive_directory_file_to(
        self,
        url: str,
        entry,
        output_path: Path,
        rows_per_page: int = 1000,
    ):
        from worldenergydata.texas_rrc.raw_refresh import DownloadedArtifact

        self.downloads.append((url, entry.filename, output_path))
        payload = self.payloads[entry.filename]
        if isinstance(payload, Exception):
            raise payload
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        return DownloadedArtifact(
            headers={"content-type": "application/zip"},
            effective_url=f"{url}#{entry.filename}",
            checksum_sha256=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
        )


def test_directory_discovery_selects_latest_filename_date(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import (
        DirectorySelection,
        RawSnapshotRefresher,
    )

    transport = FakeDirectoryTransport(
        [_page([_entry("06-27-2026.zip"), _entry("06-29-2026.zip")])]
    )
    refresher = RawSnapshotRefresher(
        catalog=_catalog_for("completion_data", "latest_by_filename_date"),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    plan = refresher.discover_directory_source(
        "completion_data",
        DirectorySelection(),
        rows_per_page=1000,
    )

    assert plan.row_count == 2
    assert [file.filename for file in plan.selected_files] == ["06-29-2026.zip"]
    assert transport.listed_urls == [
        (
            "https://mft.rrc.texas.gov/link/ed7ab066-879f-40b6-8144-2ae4b6810c04",
            1000,
        )
    ]


def test_directory_discovery_deduplicates_repeated_target_filenames(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import (
        DirectorySelection,
        RawSnapshotRefresher,
    )

    transport = FakeDirectoryTransport(
        [
            _page(
                [
                    _entry("06-28-2026.zip"),
                    _entry("06-29-2026.zip"),
                    _entry("06-29-2026.zip"),
                ],
                row_count=3,
            )
        ]
    )
    refresher = RawSnapshotRefresher(
        catalog=_catalog_for("completion_data", "latest_by_filename_date"),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    plan = refresher.discover_directory_source(
        "completion_data",
        DirectorySelection(),
        rows_per_page=1000,
    )

    assert plan.row_count == 3
    assert [file.filename for file in plan.selected_files] == ["06-29-2026.zip"]
    assert [file.target_path for file in plan.selected_files] == [
        tmp_path / "raw" / "completions" / "06-29-2026.zip"
    ]


def test_directory_discovery_selects_date_window_and_all_gis_files(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import (
        DirectorySelection,
        RawSnapshotRefresher,
    )

    completion_transport = FakeDirectoryTransport(
        [
            _page(
                [
                    _entry("06-27-2026.zip"),
                    _entry("06-28-2026.zip"),
                    _entry("06-29-2026.zip"),
                ]
            )
        ]
    )
    completion_refresher = RawSnapshotRefresher(
        catalog=_catalog_for("directional_surveys", "latest_by_filename_date"),
        output_root=tmp_path,
        transport=completion_transport,
        clock=fixed_clock,
    )

    date_window = completion_refresher.discover_directory_source(
        "directional_surveys",
        DirectorySelection(
            since_date=date(2026, 6, 28),
            through_date=date(2026, 6, 29),
        ),
    )

    assert [file.filename for file in date_window.selected_files] == [
        "06-28-2026.zip",
        "06-29-2026.zip",
    ]

    gis_transport = FakeDirectoryTransport(
        [_page([_entry("well001.zip"), _entry("well003.zip"), _entry("wellFED.zip")])]
    )
    gis_refresher = RawSnapshotRefresher(
        catalog=_catalog_for("well_gis_layers", "all_files"),
        output_root=tmp_path,
        transport=gis_transport,
        clock=fixed_clock,
    )

    gis_plan = gis_refresher.discover_directory_source(
        "well_gis_layers",
        DirectorySelection(),
    )

    assert [file.filename for file in gis_plan.selected_files] == [
        "well001.zip",
        "well003.zip",
        "wellFED.zip",
    ]


def test_directory_discovery_all_mode_selects_all_dated_files_and_ignores_malformed(
    tmp_path,
):
    from worldenergydata.texas_rrc.raw_refresh import (
        DirectorySelection,
        RawSnapshotRefresher,
    )

    transport = FakeDirectoryTransport(
        [
            _page(
                [
                    _entry("06-27-2026.zip"),
                    _entry("13-40-2026.zip"),
                    _entry("not-a-date.zip"),
                    _entry("06-29-2026.zip"),
                ]
            )
        ]
    )
    refresher = RawSnapshotRefresher(
        catalog=_catalog_for("completion_data", "latest_by_filename_date"),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    plan = refresher.discover_directory_source(
        "completion_data",
        DirectorySelection(mode="all"),
    )

    assert [file.filename for file in plan.selected_files] == [
        "06-27-2026.zip",
        "06-29-2026.zip",
    ]


def test_directory_refresh_writes_all_files_and_artifact_manifest(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher

    transport = FakeDirectoryTransport(
        [_page([_entry("well001.zip"), _entry("wellFED.zip")])],
        payloads={"well001.zip": b"one", "wellFED.zip": b"fed"},
    )
    refresher = RawSnapshotRefresher(
        catalog=_catalog_for("well_gis_layers", "all_files"),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    manifest = refresher.refresh_source("well_gis_layers")

    assert manifest.status == "downloaded"
    assert manifest.byte_size == 6
    assert manifest.checksum_sha256 is None
    assert len(manifest.artifacts) == 2
    assert (tmp_path / "raw" / "gis" / "wells" / "well001.zip").read_bytes() == b"one"
    assert (tmp_path / "raw" / "gis" / "wells" / "wellFED.zip").read_bytes() == b"fed"

    manifest_path = tmp_path / "manifests" / "well_gis_layers-20260629T200000Z.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["artifacts"][0]["filename"] == "well001.zip"
    assert payload["artifacts"][0]["raw_path"] == str(
        tmp_path / "raw" / "gis" / "wells" / "well001.zip"
    )
    assert payload["artifacts"][0]["retrieved_at"] == "2026-06-29T20:00:00Z"
    assert (
        payload["artifacts"][0]["checksum_sha256"] == hashlib.sha256(b"one").hexdigest()
    )


def test_directory_refresh_failure_removes_staging_and_preserves_existing_files(
    tmp_path,
):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher

    existing = tmp_path / "raw" / "gis" / "wells" / "well001.zip"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing")
    transport = FakeDirectoryTransport(
        [_page([_entry("well001.zip"), _entry("well003.zip")])],
        payloads={"well001.zip": b"new", "well003.zip": OSError("network failed")},
    )
    refresher = RawSnapshotRefresher(
        catalog=_catalog_for("well_gis_layers", "all_files"),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    with pytest.raises(OSError, match="network failed"):
        refresher.refresh_source("well_gis_layers")

    assert existing.read_bytes() == b"existing"
    assert not list(tmp_path.rglob("*.part"))
    assert not list(tmp_path.rglob(".staging-*"))
    manifest_path = tmp_path / "manifests" / "well_gis_layers-20260629T200000Z.json"
    assert '"status": "error"' in manifest_path.read_text(encoding="utf-8")
