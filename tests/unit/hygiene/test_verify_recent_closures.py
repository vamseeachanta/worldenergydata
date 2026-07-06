"""Tests for the recently-closed-issue claimed-vs-shipped drift verifier (#368).

All tests exercise the PURE parsing/checking logic with an injected
path-existence checker — no live ``gh`` calls and no real filesystem access.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "hygiene"))

from verify_recent_closures import (  # noqa: E402
    IssueRef,
    analyze_issue,
    extract_referenced_paths,
    fetch_recent_closed_issues,
    find_checked_acceptance_boxes,
    find_unchecked_acceptance_boxes,
    make_repo_path_checker,
    render_report,
)

# --------------------------------------------------------------------------- #
# Checkbox parsing
# --------------------------------------------------------------------------- #


def test_unchecked_boxes_detected():
    body = (
        "## Acceptance criteria\n"
        "- [ ] Script exists\n"
        "- [x] Tests added\n"
        "- [ ] Wired into cron\n"
    )
    assert find_unchecked_acceptance_boxes(body) == [
        "Script exists",
        "Wired into cron",
    ]
    assert find_checked_acceptance_boxes(body) == ["Tests added"]


def test_all_checked_means_no_unchecked():
    body = "- [x] one\n- [X] two\n"
    assert find_unchecked_acceptance_boxes(body) == []
    assert find_checked_acceptance_boxes(body) == ["one", "two"]


def test_asterisk_bullets_and_empty_body():
    assert find_unchecked_acceptance_boxes("* [ ] todo item") == ["todo item"]
    assert find_unchecked_acceptance_boxes("") == []
    assert find_unchecked_acceptance_boxes(None) == []  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Path extraction
# --------------------------------------------------------------------------- #


def test_backtick_path_extraction():
    body = (
        "Created `scripts/hygiene/verify_recent_closures.py` and "
        "tests at `tests/unit/hygiene/test_verify.py`. "
        "See also `src/worldenergydata/foo.py`."
    )
    assert extract_referenced_paths(body) == [
        "scripts/hygiene/verify_recent_closures.py",
        "tests/unit/hygiene/test_verify.py",
        "src/worldenergydata/foo.py",
    ]


def test_path_extraction_ignores_non_paths_and_dedupes():
    body = (
        "Run `gh issue list` and visit `https://example.com/x.py`. "
        "Glob `data/*.csv` is not testable. "
        "Touch `data/catalog/data-catalog.yml` twice: "
        "`data/catalog/data-catalog.yml`. Also bare word `README`."
    )
    paths = extract_referenced_paths(body)
    assert "data/catalog/data-catalog.yml" in paths
    assert paths.count("data/catalog/data-catalog.yml") == 1  # de-duped
    assert "gh issue list" not in paths  # has spaces
    assert all("*" not in p for p in paths)  # globs excluded
    assert all(not p.startswith("http") for p in paths)  # urls excluded


def test_path_extraction_strips_leading_dotslash_and_trailing_punct():
    body = "see `./scripts/hygiene/x.py`, and `tests/unit/y.py`."
    assert extract_referenced_paths(body) == [
        "scripts/hygiene/x.py",
        "tests/unit/y.py",
    ]


# --------------------------------------------------------------------------- #
# analyze_issue (injected path checker)
# --------------------------------------------------------------------------- #


def _checker(existing: set[str]):
    return lambda p: p in existing


def test_unchecked_boxes_flagged():
    issue = IssueRef(
        number=1,
        title="do a thing",
        body="- [ ] not done yet\n- [x] done",
        url="u",
    )
    finding = analyze_issue(issue, _checker(set()))
    assert finding.has_drift
    assert finding.unchecked_boxes == ("not done yet",)
    assert finding.missing_paths == ()


def test_all_checked_and_existing_files_is_clean():
    issue = IssueRef(
        number=2,
        title="shipped",
        body="- [x] file made: `scripts/hygiene/x.py`\n- [x] tested",
        url="u",
    )
    finding = analyze_issue(issue, _checker({"scripts/hygiene/x.py"}))
    assert not finding.has_drift
    assert finding.unchecked_boxes == ()
    assert finding.missing_paths == ()


def test_referenced_but_missing_file_flagged():
    issue = IssueRef(
        number=3,
        title="claims a file",
        body="- [x] all good\nDelivered `scripts/hygiene/ghost.py`.",
        url="u",
    )
    finding = analyze_issue(issue, _checker({"scripts/hygiene/real.py"}))
    assert finding.has_drift
    assert finding.unchecked_boxes == ()
    assert finding.missing_paths == ("scripts/hygiene/ghost.py",)


def test_both_drift_types_at_once():
    issue = IssueRef(
        number=4,
        title="messy",
        body="- [ ] still open box\nMade `tests/unit/missing.py`.",
        url="u",
    )
    finding = analyze_issue(issue, _checker(set()))
    assert finding.unchecked_boxes == ("still open box",)
    assert finding.missing_paths == ("tests/unit/missing.py",)
    assert finding.has_drift


# --------------------------------------------------------------------------- #
# Real path checker (uses a tmp tree, not the repo)
# --------------------------------------------------------------------------- #


def test_make_repo_path_checker(tmp_path: Path):
    (tmp_path / "scripts" / "hygiene").mkdir(parents=True)
    (tmp_path / "scripts" / "hygiene" / "x.py").write_text("# hi")
    checker = make_repo_path_checker(tmp_path)
    assert checker("scripts/hygiene/x.py") is True
    assert checker("scripts/hygiene/nope.py") is False
    # path traversal escape is treated as not-found
    assert checker("../../../etc/passwd") is False


# --------------------------------------------------------------------------- #
# Report rendering + gh fetch parsing (injected runner)
# --------------------------------------------------------------------------- #


def test_render_report_clean_and_drifted():
    clean = render_report(
        [],
        owner_repo="o/r",
        since_days=30,
        scanned=5,
        today="2026-06-20",
    )
    assert "No claimed-vs-shipped drift detected" in clean
    assert "Issues scanned: 5" in clean

    from verify_recent_closures import IssueFinding

    drifted = render_report(
        [
            IssueFinding(
                number=7,
                title="bad",
                url="http://x/7",
                unchecked_boxes=("box one",),
                missing_paths=("scripts/ghost.py",),
            )
        ],
        owner_repo="o/r",
        since_days=30,
        scanned=1,
        today="2026-06-20",
    )
    assert "#7 — bad" in drifted
    assert "scripts/ghost.py" in drifted
    assert "box one" in drifted


def test_fetch_recent_closed_issues_with_injected_runner():
    payload = (
        '[{"number": 10, "title": "t", "body": "- [ ] x", '
        '"closedAt": "2026-06-01T00:00:00Z", "url": "http://x/10"}]'
    )
    issues = fetch_recent_closed_issues("o/r", 30, 40, runner=lambda cmd: payload)
    assert len(issues) == 1
    assert issues[0].number == 10
    assert issues[0].body == "- [ ] x"


def test_fetch_handles_empty_output():
    issues = fetch_recent_closed_issues("o/r", 30, 40, runner=lambda cmd: "")
    assert issues == []
