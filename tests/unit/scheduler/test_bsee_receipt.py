"""Check the source-file provenance of the historical BSEE write receipt."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "docs/reports/issue-267-live-write.json"
SOURCE_REVISION = "1e35ee97d665432e35b3c5e7b5bd09788982a185"


def test_bsee_receipt_source_digests(monkeypatch):
    provenance = json.loads(RECEIPT.read_bytes())["provenance"]
    assert provenance["code_revision"] == SOURCE_REVISION
    digests = provenance["file_sha256"]
    assert len(digests) == 27

    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_NO_LAZY_FETCH", "1")

    def git(*args, check=True):
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            check=check,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    if git("rev-parse", "--is-shallow-repository").stdout.strip() == b"true":
        if git("cat-file", "-e", SOURCE_REVISION, check=False).returncode:
            pytest.skip("The shallow checkout omits the recorded source revision")

    for path, expected in digests.items():
        blob = git("cat-file", "blob", f"{SOURCE_REVISION}:{path}").stdout
        assert hashlib.sha256(blob).hexdigest() == expected, path
