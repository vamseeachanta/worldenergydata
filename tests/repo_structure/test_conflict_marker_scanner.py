"""Exercise the staged-content scanner against disposable Git indexes."""

import gzip
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCANNER = (
    Path(__file__).resolve().parents[2]
    / "scripts/enforcement/check-no-conflict-markers.sh"
)
MARKERS = b"<<<<<<< ours\n=======\n>>>>>>> theirs\n"
FILE_SENTINEL = b"<!-- CONFLICT_MARKER_FORENSIC_FILE_OK -->"
LINE_SENTINELS = (
    b"# CONFLICT_MARKER_FORENSIC_OK",
    b"// CONFLICT_MARKER_FORENSIC_OK",
    b"<!-- CONFLICT_MARKER_FORENSIC_OK -->",
)


@pytest.fixture
def staged_repo(tmp_path):
    """Keep inherited repository bindings away from the caller's index."""
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["LC_ALL"] = "C"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    env["TMPDIR"] = str(scratch)
    subprocess.run(
        ["git", "init", "--quiet", "--template=", str(tmp_path)],
        env=env,
        check=True,
        capture_output=True,
    )

    def stage(name, content):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        subprocess.run(
            ["git", "-c", "core.autocrlf=false", "add", "--", name],
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
        )
        return path

    def scan(file_limit=False, **overrides):
        index = tmp_path / ".git/index"
        before = index.read_bytes()
        command = ["bash", str(SCANNER)]
        if file_limit:
            command = [
                "bash",
                "-c",
                'ulimit -c 0; ulimit -f 1; exec bash "$1"',
                "scanner-test",
                str(SCANNER),
            ]
        result = subprocess.run(
            command,
            cwd=tmp_path,
            env={**env, **overrides},
            capture_output=True,
        )
        assert index.read_bytes() == before
        assert list(scratch.iterdir()) == []
        assert b"ignored null byte" not in result.stderr
        return result

    return stage, scan


@pytest.mark.parametrize(
    "content",
    [
        gzip.compress(b"sample,value\n1,2\n", mtime=0),
        b"ordinary\0binary\n",
        b"\0" + b"x" * 131072,
        b"<<<<\0<<< ours\n>>>>>>> theirs\n",
    ],
    ids=["gzip", "nul", "large-binary", "nul-does-not-join-markers"],
)
def test_binary_content_without_markers_is_quiet(staged_repo, content):
    stage, scan = staged_repo
    path = stage("data/sample.gz", content)
    result = scan()
    assert result.returncode == 0
    assert result.stdout == result.stderr == b""
    assert path.read_bytes() == content


@pytest.mark.parametrize(
    "name, displayed_name",
    [
        ("sample.txt", "sample.txt"),
        ("with spaces.txt", "with spaces.txt"),
        ("tab\tname.txt", "tab^Iname.txt"),
        ("line\nname.txt", "line^Jname.txt"),
        ("escape\x1b[31m.txt", "escape^[[31m.txt"),
        ("ending.txt\n", "ending.txt^J"),
    ],
)
@pytest.mark.parametrize(
    "content",
    [MARKERS, b"binary\0prefix\n" + MARKERS, MARKERS.rstrip(b"\n")],
    ids=["text", "nul", "no-final-newline"],
)
def test_conflicts_are_blocked_with_original_line_numbers(
    staged_repo, name, displayed_name, content
):
    stage, scan = staged_repo
    stage(name, content)
    result = scan()
    assert result.returncode == 1
    first = 2 if content.startswith(b"binary") else 1
    assert f"{displayed_name}:{first}:<<<<<<< ours".encode() in result.stderr
    assert f"{displayed_name}:{first + 2}:>>>>>>> theirs".encode() in result.stderr
    diagnostics = result.stderr.splitlines()
    assert sum(b":<<<<<<< ours" in line for line in diagnostics) == 1
    assert sum(b":>>>>>>> theirs" in line for line in diagnostics) == 1
    assert b"\x1b" not in result.stderr


@pytest.mark.parametrize(
    "content", [b"=======\n", b">>>>>>> quote\n", b"<<<<<<< alone\n"]
)
def test_both_anchors_are_required(staged_repo, content):
    stage, scan = staged_repo
    stage("sample.md", content)
    assert scan().returncode == 0


