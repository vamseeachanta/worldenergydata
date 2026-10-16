"""Offline CLI regressions for mechanical knowledge-pack checks."""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "pack_lint.py"
PASS = Path(__file__).with_name("pack_lint_fixtures") / "pass.md"
API = ".".join(("api", "github", "com"))
ISSUE = "/".join(
    ("https:", "", "github.com", "example-owner", "example-repo", "issues", "12")
)
BAD_ROLE = "project" + " manager"
OTHER_ROLE = "dis" + "patcher"
ACCOUNT_WARNING = (
    "warning: account-name check skipped: no account given "
    "(use --account NAME or set GITHUB_REPOSITORY_OWNER); "
    "issue and pull-request URLs are still checked\n"
)

# Each negative fixture changes exactly one place in the passing pack.
EDITS = {
    "S10": lambda pack: edit(
        pack, "## 10. Coverage and open items", "## Coverage and open items"
    ),
    "SWEEP": lambda pack: edit(pack, "sweep: 2 found", "Two sweep findings"),
    "NODE": lambda pack: edit(
        pack, "tests/unit/test_example.py::test_missing", "TestX::test_y"
    ),
    "URL": lambda pack: edit(pack, "See #123.", "See " + API + "."),
    "DRAFT": lambda pack: edit(pack, "issue pending (1)", "issue pending"),
    "ROLE": lambda pack: edit(
        pack, "before the maintainer merges", "before the " + BAD_ROLE + " merges"
    ),
    "TABLE": lambda pack: edit(pack, "| Counter |", "\n| Counter |"),
}


