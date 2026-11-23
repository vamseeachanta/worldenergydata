"""List publication-link metadata from saved ANP HTML without network access."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from worldenergydata.brazil_anp.production.source_discovery import (
    NATIONAL_PRODUCTION_INDEX,
    WELL_PRODUCTION_INDEX,
    parse_production_resources,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file", type=Path, help="Saved UTF-8 index HTML file")
    indexes = {"well": WELL_PRODUCTION_INDEX, "national": NATIONAL_PRODUCTION_INDEX}
    parser.add_argument("--index", choices=indexes, required=True)
    args = parser.parse_args()

    try:
        html = args.html_file.read_text(encoding="utf-8")
        resources = parse_production_resources(html, index_url=indexes[args.index])
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps([asdict(resource) for resource in resources], ensure_ascii=False))


if __name__ == "__main__":
    main()