@pytest.mark.parametrize("sentinel", LINE_SENTINELS)
def test_per_line_forensic_exemptions(staged_repo, sentinel):
    stage, scan = staged_repo
    stage("sample.txt", b"<<<<<<< ours " + sentinel + b"\n>>>>>>> theirs\n")
    result = scan()
    assert result.returncode == 1
    assert b"sample.txt:1:" not in result.stderr
    assert b"sample.txt:2:" in result.stderr
    stage(
        "sample.txt",
        b"<<<<<<< ours " + sentinel + b"\n>>>>>>> theirs " + sentinel + b"\n",
    )
    assert scan().returncode == 0


@pytest.mark.parametrize(
    "prefix",
    [
        "docs/plans/",
        "docs/governance/",
        "docs/standards/",
        "scripts/review/results/",
        "scripts/review/prompts/",
    ],
)
def test_whole_file_forensic_exemption_is_path_restricted(staged_repo, prefix):
    stage, scan = staged_repo
    content = FILE_SENTINEL + b"\n" + MARKERS
    stage(prefix + "example.md", content)
    assert scan().returncode == 0
    stage("src/example.txt", content)
    result = scan()
    assert result.returncode == 1
    assert b"src/example.txt:2:" in result.stderr


@pytest.mark.parametrize("sentinel", [FILE_SENTINEL, *LINE_SENTINELS])
def test_nul_cannot_reconstruct_forensic_sentinel(staged_repo, sentinel):
    stage, scan = staged_repo
    broken = sentinel.replace(b"FORENSIC", b"FORE\0NSIC")
    stage(
        "docs/plans/example.md",
        broken + b"\n<<<<<<< ours " + broken + b"\n>>>>>>> theirs " + broken + b"\n",
    )
    assert scan().returncode == 1


def test_only_staged_bytes_control_the_exemptions(staged_repo):
    stage, scan = staged_repo
    path = stage("docs/plans/example.md", MARKERS)
    path.write_bytes(FILE_SENTINEL + b"\n" + MARKERS)
    assert scan().returncode == 1
    stage("docs/plans/example.md", FILE_SENTINEL + b"\n" + MARKERS)
    path.write_bytes(MARKERS)
    assert scan().returncode == 0


@pytest.mark.parametrize(
    "content",
    [
        MARKERS + b"padding\n" * 32768,
        b"padding\n" * 32768 + MARKERS,
        b"<<<<<<< ours\0\xff\n>>>>>>> theirs\0\xff\n",
        b"<<<<<<<\r\n=======\r\n>>>>>>>\r\n",
        b"<<<<<<<\tours\n>>>>>>>\ttheirs\n",
    ],
    ids=["large-suffix", "large-prefix", "binary-marker-lines", "crlf", "tabs"],
)
def test_marker_detection_uses_raw_bytes(staged_repo, content):
    stage, scan = staged_repo
    stage("sample.txt", content)
    assert scan().returncode == 1


@pytest.mark.parametrize(
    "separator, exit_code",
    [("\u2003".encode("utf-8"), 0), (b" \xff", 1)],
    ids=[
        "multibyte-whitespace-is-not-a-byte-delimiter",
        "ascii-delimiter-invalid-byte",
    ],
)
def test_byte_semantics_ignore_the_callers_locale(staged_repo, separator, exit_code):
    stage, scan = staged_repo
    stage(
        "sample.txt",
        b"<<<<<<<" + separator + b"ours\n>>>>>>>" + separator + b"theirs\n",
    )
    assert scan(LC_ALL="C.utf8").returncode == exit_code


@pytest.mark.parametrize("suffix", [b"\0", b" extra", b"\r"])
def test_line_exemption_requires_exact_suffix(staged_repo, suffix):
    stage, scan = staged_repo
    sentinel = LINE_SENTINELS[0] + suffix
    stage("sample.txt", b"<<<<<<< ours " + sentinel + b"\n>>>>>>> theirs\n")
    result = scan()
    assert result.returncode == 1
    assert b"sample.txt:1:" in result.stderr


def test_anchors_must_occur_in_the_same_blob(staged_repo):
    stage, scan = staged_repo
    stage("open.txt", b"<<<<<<< ours\n")
    stage("close.txt", b">>>>>>> theirs\n")
    assert scan().returncode == 0


