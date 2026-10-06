#!/usr/bin/env python3
"""Build a local decision preview; publish only explicitly reviewed eligible exports."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "catalog_integration", ROOT / "src/worldenergydata/field_development/catalog_integration.py"
)
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


def optional_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--legacy", type=Path, default=ROOT / "data/modules/offshore_assets/curated/fields.csv")
    parser.add_argument("--parent-costs", type=Path, default=ROOT / "data/modules/cost/curated/sanctioned_projects.csv")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--match-decisions", type=Path)
    parser.add_argument("--eligibility", type=Path)
    parser.add_argument("--public-export", action="store_true")
    args = parser.parse_args()
    output, snapshot = args.output.resolve(), args.snapshot.resolve()
    if output == snapshot or snapshot in output.parents:
        parser.error("output must be outside the preserved original snapshot")
    bundle = API.build_integration(args.snapshot, args.legacy, args.parent_costs,
        decisions=optional_json(args.match_decisions), eligibility=optional_json(args.eligibility))
    if args.public_export:
        bundle = API.public_export(bundle)
    API.write_bundle(bundle, output)
    print(json.dumps({"state": bundle["manifest"]["state"], "counts": bundle["manifest"]["counts"],
                      "entities": bundle["manifest"]["entity_counts"], "output": str(output),
                      "authority_note": "Signoff metadata is evidence, not authenticated authority; operator must verify originating owner/action authorization."}, indent=2))


if __name__ == "__main__":
    main()
