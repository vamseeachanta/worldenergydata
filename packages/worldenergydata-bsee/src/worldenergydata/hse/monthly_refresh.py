# ABOUTME: Run configuration-driven monthly refreshes of public HSE sources.
# ABOUTME: Retain raw files, content digests and access outcomes on explicit storage.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import zipfile
from collections import Counter
from collections.abc import Callable, Iterable
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import httpx
import yaml

from worldenergydata.hse.monthly_refresh_fetch import (
    CitizenFetcher,
    FetchError,
    ListingParser,
    check_content,
    file_record,
    url_filename,
    validate_url,
)


@dataclass(frozen=True)
class SourceConfig:
    """One explicitly authorised public source and its storage instructions."""

    id: str
    authority: str
    description: str
    licence: str
    terms_url: str
    kind: str
    expect: str
    required: bool
    enabled: bool
    urls: tuple[str, ...]
    manual_drop_dir: str | None = None
    link_patterns: tuple[str, ...] | None = None
    link_classes: tuple[str, ...] | None = None


@dataclass(frozen=True)
class RefreshConfig:
    """Validated configuration, pinned to the bytes parsed by the loader."""

    schema_version: int
    user_agent: str
    sources: tuple[SourceConfig, ...]
    path: str
    sha256: str


class _UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node: Any, deep: bool = False) -> dict:
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError("duplicate or non-string YAML key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _keys(value: Any, required: set[str], optional: set[str]) -> None:
    if not isinstance(value, dict):
        raise ValueError("configuration entries must be mappings")
    if missing := required - value.keys():
        raise ValueError(f"missing fields: {', '.join(sorted(missing))}")
    if unknown := value.keys() - required - optional:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")


def _relative_path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\\" in value
        or ":" in value
        or PurePosixPath(value).is_absolute()
        or ".." in value.split("/")
        or not PurePosixPath(value).parts
        or any(not c.isprintable() for c in value)
    ):
        raise ValueError(
            "manual_drop_dir must be a non-empty relative path without traversal"
        )
    return value


def _link_selectors(value: dict) -> dict:
    selectors = {}
    for field in ("link_patterns", "link_classes"):
        if field not in value:
            continue
        if value["kind"] != "listing_page":
            raise ValueError(f"{field} is allowed only for listing_page sources")
        items = value[field]
        if not isinstance(items, list) or any(
            not isinstance(item, str) or not item.strip() for item in items
        ):
            raise ValueError(f"{field} must be a list of non-empty strings")
        for item in items:
            if field == "link_patterns":
                try:
                    re.compile(item)
                except re.error as exc:
                    raise ValueError(f"invalid link_patterns regex: {exc}") from exc
            elif any(c.isspace() for c in item):
                raise ValueError("link_classes entries must be single class tokens")
        selectors[field] = tuple(items)
    return selectors