def test_temporary_file_creation_failure_is_blocking(staged_repo, tmp_path):
    stage, scan = staged_repo
    stage("sample.txt", b"ordinary text\n")
    result = scan(TMPDIR=str(tmp_path / "missing"))
    assert result.returncode != 0
    assert b"ERROR: Cannot create staged-content snapshot." in result.stderr


def test_incomplete_snapshot_is_blocking(staged_repo):
    stage, scan = staged_repo
    # A truncated snapshot has no markers and would pass an incomplete scan.
    stage("sample.txt", b"padding\n" * 1024 + MARKERS)
    result = scan(file_limit=True)
    assert result.returncode != 0
    assert b"ERROR: Cannot snapshot staged content: sample.txt" in result.stderr


@pytest.mark.parametrize(
    "tool, pattern, read_file",
    [
        ("grep", FILE_SENTINEL.decode(), True),
        ("grep", "^<<<<<<<([[:space:]]|$)", True),
        ("grep", "^>>>>>>>([[:space:]]|$)", True),
        ("grep", "^(<<<<<<<|>>>>>>>)([[:space:]]|$)", True),
        (
            "grep",
            "(# CONFLICT_MARKER_FORENSIC_OK|// CONFLICT_MARKER_FORENSIC_OK|"
            "<!-- CONFLICT_MARKER_FORENSIC_OK -->)$",
            False,
        ),
        ("cat", "-v", False),
    ],
    ids=["file-sentinel", "open-anchor", "close-anchor", "matcher", "filter", "render"],
)
def test_snapshot_read_and_matcher_errors_are_blocking(
    staged_repo, tmp_path, tool, pattern, read_file
):
    stage, scan = staged_repo
    stage(
        "docs/plans/example.md",
        b"<<<<<<< ours "
        + LINE_SENTINELS[0]
        + b"\n>>>>>>> theirs "
        + LINE_SENTINELS[0]
        + b"\n",
    )
    assert scan().returncode == 0
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Reading a directory fails even when a privileged user runs the test.
    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    wrapper = bin_dir / tool
    wrapper.write_text(
        '#!/usr/bin/env bash\nargs=("$@")\n'
        'for arg in "$@"; do\n'
        '  if [[ "$arg" == "$SCANNER_TEST_PATTERN" ]]; then\n'
        '    if [[ "$SCANNER_TEST_READ_FILE" == 1 ]]; then\n'
        '      args[${#args[@]}-1]="$SCANNER_TEST_UNREADABLE"\n'
        '      exec "$SCANNER_TEST_TOOL" "${args[@]}"\n'
        "    fi\n"
        '    "$SCANNER_TEST_TOOL" "$@"\n'
        "    exit 2\n"
        "  fi\ndone\n"
        'exec "$SCANNER_TEST_TOOL" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    wrapper.chmod(0o755)
    result = scan(
        PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
        SCANNER_TEST_TOOL=shutil.which(tool),
        SCANNER_TEST_PATTERN=pattern,
        SCANNER_TEST_READ_FILE=str(int(read_file)),
        SCANNER_TEST_UNREADABLE=str(unreadable),
    )
    assert result.returncode != 0
    assert b"ERROR: Cannot read staged content: docs/plans/example.md" in result.stderr


@pytest.mark.parametrize("signal, exit_code", [("TERM", 143), ("HUP", 129)])
@pytest.mark.parametrize("tool", ["git", "mktemp"])
def test_termination_exits_nonzero_and_cleans_snapshot(
    staged_repo, tmp_path, signal, exit_code, tool
):
    stage, scan = staged_repo
    stage("sample.txt", MARKERS)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / tool
    trigger = '[ "$1" = show ]' if tool == "git" else "true"
    wrapper.write_text(
        f"#!/bin/sh\nif {trigger}; then\n"
        '  "$SCANNER_TEST_TOOL" "$@"\n'
        f'  kill -{signal} "$PPID"\n  exit 1\nfi\n'
        'exec "$SCANNER_TEST_TOOL" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    wrapper.chmod(0o755)
    result = scan(
        PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
        SCANNER_TEST_TOOL=shutil.which(tool),
    )
    assert result.returncode == exit_code
