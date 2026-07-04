"""Tests for Texas RRC raw snapshot refresh."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest


class FakeTransport:
    def __init__(
        self,
        payload: bytes = b"source-bytes",
        content_type: str = "application/zip",
        status_code: int = 200,
        error: Exception | None = None,
        errors: list[Exception | None] | None = None,
        content_length: int | None = None,
    ):
        self.payload = payload
        self.content_type = content_type
        self.status_code = status_code
        self.error = error
        self.errors = errors or []
        self.content_length = content_length
        self.urls: list[str] = []

    def _headers(self) -> dict[str, str]:
        headers = {"content-type": self.content_type}
        if self.content_length is not None:
            headers["content-length"] = str(self.content_length)
        return headers

    def _raise_next_error(self) -> None:
        if self.errors:
            error = self.errors.pop(0)
            if error:
                raise error
            return
        if self.error:
            raise self.error

    def get(self, url: str):
        from worldenergydata.texas_rrc.raw_refresh import TransportResponse

        self.urls.append(url)
        self._raise_next_error()
        return TransportResponse(
            status_code=self.status_code,
            headers=self._headers(),
            content=self.payload,
            effective_url=url,
        )

    def download_to(self, url: str, output_path: Path):
        from worldenergydata.texas_rrc.raw_refresh import DownloadedArtifact

        self.urls.append(url)
        self._raise_next_error()
        if self.status_code >= 400:
            raise ValueError(f"Download failed with HTTP status {self.status_code}")
        if "text/html" in self.content_type.lower():
            raise ValueError(
                "Direct-source refresh received HTML instead of a data artifact"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.payload)
        return DownloadedArtifact(
            headers=self._headers(),
            effective_url=url,
            checksum_sha256=hashlib.sha256(self.payload).hexdigest(),
            byte_size=len(self.payload),
        )

    def download_godrive_file_to(
        self,
        url: str,
        output_path: Path,
        expected_filename: str,
    ):
        return self.download_to(url, output_path)


class GetOnlyTransport:
    def __init__(self, *responses: FakeTransport):
        self.responses = list(responses)
        self.urls: list[str] = []

    def get(self, url: str):
        if not self.responses:
            raise AssertionError("No fake response configured")
        response = self.responses.pop(0).get(url)
        self.urls.append(url)
        return response


def fixed_clock() -> datetime:
    return datetime(2026, 6, 29, 20, 0, 0, tzinfo=timezone.utc)


def test_godrive_parser_extracts_expected_file_form():
    from worldenergydata.texas_rrc.godrive import parse_godrive_file_form

    form = parse_godrive_file_form(
        """
        <form id="fileList">
          <input type="hidden" name="javax.faces.ViewState" value="older" />
          <input type="hidden" name="javax.faces.ViewState" value="state-123" />
          <a id="fileTable:0:j_id_2f" href="#">PDQ_DSV.zip</a>
        </form>
        """,
        "PDQ_DSV.zip",
    )

    assert form.command_id == "fileTable:0:j_id_2f"
    assert form.view_state == "state-123"


def test_raw_refresh_plan_uses_direct_official_rrc_sources_only(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    refresher = RawSnapshotRefresher(
        catalog=load_source_catalog(),
        output_root=tmp_path,
        clock=fixed_clock,
    )

    plans = {
        plan.source_id: plan
        for plan in refresher.plan_sources(
            [
                "production_pdq",
                "completion_data",
                "patchops_rrc_validation",
                "rrc_ewa_lease_query_validation",
            ]
        )
    }

    assert plans["production_pdq"].refreshable is True
    assert plans["production_pdq"].download_strategy == "official_godrive_file"
    assert plans["production_pdq"].download_url.startswith(
        "https://mft.rrc.texas.gov/link/"
    )
    assert plans["production_pdq"].target_path.is_relative_to(tmp_path)
    assert plans["completion_data"].refreshable is False
    assert plans["completion_data"].skip_reason == "official_godrive_directory"
    assert plans["patchops_rrc_validation"].refreshable is False
    assert plans["patchops_rrc_validation"].skip_reason == "validation_only"
    assert plans["rrc_ewa_lease_query_validation"].refreshable is False
    assert plans["rrc_ewa_lease_query_validation"].skip_reason == "validation_only"


def test_raw_refresh_writes_snapshot_and_manifest_with_fake_transport(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    transport = FakeTransport(payload=b"abc123")
    refresher = RawSnapshotRefresher(
        catalog=load_source_catalog(),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    manifest = refresher.refresh_source("production_pdq")

    assert transport.urls == [
        "https://mft.rrc.texas.gov/link/1f5ddb8d-329a-4459-b7f8-177b4f5ee60d"
    ]
    assert manifest.status == "downloaded"
    assert manifest.byte_size == 6
    assert (
        manifest.checksum_sha256
        == "6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090"
    )
    assert Path(manifest.raw_path).read_bytes() == b"abc123"

    manifest_path = tmp_path / "manifests" / "production_pdq-20260629T200000Z.json"
    assert manifest_path.exists()
    assert "production_pdq" in manifest_path.read_text(encoding="utf-8")


def test_raw_refresh_manifest_names_do_not_collide_with_same_second_attempts(
    tmp_path,
):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    refresher = RawSnapshotRefresher(
        catalog=load_source_catalog(),
        output_root=tmp_path,
        transport=FakeTransport(payload=b"abc123"),
        clock=fixed_clock,
    )

    refresher.refresh_source("production_pdq")
    refresher.refresh_source("production_pdq")

    manifests = sorted((tmp_path / "manifests").glob("production_pdq-*.json"))
    assert len(manifests) == 2


def test_raw_refresh_rejects_html_response_and_removes_partial_file(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    refresher = RawSnapshotRefresher(
        catalog=load_source_catalog(),
        output_root=tmp_path,
        transport=FakeTransport(payload=b"<html></html>", content_type="text/html"),
        clock=fixed_clock,
    )

    with pytest.raises(ValueError, match="HTML"):
        refresher.refresh_source("production_pdq")

    assert not list(tmp_path.rglob("*.part"))
    failure_manifest = tmp_path / "manifests" / "production_pdq-20260629T200000Z.json"
    assert failure_manifest.exists()
    assert '"status": "error"' in failure_manifest.read_text(encoding="utf-8")


def test_raw_refresh_rejects_content_length_mismatch(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    refresher = RawSnapshotRefresher(
        catalog=load_source_catalog(),
        output_root=tmp_path,
        transport=FakeTransport(payload=b"short", content_length=12),
        clock=fixed_clock,
    )

    with pytest.raises(ValueError, match="Content-Length"):
        refresher.refresh_source("production_pdq")

    assert not list(tmp_path.rglob("*.part"))
    assert not list((tmp_path / "raw").rglob("PDQ_DSV.zip"))
    failure_manifest = tmp_path / "manifests" / "production_pdq-20260629T200000Z.json"
    assert failure_manifest.exists()
    assert '"status": "error"' in failure_manifest.read_text(encoding="utf-8")


def test_raw_refresh_retries_transient_download_failure(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    transport = FakeTransport(
        payload=b"retry-success",
        errors=[OSError("temporary network failure"), None],
    )
    refresher = RawSnapshotRefresher(
        catalog=load_source_catalog(),
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    manifest = refresher.refresh_source("production_pdq")

    assert len(transport.urls) == 2
    assert manifest.status == "downloaded"
    assert Path(manifest.raw_path).read_bytes() == b"retry-success"
    assert not list(tmp_path.rglob("*.part"))


def test_raw_refresh_rejects_repo_output_root():
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    with pytest.raises(ValueError, match="git worktree"):
        RawSnapshotRefresher(
            catalog=load_source_catalog(),
            output_root=Path.cwd() / "data" / "texas_rrc",
            transport=FakeTransport(),
            clock=fixed_clock,
        )


def test_raw_refresh_rejects_repo_output_root_when_launched_elsewhere(
    tmp_path,
):
    import os

    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    original_cwd = Path.cwd()
    repo_output = original_cwd / "data" / "texas_rrc"
    os.chdir(tmp_path)

    try:
        with pytest.raises(ValueError, match="git worktree"):
            RawSnapshotRefresher(
                catalog=load_source_catalog(),
                output_root=repo_output,
                transport=FakeTransport(),
                clock=fixed_clock,
            )
    finally:
        os.chdir(original_cwd)


def test_raw_refresh_retries_get_transport_http_status_failure(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()
    catalog["production_pdq"] = {
        **catalog["production_pdq"],
        "download_strategy": "direct_http",
    }
    transport = GetOnlyTransport(
        FakeTransport(status_code=503),
        FakeTransport(payload=b"get-success"),
    )
    refresher = RawSnapshotRefresher(
        catalog=catalog,
        output_root=tmp_path,
        transport=transport,
        clock=fixed_clock,
    )

    manifest = refresher.refresh_source("production_pdq")

    assert len(transport.urls) == 2
    assert manifest.status == "downloaded"
    assert Path(manifest.raw_path).read_bytes() == b"get-success"


def test_raw_refresh_validates_injected_catalog_direct_urls(tmp_path):
    from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()
    catalog["production_pdq"] = {
        **catalog["production_pdq"],
        "download_url": "https://example.com/not-rrc.zip",
    }

    with pytest.raises(ValueError, match="official RRC host"):
        RawSnapshotRefresher(catalog=catalog, output_root=tmp_path)


def test_raw_refresh_cli_lists_and_dry_runs_without_network(tmp_path):
    from typer.testing import CliRunner

    from worldenergydata.cli.commands.texas_rrc import app

    runner = CliRunner()

    list_result = runner.invoke(app, ["refresh", "--list-sources"])
    assert list_result.exit_code == 0
    assert "production_pdq" in list_result.output
    assert "patchops_rrc_validation" in list_result.output
    assert "validation_only" in list_result.output

    dry_run_result = runner.invoke(
        app,
        [
            "refresh",
            "--dry-run",
            "--source",
            "production_pdq",
            "--output-root",
            str(tmp_path),
        ],
    )
    assert dry_run_result.exit_code == 0
    assert "production_pdq" in dry_run_result.output
    assert "planned" in dry_run_result.output
    assert not any(tmp_path.rglob("*"))
