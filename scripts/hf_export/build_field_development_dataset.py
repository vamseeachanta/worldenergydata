"""Prepare an offline field-development dataset candidate; never upload data.

The matched_concepts config projects the committed summary used by the matched
portfolio report. No economics, engineering coefficients or free-text notes
are exported. Hugging Face supports row-oriented JSON and named configs:
https://huggingface.co/docs/datasets/loading#json
https://huggingface.co/docs/hub/datasets-data-files-configuration

Usage: python scripts/hf_export/build_field_development_dataset.py --output "$OUTPUT"
The output directory must be outside the source repository. An identical partial
bundle can be resumed; differing or unrelated files are preserved and rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE = Path("reports/field_development/bsee_matched/_summary.json")

DATA_LIMITS = (
    "Committed catalogue-to-BSEE block matches only; not all offshore fields. "
    "Actual concepts originate in a commercial catalogue; recommendations are "
    "screening output, not qualified designs. Null actual/match means unknown "
    "ground truth. Source acquisition cut-off is not recorded. Source rights, "
    "absence of identifying content and engineering accuracy require review "
    "before publication. No economics or engineering design values are included."
)


def dataset_card() -> bytes:
    """Declare the stable config without claiming live publication or readiness."""
    return f"""---
license: cc-by-4.0
pretty_name: Field development matched concepts
configs:
  - config_name: matched_concepts
    data_files:
      - split: train
        path: matched_concepts.jsonl
---

# Field development matched concepts

Offline candidate for the worldenergydata-field-development dataset group.
The declared licence is the intended publication licence, pending source review.

## Data limits

{DATA_LIMITS}

## Qualification

NOT_EVALUATED: this export verifies projection consistency only. It does not
establish publication rights, absence of identifying content or design validity.
The candidate is not uploaded and is not an engineering input.

## Provenance

Source: `{SOURCE.as_posix()}`. Full source and output SHA-256 digests, byte counts
and coverage are recorded in `manifest.json`. The governing source definitions
are `PortfolioRow.is_match` and `summarize` in
`src/worldenergydata/field_development/portfolio_matched.py`.

## Columns

- `field_name`: source name, preserved verbatim; not a newly assigned identifier.
- `block`: source BSEE lease-block code, preserved verbatim.
- `actual`: catalogue as-built concept or null when unknown.
- `recommended`: screened concept or null when unavailable.
- `match`: true/false comparison only when actual is known; otherwise null.

No physical units apply to these categorical and boolean columns.
""".encode()


class InvalidSummary(ValueError):
    """The serialized source cannot satisfy the matched-summary contract."""


def unique_object(pairs: list[tuple]) -> dict:
    """Reject duplicate JSON keys before their evidence can be discarded."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidSummary("duplicate source key")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    """Reject the non-standard JSON tokens Python otherwise accepts."""
    raise InvalidSummary("non-finite source value")


def validate_summary(source: dict) -> None:
    """Reconcile source facts using portfolio_matched.summarize definitions."""
    if not isinstance(source, dict) or not isinstance(source.get("fields"), list):
        raise InvalidSummary("source must contain a fields array")
    rows = source["fields"]
    if not rows:
        raise InvalidSummary("empty fields array")
    identities = set()
    for row in rows:
        if not isinstance(row, dict):
            raise InvalidSummary("field must be an object")
        for key in ("name", "block", "actual", "recommended", "match"):
            if key not in row:
                raise InvalidSummary("missing field column: " + key)
        for key in ("name", "block", "actual", "recommended"):
            value = row[key]
            if value is None and key in ("actual", "recommended"):
                continue
            if not isinstance(value, str) or not value.strip():
                raise InvalidSummary("invalid field column: " + key)
        identity = (row["block"], row["name"])
        if identity in identities:
            raise InvalidSummary("duplicate field identity")
        identities.add(identity)
        # Source: PortfolioRow.is_match; null means no recorded ground truth.
        expected = (
            None if row["actual"] is None else row["actual"] == row["recommended"]
        )
        if row["match"] is not expected:
            raise InvalidSummary("inconsistent match value")
    n_actual = sum(row["actual"] is not None for row in rows)
    n_matched = sum(row["match"] is True for row in rows)
    counts = {"n_total": len(rows), "n_with_actual": n_actual, "n_matched": n_matched}
    for key, expected in counts.items():
        if type(source.get(key)) is not int or source[key] != expected:
            raise InvalidSummary("inconsistent summary count: " + key)
    # Source: portfolio_matched.summarize; no numeric tolerance is introduced.
    expected_rate = n_matched / n_actual if n_actual else 0.0
    rate = source.get("top1_match_rate")
    if type(rate) not in (int, float) or rate != expected_rate:
        raise InvalidSummary("inconsistent top1_match_rate")


def build_dataset(repo: Path) -> dict[str, bytes]:
    """Return the deterministic candidate files without writing anything."""
    raw = (repo / SOURCE).read_bytes()
    source = json.loads(
        raw, object_pairs_hook=unique_object, parse_constant=reject_constant
    )
    validate_summary(source)
    rows = [
        {
            "field_name": row["name"],
            **{key: row[key] for key in ("block", "actual", "recommended", "match")},
        }
        for row in source["fields"]
    ]
    rows.sort(key=lambda row: (row["block"], row["field_name"]))
    table = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    table_bytes = table.encode()
    card = dataset_card()
    manifest = {
        "schema_version": "1.0.0",  # Export contract version, not a physical value.
        "dataset_group": "worldenergydata-field-development",
        "source": {
            "path": SOURCE.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        },
        "configs": {
            "matched_concepts": {
                "path": "matched_concepts.jsonl",
                "sha256": hashlib.sha256(table_bytes).hexdigest(),
                "bytes": len(table_bytes),
                "rows": len(rows),
                "unknown_actual": sum(row["actual"] is None for row in rows),
            }
        },
        "card_sha256": hashlib.sha256(card).hexdigest(),
        "data_limits": DATA_LIMITS,
        "qualification": {
            "status": "NOT_EVALUATED",
            "reason": "Source rights, identifying-content review and engineering "
            "accuracy are not established by projection checks.",
        },
    }
    return {
        "matched_concepts.jsonl": table_bytes,
        "README.md": card,
        "manifest.json": (
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        ).encode(),
    }


def main(argv: list[str] | None = None) -> int:
    """Write or resume an identical bundle outside the source repository."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    repo, output = args.repo_root.resolve(), args.output.resolve()
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        raise ValueError("output and source repository overlap")
    files = build_dataset(repo)
    # Preflight all files before writing any. Existing differing data is preserved.
    if output.exists():
        if not output.is_dir() or any(
            path.name not in files for path in output.iterdir()
        ):
            raise ValueError("existing output contains unrelated data")
        for name, content in files.items():
            path = output / name
            if path.is_symlink() or (
                path.exists() and (not path.is_file() or path.read_bytes() != content)
            ):
                raise ValueError("existing output differs from candidate")
    output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = output / name
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(content)
        if path.read_bytes() != content:
            raise ValueError("output readback differs from candidate")
    manifest = json.loads(files["manifest.json"])
    count = manifest["configs"]["matched_concepts"]["rows"]
    print(f"matched_concepts: {count} rows; qualification NOT_EVALUATED; no upload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
