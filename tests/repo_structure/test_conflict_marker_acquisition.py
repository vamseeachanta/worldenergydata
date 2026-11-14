"""Fail closed on incomplete acquisition without changing disposable indexes."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCANNER = (
    Path(__file__).resolve().parents[2]
    / "scripts/enforcement/check-no-conflict-markers.sh"
)
MARKERS = b"<<<<<<< ours\n>>>>>>> theirs\n"
NAME = "tab\tline\nending\n"
DISPLAY = "tab^Iline^Jending^J"


def _snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


@pytest.fixture
def repository(tmp_path):
    def create(label="target"):
        root = tmp_path / label
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        root.mkdir()
        real_git = shutil.which("git")

        def git(*args, data=None):
            return subprocess.run(
                [real_git, *args],
                cwd=root,
                env=env,
                input=data,
                capture_output=True,
                check=True,
            ).stdout

        git("init", "--quiet", "--template=", ".")
        assert Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip()) == root
        scratch = tmp_path / (label + "-scratch")
        scratch.mkdir()
        tools = tmp_path / (label + "-tools")
        tools.mkdir()
        for tool in ("git", "mktemp"):
            wrapper = tools / tool
            wrapper.write_text(
                f"#!{sys.executable}\n"
                "import os, pathlib, sys\n"
                "a = sys.argv[1:]\n"
                "tool = pathlib.Path(sys.argv[0]).name\n"
                "if any(x.startswith('--format') for x in a): sys.exit(99)\n"
                "point = a[1] if a and a[0] == '--literal-pathspecs' else (a[0] if a else '')\n"
                "if tool == 'mktemp':\n"
                " p = pathlib.Path(os.environ['CALLS'])\n"
                " n = int(p.read_text()) + 1 if p.exists() else 1\n"
                " p.write_text(str(n))\n"
                " if n == int(os.environ['ALLOCATION']): sys.exit(1)\n"
                "elif point == os.environ['POINT']:\n"
                " os.write(1, bytes.fromhex(os.environ['OUTPUT']))\n"
                " sys.exit(int(os.environ['STATUS']))\n"
                "os.execv(os.environ['REAL_' + tool.upper()], [tool, *a])\n"
            )
            wrapper.chmod(0o755)

        def stage(name=NAME, content=b"clean\n", mode="100644", oid=None):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            oid = (
                oid
                or git("hash-object", "-w", "--stdin", data=content).decode().strip()
            )
            git("update-index", "--add", "--cacheinfo", mode, oid, name)
            return oid

        def scan(point="", output=b"", status=1, allocation=0):
            before = _snapshot(root)
            result = subprocess.run(
                ["bash", str(SCANNER)],
                cwd=root,
                capture_output=True,
                env={
                    **env,
                    "TMPDIR": str(scratch),
                    "LC_ALL": "C",
                    "PATH": str(tools) + os.pathsep + env["PATH"],
                    "REAL_GIT": real_git,
                    "REAL_MKTEMP": shutil.which("mktemp"),
                    "POINT": point,
                    "OUTPUT": output.hex(),
                    "STATUS": str(status),
                    "ALLOCATION": str(allocation),
                    "CALLS": str(tools / "calls"),
                },
            )
            assert _snapshot(root) == before
            assert list(scratch.iterdir()) == []
            assert b"ignored null byte" not in result.stderr
            return result

        return root, git, stage, scan

    return create


def _error(result, message, path=True):
    assert result.returncode == 1
    assert result.stdout == b""
    expected = "ERROR: " + message + (": " + DISPLAY if path else ".") + "\n"
    assert result.stderr == expected.encode()


@pytest.mark.parametrize("content", [b"clean\n", MARKERS])
@pytest.mark.parametrize("output", [b"", os.fsencode(NAME) + b"\0"])
def test_failed_enumeration(repository, content, output):
    _, _, stage, scan = repository()
    stage(content=content)
    _error(scan("diff", output), "Cannot enumerate staged paths", path=False)


@pytest.mark.parametrize("content", [b"clean\n", MARKERS])
@pytest.mark.parametrize(
    "point, message",
    [
        ("ls-files", "Cannot read staged index entry"),
        ("cat-file", "Cannot inspect staged object"),
    ],
)
def test_failed_entry_or_object(repository, content, point, message):
    _, _, stage, scan = repository()
    stage(content=content)
    _error(scan(point), message)


@pytest.mark.parametrize(
    "damage",
    [
        "empty",
        "truncated",
        "multiple",
        "partial-extra",
        "stage",
        "mode",
        "oid",
        "path",
        "header",
        "tab",
    ],
)
def test_invalid_metadata(repository, damage):
    _, git, stage, scan = repository()
    stage()
    record = git("ls-files", "-s", "-z", "--", NAME)
    header, path = record.split(b"\t", 1)
    mode, oid, _ = header.split()
    bad = {
        "empty": b"",
        "truncated": record[:-1],
        "multiple": record * 2,
        "partial-extra": record + b"x",
        "stage": header[:-1] + b"1\t" + path,
        "mode": b"100600 " + oid + b" 0\t" + path,
        "oid": mode + b" not-hex 0\t" + path,
        "path": header + b"\tother\0",
        "header": b"bad\t" + path,
        "tab": header + b" " + path,
    }[damage]
    _error(scan("ls-files", bad, status=0), "Invalid staged index entry")


@pytest.mark.parametrize(
    "allocation, message",
    [
        (2, "Cannot create staged-path list"),
        (3, "Cannot create staged-entry snapshot"),
    ],
)
def test_additional_allocation_failure(repository, allocation, message):
    _, _, stage, scan = repository()
    stage()
    _error(scan(allocation=allocation), message, path=False)


@pytest.mark.parametrize("kind", ["missing", "tree"])
def test_unreadable_blob(repository, kind):
    _, git, stage, scan = repository()
    oid = "f" * 40 if kind == "missing" else git("mktree", data=b"").decode().strip()
    stage(oid=oid)
    _error(scan(), "Cannot inspect staged object")


@pytest.mark.parametrize(
    "name", ["with spaces", "tab\tname", "line\nname", "end\n", "[x]*", "1:name.txt"]
)
@pytest.mark.parametrize("content", [b"clean\n", MARKERS])
def test_literal_paths(repository, name, content):
    _, _, stage, scan = repository()
    stage(name, content)
    assert scan().returncode == int(content == MARKERS)


@pytest.mark.parametrize("mode", ["100644", "100755", "120000", "160000"])
def test_supported_modes(repository, mode):
    _, _, stage, scan = repository()
    stage(mode=mode, oid="f" * 40 if mode == "160000" else None)
    result = scan()
    assert result.returncode == 0
    assert result.stdout == result.stderr == b""


@pytest.mark.parametrize("deletion", [False, True])
def test_empty_enumeration(repository, deletion):
    _, git, stage, scan = repository()
    stage()
    tree = git("write-tree").strip()
    # A synthetic parent requires no identity or real commit command.
    parent = git(
        "hash-object",
        "-t",
        "commit",
        "-w",
        "--stdin",
        data=b"tree " + tree + b"\nauthor Fixture <fixture> 1 +0000\n"
        b"committer Fixture <fixture> 1 +0000\n\nfixture\n",
    ).strip()
    git("update-ref", "HEAD", parent.decode())
    if deletion:
        git("update-index", "--force-remove", "--", NAME)
    result = scan()
    assert result.returncode == 0
    assert result.stdout == result.stderr == b""


def test_inherited_bindings_preserve_decoy(repository, monkeypatch):
    decoy, _, stage, _ = repository("decoy")
    stage("decoy.txt")
    before = _snapshot(decoy)
    for key, value in {
        "GIT_DIR": decoy / ".git",
        "GIT_WORK_TREE": decoy,
        "GIT_COMMON_DIR": decoy / ".git",
        "GIT_INDEX_FILE": decoy / ".git/index",
    }.items():
        monkeypatch.setenv(key, str(value))
    _, _, stage, scan = repository()
    stage(content=MARKERS)
    _error(scan("diff"), "Cannot enumerate staged paths", path=False)
    assert _snapshot(decoy) == before
