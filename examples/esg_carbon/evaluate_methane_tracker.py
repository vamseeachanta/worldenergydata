"""Print the dated IEA publication assessment for an explicit intended use.

No sources are refreshed, data files ingested or abatement models imported.
See docs/data-sources/iea-methane-tracker-evaluation.md for the evidence limits.
"""

import argparse
import json
from dataclasses import asdict

from worldenergydata.esg_carbon import IntendedUse, evaluate_iea_methane_tracker


def main(argv: list[str] | None = None) -> None:
    """Serialize the existing offline assessment with standard-library JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intended-use",
        required=True,
        choices=[use.value for use in IntendedUse],
        help="Requested use of the dated publication assessment.",
    )
    args = parser.parse_args(argv)
    assessment = evaluate_iea_methane_tracker(args.intended_use)
    print(json.dumps(asdict(assessment), indent=2))


if __name__ == "__main__":
    main()
