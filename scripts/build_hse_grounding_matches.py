"""Build a reproducible identifier note for riser and pressure candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from worldenergydata.hse.grounding import (
    FAILURE_MODES,
    _parse_date,
    corpus_vintage,
    default_bsee_path,
    load_bsee,
)

MODES = ("riser_viv_fatigue", "structural_overpressure")
ROOT = Path(__file__).resolve().parents[1]


def source_line(source: dict) -> str:
    """Keep source identity and acquisition-date evidence in the revision record."""
    if source["download_date"]:
        date_text = f"downloaded {source['download_date']}"
    elif source["data_added_commit_date"]:
        date_text = (
            "download date not recorded; data added to the repository by a "
            f"commit dated {source['data_added_commit_date']}"
        )
    else:
        date_text = (
            "download date not recorded; data-addition commit date not recorded "
            "(external corpus)"
        )
    return (
        f"Source: [{source['dataset_name']}]({source['download_url']}); "
        f"file `{source['file_name']}`; {date_text}."
    )


def build_note(corpus: Path, revisions: Path) -> str:
    """Render candidate identifiers using the production classifier's picks."""
    history = json.loads(revisions.read_text(encoding="utf-8"))
    current = history["revision"]
    if history["history"][-1]["revision"] != current:
        raise ValueError("Newest revision record does not match the declared revision")
    with corpus.open(encoding="latin-1") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("BSEE incident corpus is empty")
    lines = [
        "# Riser and pressure incident grounding candidates", "", "## Summary", "",
        f"Revision {current}. Corpus current to {corpus_vintage(corpus)}; "
        f"{len(rows):,} incident records. Accident classifications identify "
        "candidates; VIV, fatigue and overpressure causes are not established.", "",
        "## Revision history", "",
        "| Revision | Date | What changed and why |", "| --- | --- | --- |",
    ]
    for entry in history["history"]:
        lines.append(f"| {entry['revision']} | {entry['date']} | {entry['change']} |")
    lines += [
        "", "## Corpus basis", "",
        source_line(history["source"]),
        f"Corpus SHA-256: `{hashlib.sha256(corpus.read_bytes()).hexdigest()}`.", "",
        "Identifiers below combine incident date, recorded time, lease and area "
        "block; the source has no separate incident identifier. Empty fields "
        "are preserved. No operator column is included.", "",
        "## Classification limits", "",
        "On these corpus rows, `riser_viv_fatigue` is a subset of the existing "
        "`riser_fatigue` matches. `structural_overpressure` overlaps "
        "`fire_explosion` on gas-release-with-fire rows.",
        "",
        "Riser disconnect candidates require a join to "
        "incident text that confirms the cause before citation as VIV or fatigue "
        "precedent. Weather, "
        "emergency and dropped item classifications are excluded. A missing "
        "fatigue term cannot establish absence of fatigue.", "",
        "Gas and pressure releases, regulator failures, trapped well pressure "
        "and pressurized riser strings identify pressure-containment candidates. "
        "Overpressure and structural failure require corroboration. General "
        "shutdown, fire shutdown and glycol release do not qualify alone.",
    ]
    for key in MODES:
        lines += candidate_section(key, corpus, rows)
    return "\n".join(lines) + "\n"


def candidate_section(key: str, corpus: Path, rows: list[dict]) -> list[str]:
    mode = FAILURE_MODES[key]
    picks = load_bsee(mode, corpus)
    if len(picks) / len(rows) > 0.30:
        raise ValueError(f"{key} exceeds the 30% candidate-share criterion")
    identities = {(p.date, p.location, p.description) for p in picks}
    identifiers = []
    for row in rows:
        date = _parse_date(row.get("DATE_OCCURRED", ""))
        if date is None:
            continue
        location = " ".join(row[k].strip() for k in ("AREA_BLOCK", "LEASE_NUMBER")
                            if row[k].strip() and row[k].strip() != "Not Applicable") or "GoM (unspecified)"
        if (date.isoformat(), location, row["ACCIDENT_TYPE"].strip(" -")) in identities:
            identifiers.append("|".join((date.isoformat(), row["MILITARY_TIME"],
                                         row["LEASE_NUMBER"], row["AREA_BLOCK"])))
    if len(set(identifiers)) != len(picks):
        raise ValueError("Candidate identifiers are not unique")
    lines = ["", f"## {key}", "", f"{len(picks)} candidates "
              f"({len(picks) / len(rows):.1%} of the corpus).", ""]
    lines += [f"- `{identifier}`" for identifier in sorted(identifiers)]
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=default_bsee_path())
    parser.add_argument("--revisions", type=Path,
                        default=ROOT / "docs/hse/grounding-riser-revisions.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.corpus is None:
        parser.error("Live BSEE incident corpus is not present")
    args.output.write_text(build_note(args.corpus, args.revisions), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
