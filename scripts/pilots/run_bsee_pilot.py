#!/usr/bin/env python
# ABOUTME: Runnable dry-run for the wed#927 BSEE public run-ledger pilot (InMemoryHfPort,
# ABOUTME: NO HF network) + a gated, execution-only live-publish entry point (DO NOT auto-run).
"""BSEE production-summary run-ledger pilot (worldenergydata#927).

Dry run (default): drives V1-V3 + one exact replay through
projection -> promotion -> InMemoryHfPort -> source-repo Ledger, writes the
rolling HTML report, and prints a summary. Exits 0 on success. NO Hugging Face
network, NO real publish.

    uv run --python 3.11 --with-editable <assetutilities-main-checkout> \\
        --with huggingface_hub python scripts/pilots/run_bsee_pilot.py

Live publish (gated, execution-only, NEVER in CI): pushes the projection to the
real Hugging Face dataset ``aceengineer/worldenergydata-runs`` via the real
HfPort. It requires ALL of: explicit owner go-ahead (``--yes-publish-to-hf``), a
WRITE-scope token in ``HF_TOKEN`` (read by huggingface_hub itself, never passed
here), AND -- for a PUBLIC / cc-by-4.0 / source_authority:BSEE dataset -- a
committed REAL public-domain BSEE extract (``publication.is_real_extract: true``
in the config). Errors are scrubbed of anything token-adjacent.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys


def _dry_run(write_report: bool) -> int:
    logging.disable(logging.CRITICAL)  # silence the chatty wed engine
    from worldenergydata.workflow_api import bsee_pilot as P

    summary = P.run_pilot(write_report=write_report)
    print("=" * 72)
    print("BSEE production-summary run-ledger pilot — DRY RUN (InMemoryHfPort)")
    print("=" * 72)
    print("run_ids:")
    for vid, rid in summary["run_ids"].items():
        print(f"  {vid}: {rid}")
    r = summary["replay"]
    print(f"exact replay: variant={r['variant']} same_run_id={r['same_run_id']}")
    print("in-memory HF revisions (immutable, content-addressed):")
    for vid, rev in summary["revisions"].items():
        print(f"  {vid}: {rev}")
    print(f"accepted: {summary['accepted_count']}  rejected: {summary['rejected_count']}")
    print(f"ledger-eligible run_ids: {len(summary['eligible_run_ids'])}")
    vis = summary["visibility"]
    label = "PUBLIC/cc-by-4.0/BSEE" if vis["public"] else "PRIVATE/synthetic-derived"
    print(f"visibility (MAJOR-1 gate): {label}  license={vis['license']}")
    print("metrics:")
    for vid, m in summary["metrics"].items():
        print(f"  {vid}: {json.dumps(m)}")
    print("ledger (publications.jsonl rows):")
    for row in summary["ledger"]:
        print(f"  {json.dumps({k: row[k] for k in ('run_id', 'hf_revision', 'state')})}")
    print(f"report path: {summary['report_path']}")
    ok = (
        summary["accepted_count"] == 3
        and summary["replay"]["same_run_id"] is True
        and len(set(summary["run_ids"].values())) == 3
    )
    print("RESULT:", "GREEN" if ok else "FAILED")
    return 0 if ok else 1


def _live_publish(assume_yes: bool) -> int:
    """Execution-only real HF publish. Gated; never run in CI."""
    logging.disable(logging.CRITICAL)
    from assetutilities.workflow_api.publication.hf_port import (
        HfError,
        HuggingFaceHubHfPort,
    )
    from worldenergydata.workflow_api import bsee_pilot as P

    config = P.load_config()
    vis = P.resolve_visibility(config)
    if not assume_yes:
        print("REFUSING: live HF publish requires --yes-publish-to-hf (owner go-ahead).",
              file=sys.stderr)
        return 2
    # MAJOR-1: a PUBLIC/federal dataset requires a committed REAL extract.
    for v in config["variants"]:
        d = P.build_snapshot_descriptor(config, v["snapshot"], v["api12"])
        P.assert_federal_claim_allowed(d)  # raises if a federal claim lacks a real extract
    repo_id = config["publication"]["hf_repo"]
    try:
        # The token is resolved by huggingface_hub from HF_TOKEN — never passed here.
        port = HuggingFaceHubHfPort(repo_id=repo_id, private=vis["private"])
        summary = P.run_pilot(config=config, hf_port=port, write_report=True)
    except HfError as exc:  # already scrubbed of token-adjacent detail by the port
        print(f"live publish failed (scrubbed): {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # defence-in-depth: never echo a raw, unclassified error
        print(f"live publish failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"published {summary['accepted_count']} runs to {repo_id} "
          f"({'public' if vis['public'] else 'private'})")
    for vid, rev in summary["revisions"].items():
        print(f"  {vid}: {rev}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="wed#927 BSEE run-ledger pilot")
    parser.add_argument("--write-report", action="store_true",
                        help="write the rolling HTML report to the configured path")
    parser.add_argument("--live-publish", action="store_true",
                        help="GATED: push to the real Hugging Face dataset (execution-only)")
    parser.add_argument("--yes-publish-to-hf", action="store_true",
                        help="explicit owner go-ahead required for --live-publish")
    args = parser.parse_args(argv)
    if args.live_publish:
        return _live_publish(assume_yes=args.yes_publish_to_hf)
    return _dry_run(write_report=args.write_report)


if __name__ == "__main__":
    raise SystemExit(main())
