"""Tests for the recently-closed-issue claimed-vs-shipped drift verifier (#368).

Parsing tests use injected checkers; filesystem tests use temporary trees.
No test makes live ``gh`` calls. Symlink expectations follow issue #368's
``test -L`` requirement: the link itself must exist, including dangling links.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "hygiene"))

from verify_recent_closures import (  # noqa: E402
    DEFAULT_SINCE_DAYS,
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


def _symlink_issue(body: str) -> IssueRef:
    return IssueRef(number=368, title="Symlink presence", body=body)


def test_symlink_claim_distinguishes_regular_and_dangling_paths(tmp_path: Path):
    from verify_recent_closures import make_repo_link_checker

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "regular").write_text("present")
    (tmp_path / "data" / "valid").symlink_to("regular")
    (tmp_path / "data" / "dangling").symlink_to("absent")
    exists = make_repo_path_checker(tmp_path)
    is_link = make_repo_link_checker(tmp_path)
    # Independent truth table from #368's test -L semantics, not path existence.
    cases = {"valid": True, "dangling": True, "regular": False, "missing": False}
    for name, expected in cases.items():
        path = f"data/{name}"
        finding = analyze_issue(
            _symlink_issue(f"- [x] Symlink `{path}` is present."), exists, is_link
        )
        assert is_link(path) is expected
        assert finding.missing_symlinks == (() if expected else (path,))
        assert finding.missing_paths == ()
        assert finding.has_drift is not expected


def test_symlink_claim_rejects_parent_escape(tmp_path: Path, monkeypatch):
    from verify_recent_closures import make_repo_link_checker

    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (outside / "link").symlink_to("absent")
    (repo / "data").symlink_to(outside, target_is_directory=True)
    inspected = []
    original = Path.is_symlink

    def record_inspection(path):
        inspected.append(path)
        return original(path)

    monkeypatch.setattr(Path, "is_symlink", record_inspection)
    checker = make_repo_link_checker(repo)
    assert checker("data/link") is False
    assert inspected == []  # Reject the parent before inspecting an external link.
    finding = analyze_issue(
        _symlink_issue("- [x] Symlink present: `data/link`"),
        make_repo_path_checker(repo),
        checker,
    )
    assert finding.missing_symlinks == ("data/link",)
    assert inspected == []


def test_link_checker_rejects_traversal_and_absolute_paths(tmp_path: Path):
    from verify_recent_closures import make_repo_link_checker

    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "link").symlink_to("absent")
    checker = make_repo_link_checker(repo)
    assert checker("../link") is False
    assert checker("data/../../link") is False
    assert checker(str(tmp_path / "link")) is False
    assert checker("") is False
    assert checker(".") is False


def test_link_checker_resolves_only_parent_and_handles_parent_loop(tmp_path: Path):
    from verify_recent_closures import make_repo_link_checker

    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "alias").symlink_to("data", target_is_directory=True)
    (repo / "data" / "link").symlink_to(tmp_path / "external-target")
    (repo / "loop").symlink_to("loop")
    checker = make_repo_link_checker(repo)
    assert checker("alias/link") is True
    assert checker("loop/link") is False


def test_symlink_claims_use_injected_checker_and_preserve_generic_mentions():
    calls = []

    def is_link(path):
        calls.append(path)
        return True

    finding = analyze_issue(
        _symlink_issue(
            "- [X] Symbolic link `./data/link` exists\n"
            "- [x] Symlink present: `data/link`\n"
            "Delivered `data/link`.\n"
        ),
        _checker(set()),
        is_link,
    )
    assert calls == ["data/link"]  # Duplicate claims need one presence check.
    assert finding.missing_symlinks == ()
    assert finding.missing_paths == ("data/link",)


def test_unrecognized_symlink_prose_remains_unverified():
    claims = (
        "Symlink `data/link` might be generated by `touch data/link`",
        "Symlink `../link` exists",
        "Symlink `data/link` is present and executable",
    )

    def unexpected_check(path):
        raise AssertionError("Unrecognized claims must not be checked")

    finding = analyze_issue(
        _symlink_issue("\n".join(f"- [x] {claim}" for claim in claims)),
        unexpected_check,
        unexpected_check,
    )
    assert finding.unverified_symlink_claims == claims
    assert finding.missing_paths == ()
    assert finding.has_drift


def test_symlink_claim_without_checker_is_unverified():
    claim = "Symlink `data/link` exists"
    finding = analyze_issue(_symlink_issue(f"- [x] {claim}"), _checker(set()))
    assert finding.unverified_symlink_claims == (claim,)
    assert finding.missing_symlinks == ()
    assert finding.missing_paths == ()


def test_unchecked_symlink_claim_is_still_incomplete():
    claim = "Symlink present: `link`"
    finding = analyze_issue(
        _symlink_issue(f"- [ ] {claim}"), _checker(set()), _checker({"link"})
    )
    assert finding.unchecked_boxes == (claim,)
    assert finding.missing_symlinks == ()
    assert finding.has_drift


def test_symlink_findings_render_in_existing_report():
    findings = [
        analyze_issue(
            _symlink_issue("- [x] Symlink `data/link` exists"),
            _checker(set()),
            _checker(set()),
        ),
        analyze_issue(
            _symlink_issue("- [x] Symlink `data/other` might exist"),
            _checker(set()),
            _checker(set()),
        ),
    ]
    report = render_report(
        findings,
        owner_repo="o/r",
        since_days=DEFAULT_SINCE_DAYS,
        scanned=len(findings),
    )
    assert "Claimed symlink missing or not a symlink" in report
    assert "`data/link`" in report
    assert "Symlink claims unverified" in report
    assert "Symlink `data/other` might exist" in report


def test_main_injects_link_checker_without_live_github(
    tmp_path: Path, monkeypatch, capsys
):
    import verify_recent_closures as verifier

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "link").symlink_to("absent")
    monkeypatch.setattr(
        verifier,
        "fetch_recent_closed_issues",
        lambda *args: [_symlink_issue("- [x] Symlink `data/link` exists")],
    )
    # CLI status values follow its existing clean/drift contract.
    assert verifier.main(["--repo-root", str(tmp_path), "--no-report"]) == 0
    assert "No claimed-vs-shipped drift detected" in capsys.readouterr().out
    monkeypatch.setattr(
        verifier,
        "fetch_recent_closed_issues",
        lambda *args: [_symlink_issue("- [x] Symlink `data/missing` exists")],
    )
    assert verifier.main(["--repo-root", str(tmp_path), "--no-report"]) == 1
    assert "Claimed symlink missing or not a symlink" in capsys.readouterr().out


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
