"""Keep the article's historical replay tied to the four published archives."""

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "docs/articles/gulf-of-america-well-interventions/reusable-prompt.md"
OUTPUT = ROOT / "examples/bsee/interventions_by_depth/output"
ARCHIVES = ROOT / "data/modules/bsee/zip/2026-11-13"
NAMES = (
    "BoreholeRawData.zip",
    "eWellAPMRawData.zip",
    "eWellEORRawData.zip",
    "eWellWARRawData.zip",
)


def article_checksums():
    prompt = ARTICLE.read_text(encoding="utf-8")
    rows = re.findall(r"^([0-9a-f]{64})  (\w+\.zip)$", prompt, re.MULTILINE)
    assert sorted(name for _, name in rows) == sorted(NAMES)
    return {name: digest for digest, name in rows}


def test_prompt_checksums_match_published_receipts():
    receipts = json.loads((OUTPUT / "manifest.json").read_bytes())["files"]
    assert article_checksums() == {
        row["name"]: row["sha256"] for row in receipts if row["status"] == "downloaded"
    }


@pytest.mark.parametrize("name", NAMES)
def test_archived_bytes_match_article_checksum(name):
    if not ARCHIVES.exists():
        pytest.skip("historical archives are distributed separately")
    with (ARCHIVES / name).open("rb") as archive:
        digest = hashlib.sha256()
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    assert digest.hexdigest() == article_checksums()[name]


def analysis_block():
    prompt = ARTICLE.read_text(encoding="utf-8")
    blocks = re.findall(r"^```sh\n(.*?)^```$", prompt, re.MULTILINE | re.DOTALL)
    matches = [block for block in blocks if "count_interventions.py" in block]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_analysis_block_stops_at_first_failure(tmp_path):
    log = tmp_path / "calls.log"
    stub = (
        'python() { echo "$1" >> "$CALL_LOG"; '
        'case "$1" in *count_interventions.py) return 1;; esac; }\n'
    )
    result = subprocess.run(
        ["bash", "-c", stub + analysis_block()],
        cwd=tmp_path,
        env={**os.environ, "CALL_LOG": str(log)},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls == ["examples/bsee/interventions_by_depth/count_interventions.py"]
