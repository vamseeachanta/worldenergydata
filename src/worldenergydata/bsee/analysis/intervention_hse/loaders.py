"""Data loaders for the intervention-HSE Phase-2 package.

Reads the authoritative BSEE INCINV (accident-investigation) raw source — the
"gold" deep-incident surface #416 identified. Stdlib only; no heavy deps at import.

Extracted verbatim (behavior-preserving) from the #416 / #426 exploration scripts.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Default INCINV raw-source candidates. Prefer the in-repo path; fall back to the
# module external_data_root mount. Same candidate list the #426 script used.
_PKG_ROOT = Path(__file__).resolve().parents[3]  # src/worldenergydata
_REPO = _PKG_ROOT.parents[1]  # repo root (src/worldenergydata -> src -> repo)

DEFAULT_INCINV_CANDIDATES: Tuple[Path, ...] = (
    _REPO
    / "data"
    / "modules"
    / "hse"
    / "raw"
    / "bsee"
    / "IncInvRawData"
    / "mv_acc_investigations.txt",
    Path(
        "/mnt/ace/worldenergydata/data/modules/hse/raw/bsee/IncInvRawData"
        "/mv_acc_investigations.txt"
    ),
)


def resolve_incinv_source(
    candidates: Optional[Sequence[Path]] = None,
) -> Path:
    """Return the first existing, non-empty INCINV source path.

    Raises FileNotFoundError if none of the candidates resolve.
    """
    cands = (
        list(candidates) if candidates is not None else list(DEFAULT_INCINV_CANDIDATES)
    )
    src = next(
        (p for p in cands if Path(p).exists() and Path(p).stat().st_size > 0),
        None,
    )
    if src is None:
        raise FileNotFoundError(
            "INCINV source not found; checked: " + ", ".join(str(p) for p in cands)
        )
    return Path(src)


def load_incinv_file(path: Path) -> List[Dict[str, str]]:
    """Parse a single INCINV CSV file into a list of stripped-key/value dicts.

    Uses latin-1 (the BSEE source encoding) and strips whitespace from keys and
    string values, matching the #426 loader exactly.
    """
    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    (k or "").strip(): (v.strip() if isinstance(v, str) else v)
                    for k, v in r.items()
                }
            )
    return rows


def load_incinv_records(
    candidates: Optional[Sequence[Path]] = None,
) -> Tuple[Path, List[Dict[str, str]]]:
    """Resolve and load the INCINV records.

    Returns (resolved_source_path, rows). Mirrors the #426 ``_load_incinv``.
    """
    src = resolve_incinv_source(candidates)
    return src, load_incinv_file(src)
