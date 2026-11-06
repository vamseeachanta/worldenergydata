"""Offline archive membership evidence for issue #1338.

Expected members follow the Markdown inclusion in the member pyproject.toml,
tool.setuptools.package-data, and the source-tree loader.py runtime control.
No archive is extracted, installed or imported. With no supplied archives, the
fixture needs the declared build requirements (setuptools and wheel) installed;
it calls the unchanged backend on a disposable source copy without resolution.
BAKER_HUGHES_ARTIFACT_DIR may supply a freshly built wheel and sdist instead.
"""

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

PACKAGE_MEMBERS = {
    "worldenergydata/baker_hughes/docs/agent-pack.md",
    "worldenergydata/baker_hughes/loader.py",
}


def _copy_source(source, destination):
    """Copy the member source for an offline build."""
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("build", "dist", "*.egg-info", "__pycache__"),
    )


def test_source_copy_excludes_generated_directories(tmp_path):
    source = tmp_path / "checkout"
    for relative in (
        "build/stale.py",
        "dist/stale.whl",
        "src/stale.egg-info/SOURCES.txt",
        "src/__pycache__/stale.pyc",
        "src/loader.py",
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")

    destination = tmp_path / "source"
    _copy_source(source, destination)

    assert sorted(
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    ) == ["src/loader.py"]


def test_distribution_boundary_retains_evidence_gap():
    repo = Path(__file__).resolve().parents[3]
    pack = repo / (
        "packages/worldenergydata-baker_hughes/src/"
        "worldenergydata/baker_hughes/docs/agent-pack.md"
    )
    (row,) = (
        line
        for line in pack.read_text(encoding="utf-8").splitlines()
        if line.startswith("| Distribution boundary |")
    )
    disposition = row.split("|")[2].strip()
    assert disposition.startswith("UNVERIFIED:")
    for required in (
        "artifact-evidence gap remains open",
        "supplied archives are not bound to the reviewed source",
        "source revision and digests",
        "build command",
        "measured tool versions",
        "archive digests",
        "member inventories and result",
        "Membership alone does not verify installed behavior",
    ):
        assert required in disposition, required


@pytest.fixture(scope="module")
def distribution_archives(tmp_path_factory):
    """Supply scratch archive paths, building offline when none are supplied."""
    supplied = os.environ.get("BAKER_HUGHES_ARTIFACT_DIR")
    if supplied:
        artifact_dir = Path(supplied).resolve()
    else:
        scratch = tmp_path_factory.mktemp("baker-hughes-distribution")
        # tests/unit/baker_hughes/test_distribution.py -> repository root.
        repo = Path(__file__).resolve().parents[3]
        source = scratch / "source"
        _copy_source(repo / "packages/worldenergydata-baker_hughes", source)
        artifact_dir = scratch / "dist"
        artifact_dir.mkdir()
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from setuptools.build_meta import build_sdist, build_wheel; "
                "import sys; destination = sys.argv[1]; "
                "build_sdist(destination); build_wheel(destination)",
                str(artifact_dir),
            ],
            cwd=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        (scratch / "build.log").write_text(result.stdout, encoding="utf-8")
        assert result.returncode == 0, result.stdout

    # Exactly one of each format must be supplied; missing/ambiguous input fails.
    (wheel,) = artifact_dir.glob("*.whl")
    (sdist,) = artifact_dir.glob("*.tar.gz")
    return wheel, sdist


def test_wheel_contains_pack_and_loader(distribution_archives, capsys):
    wheel, _ = distribution_archives
    with zipfile.ZipFile(wheel) as archive:
        members = {
            member.filename for member in archive.infolist() if not member.is_dir()
        }

    assert PACKAGE_MEMBERS <= members, sorted(members)
    print("Wheel members:", *sorted(members), sep="\n")
    output = capsys.readouterr().out
    assert output.splitlines() == ["Wheel members:", *sorted(members)]
    print(output, end="")


def test_sdist_contains_pack_and_loader(distribution_archives, capsys):
    _, sdist = distribution_archives
    prefix = sdist.name.removesuffix(".tar.gz") + "/src/"
    expected = {prefix + member for member in PACKAGE_MEMBERS}
    with tarfile.open(sdist, "r:gz") as archive:
        members = {member.name for member in archive.getmembers() if member.isfile()}

    assert expected <= members, sorted(members)
    print("Sdist members:", *sorted(members), sep="\n")
    output = capsys.readouterr().out
    assert output.splitlines() == ["Sdist members:", *sorted(members)]
    print(output, end="")
