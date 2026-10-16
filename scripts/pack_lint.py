#!/usr/bin/env python3
"""pack_lint.py [--account NAME] [--drafts FILE] [--skip RULE[,RULE]] PACK.md [PACK.md ...]

Mechanical checks of a module knowledge pack (agent-pack.md) before it is published.
Each failure prints `file:line: RULE: message`; the exit status is 1 if there is any failure, 0 if clean, 2 on a usage error.

Rules
  S10    sections 1 to 10 are present as headings (`## 1. Name` ... `## 10. Name`; any heading level, dot optional, a space after the hashes). Fenced code is skipped.
  SWEEP  the pack has a line `sweep: N found` (N a number). `sweep: 0 found` is allowed; the author then shows the grep that was run next to it. Fenced code is skipped.
  NODE   every test node id (`path::Class::test_name`) starts with `tests/` or contains `/tests/`. A bare `TestClass::test_x` or `test_file.py::test_x` fails.
         A `source_file.py::symbol` reference to code is not a test node id and is not checked.
  URL    no `api.github.com`; no issue or pull-request URL (write `#NNN` for an issue of this repository; for another project use link text, not `#NNN`);
         no account name (the owner given by --account, or the environment variable GITHUB_REPOSITORY_OWNER) in a URL. Issue and pull-request URLs are
         flagged for any owner. When no account is given the account-name check is off, and a warning on stderr says so.
  DRAFT  every `issue pending` is followed by a draft number, `issue pending (3)`. With --drafts FILE (the issue-draft list of the job) every
         draft number used in the pack also has an entry in that file: a line that starts with `Draft N:` (case-insensitive; a heading mark, a list
         mark or bold marks before it are allowed). Without --drafts only the number is checked, and a note says so.
  ROLE   in `before the <subject> merges` a subject ending in a coordination role noun must read `maintainer`.
         Change nouns (PR, branch, fix, patch, commit) and ordinary engineering prose are allowed; the coordination title matched by ROLE_WORDS is banned.
  TABLE  no blank line splits a Markdown table: a table row, one or more blank lines, a table row that is not the start of a new table (header and delimiter row).
Standard library only."""
import os
import re
import sys

DELIM = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
NODE = re.compile(r"([A-Za-z0-9_./\-]*)::([A-Za-z0-9_\[\]\-.:]*[A-Za-z0-9_\]])")
ROLE_WORDS = re.compile(r"(?i)\b(project[ ]manager)\b")
ROLE_NOUNS = {"manager", "p" + "m", "dis" + "patcher", "coordinator", "owner", "lead", "reviewer", "engineer", "admin", "administrator",
              "steward", "supervisor", "director", "operator"}
MERGING = re.compile(r"(?i)\bbefore the (\w[\w -]{0,30}?) merges\b")
PENDING = re.compile(r"(?i)issue[- ]pending")
PENDING_NUM = re.compile(r"(?i)issue[- ]pending\s*\((\d+)\)")
PENDING_PROSE = re.compile(r"\s*(?:\(n\)|`?\s*(?:markers?|numbers?|references?|drafts?|items?|entries)\b)", re.I)
NOTES = set()
ISSUE_URL = re.compile(r"github\.com/[^/\s)\]]+/[^/\s)\]]+/(?:issues|pull|pulls)/\d+", re.I)


