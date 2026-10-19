"""Emit an offline research catalog or keyword evidence report as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from worldenergydata.semiconductor.taxonomy import (
    ARTIFACTS,
    ROLES,
    SKILLS,
    SOURCES,
    match_roles,
)


def main(argv: list[str] | None = None) -> int:
    """Read caller-supplied text from stdin in match mode; write JSON to stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("catalog", "match"))
    args = parser.parse_args(argv)
    report = {
        "kind": "research_catalog",
        "sources": [asdict(source) for source in SOURCES],
        "skills": [asdict(skill) for skill in SKILLS],
        "roles": [asdict(role) for role in ROLES],
        "proposed_artifacts": [asdict(artifact) for artifact in ARTIFACTS],
        "assessment": {
            "artifact_completion": "NOT_EVALUATED",
            "engineering_acceptance": "NOT_EVALUATED",
            "hiring_demand": "NOT_EVALUATED",
            "suitability": "NOT_EVALUATED",
        },
        "limitations": (
            "Curated role families are research aids, not current job-market data.",
            "Keyword evidence is literal; context and negation require human review.",
            "Proposed artifacts are requirements to build, not completed work.",
        ),
    }
    if args.mode == "match":
        matches = match_roles(sys.stdin.read())
        role_ids = {match.role_id for match in matches}
        roles = [role for role in ROLES if role.id in role_ids]
        artifact_ids = {
            artifact_id for role in roles for artifact_id in role.artifact_ids
        }
        report.update(
            kind="keyword_evidence",
            matches=[asdict(match) for match in matches],
            roles=[asdict(role) for role in roles],
            proposed_artifacts=[
                asdict(artifact)
                for artifact in ARTIFACTS
                if artifact.id in artifact_ids
            ],
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
