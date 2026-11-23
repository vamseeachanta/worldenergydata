"""Check the source-file provenance of the historical BSEE write receipt."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "docs/reports/issue-267-live-write.json"
SOURCE_REVISION = "1e35ee97d665432e35b3c5e7b5bd09788982a185"
# Set by the CI step that fetches SOURCE_REVISION (domain-matrix.yml), so a
# missing revision fails there instead of skipping; shallow local checkouts skip.
REQUIRE_HISTORY = "WED_REQUIRE_BSEE_RECEIPT_HISTORY"


def git(*args, check=True):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        check=check,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def require_source_revision(revision):
    if git("cat-file", "-e", f"{revision}^{{commit}}", check=False).returncode == 0:
        return
    if os.environ.get(REQUIRE_HISTORY) == "1":
        pytest.fail(f"{REQUIRE_HISTORY}=1 but source revision {revision} is missing")
    if git("rev-parse", "--is-shallow-repository").stdout.strip() == b"true":
        pytest.skip("The shallow checkout omits the recorded source revision")


@pytest.fixture
def isolated_git(monkeypatch):
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_NO_LAZY_FETCH", "1")


def test_bsee_receipt_source_digests(isolated_git):
    provenance = json.loads(RECEIPT.read_bytes())["provenance"]
    assert provenance["code_revision"] == SOURCE_REVISION
    digests = provenance["file_sha256"]
    assert len(digests) == 27

    require_source_revision(SOURCE_REVISION)

    for path, expected in digests.items():
        blob = git("cat-file", "blob", f"{SOURCE_REVISION}:{path}").stdout
        assert hashlib.sha256(blob).hexdigest() == expected, path


def test_missing_revision_fails_when_history_is_required(isolated_git, monkeypatch):
    monkeypatch.setenv(REQUIRE_HISTORY, "1")
    with pytest.raises(pytest.fail.Exception, match=REQUIRE_HISTORY):
        require_source_revision("0" * 40)
