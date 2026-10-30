"""Select Pages builders from changed inputs; emit GitHub Actions outputs.

Input ownership follows scripts/build_pages.py. Unknown report paths, shared
dependencies and removed inputs require a clean build (issue #528). The caller
must additionally require an exact cache hit for the diff's base revision.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterable

SHARED_FILES = frozenset(
    {
        "scripts/build_pages.py",
        "scripts/pages_scope.py",
        "scripts/site_nav.py",
        "scripts/lower_tertiary/war_methodology.py",
        "config/nav_spine.json",
        ".github/workflows/pages.yml",
    }
)

# Additional inputs read by builders outside their reports/<domain>/ directory.
EXTRA_INPUTS = {
    "reports/IMO_GISIS_Executive_Report.html": "marine_safety",
    "docs/intervention-db/intervention-stats-brief.html": "capabilities",
}


def select_domains(
    changes: Iterable[tuple[str, str]], known_domains: Iterable[str]
) -> tuple[bool, list[str]]:
    """Return (full_rebuild, domains), retaining registry order and unique keys.

    Every changed report must have a registered builder, even if other changed
    reports were attributed successfully. Deletions and file-type changes use
    a clean build because the copy-only builders cannot retire stale outputs.
    Git diff's --no-renames represents a move as deletion plus addition.
    """
    known = list(known_domains)
    selected = set()
    for status, path in changes:
        if path in SHARED_FILES or path.startswith("site_assets/"):
            return True, []
        if path in EXTRA_INPUTS:
            domain = EXTRA_INPUTS[path]
        elif path.startswith("reports/lower_tertiary_field_summary.md"):
            domain = "lower_tertiary"
        elif path.startswith("reports/"):
            domain = path.removeprefix("reports/").split("/")[0]
        else:
            continue
        if domain not in known or status not in {"A", "M"}:
            return True, []
        selected.add(domain)
    return False, [domain for domain in known if domain in selected]


def revision_scope(
    base: str, head: str, known_domains: Iterable[str]
) -> tuple[bool, list[str]]:
    """Diff complete push endpoints; unavailable history safely rebuilds all."""
    if not base:
        return True, []
    try:
        result = subprocess.run(
            ["git", "diff", "--no-renames", "--name-status", "-z", base, head, "--"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return True, []
    # Git -z emits alternating status/path fields without quoting filenames.
    fields = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    statuses = iter(fields[:-1])
    return select_domains(zip(statuses, statuses, strict=True), known_domains)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--event", default="push")
    args = parser.parse_args(argv)

    # Import the live registry rather than duplicate its domain list in CI.
    from build_pages import DOMAINS

    full, domains = (
        revision_scope(args.base, args.head, DOMAINS)
        if args.event == "push"
        else (True, [])
    )
    print(f"full={str(full).lower()}")
    print(f"domains={','.join(domains)}")


if __name__ == "__main__":
    main()