def draft_numbers(path):
    """numbers that have an entry in the issue-draft list file"""
    have = set()
    try:
        lines = open(path, encoding="utf-8").read().replace("\r", "").split("\n")
    except (OSError, UnicodeError):
        return None
    for ln in lines:
        m = re.match(r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?\**draft\s+(\d+)\s*:", ln, re.I)
        if m:
            have.add(int(m.group(1)))
    return have


def lint(path, account=None, drafts=None, skip=()):
    out = []
    try:
        lines = open(path, encoding="utf-8").read().replace("\r", "").split("\n")
    except (OSError, UnicodeError) as e:
        return ["%s:1: READ: cannot read the file (%s)" % (path, e)]
    fence = False
    in_code = []
    for ln in lines:
        if ln.lstrip().startswith(("```", "~~~")):
            fence = not fence
        in_code.append(fence)
    # S10
    found = set()
    for k, ln in enumerate(lines):
        if in_code[k]:
            continue
        m = re.match(r"^#{1,6}\s+(\d{1,2})(?:[.)\s:]|$)", ln)
        if m:
            found.add(int(m.group(1)))
    missing = [n for n in range(1, 11) if n not in found]
    if missing:
        out.append("%s:1: S10: section heading(s) missing: %s" % (path, ", ".join(str(n) for n in missing)))
    # SWEEP (fenced code does not count)
    plain = "\n".join(ln for ln, c in zip(lines, in_code) if not c)
    if not re.search(r"(?im)^\s*sweep:\s*\d+\s+found\b", plain):
        out.append("%s:1: SWEEP: no line `sweep: N found` (run the silent-failure sweep; `sweep: 0 found` needs the grep that was run)" % path)
    acct = (account or os.environ.get("GITHUB_REPOSITORY_OWNER") or "").strip()
    for i, ln in enumerate(lines, 1):
        # NODE
        for m in NODE.finditer(ln):
            pre = m.group(1)
            first = m.group(2).split("::")[0]
            base = pre.rsplit("/", 1)[-1]
            testy = (base.startswith("test_") or base.endswith("_test.py") or first.startswith(("test", "Test"))
                     or pre.startswith("Test"))
            if testy and not (pre.startswith("tests/") or "/tests/" in pre):
                out.append("%s:%d: NODE: test node id `%s::%s` does not start with tests/" % (path, i, pre, m.group(2)))
        # URL
        if "api.github.com" in ln:
            out.append("%s:%d: URL: api.github.com appears (write the issue or pull request as #NNN)" % (path, i))
        urls = re.findall(r"(?:https?://|www\.|github\.com/)[^\s<>\]\)]+", ln, re.I)
        if ISSUE_URL.search(ln) or (acct and any(re.search(re.escape(acct), url, re.I) for url in urls)):
            out.append("%s:%d: URL: an issue or pull-request URL or account name in a URL (write #NNN for an issue of this repository; for another project use link text, not #NNN)" % (path, i))
        # ROLE: a role noun ending the merging subject, or the coordination title
        m = MERGING.search(ln)
        if m and m.group(1).lower().split()[-1] in ROLE_NOUNS:
            out.append("%s:%d: ROLE: the merging role is `%s`; it must read `maintainer`" % (path, i, m.group(1)))
        m = ROLE_WORDS.search(ln)
        if m:
            out.append("%s:%d: ROLE: the role word `%s` appears; write `maintainers`" % (path, i, m.group(1)))
    # DRAFT
    used = []
    for i, ln in enumerate(lines, 1):
        for m in PENDING.finditer(ln):
            n = PENDING_NUM.match(ln, m.start())
            if n:
                used.append((int(n.group(1)), i))
            elif PENDING_PROSE.match(ln, m.end()):
                continue  # prose that explains the marker, not a marker
            else:
                out.append("%s:%d: DRAFT: `issue pending` without a draft number (write `issue pending (N)` and give draft N in the issue-draft list)" % (path, i))
    if used and drafts:
        have = draft_numbers(drafts)
        if have is None:
            out.append("%s:%d: DRAFT: the issue-draft list `%s` cannot be read" % (path, used[0][1], drafts))
        else:
            first = {}
            for n, i in used:
                first.setdefault(n, i)
            for n in sorted(first):
                if n not in have:
                    out.append("%s:%d: DRAFT: `issue pending (%d)` has no entry (%d) in the issue-draft list" % (path, first[n], n, n))
    elif used and not drafts:
        NOTES.add("DRAFT numbers are not matched to an issue-draft list (no --drafts file given)")
    # TABLE
    idx = [i for i, ln in enumerate(lines) if ln.strip()]
    for a, b in zip(idx, idx[1:]):
        if b - a > 1 and lines[a].lstrip().startswith("|") and lines[b].lstrip().startswith("|") and not in_code[a]:
            nxt = b + 1
            if not (nxt < len(lines) and DELIM.match(lines[nxt])):
                out.append("%s:%d: TABLE: a blank line splits a table (the rows after it do not render as table rows)" % (path, a + 2))
    if skip:
        out = [x for x in out if x.split(": ", 2)[1] not in skip]
    return out


def main(argv):
    NOTES.clear()
    account = None
    drafts = None
    skip = set()
    files = []
    it = iter(argv)
    for a in it:
        if a in ("--account", "--drafts", "--skip"):
            value = next(it, None)
            if value is None or value.startswith("-"):
                sys.stderr.write("option %s requires a value\n" % a)
                return 2
            if a == "--account":
                account = value
            elif a == "--drafts":
                drafts = value
            else:
                skip |= set(value.split(","))
        elif a.startswith("-"):
            sys.stderr.write("unknown option %s\n" % a)
            return 2
        else:
            files.append(a)
    if not files:
        sys.stdout.write(__doc__ + "\n")
        return 2
    if not (account or os.environ.get("GITHUB_REPOSITORY_OWNER") or "").strip():
        sys.stderr.write("warning: account-name check skipped: no account given (use --account NAME or set GITHUB_REPOSITORY_OWNER); issue and pull-request URLs are still checked\n")
    bad = []
    for f in files:
        bad += lint(f, account, drafts, skip)
    for b in bad:
        print(b)
    for n in sorted(NOTES):
        print("note: " + n)
    print("pack_lint: %s (%d failure(s) in %d file(s))" % ("FAILED" if bad else "clean", len(bad), len(files)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