@pytest.fixture(autouse=True)
def clear_owner(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY_OWNER", raising=False)


@pytest.fixture
def pack(tmp_path):
    path = tmp_path / "agent-pack.md"
    path.write_bytes(PASS.read_bytes())
    return path


def run(*args, default_account=True):
    account = ["--account", "example-owner"] if default_account else []
    return subprocess.run(
        [sys.executable, str(SCRIPT), *account, *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def edit(pack, old, new):
    text = pack.read_text()
    assert text.count(old) == 1
    pack.write_text(text.replace(old, new, 1))
    return text[: text.index(old)].count("\n") + 1


def assert_clean(result, count=1, stderr=""):
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == stderr
    assert result.stdout.rstrip().endswith(
        f"pack_lint: clean (0 failure(s) in {count} file(s))"
    )


def assert_rule(result, rule, locations, stderr=""):
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr == stderr
    lines = [line for line in result.stdout.splitlines() if ": " + rule + ": " in line]
    failures = [
        line
        for line in result.stdout.splitlines()
        if re.match(r"^.+:\d+: [A-Z0-9]+: .+", line)
    ]
    assert lines == failures, result.stdout
    assert {line.split(": ", 2)[1] for line in failures} == {rule}
    assert {line.split(": " + rule + ":", 1)[0] for line in lines} == {
        f"{path}:{number}" for path, number in locations
    }
    assert result.stdout.rstrip().endswith(
        f"pack_lint: FAILED ({len(lines)} failure(s) in "
        f"{len({path for path, _ in locations})} file(s))"
    )


def test_pass():
    assert_clean(run(PASS))


@pytest.mark.parametrize("rule", EDITS)
def test_one_edit_one_rule(pack, rule):
    number = EDITS[rule](pack)
    if rule in {"S10", "SWEEP"}:
        number = 1
    assert_rule(run(pack), rule, [(pack, number)])


@pytest.mark.parametrize("account", [None, "example-owner"])
@pytest.mark.parametrize("url", [API, ISSUE])
def test_url_forms(pack, account, url):
    number = edit(pack, "See #123.", "See " + url + ".")
    args = [] if account is None else ["--account", account]
    assert_rule(
        run(*args, pack, default_account=False),
        "URL",
        [(pack, number)],
        stderr=ACCOUNT_WARNING if account is None else "",
    )


def test_account_url(pack):
    url = "/".join(("https:", "", "example.org", "example-owner", "notes"))
    number = edit(pack, "See #123.", "See " + url + ".")
    assert_rule(run("--account", "example-owner", pack), "URL", [(pack, number)])


def test_account_prose_is_allowed():
    assert_clean(run("--account", "example-owner", PASS))


def test_environment_account(pack, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "example-owner")
    number = edit(pack, "See #123.", "See https://example.org/example-owner.")
    assert_rule(run(pack, default_account=False), "URL", [(pack, number)])


def test_explicit_account_overrides_environment(pack, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "other-owner")
    number = edit(pack, "See #123.", "See https://example.org/example-owner.")
    assert_rule(run("--account", "example-owner", pack), "URL", [(pack, number)])


@pytest.mark.parametrize(
    "node,valid",
    [
        ("TestX::test_y", False),
        ("test_x.py::test_y", False),
        ("tests/unit/test_x.py::TestX::test_y", True),
        ("pkg/tests/test_x.py::test_y", True),
        ("src/pkg/mod.py::function_name", True),
    ],
)
def test_node_forms(pack, node, valid):
    number = edit(pack, "tests/unit/test_example.py::test_missing", node)
    result = run(pack)
    if valid:
        assert_clean(result)
    else:
        assert_rule(result, "NODE", [(pack, number)])


@pytest.mark.parametrize(
    "prose", ["issue-pending markers", "issue pending (n)", "issue pending draft 3"]
)
def test_pending_prose(pack, prose):
    edit(pack, "issue pending (1)", prose)
    assert_clean(run(pack))


@pytest.mark.parametrize(
    "entry",
    [
        "Draft 1: Example",
        "**Draft 1:** Example",
        "- **Draft 1:** Example",
        "## Draft 1: Example",
        "* Draft 1: Example",
        "dRaFt 1: Example",
    ],
)
def test_draft_entry_forms(pack, tmp_path, entry):
    drafts = tmp_path / "drafts.md"
    drafts.write_text(entry + "\n")
    assert_clean(run("--drafts", drafts, pack))


def test_missing_draft_entry(pack, tmp_path):
    drafts = tmp_path / "drafts.md"
    drafts.write_text("(2) Another draft\n")
    number = next(
        i
        for i, line in enumerate(pack.read_text().splitlines(), 1)
        if "issue pending" in line
    )
    assert_rule(run("--drafts", drafts, pack), "DRAFT", [(pack, number)])


def test_unreadable_draft_list(pack, tmp_path):
    number = next(
        i
        for i, line in enumerate(pack.read_text().splitlines(), 1)
        if "issue pending" in line
    )
    assert_rule(
        run("--drafts", tmp_path / "absent.md", pack), "DRAFT", [(pack, number)]
    )


def test_without_drafts_note():
    result = run(PASS)
    assert_clean(result)
    assert "note: DRAFT numbers are not matched" in result.stdout


@pytest.mark.parametrize("role", [BAD_ROLE, OTHER_ROLE, "maintainer", "coordinator"])
def test_role_words(pack, role):
    number = edit(
        pack, "The maintainers arrange review", "The " + role + " arranges review"
    )
    result = run(pack)
    if role in {OTHER_ROLE, "maintainer", "coordinator"}:
        assert_clean(result)
    else:
        assert_rule(result, "ROLE", [(pack, number)])


def test_merging_role(pack):
    number = edit(pack, "before the maintainer merges", "before the coordinator merges")
    assert_rule(run(pack), "ROLE", [(pack, number)])


def test_two_separate_tables(pack):
    edit(
        pack,
        "| Counter |",
        "\n| Location | Symptom | Detection |\n| --- | --- | --- |\n| Counter |",
    )
    assert_clean(run(pack))


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_table(pack, fence):
    with pack.open("a") as stream:
        stream.write(f"\n{fence}text\n| first | row |\n\n| second | row |\n{fence}\n")
    assert_clean(run(pack))


def test_crlf(pack):
    pack.write_bytes(PASS.read_bytes().replace(b"\n", b"\r\n"))
    assert_clean(run(pack))


def test_no_arguments():
    assert run().returncode == 2


@pytest.mark.parametrize(
    "args", [["--unknown"], ["--account"], ["--drafts"], ["--skip"]]
)
def test_usage_errors(args):
    assert run(*args).returncode == 2


def test_two_files(pack, tmp_path):
    other = tmp_path / "other.md"
    other.write_bytes(pack.read_bytes())
    number = EDITS["SWEEP"](pack)
    EDITS["SWEEP"](other)
    assert number > 1
    result = run(pack, other)
    assert_rule(result, "SWEEP", [(pack, 1), (other, 1)])
    assert result.stdout.count("pack_lint:") == 1


@pytest.mark.parametrize("kind", ["absent", "directory", "encoding"])
def test_unreadable_pack(tmp_path, kind):
    path = tmp_path / "bad.md"
    if kind == "directory":
        path.mkdir()
    elif kind == "encoding":
        path.write_bytes(b"\xff")
    assert_rule(run(path), "READ", [(path, 1)])


def test_unreadable_draft_encoding(pack, tmp_path):
    drafts = tmp_path / "drafts.md"
    drafts.write_bytes(b"\xff")
    number = next(
        i
        for i, line in enumerate(pack.read_text().splitlines(), 1)
        if "issue pending" in line
    )
    assert_rule(run("--drafts", drafts, pack), "DRAFT", [(pack, number)])


def test_skip_rule(pack):
    EDITS["SWEEP"](pack)
    assert_clean(run("--skip", "SWEEP", pack))


def test_skip_cannot_hide_read_error(tmp_path):
    path = tmp_path / "absent.md"
    assert_rule(run("--skip", "READ", path), "READ", [(path, 1)])


def test_repeat_main_resets_notes(pack, capsys):
    spec = importlib.util.spec_from_file_location("pack_lint", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([str(pack)]) == 0
    assert "note:" in capsys.readouterr().out
    edit(pack, "issue pending (1)", "#123")
    assert module.main([str(pack)]) == 0
    assert "note:" not in capsys.readouterr().out


def test_inline_sweep_example_is_not_evidence(pack):
    edit(pack, "sweep: 2 found", "The required marker is `sweep: 2 found`.")
    assert_rule(run(pack), "SWEEP", [(pack, 1)])


@pytest.mark.parametrize("option", ["--account", "--drafts", "--skip"])
def test_missing_option_value_after_pack(pack, option):
    assert run(pack, option).returncode == 2


def test_issue_url_for_other_owner(pack):
    number = edit(pack, "See #123.", "See " + ISSUE + ".")
    assert_rule(run("--account", "another-owner", pack), "URL", [(pack, number)])


@pytest.mark.parametrize("marker", ["sweep: 0 found", "sweep: 02 found"])
def test_sweep_counts(pack, marker):
    edit(pack, "sweep: 2 found", marker)
    assert_clean(run(pack))


def test_repeated_draft_number(pack, tmp_path):
    with pack.open("a") as stream:
        stream.write("\nAlso tracked by issue pending (1).\n")
    drafts = tmp_path / "drafts.md"
    drafts.write_text("Draft 2\n")
    number = next(
        i
        for i, line in enumerate(pack.read_text().splitlines(), 1)
        if "issue pending" in line
    )
    assert_rule(run("--drafts", drafts, pack), "DRAFT", [(pack, number)])


def test_leading_zero_draft_number(pack, tmp_path):
    edit(pack, "issue pending (1)", "issue pending (01)")
    drafts = tmp_path / "drafts.md"
    drafts.write_text("Draft 01: Example\n")
    assert_clean(run("--drafts", drafts, pack))


def test_no_draft_markers_produce_no_note(pack):
    edit(pack, "issue pending (1)", "#123")
    result = run(pack)
    assert_clean(result)
    assert "note:" not in result.stdout


@pytest.mark.parametrize(
    "prose",
    [
        "The query " + OTHER_ROLE + " routes requests to the adapters.",
        "removed before the PR merges",
        "removed before the branch merges",
        "wait until before the upstream fix merges",
        "removed before the pull request merges",
        "removed before the change merges",
        "removed before the patch merges",
        "removed before the commit merges",
    ],
)
def test_engineering_prose(pack, prose):
    edit(pack, "The maintainers arrange review before the maintainer merges.", prose)
    assert_clean(run(pack))


@pytest.mark.parametrize(
    "role",
    [
        OTHER_ROLE,
        BAD_ROLE,
        "P" + "M",
        "manager",
        "coordinator",
        "owner",
        "lead",
        "reviewer",
        "engineer",
        "admin",
        "administrator",
        "steward",
        "supervisor",
        "director",
        "operator",
        "upstream lead",
    ],
)
def test_merging_role_nouns(pack, role):
    number = edit(
        pack, "before the maintainer merges", "before the " + role + " merges"
    )
    assert_rule(run(pack), "ROLE", [(pack, number)])


@pytest.mark.parametrize("account", [None, "", "   "])
def test_missing_account_warning_once(pack, tmp_path, account):
    other = tmp_path / "other.md"
    other.write_bytes(pack.read_bytes())
    args = [] if account is None else ["--account", account]
    assert_clean(
        run(*args, pack, other, default_account=False),
        count=2,
        stderr=ACCOUNT_WARNING,
    )


@pytest.mark.parametrize("source", ["option", "environment"])
def test_account_has_no_warning(monkeypatch, source):
    args = ["--account", "example-owner"] if source == "option" else []
    if source == "environment":
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "example-owner")
    assert_clean(run(*args, PASS, default_account=False))


def test_issue_url_guidance(pack):
    number = edit(pack, "See #123.", "See " + ISSUE + ".")
    result = run(pack)
    assert_rule(result, "URL", [(pack, number)])
    assert (
        "write #NNN for an issue of this repository; "
        "for another project use link text, not #NNN"
    ) in result.stdout


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_section_is_not_evidence(pack, fence):
    heading = "## 7. Lessons log"
    edit(pack, heading, f"{fence}text\n{heading}\n{fence}")
    result = run(pack)
    assert_rule(result, "S10", [(pack, 1)])
    assert "section heading(s) missing: 7" in result.stdout


@pytest.mark.parametrize("heading", ["##7. Lessons log", "#7. Lessons log"])
def test_heading_needs_space(pack, heading):
    edit(pack, "## 7. Lessons log", heading)
    assert_rule(run(pack), "S10", [(pack, 1)])


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_sweep_is_not_evidence(pack, fence):
    edit(pack, "sweep: 2 found", f"{fence}text\nsweep: 2 found\n{fence}")
    assert_rule(run(pack), "SWEEP", [(pack, 1)])


@pytest.mark.parametrize(
    "entry",
    ["1.", "(1)", "Draft 1 - Example", "1. Example", "1) Example", "1", "Draft 1"],
)
def test_non_draft_entries_do_not_count(pack, tmp_path, entry):
    drafts = tmp_path / "drafts.md"
    drafts.write_text(entry + "\n")
    number = next(
        i
        for i, line in enumerate(pack.read_text().splitlines(), 1)
        if "issue pending" in line
    )
    assert_rule(run("--drafts", drafts, pack), "DRAFT", [(pack, number)])
