# Copyright (c) 2026 AceEngineer. Licensed under the MIT License.
"""Eval: Gulf of Mexico new-well permits by rig type (newsletter issue 2, Public data).

Runs the published counting script (examples/bsee/rawdata_fact_check/count_rawdata.py
at the commit named in results.json) on today's BSEE Application for Permit to
Drill file, and compares Table 1, the opening counts and Figure 1 with
results.json. Standard library only; it downloads about 4 MB from data.bsee.gov
and the published Figure 1 CSV from aceengineer.com.

    python examples/report-evals/issue-002-gom-well-permits/eval.py
    python examples/report-evals/issue-002-gom-well-permits/eval.py --compare my-results.json

The counting script is read from the pinned commit of the clone (fetched from
GitHub if the clone lacks it), so the eval runs from any checkout of
worldenergydata. With --script it runs that copy and grades whether its bytes
equal the pinned blob. With --data-dir it uses BSEE files the reader saved.
A failed source marks only its own results; the run record is always written.
"""

from __future__ import annotations

import csv
import hashlib
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
                    help="worldenergydata clone; the counting script is read from its pinned commit")
    ap.add_argument("--script", type=Path,
                    help="run this copy of count_rawdata.py; it is checked against the pinned commit")
    ap.add_argument("--data-dir", type=Path,
                    help="folder that already holds APDRawData.zip and IncInvRawData.zip")
    ap.add_argument("--cache", type=Path,
                    default=Path(tempfile.gettempdir()) / "report-evals-cache" / date.today().isoformat(),
                    help="folder for downloaded files (one folder per day by default)")


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def resolve_script(args, pin: str, values: dict, notes: dict, context: dict) -> Path:
    """Return the script to run, and grade its identity with the pinned commit."""
    blob = evalkit.git_blob(args.repo_root, pin, SCRIPT)
    if args.script is not None:
        script = args.script
        if blob is None:
            notes["script_matches_pinned_commit"] = "pinned commit not readable from --repo-root; identity not checked"
        else:
            values["script_matches_pinned_commit"] = _lf(script.read_bytes()) == _lf(blob)
    elif blob is not None:
        script = args.cache / f"count_rawdata-{pin[:12]}.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_bytes(blob)
        values["script_matches_pinned_commit"] = True
        notes["script_matches_pinned_commit"] = f"read from commit {pin[:12]} of the clone"
        context["code_mode"] = "historical"
    else:
        raise FileNotFoundError(f"{SCRIPT} at commit {pin[:12]} is not readable from {args.repo_root}; "
                                "clone worldenergydata (PROMPT.md step 1) or pass --script")
    context["counting_script"] = {"path": SCRIPT if args.script is None else script.name,
                                  "sha256_lf": hashlib.sha256(_lf(script.read_bytes())).hexdigest()}
    return script


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if out.returncode != 0:
        tail = out.stderr[-400:]
        if any(k in tail for k in ("URLError", "HTTPError", "urlopen", "TimeoutError", "ConnectionError")):
            raise OSError(f"BSEE download failed: {tail}")
        raise RuntimeError(f"counting script failed: {tail}")
    return out


def compute(args, values, notes, context):
    doc = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    pin = doc["code"]["commit"]
    ids = [r["id"] for r in doc["results"]]
    context.update(repo_root=str(args.repo_root), repo_head=evalkit.git_head(args.repo_root))
    state: dict = {}

    def counts():
        script = resolve_script(args, pin, values, notes, context)
        self_test = subprocess.run([sys.executable, str(script), "--self-test"],
                                   capture_output=True, text=True, encoding="utf-8", timeout=300)
        values["script_self_test_passed"] = self_test.returncode == 0 and "self-test passed" in self_test.stdout
        data_dir = args.data_dir or args.cache / "bsee-raw"
        run = _run([sys.executable, str(script), "--data-dir", str(data_dir),
                    "--out", str(args.cache / "apd-out"), "--last-year", "2026"], timeout=1800)
        result = json.loads(run.stdout)
        context["bsee_files"] = result["files"]
        permits = result["permits"]
        state["by_year"] = {row["year"]: row for row in permits["by_year"]}
        values["permits_all_2005_2026"] = permits["all"]
        for name, key in TYPES.items():
            values[f"permits_{key}"] = permits["totals"][name]
            depth = permits["water_depth"][name]
            values[f"median_depth_ft_{key}"] = depth["median_ft"]
            values[f"min_depth_ft_{key}"] = depth["min_ft"]
            values[f"max_depth_ft_{key}"] = depth["max_ft"]
        for year in (2005, 2025):
            row = state["by_year"][year]
            values[f"permits_{year}_total"] = row["total"]
            values[f"permits_{year}_jackup"] = row["Jack-up"]
            values[f"permits_{year}_drillship"] = row["Drillship"]
        values["other_grouped_permits"] = sum(permits["other_grouped"].values())
        apd = result["files"]["APDRawData.zip"]
        notes["permits_all_2005_2026"] = f"APD file sha256 {apd['sha256'][:12]}..., retrieved {apd['retrieved_utc']}"

    evalkit.guard([i for i in ids if i != "fig1_cells_differing_2005_2025"], values, notes, counts)

    def figure1():
        # Every cell of 2005 to 2025 against the published CSV (2026 is still being filled).
        by_year = state["by_year"]
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

    if "by_year" in state:
        evalkit.guard(["fig1_cells_differing_2005_2025"], values, notes, figure1)
    else:
        notes["fig1_cells_differing_2005_2025"] = "counts not available"


if __name__ == "__main__":
    raise SystemExit(evalkit.main(HERE / "results.json", compute, add_args))
