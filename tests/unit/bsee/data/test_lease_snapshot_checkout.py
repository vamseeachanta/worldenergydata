"""Lease snapshot checkout bytes must retain their committed digest basis."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SNAPSHOT = "data/modules/bsee/leases"
GIT_BINDINGS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")


@pytest.mark.parametrize("autocrlf", ["false", "true"])
@pytest.mark.parametrize("inherited_git", [False, True])
def test_lease_snapshot_checkout_preserves_committed_bytes(
    tmp_path, monkeypatch, autocrlf, inherited_git
):
    """Exercise real Git checkout conversion in an isolated repository."""
    if inherited_git:
        for name in GIT_BINDINGS:
            monkeypatch.setenv(name, str(tmp_path / name))
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(
        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM="1"
    )

    def git(*arguments, cwd=ROOT, input=None):
        return subprocess.check_output(
            ["git", "-c", f"core.attributesFile={os.devnull}", *arguments],
            cwd=cwd,
            env=environment,
            input=input,
        )

    entries = git("ls-tree", "-rz", "HEAD", "--", SNAPSHOT)
    originals, modes = {}, {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        header, name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        assert kind == "blob"
        path = name.decode("utf-8")
        modes[path] = mode
        originals[path] = git("cat-file", "blob", blob)
    assert originals, "No committed lease snapshot files were enumerated"
    index = git("ls-files", "--stage", "-z")
    config = ROOT / git("rev-parse", "--git-path", "config").decode().strip()
    config_bytes = config.read_bytes()
    attributes = (ROOT / ".gitattributes").read_bytes()
    caller_files = {path: (ROOT / path).read_bytes() for path in originals}

    checkout = tmp_path / "checkout"
    git("init", "--quiet", "--template=", str(checkout))
    git("config", "core.autocrlf", autocrlf, cwd=checkout)
    git("config", "core.eol", "lf", cwd=checkout)
    git("config", "core.safecrlf", "false", cwd=checkout)
    (checkout / ".gitattributes").write_bytes(attributes)
    for path, content in originals.items():
        blob = git(
            "hash-object", "-w", "--stdin", "--no-filters", cwd=checkout, input=content
        )
        git(
            "update-index",
            "--add",
            "--cacheinfo",
            f"{modes[path]},{blob.decode().strip()},{path}",
            cwd=checkout,
        )
    git("checkout-index", "--all", cwd=checkout)

    assert git("ls-files", "--stage", "-z") == index
    assert config.read_bytes() == config_bytes
    assert (ROOT / ".gitattributes").read_bytes() == attributes
    assert {path: (ROOT / path).read_bytes() for path in originals} == caller_files
    changed = [
        path
        for path, content in originals.items()
        if (checkout / path).read_bytes() != content
    ]
    assert not changed, f"Lease snapshot checkout changed committed bytes: {changed}"
