# ABOUTME: Demand signal for HSE incident grounding — logs requests, ranks coverage gaps.
# ABOUTME: Misses (unknown / thin failure modes) name the next coverage to build (#491).

"""Grounding demand signal.

What turns the grounded-analysis stream (epic #486) from a static library into a
flywheel: log which failure modes get *requested*, then roll the log up into a
ranked list of coverage gaps. A request for a mode we don't have — or one whose
corpus is too thin to fill 2-latest + 2-severe — is the gold: it names the next
``FAILURE_MODES`` entry to add (feeding the coverage child #488).

Mirrors the deckhand demand-signal pattern (deckhand#368): read the signal, rank
into priority tiers, emit markdown.

Flow::

    from worldenergydata.hse.grounding_demand import ground_and_log, rollup, load_demand

    ground_and_log("riser_viv_fatigue")     # unknown -> logged as a GAP, re-raises
    ground_and_log("mooring_fatigue")        # covered -> logged as a HIT
    print(render_rollup_md(rollup(load_demand())))

CLI::

    python -m worldenergydata.hse.grounding_demand --rollup [--out FILE]
    python -m worldenergydata.hse.grounding_demand --record <failure_mode>

The log is JSONL (one request per line) so it is append-only and trivially
mergeable. ``MIN_COVERAGE`` is the corpus size needed to fill a card (2+2).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from worldenergydata.hse.grounding import FAILURE_MODES, ground

# Need >= 4 matched incidents to fill 2-latest + 2-highest-severity.
MIN_COVERAGE = 4

DEFAULT_LOG = (
    Path(__file__).resolve().parents[3] / "data/modules/hse/grounding_demand.jsonl"
)


def _today() -> str:
    return dt.date.today().isoformat()


def record_demand(
    failure_mode: str,
    *,
    covered: bool,
    n_incidents: int,
    reason: str = "",
    when: Optional[str] = None,
    log_path: str | Path = DEFAULT_LOG,
) -> dict[str, Any]:
    """Append one demand record (JSONL) and return it."""
    rec = {
        "when": when or _today(),
        "failure_mode": failure_mode,
        "covered": bool(covered),
        "n_incidents": int(n_incidents),
        "reason": reason,
    }
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def _matched_count(grounding) -> int:
    return sum(v for v in grounding.source_counts.values() if isinstance(v, int))


def ground_and_log(
    failure_mode: str,
    *,
    when: Optional[str] = None,
    log_path: str | Path = DEFAULT_LOG,
    bsee_path: Optional[Path] = None,
):
    """Run :func:`ground` and record the demand. Returns the Grounding.

    Records a GAP and re-raises ``KeyError`` for an unknown mode; records a GAP
    (``reason='thin_corpus'``) when a known mode matches < ``MIN_COVERAGE``; else
    records a HIT.
    """
    if failure_mode not in FAILURE_MODES:
        record_demand(
            failure_mode,
            covered=False,
            n_incidents=0,
            reason="unknown_mode",
            when=when,
            log_path=log_path,
        )
        raise KeyError(
            f"unknown failure_mode {failure_mode!r}; known: {sorted(FAILURE_MODES)}"
        )
    g = ground(failure_mode, bsee_path=bsee_path)
    n = _matched_count(g)
    covered = n >= MIN_COVERAGE
    record_demand(
        failure_mode,
        covered=covered,
        n_incidents=n,
        reason="" if covered else "thin_corpus",
        when=when,
        log_path=log_path,
    )
    return g


def load_demand(log_path: str | Path = DEFAULT_LOG) -> list[dict[str, Any]]:
    p = Path(log_path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def rollup(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate demand per failure mode and rank coverage gaps first.

    A mode is a GAP if it is unknown (not in ``FAILURE_MODES``) or its corpus is
    thin (every request saw < ``MIN_COVERAGE`` incidents). Gaps rank by request
    count (most-requested gap = build next).
    """
    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"requests": 0, "max_incidents": 0, "reasons": set()}
    )
    for r in records:
        a = agg[r["failure_mode"]]
        a["requests"] += 1
        a["max_incidents"] = max(a["max_incidents"], int(r.get("n_incidents", 0)))
        if r.get("reason"):
            a["reasons"].add(r["reason"])

    gaps, covered = [], []
    for mode, a in agg.items():
        known = mode in FAILURE_MODES
        is_gap = (not known) or a["max_incidents"] < MIN_COVERAGE
        entry = {
            "failure_mode": mode,
            "requests": a["requests"],
            "max_incidents": a["max_incidents"],
            "status": ("unknown" if not known else "thin" if is_gap else "covered"),
            "reasons": sorted(a["reasons"]),
        }
        (gaps if is_gap else covered).append(entry)

    gaps.sort(key=lambda e: (e["requests"], -ord(e["status"][0])), reverse=True)
    covered.sort(key=lambda e: e["requests"], reverse=True)
    return {
        "total_requests": sum(a["requests"] for a in agg.values()),
        "gaps": gaps,
        "covered": covered,
    }


def render_rollup_md(roll: dict[str, Any]) -> str:
    L = ["# HSE grounding — demand signal", ""]
    L.append(
        "> Generated by `worldenergydata.hse.grounding_demand` (#491). "
        "Ranks requested failure modes; **gaps are the next coverage to build** (#488)."
    )
    L.append("")
    L.append(
        f"**{roll['total_requests']} requests** · "
        f"{len(roll['gaps'])} coverage gap(s) · {len(roll['covered'])} covered."
    )
    L.append("")
    if roll["gaps"]:
        L.append("## Coverage gaps — build next (most-requested first)")
        L.append("")
        L.append("| Failure mode | Requests | Status | Max incidents |")
        L.append("|---|---:|---|---:|")
        for e in roll["gaps"]:
            L.append(
                f"| `{e['failure_mode']}` | {e['requests']} | {e['status']} "
                f"| {e['max_incidents']} |"
            )
        L.append("")
    if roll["covered"]:
        L.append("## Covered (served a full 2+2 card)")
        L.append("")
        for e in roll["covered"]:
            L.append(f"- `{e['failure_mode']}` — {e['requests']} request(s)")
    return "\n".join(L)


def _main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="HSE grounding demand signal")
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument(
        "--rollup", action="store_true", help="emit the ranked rollup (markdown)"
    )
    ap.add_argument(
        "--record", metavar="MODE", help="run + log a grounding request for MODE"
    )
    ap.add_argument("--out", help="write rollup markdown to FILE instead of stdout")
    a = ap.parse_args(argv)

    if a.record:
        try:
            g = ground_and_log(a.record, log_path=a.log)
            print(f"logged HIT: {a.record} ({_matched_count(g)} incidents)")
        except KeyError:
            print(f"logged GAP: {a.record} (unknown mode)")
        return 0

    md = render_rollup_md(rollup(load_demand(a.log)))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
