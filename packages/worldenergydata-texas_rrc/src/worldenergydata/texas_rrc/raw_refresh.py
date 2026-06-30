"""Raw snapshot refresh for Texas RRC official source data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from worldenergydata.texas_rrc.raw_directory import (
    DirectoryRefreshFile,
    DirectoryRefreshPlan,
    DirectorySelection,
    SnapshotArtifactManifest,
    build_directory_refresh_plan,
    cleanup_directory_staging,
    download_directory_files,
    promote_directory_files,
)
from worldenergydata.texas_rrc.raw_manifest import RefreshPlan, SnapshotManifest
from worldenergydata.texas_rrc.raw_transport import (
    DownloadedArtifact,
    RawRefreshTransport,
    RetryableDownloadError,
    TransportResponse,
    UrlLibTransport,
)
from worldenergydata.texas_rrc.source_catalog import (
    SOURCE_CATALOG_ROOT,
    load_source_catalog,
    validate_source_catalog,
)


class RawSnapshotRefresher:
    """Plan and execute official Texas RRC raw snapshot refreshes."""

    def __init__(
        self,
        catalog: dict[str, dict[str, Any]] | None = None,
        output_root: Path | str = SOURCE_CATALOG_ROOT,
        transport: RawRefreshTransport | None = None,
        clock: Callable[[], datetime] | None = None,
        max_attempts: int = 3,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.catalog = catalog or load_source_catalog()
        validate_source_catalog(self.catalog)
        self.output_root = Path(output_root)
        self._reject_repo_output_root()
        self.transport = transport or UrlLibTransport()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.max_attempts = max_attempts

    def plan_sources(
        self, source_ids: Iterable[str] | None = None
    ) -> list[RefreshPlan]:
        """Return refresh plans without touching the network."""
        ids = list(source_ids) if source_ids else sorted(self.catalog)
        return [self._plan_source(source_id) for source_id in ids]

    def discover_directory_source(
        self,
        source_id: str,
        selection: DirectorySelection | None = None,
        rows_per_page: int = 1000,
    ) -> DirectoryRefreshPlan:
        """List and select files for one official GoDrive directory source."""
        if source_id not in self.catalog:
            raise KeyError(f"Unknown Texas RRC source: {source_id}")
        entry = self.catalog[source_id]
        if entry["download_strategy"] != "official_godrive_directory":
            raise ValueError(f"Source '{source_id}' is not a GoDrive directory")
        list_directory = getattr(self.transport, "list_godrive_directory", None)
        if not list_directory:
            raise ValueError("Transport does not support official GoDrive directories")
        pages = list_directory(entry["download_url"], rows_per_page=rows_per_page)
        return build_directory_refresh_plan(
            source_id,
            entry,
            self.output_root,
            pages,
            selection or DirectorySelection(),
        )

    def refresh_source(
        self,
        source_id: str,
        selection: DirectorySelection | None = None,
        rows_per_page: int = 1000,
    ) -> SnapshotManifest:
        """Download one refreshable official-source snapshot and write a manifest."""
        if self.catalog[source_id]["download_strategy"] == "official_godrive_directory":
            return self._refresh_directory_source(source_id, selection, rows_per_page)

        plan = self._refreshable_plan(source_id)
        part_path = plan.target_path.with_suffix(plan.target_path.suffix + ".part")
        retrieved_at = self._timestamp()

        try:
            artifact = self._download_with_retries(plan, part_path)
            part_path.replace(plan.target_path)
            return self._write_success_manifest(plan, artifact, retrieved_at)
        except Exception as exc:
            self._write_error_manifest(plan, retrieved_at, part_path, exc)
            raise

    def _refresh_directory_source(
        self,
        source_id: str,
        selection: DirectorySelection | None,
        rows_per_page: int,
    ) -> SnapshotManifest:
        retrieved_at = self._timestamp()
        plan = self.discover_directory_source(source_id, selection, rows_per_page)
        staging = plan.target_path / f".staging-{source_id}-{retrieved_at}"
        try:
            artifacts = download_directory_files(
                plan,
                self.transport,
                staging,
                rows_per_page,
                self._validate_artifact,
                retrieved_at,
            )
            promote_directory_files(plan, staging)
            return self._write_directory_manifest(plan, retrieved_at, artifacts)
        except Exception as exc:
            cleanup_directory_staging(staging)
            self._write_directory_manifest(plan, retrieved_at, error=exc)
            raise

    def _refreshable_plan(self, source_id: str) -> RefreshPlan:
        plan = self._plan_source(source_id)
        if not plan.refreshable:
            raise ValueError(
                f"Source '{source_id}' is not refreshable: {plan.skip_reason}"
            )
        return plan

    def _download_with_retries(
        self,
        plan: RefreshPlan,
        part_path: Path,
    ) -> DownloadedArtifact:
        for attempt in range(1, self.max_attempts + 1):
            self._remove_partial(part_path)
            try:
                return self._download_artifact(plan, part_path)
            except RetryableDownloadError:
                if attempt == self.max_attempts:
                    raise
            except ValueError:
                raise
            except Exception:
                if attempt == self.max_attempts:
                    raise
        raise RuntimeError("download retry loop exited without a result")

    def _download_artifact(
        self,
        plan: RefreshPlan,
        part_path: Path,
    ) -> DownloadedArtifact:
        assert plan.download_url is not None
        if plan.download_strategy == "official_godrive_file":
            download_godrive_file_to = getattr(
                self.transport,
                "download_godrive_file_to",
                None,
            )
            if not download_godrive_file_to:
                raise ValueError("Transport does not support official GoDrive files")
            artifact = download_godrive_file_to(
                plan.download_url,
                part_path,
                plan.target_path.name,
            )
            self._validate_artifact(artifact)
            return artifact

        download_to = getattr(self.transport, "download_to", None)
        if download_to:
            artifact = download_to(plan.download_url, part_path)
            self._validate_artifact(artifact)
            return artifact

        response = self._download_response(plan)
        part_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.write_bytes(response.content)
        return DownloadedArtifact(
            headers=response.headers,
            effective_url=response.effective_url,
            checksum_sha256=hashlib.sha256(response.content).hexdigest(),
            byte_size=len(response.content),
        )

    def _download_response(self, plan: RefreshPlan) -> TransportResponse:
        assert plan.download_url is not None
        response = self.transport.get(plan.download_url)
        UrlLibTransport._validate_artifact_response(
            response.status_code,
            response.headers,
        )
        UrlLibTransport._validate_content_length(
            response.headers, len(response.content)
        )
        return response

    def _validate_artifact(self, artifact: DownloadedArtifact) -> None:
        UrlLibTransport._validate_content_length(artifact.headers, artifact.byte_size)

    def _write_success_manifest(
        self,
        plan: RefreshPlan,
        artifact: DownloadedArtifact,
        retrieved_at: str,
    ) -> SnapshotManifest:
        manifest = SnapshotManifest(
            source_id=plan.source_id,
            source_url=plan.source_url,
            download_url=plan.download_url,
            effective_url=artifact.effective_url,
            retrieved_at=retrieved_at,
            refresh_cadence=plan.refresh_cadence,
            raw_path=str(plan.target_path),
            checksum_sha256=artifact.checksum_sha256,
            byte_size=artifact.byte_size,
            status="downloaded",
        )
        self._write_manifest(manifest)
        return manifest

    def _write_error_manifest(
        self,
        plan: RefreshPlan,
        retrieved_at: str,
        part_path: Path,
        exc: Exception,
    ) -> SnapshotManifest:
        self._remove_partial(part_path)
        manifest = SnapshotManifest(
            source_id=plan.source_id,
            source_url=plan.source_url,
            download_url=plan.download_url,
            effective_url=None,
            retrieved_at=retrieved_at,
            refresh_cadence=plan.refresh_cadence,
            raw_path=str(plan.target_path),
            checksum_sha256=None,
            byte_size=0,
            status="error",
            error=str(exc),
        )
        self._write_manifest(manifest)
        return manifest

    def _write_directory_manifest(
        self,
        plan: DirectoryRefreshPlan,
        retrieved_at: str,
        artifacts: tuple[SnapshotArtifactManifest, ...] = (),
        error: Exception | None = None,
    ) -> SnapshotManifest:
        manifest = SnapshotManifest(
            source_id=plan.source_id,
            source_url=plan.source_url,
            download_url=plan.download_url,
            effective_url=None,
            retrieved_at=retrieved_at,
            refresh_cadence=plan.refresh_cadence,
            raw_path=str(plan.target_path),
            checksum_sha256=None,
            byte_size=sum(item.byte_size for item in artifacts),
            status="error" if error else "downloaded",
            error=str(error) if error else None,
            artifacts=artifacts,
        )
        self._write_manifest(manifest)
        return manifest

    def _remove_partial(self, part_path: Path) -> None:
        if part_path.exists():
            part_path.unlink()

    def _plan_source(self, source_id: str) -> RefreshPlan:
        if source_id not in self.catalog:
            raise KeyError(f"Unknown Texas RRC source: {source_id}")

        entry = self.catalog[source_id]
        strategy = entry["download_strategy"]
        target_path = self._target_path(entry)
        skip_reason = self._skip_reason(entry)

        return RefreshPlan(
            source_id=source_id,
            refreshable=skip_reason is None,
            download_strategy=strategy,
            source_url=entry["source_url"],
            download_url=entry.get("download_url"),
            target_path=target_path,
            refresh_cadence=entry["refresh_cadence"],
            skip_reason=skip_reason,
        )

    def _target_path(self, entry: dict[str, Any]) -> Path:
        raw_path = Path(entry["raw_path"])
        relative_raw = raw_path.relative_to(SOURCE_CATALOG_ROOT)
        target_dir = self.output_root / relative_raw
        filename = entry.get("snapshot_filename")
        if not filename:
            filename = Path(entry.get("download_url") or entry["source_url"]).name
        return target_dir / filename

    def _skip_reason(self, entry: dict[str, Any]) -> str | None:
        if entry["availability_status"] == "validation_only":
            return "validation_only"
        if not entry["source_of_record"]:
            return "not_source_of_record"
        if entry["download_strategy"] not in {"direct_http", "official_godrive_file"}:
            return entry["download_strategy"]
        return None

    def _timestamp(self) -> str:
        timestamp = self.clock()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _manifest_path(self, manifest: SnapshotManifest) -> Path:
        stamp = manifest.retrieved_at.replace("-", "").replace(":", "")
        manifest_dir = self.output_root / "manifests"
        base_path = manifest_dir / f"{manifest.source_id}-{stamp}.json"
        if not base_path.exists():
            return base_path
        for index in range(2, 10_000):
            candidate = manifest_dir / f"{manifest.source_id}-{stamp}-{index}.json"
            if not candidate.exists():
                return candidate
        raise RuntimeError("Unable to allocate unique snapshot manifest path")

    def _write_manifest(self, manifest: SnapshotManifest) -> Path:
        manifest_path = self._manifest_path(manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(manifest)
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest_path

    def _reject_repo_output_root(self) -> None:
        repo_root = self._find_repo_root(Path(__file__).resolve())
        if repo_root and self.output_root.resolve().is_relative_to(repo_root):
            raise ValueError("Raw refresh output_root must not be inside git worktree")

    @staticmethod
    def _find_repo_root(start: Path) -> Path | None:
        current = start.resolve()
        for path in (current, *current.parents):
            if (path / ".git").exists():
                return path
        return None


__all__ = [
    "RawSnapshotRefresher",
    "DownloadedArtifact",
    "DirectoryRefreshFile",
    "DirectoryRefreshPlan",
    "DirectorySelection",
    "RefreshPlan",
    "SnapshotArtifactManifest",
    "SnapshotManifest",
    "TransportResponse",
    "RetryableDownloadError",
    "UrlLibTransport",
]
