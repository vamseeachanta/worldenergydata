"""BSEE binary ingestion contracts; all inputs are synthetic local fixtures."""

import hashlib
import os
import pickle
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ingest/bsee_binary_ingest.py"


@pytest.fixture
def workspace(tmp_path):
    source = tmp_path / "source"
    project = tmp_path / "project"
    current = source / "current"
    current.mkdir(parents=True)
    (project / "data").mkdir(parents=True)
    (project / "data/catalog.yaml").write_text(
        "version: 2.1.0\nmodules:\n  existing:\n    datasets: []\n", encoding="utf-8"
    )
    return source, project, current


def write_zip(source, relative, members):
    path = source / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    return path


def run_ingest(workspace, *args):
    source, project, current = workspace
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(source),
            "--project-root",
            str(project),
            "--current-root",
            str(current),
            "--date",
            "2026-11-13",
            "--chunk-size",
            "1",
            *args,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def entries(project):
    return yaml.safe_load((project / "data/catalog.yaml").read_text())["modules"][
        "bsee"
    ]["datasets"]