def _source(value: Any) -> SourceConfig:
    required = {
        "id",
        "authority",
        "description",
        "licence",
        "terms_url",
        "kind",
        "expect",
        "required",
        "enabled",
        "urls",
    }
    _keys(value, required, {"manual_drop_dir", "link_patterns", "link_classes"})
    for field in ("id", "authority", "description", "licence", "kind", "expect"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", value["id"]):
        raise ValueError("id must match [a-z][a-z0-9_]*")
    if value["kind"] not in {"bulk_file", "listing_page", "manual"}:
        raise ValueError("invalid kind")
    if value["expect"] not in {"zip", "csv", "xlsx", "pdf", "html", "json"}:
        raise ValueError("invalid expect")
    for field in ("required", "enabled"):
        if type(value[field]) is not bool:
            raise ValueError(f"{field} must be boolean")
    validate_url(value["terms_url"])
    urls = value["urls"]
    if not isinstance(urls, list) or not urls:
        raise ValueError("urls must be a non-empty list")
    for url in urls:
        validate_url(url)
    if len(set(urls)) != len(urls):
        raise ValueError("duplicate URLs")
    if value["kind"] != "manual":
        names = [url_filename(url, value["expect"]).casefold() for url in urls]
        if len(set(names)) != len(names):
            raise ValueError("duplicate URL filenames")
    if value["kind"] == "manual" and "manual_drop_dir" not in value:
        raise ValueError("manual sources require manual_drop_dir")
    if "manual_drop_dir" in value:
        _relative_path(value["manual_drop_dir"])
    return SourceConfig(**(value | {"urls": tuple(urls)} | _link_selectors(value)))


def load_config(path: str | Path) -> RefreshConfig:
    """Read strict YAML; unknown fields, duplicate keys and invalid values fail."""
    try:
        raw = Path(path).read_bytes()
        value = yaml.load(raw.decode("utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read configuration: {exc}") from exc
    _keys(value, {"schema_version", "user_agent", "sources"}, set())
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    agent = value["user_agent"]
    if (
        not isinstance(agent, str)
        or not agent.strip()
        or any(ord(c) < 32 or ord(c) > 126 for c in agent)
    ):
        raise ValueError("user_agent must be non-empty printable ASCII")
    if not isinstance(value["sources"], list) or not value["sources"]:
        raise ValueError("sources must be a non-empty list")
    sources = tuple(_source(row) for row in value["sources"])
    if len({row.id for row in sources}) != len(sources):
        raise ValueError("duplicate source ids")
    return RefreshConfig(1, agent, sources, str(path), _sha(raw))


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _utc(now: datetime | None = None) -> str:
    value = now if now is not None else datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be a timezone-aware UTC datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _contained(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError("output path escapes output_root")
    return path


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".refresh-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(payload)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _json(path: Path, value: Any) -> None:
    _write(path, _json_bytes(value))


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def _commit(outputs: dict[Path, bytes]) -> None:
    """Restore prior evidence if any payload, manifest or latest write fails."""
    previous = {path: path.read_bytes() if path.exists() else None for path in outputs}
    written: list[Path] = []
    try:
        for path, payload in outputs.items():
            _write(path, payload)
            written.append(path)
    except OSError:
        for path in reversed(written):
            old = previous[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                _write(path, old)
        raise


def _latest(root: Path, source_id: str) -> dict:
    path = _contained(root, f"{source_id}/latest.json")
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("files"), list)
        or any(
            not isinstance(r, dict) or not isinstance(r.get("url"), str)
            for r in value["files"]
        )
        or not isinstance(value.get("month"), str)
    ):
        raise ValueError("invalid latest.json manifest")
    return value


def _manual(source: SourceConfig, root: Path, manifest: dict) -> None:
    drop = _contained(root, source.manual_drop_dir or "")
    for path in sorted(drop.iterdir()) if drop.is_dir() else []:
        if path.is_symlink():
            raise ValueError("manual files must not be symlinks")
        if path.is_file():
            manifest["files"].append(
                {
                    "name": path.name,
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha(path.read_bytes()),
                    "mtime": _utc(
                        datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                    ),
                }
            )
    manifest["status"] = "manual_present" if manifest["files"] else "manual_pending"
    if not manifest["files"]:
        manifest["reason"] = "Download manually from " + ", ".join(source.urls)


def _downloads(
    source: SourceConfig, fetcher: CitizenFetcher, manifest: dict, timestamp: str | None
) -> dict[str, bytes]:
    payloads = {}
    for url in source.urls:
        response = None
        try:
            response = fetcher.fetch(url)
            record = file_record(url, timestamp or _utc(), response)
            record["encoding"] = response.encoding or "utf-8-sig"
            record["members"] = check_content(
                response.content, source.expect, record["encoding"]
            )
            record["status"] = "success"
            payloads[url] = response.content
        except FetchError as exc:
            record = file_record(url, timestamp or _utc(), exc.response)
            record.update(status=exc.status, reason=str(exc), effective_url=exc.url)
        except (ValueError, zipfile.BadZipFile, RuntimeError, OSError, EOFError) as exc:
            record = file_record(url, timestamp or _utc(), response)
            record.update(status="unexpected_content", reason=str(exc))
        if source.kind == "listing_page":
            record["retained"] = "links_only"
        manifest["files"].append(record)
    manifest["status"] = next(
        (r["status"] for r in manifest["files"] if r["status"] != "success"), "success"
    )
    return payloads


def _reuse(root: Path, record: dict, old: dict | None, *, links_only: bool) -> bool:
    if not old or old.get("sha256") != record["sha256"]:
        return False
    if links_only:
        return True
    if not old.get("path"):
        return False
    path = _contained(root, old["path"])
    return path.is_file() and _sha(path.read_bytes()) == record["sha256"]


def _listing_outputs(
    source: SourceConfig, root: Path, manifest: dict, payloads: dict[str, bytes]
) -> dict[Path, bytes]:
    links: dict[str, str] = {}
    for record in manifest["files"]:
        parser = ListingParser(
            record["effective_url"], source.link_patterns, source.link_classes
        )
        parser.feed(payloads[record["url"]].decode(record["encoding"]))
        parser.close()
        for url, text in parser.links.items():
            if not links.get(url):
                links[url] = text
    if not links:
        manifest.update(status="no_links", reason="Listing pages yielded no kept links")
    index = [{"url": url, "text": links[url]} for url in sorted(links)]
    path = _contained(root, f"{source.id}/{manifest['month']}/links.json")
    return {path: _json_bytes(index)}


def _payload_path(
    root: Path, relative: str, payload: bytes, outputs: dict[Path, bytes]
) -> str:
    """Stage new bytes without replacing an existing or pending payload."""
    target = _contained(root, relative)
    candidates = (target, target.with_name(f"{_sha(payload)[:12]}-{target.name}"))
    for candidate in candidates:
        candidate = _contained(root, candidate.relative_to(root).as_posix())
        if candidate in outputs:
            if outputs[candidate] == payload:
                return candidate.relative_to(root).as_posix()
        elif candidate.exists():
            if candidate.read_bytes() == payload:
                return candidate.relative_to(root).as_posix()
        else:
            outputs[candidate] = payload
            return candidate.relative_to(root).as_posix()
    raise ValueError("digest-prefixed payload path contains different bytes")


def _store(
    source: SourceConfig, root: Path, manifest: dict, payloads: dict[str, bytes]
) -> dict[Path, bytes]:
    latest = _latest(root, source.id)
    previous = {row["url"]: row for row in latest.get("files", [])}
    unchanged = set(previous) == set(source.urls) and all(
        _reuse(
            root, r, previous.get(r["url"]), links_only=source.kind == "listing_page"
        )
        for r in manifest["files"]
    )
    if unchanged:
        manifest["status"] = "unchanged"
    if source.kind == "listing_page":
        return _listing_outputs(source, root, manifest, payloads)
    outputs: dict[Path, bytes] = {}
    for record in manifest["files"]:
        if unchanged:
            record["path"] = previous[record["url"]]["path"]
        else:
            filename = url_filename(record["url"], source.expect)
            relative = f"{source.id}/{manifest['month']}/{filename}"
            record["path"] = _payload_path(
                root, relative, payloads[record["url"]], outputs
            )
    return outputs


def _run_source(
    source: SourceConfig,
    root: Path,
    month: str,
    dry_run: bool,
    fetcher: CitizenFetcher,
    timestamp: str | None,
) -> dict:
    manifest: dict[str, Any] = {
        "source_id": source.id,
        "month": month,
        "status": "success",
        "files": [],
        "authority": source.authority,
        "description": source.description,
        "licence": source.licence,
        "terms_url": source.terms_url,
        "urls": list(source.urls),
    }
    outputs: dict[Path, bytes] = {}
    try:
        if not source.enabled:
            manifest["status"] = "skipped_disabled"
        elif dry_run:
            manifest["status"] = "dry_run"
        elif source.kind == "manual":
            _manual(source, root, manifest)
        else:
            payloads = _downloads(source, fetcher, manifest, timestamp)
            if manifest["status"] == "success":
                outputs = _store(source, root, manifest, payloads)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        manifest.update(status="failed", reason=str(exc))
        for record in manifest["files"]:
            record.pop("path", None)
    manifest["bytes"] = sum(r.get("bytes", 0) for r in manifest["files"])
    manifest["rows"] = sum(
        m.get("rows", 0) for r in manifest["files"] for m in r.get("members", [])
    )
    if not dry_run:
        path = _contained(root, f"{source.id}/{month}/manifest.json")
        try:
            outputs[path] = _json_bytes(manifest)
            if manifest["status"] in {"success", "unchanged"}:
                if month >= _latest(root, source.id).get("month", ""):
                    outputs[_contained(root, f"{source.id}/latest.json")] = _json_bytes(
                        manifest
                    )
            _commit(outputs)
        except (OSError, ValueError) as exc:
            manifest.update(status="failed", reason=str(exc))
            for record in manifest["files"]:
                record.pop("path", None)
            _json(path, manifest)
    return manifest


def run_refresh(
    config: RefreshConfig,
    output_root: str | Path | None,
    *,
    month: str | None = None,
    only: Iterable[str] | None = None,
    dry_run: bool = False,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Collect configured sources; dry runs return a summary without IO or requests."""
    started = _utc(now)
    month = month if month is not None else started[:7]
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month) or month.startswith("0000"):
        raise ValueError("month must be YYYY-MM")
    destination = (
        output_root
        if output_root is not None
        else os.environ.get("WED_HSE_SOURCES_ROOT")
    )
    if destination is None or not str(destination).strip():
        raise ValueError("output_root or WED_HSE_SOURCES_ROOT must be given explicitly")
    root = Path(destination).resolve()
    selected = (
        set([only] if isinstance(only, str) else only) if only is not None else None
    )
    if selected is not None and selected - {s.id for s in config.sources}:
        raise ValueError("unknown source id in --source")
    with ExitStack() as stack:
        if client is None:
            client = stack.enter_context(httpx.Client(timeout=300, trust_env=False))
        fetcher = CitizenFetcher(client, config.user_agent, sleep, clock)
        sources = [
            _run_source(
                s, root, month, dry_run, fetcher, started if now is not None else None
            )
            for s in config.sources
            if selected is None or s.id in selected
        ]
    passing = {"success", "unchanged", "manual_present", "skipped_disabled", "dry_run"}
    required = {s.id for s in config.sources if s.required}
    summary = {
        "sources": sources,
        "counts": dict(Counter(s["status"] for s in sources)),
        "required_failures": [
            s["source_id"]
            for s in sources
            if s["source_id"] in required and s["status"] not in passing
        ],
        "started_at_utc": started,
        "finished_at_utc": _utc(now),
        "config_path": config.path,
        "config_sha256": config.sha256,
    }
    if not dry_run:
        _json(_contained(root, "refresh-summary.json"), summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("config/hse/monthly_sources.yml")
    )
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--source", action="extend", nargs="+", dest="only")
    parser.add_argument("--month")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_refresh(
            load_config(args.config),
            args.output_root,
            month=args.month,
            only=args.only,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"refresh storage failure: {exc}", file=sys.stderr)
        return 1
    for source in result["sources"]:
        print(
            f"{source['source_id']} {source['status']} "
            f"{source['bytes']} bytes {source['rows']} rows",
            file=sys.stderr if args.json else sys.stdout,
        )
    if args.json:
        print(json.dumps(result, indent=2))
    return 1 if result["required_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
