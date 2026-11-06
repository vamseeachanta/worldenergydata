# Copyright (c) 2026 AceEngineer. Licensed under the MIT License.
"""Eval: Gulf of Mexico new-well permits by rig type (newsletter issue 2, Public data).

Runs the published counting script (examples/bsee/rawdata_fact_check/count_rawdata.py
at the commit named in results.json) on today's BSEE Application for Permit to
Drill file, and compares Table 1, the opening counts and Figure 1 with
results.json. Standard library only; it downloads about 4 MB from data.bsee.gov
and the published Figure 1 CSV from aceengineer.com.

    python examples/report-evals/issue-002-gom-well-permits/eval.py
    python examples/report-evals/issue-002-gom-well-permits/eval.py --compare my-results.json

The counting script must be in the clone. Until it is on the main branch, check
out the pinned commit and bring the eval files in (see PROMPT.md).
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import evalkit  # noqa: E402

REPO_ROOT = HERE.parents[2]
SCRIPT = "examples/bsee/rawdata_fact_check/count_rawdata.py"
FIG1_URL = ("https://www.aceengineer.com/assets/data/newsletter/issue-002/"
            "fig-p1-new-well-permits-by-rig-type.csv")
TYPES = {"Jack-up": "jackup", "Drillship": "drillship", "Semisubmersible": "semisub",
         "DP semisubmersible": "dp_semisub", "Platform rig": "platform_rig",
         "Submersible": "submersible", "Other": "other"}


def add_args(ap):
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT,
                    help="worldenergydata clone that holds the counting script")
    ap.add_argument("--script", type=Path, help="path of count_rawdata.py, if not in the clone")
    ap.add_argument("--cache", type=Path,
                    default=Path(tempfile.gettempdir()) / "report-evals-cache" / date.today().isoformat(),
                    help="folder for downloaded files (one folder per day by default)")


def compute(args):
    values, notes = {}, {}
    context = {"repo_root": str(args.repo_root), "repo_head": evalkit.git_head(args.repo_root)}
    script = args.script or args.repo_root / SCRIPT
    if not script.exists():
        msg = f"{SCRIPT} not in this checkout; check out the pinned commit (PROMPT.md step 1)"
        context["counting_script"] = msg
        return values, {"permits_all_2005_2026": msg}, context
    context["counting_script"] = {"path": SCRIPT if args.script is None else script.name,
                                  "sha256": evalkit.sha256_file(script)}
    self_test = subprocess.run([sys.executable, str(script), "--self-test"],
                               capture_output=True, text=True, encoding="utf-8", timeout=300)
    values["script_self_test_passed"] = self_test.returncode == 0 and "self-test passed" in self_test.stdout
    out_dir = args.cache / "apd-out"
    run = subprocess.run([sys.executable, str(script), "--data-dir", str(args.cache / "bsee-raw"),
                          "--out", str(out_dir), "--last-year", "2026"],
                         capture_output=True, text=True, encoding="utf-8", timeout=1800)
    if run.returncode != 0:
        raise RuntimeError(f"counting script failed: {run.stderr[-500:]}")
    counts = json.loads(run.stdout)
    context["bsee_files"] = counts["files"]
    permits = counts["permits"]
    values["permits_all_2005_2026"] = permits["all"]
    for name, key in TYPES.items():
        values[f"permits_{key}"] = permits["totals"][name]
        depth = permits["water_depth"][name]
        values[f"median_depth_ft_{key}"] = depth["median_ft"]
        values[f"min_depth_ft_{key}"] = depth["min_ft"]
        values[f"max_depth_ft_{key}"] = depth["max_ft"]
    by_year = {row["year"]: row for row in permits["by_year"]}
    for year in (2005, 2025):
        values[f"permits_{year}_total"] = by_year[year]["total"]
        values[f"permits_{year}_jackup"] = by_year[year]["Jack-up"]
        values[f"permits_{year}_drillship"] = by_year[year]["Drillship"]
    values["other_grouped_permits"] = sum(permits["other_grouped"].values())

    # Figure 1: compare every cell of 2005 to 2025 with the published CSV
    # (2026 is still being filled in the daily file).
    pub = evalkit.fetch(FIG1_URL, args.cache / "fig-p1-new-well-permits-by-rig-type.csv")
    context["fig1_csv"] = pub
    published = {int(r["year"]): r for r in csv.DictReader(open(pub["path"], encoding="utf-8"))}
    columns = ["total", *TYPES]
    differing = [(y, c) for y in range(2005, 2026) for c in columns
                 if int(published[y][c]) != int(by_year[y][c])]
    values["fig1_cells_differing_2005_2025"] = len(differing)
    if differing:
        notes["fig1_cells_differing_2005_2025"] = f"first differences: {differing[:5]}"
    context["fig1_2026_total"] = by_year[2026]["total"]
    notes["permits_all_2005_2026"] = (f"APD file sha256 {counts['files']['APDRawData.zip']['sha256'][:12]}..., "
                                      f"retrieved {counts['files']['APDRawData.zip']['retrieved_utc']}")
    return values, notes, context


if __name__ == "__main__":
    raise SystemExit(evalkit.main(HERE / "results.json", compute, add_args))
