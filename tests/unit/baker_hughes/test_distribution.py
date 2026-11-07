"""Offline archive membership evidence for issue #1338.

Expected members follow the Markdown inclusion in the member pyproject.toml,
tool.setuptools.package-data, and the source-tree loader.py runtime control.
No archive is extracted, installed or imported. With no supplied archives, the
fixture needs the declared build requirements (setuptools and wheel) installed;
it calls the unchanged backend on a disposable source copy without resolution.
BAKER_HUGHES_ARTIFACT_DIR may supply a freshly built wheel and sdist instead.
Sorted regular-member inventories default to test scratch; local builds save
build.log there too. Supplied archives do not determine the evidence path.
BAKER_HUGHES_EVIDENCE_DIR redirects inventories and build.log for retention;
uploading these files and binding artifacts to source remain separate steps.
"""

import io
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


@pytest.mark.parametrize("configured_output", [None, "empty", "absolute", "relative"])
def test_supplied_archives_keep_inventories_in_scratch(
    tmp_path, tmp_path_factory, monkeypatch, configured_output
):
    """Inspection must not write beside externally supplied archives."""
    artifact_dir = tmp_path / "caller" / "artifacts"
    artifact_dir.mkdir(parents=True)
    wheel = artifact_dir / "example.whl"
    sdist = artifact_dir / "example.tar.gz"
    with zipfile.ZipFile(wheel, "w") as archive:
        for member in sorted(PACKAGE_MEMBERS):
            archive.writestr(member, "fixture")
    with tarfile.open(sdist, "w:gz") as archive:
        for member in sorted(PACKAGE_MEMBERS):
            info = tarfile.TarInfo("example/src/" + member)
            info.size = 7
            archive.addfile(info, io.BytesIO(b"fixture"))
    before = {path.name: path.read_bytes() for path in artifact_dir.iterdir()}
    monkeypatch.setenv("BAKER_HUGHES_ARTIFACT_DIR", str(artifact_dir))
    monkeypatch.delenv("BAKER_HUGHES_EVIDENCE_DIR", raising=False)
    if configured_output == "absolute":
        monkeypatch.setenv("BAKER_HUGHES_EVIDENCE_DIR", str(tmp_path / "retained"))
    elif configured_output == "relative":
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BAKER_HUGHES_EVIDENCE_DIR", "retained")
    elif configured_output == "empty":
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BAKER_HUGHES_EVIDENCE_DIR", "")

    archives = distribution_archives.__wrapped__(tmp_path_factory)
    test_wheel_contains_pack_and_loader(archives)
    test_sdist_contains_pack_and_loader(archives)

    assert sorted(artifact_dir.parent.iterdir()) == [artifact_dir]
    assert {path.name: path.read_bytes() for path in artifact_dir.iterdir()} == before
    _, _, evidence_dir = archives
    assert evidence_dir.is_absolute()
    if configured_output in ("absolute", "relative"):
        assert evidence_dir == tmp_path / "retained"
    else:
        assert evidence_dir.parent == tmp_path_factory.getbasetemp()
        assert evidence_dir != tmp_path
    inventories = sorted(path.name for path in evidence_dir.glob("*.members.txt"))
    assert inventories == [sdist.name + ".members.txt", wheel.name + ".members.txt"]


@pytest.fixture(scope="module")
def distribution_archives(tmp_path_factory):
    """Supply scratch archive paths, building offline when none are supplied."""
    scratch = tmp_path_factory.mktemp("baker-hughes-distribution")
    evidence_dir = Path(
        os.environ.get("BAKER_HUGHES_EVIDENCE_DIR") or scratch
    ).resolve()
    supplied = os.environ.get("BAKER_HUGHES_ARTIFACT_DIR")
    if supplied:
        artifact_dir = Path(supplied).resolve()
    else:
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
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "build.log").write_text(result.stdout, encoding="utf-8")
        assert result.returncode == 0, result.stdout

    # Exactly one of each format must be supplied; missing/ambiguous input fails.
    (wheel,) = artifact_dir.glob("*.whl")
    (sdist,) = artifact_dir.glob("*.tar.gz")
    return wheel, sdist, evidence_dir


def _archive_members(path, output_dir):
    """Inspect regular archive members and retain the complete sorted inventory."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            members = {
                member.filename for member in archive.infolist() if not member.is_dir()
            }
    else:
        with tarfile.open(path, "r:gz") as archive:
            members = {
                member.name for member in archive.getmembers() if member.isfile()
            }

    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = output_dir / (path.name + ".members.txt")
    inventory.write_text("\n".join(sorted(members)) + "\n", encoding="utf-8")
    return members


def test_wheel_contains_pack_and_loader(distribution_archives):
    wheel, _, evidence_dir = distribution_archives
    members = _archive_members(wheel, evidence_dir)

    assert PACKAGE_MEMBERS <= members, sorted(members)
    print("Wheel members:", *sorted(members), sep="\n")


def test_sdist_contains_pack_and_loader(distribution_archives):
    _, sdist, evidence_dir = distribution_archives
    prefix = sdist.name.removesuffix(".tar.gz") + "/src/"
    expected = {prefix + member for member in PACKAGE_MEMBERS}
    members = _archive_members(sdist, evidence_dir)

    assert expected <= members, sorted(members)
    print("Sdist members:", *sorted(members), sep="\n")


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
@pytest.mark.parametrize("nested_output", [False, True])
def test_archive_inventory_retains_all_members(tmp_path, kind, nested_output):
    """Persist every inspected regular member, including unexpected files."""
    artifact_dir = tmp_path / "dist"
    artifact_dir.mkdir()
    members = PACKAGE_MEMBERS | {"unexpected.txt"}
    if kind == "wheel":
        archive_path = artifact_dir / "example.whl"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("empty/", "")
            for member in sorted(members, reverse=True):
                archive.writestr(member, "fixture")
    else:
        archive_path = artifact_dir / "example.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            directory = tarfile.TarInfo("empty")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
            for member in sorted(members, reverse=True):
                info = tarfile.TarInfo(member)
                info.size = 7
                archive.addfile(info, io.BytesIO(b"fixture"))

    output_dir = tmp_path / "scratch"
    if nested_output:
        output_dir = tmp_path / "retained" / "evidence"

    inspected = _archive_members(archive_path, output_dir)

    assert inspected == members
    inventory = output_dir / (archive_path.name + ".members.txt")
    assert inventory.read_text(encoding="utf-8").splitlines() == sorted(members)
