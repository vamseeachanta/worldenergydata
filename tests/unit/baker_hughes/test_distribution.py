"""Build and inspect actual archives for #1338, knowledge pack section 12.

The policy deliberately includes the pack. Expected bytes come directly from
the checked-in document, independently of the archive builder. Payload paths
are enumerated from the member's ownership contract, not inferred from output.
Build dependencies (build, setuptools, wheel) must be supplied by the caller.
"""

import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MEMBER = ROOT / "packages" / "worldenergydata-baker_hughes"
PAYLOAD = {
    "worldenergydata/baker_hughes/__init__.py",
    "worldenergydata/baker_hughes/loader.py",
    "worldenergydata/baker_hughes/report.py",
    "worldenergydata/baker_hughes/docs/agent-pack.md",
}


@pytest.fixture(scope="module")
def archives(tmp_path_factory):
    """Default build checks sdist creation and builds the wheel from that sdist."""
    scratch = tmp_path_factory.mktemp("distribution")
    source = scratch / "member"
    shutil.copytree(
        MEMBER,
        source,
        ignore=shutil.ignore_patterns("*.egg-info", "build", "__pycache__"),
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(scratch / "dist"),
            str(source),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    (scratch / "build.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, "Archive build failed; see external build.log"
    wheel = next((scratch / "dist").glob("*.whl"))
    sdist = next((scratch / "dist").glob("*.tar.gz"))
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = sorted(archive.namelist())
    with tarfile.open(sdist) as archive:
        sdist_names = sorted(archive.getnames())
    evidence = json.loads(
        (ROOT / "docs/modules/baker_hughes-distribution-contents.json").read_text()
    )
    assert evidence["members"] == {"wheel": wheel_names, "sdist": sdist_names}
    (scratch / "contents.json").write_text(
        json.dumps({"wheel": wheel_names, "sdist": sdist_names}, indent=2) + "\n"
    )
    return wheel, sdist


def test_wheel_documentation_policy(archives):
    """The wheel owns exactly three Python modules plus the included pack."""
    with zipfile.ZipFile(archives[0]) as archive:
        payload = {
            name for name in archive.namelist() if name.startswith("worldenergydata/")
        }
        assert payload == PAYLOAD
        for name in PAYLOAD:
            assert archive.read(name) == (MEMBER / "src" / name).read_bytes()


def test_sdist_documentation_policy(archives):
    """All four payloads and build inputs survive the source distribution."""
    with tarfile.open(archives[1]) as archive:
        files = {
            "/".join(member.name.split("/")[1:]): member
            for member in archive.getmembers()
            if member.isfile()
        }
        payload = {
            name.removeprefix("src/")
            for name in files
            if name.startswith("src/worldenergydata/")
        }
        assert payload == PAYLOAD
        for name in PAYLOAD:
            assert (
                archive.extractfile(files["src/" + name]).read()
                == (MEMBER / "src" / name).read_bytes()
            )
        for name in ("README.md", "pyproject.toml"):
            assert (
                archive.extractfile(files[name]).read() == (MEMBER / name).read_bytes()
            )
