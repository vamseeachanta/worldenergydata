#!/usr/bin/env python3
"""ABOUTME: Regenerate all V50 per-field economics reports in one process.
ABOUTME: Loads OGOR once (lru_cache shared) and writes field_economics_<dev>_v50.md.

V50 = latest OGOR-A window + verified first-oil corrections, matching
golden_baseline_v50.yml. Frozen V30 reports (*_v30.md) are untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "worldenergydata-bsee" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "lower_tertiary"))

import generate_field_economics_report as report  # noqa: E402

from worldenergydata.lower_tertiary.latest_runner import (  # noqa: E402
    FIRST_OIL_CORRECTIONS,
)
from worldenergydata.lower_tertiary.ops_timeline import (  # noqa: E402
    detect_latest_ogor_month,
    month_end_str,
)

PRODUCERS = [
    "Jack St Malo",
    "Stones",
    "Julia",
    "Big Foot",
    "Cascade Chinook",
    "Anchor",
    "Shenandoah",
    "Buckskin",
]


def main() -> None:
    source = report._ensure_ogor_loader()
    end_date = month_end_str(detect_latest_ogor_month())
    print(f"V50 reports: source={source} end_date={end_date}")
    out_dir = PROJECT_ROOT / "reports" / "lower_tertiary"
    out_dir.mkdir(parents=True, exist_ok=True)
    for dev in PRODUCERS:
        md = report.build_report(
            dev,
            end_date=end_date,
            first_oil_overrides=FIRST_OIL_CORRECTIONS,
            input_set="v50_kc" if dev == "Buckskin" else "v30",
        )
        slug = dev.lower().replace(" ", "_").replace("/", "_")
        path = out_dir / f"field_economics_{slug}_v50.md"
        path.write_text(md, encoding="utf-8")
        print(f"  wrote {path.name}")


if __name__ == "__main__":
    main()
