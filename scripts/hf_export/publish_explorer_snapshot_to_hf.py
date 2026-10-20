#!/usr/bin/env python3
"""Local preview by default; explicit authenticated atomic HF publication.

The HF SDK is imported only for live writes. Public raw readback sends no token.
See docs/data/field-explorer-snapshot.md for admission and migration requirements.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from explorer_snapshot import (
    build_from_git,
    canonical_json,
    publish_snapshot,
    require,
    resolve_url,
)


class PublicRedirect(HTTPRedirectHandler):
    """Public browser artifacts may follow only HTTPS same-origin HF redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        require(
            parsed.scheme == "https"
            and parsed.netloc == "huggingface.co"
            and not parsed.username
            and not parsed.password,
            "unapproved raw readback redirect",
        )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_public(request):
    return build_opener(PublicRedirect()).open(request)


class HuggingFaceBackend:
    def __init__(self, token):
        require(bool(token), "explicit authentication required")
        self._token = token

    def commit(self, dataset_id, parent, files):
        # HF API reference (retrieved 2026-10-20): one create_commit with
        # parent_commit guards concurrent changes; .oid is the new exact SHA.
        from huggingface_hub import CommitOperationAdd, HfApi

        operations = [
            CommitOperationAdd(path_in_repo=path, path_or_fileobj=data)
            for path, data in sorted(files.items())
        ]
        return (
            HfApi(token=self._token)
            .create_commit(
                repo_id=dataset_id,
                repo_type="dataset",
                operations=operations,
                parent_commit=parent,
                commit_message="Publish complete Explorer snapshot",
            )
            .oid
        )

    def read(self, dataset_id, sha, path):
        request = Request(resolve_url(dataset_id, sha, path))
        with _open_public(request) as response:
            require(
                response.headers.get("x-repo-commit") == sha,
                "raw response commit mismatch",
            )
            return response.read()


def main(argv=None, *, default_dataset=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--config", required=True, help="committed admission JSON path")
    parser.add_argument("--source-sha", required=True, help="exact clean source HEAD")
    parser.add_argument(
        "--dataset-id", required=default_dataset is None, default=default_dataset
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--dry-run", action="store_true", help="local and write-free (default)"
    )
    action.add_argument("--publish", action="store_true", help="explicit live mutation")
    parser.add_argument("--expected-parent", help="exact expected HF head SHA")
    parser.add_argument(
        "--accept-json-migration",
        action="store_true",
        help="confirm consumers have reviewed the analytical format migration",
    )
    args = parser.parse_args(argv)
    try:
        files = build_from_git(args.repo, args.config, args.source_sha, args.dataset_id)
        backend = None
        if args.publish:
            require(args.accept_json_migration, "analytical migration requires review")
            require(args.expected_parent, "expected parent required")
            backend = HuggingFaceBackend(os.environ.get("HF_TOKEN"))
        result = publish_snapshot(
            files, args.expected_parent, backend, dry_run=not args.publish
        )
        # A receipt exists only after every byte was verified. stdout can be
        # redirected by the caller; no partial receipt is ever written here.
        sys.stdout.buffer.write(canonical_json(result))
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, ImportError):
        # SDK/HTTP exceptions can contain credentials, paths or response bodies.
        print(
            "Snapshot failed; no verified publication receipt was produced.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
