from pathlib import Path

import pandas as pd


def test_pass_pipeline():
    # all_yml status artifacts live under tests/unit/all_yml/. Resolve them
    # relative to this test file so the test is rootdir/cwd independent (it
    # previously hard-coded the cwd-relative, now-stale tests/modules/all_yml/
    # path and called itself at import time, which broke collection).
    all_yml_dir = Path(__file__).resolve().parents[1] / "all_yml"
    repo_yml_status_csv = all_yml_dir / "repo_yml_status.csv"
    summary_file = all_yml_dir / "yml_summary_pytest.txt"

    df = pd.read_csv(repo_yml_status_csv)
    tests_expected = len(df[df["Status"] == "Success"])  # Number of tests passed

    content = summary_file.read_text()

    tests_passed = None
    for line in content.splitlines():
        if "Tests passed:" in line:
            tests_passed = int(line.split(":")[1].strip())
            break

    assert (
        tests_expected == tests_passed
    ), f"Mismatch in tests passed: expected ({tests_expected}) != original ({tests_passed})"
