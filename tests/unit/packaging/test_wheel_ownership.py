"""Artifact ownership cases derived independently from archive member lists.

PEP 427 (2013), sections "File contents" and "The .data directory", defines
the installed paths. PEP 503 (2015), "Normalized Names", defines identity.
ADR 0001, "Risks", assigns the namespace initializer to the root distribution.
Fixture versions are arbitrary identifiers, not engineering inputs.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "ci" / "check_wheel_ownership.py"
)
SPEC = importlib.util.spec_from_file_location("check_wheel_ownership", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def wheel(tmp_path, name, files, *, version="0.1.0", metadata=True):
    """Construct archives from explicit paths, without using the checker."""
    stem = f"{name.replace('-', '_')}-{version}"
    path = tmp_path / f"{stem}-py3-none-any.whl"
    with ZipFile(path, "w") as archive:
        if metadata:
            archive.writestr(
                f"{stem}.dist-info/METADATA",
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
            )
        for filename in files:
            archive.writestr(filename, "")
    return path


def test_disjoint_members_without_root_are_independent(tmp_path):
    """common/a.py and eia/a.py have empty intersection; no root is required."""
    core = wheel(tmp_path, "worldenergydata-core", ["worldenergydata/common/a.py"])
    domain = wheel(tmp_path, "worldenergydata-eia", ["worldenergydata/eia/a.py"])
    assert checker.check_wheels([core, domain]) == []


def test_root_distribution_may_own_initializer(tmp_path):
    root = wheel(tmp_path, "worldenergydata", ["worldenergydata/__init__.py"])
    core = wheel(tmp_path, "worldenergydata-core", ["worldenergydata/common/a.py"])
    assert checker.check_wheels([root, core]) == []


@pytest.mark.parametrize("placement", ["", "purelib", "platlib"])
def test_member_cannot_own_namespace_initializer(tmp_path, placement):
    """Each library placement installs the same forbidden namespace root."""
    prefix = f"worldenergydata_eia-0.1.0.data/{placement}/" if placement else ""
    domain = wheel(
        tmp_path, "worldenergydata-eia", [prefix + "worldenergydata/__init__.py"]
    )
    errors = checker.check_wheels([domain])
    assert any("namespace root" in error for error in errors)


@pytest.mark.parametrize("placement", ["", "purelib", "platlib"])
def test_overlapping_installed_files_are_rejected(tmp_path, placement):
    """Intersection is {worldenergydata/common/a.py}, including .data spreading."""
    shared = "worldenergydata/common/a.py"
    prefix = f"worldenergydata_eia-0.1.0.data/{placement}/" if placement else ""
    core = wheel(tmp_path, "worldenergydata-core", [shared])
    domain = wheel(tmp_path, "worldenergydata-eia", [prefix + shared])
    errors = checker.check_wheels([core, domain])
    assert any("overlap" in error and shared in error for error in errors)


def test_data_files_are_owned_too(tmp_path):
    """Identical bytes still conflict: uninstalling either removes the file."""
    shared = "worldenergydata/common/schema.json"
    core = wheel(tmp_path, "worldenergydata-core", [shared])
    domain = wheel(tmp_path, "worldenergydata-eia", [shared])
    assert any("overlap" in error for error in checker.check_wheels([core, domain]))


def test_shared_directory_entries_do_not_conflict(tmp_path):
    core = wheel(tmp_path, "worldenergydata-core", ["worldenergydata/"])
    domain = wheel(tmp_path, "worldenergydata-eia", ["worldenergydata/"])
    assert checker.check_wheels([core, domain]) == []


def test_non_library_data_does_not_claim_namespace(tmp_path):
    root = wheel(tmp_path, "worldenergydata", ["worldenergydata/__init__.py"])
    domain = wheel(
        tmp_path,
        "worldenergydata-eia",
        ["worldenergydata_eia-0.1.0.data/data/worldenergydata/__init__.py"],
    )
    assert checker.check_wheels([root, domain]) == []


def test_normalized_distribution_identity_must_be_unique(tmp_path):
    """PEP 503: underscores, dots and hyphen runs normalize to a hyphen."""
    first = wheel(tmp_path, "WorldEnergyData_EIA", ["worldenergydata/eia/a.py"])
    second = wheel(tmp_path, "worldenergydata.eia", ["worldenergydata/eia/b.py"])
    assert any(
        "duplicate distribution" in error
        for error in checker.check_wheels([first, second])
    )


def test_multiple_versions_are_not_coinstallable(tmp_path):
    first = wheel(tmp_path, "worldenergydata-eia", [], version="0.1.0")
    second = wheel(tmp_path, "worldenergydata-eia", [], version="0.2.0")
    assert any(
        "duplicate distribution" in error
        for error in checker.check_wheels([first, second])
    )


def test_missing_metadata_is_an_error(tmp_path):
    artifact = wheel(tmp_path, "worldenergydata-eia", [], metadata=False)
    assert any("METADATA" in error for error in checker.check_wheels([artifact]))


def test_multiple_metadata_records_are_an_error(tmp_path):
    artifact = wheel(tmp_path, "worldenergydata-eia", [])
    with ZipFile(artifact, "a") as archive:
        archive.writestr("other-0.1.0.dist-info/METADATA", "Name: other\n")
    assert any("METADATA" in error for error in checker.check_wheels([artifact]))


@pytest.mark.parametrize("missing", ["Name", "Version"])
def test_incomplete_identity_is_an_error(tmp_path, missing):
    artifact = wheel(tmp_path, "worldenergydata-eia", [], metadata=False)
    fields = {"Name": "worldenergydata-eia", "Version": "0.1.0"}
    fields.pop(missing)
    with ZipFile(artifact, "a") as archive:
        archive.writestr(
            "worldenergydata_eia-0.1.0.dist-info/METADATA",
            "".join(f"{key}: {value}\n" for key, value in fields.items()),
        )
    assert any("identity" in error for error in checker.check_wheels([artifact]))


def test_invalid_archive_is_an_error(tmp_path):
    artifact = tmp_path / "broken.whl"
    artifact.write_text("not a ZIP archive", encoding="utf-8")
    assert any("cannot read" in error for error in checker.check_wheels([artifact]))


def test_empty_selection_is_an_error():
    assert checker.check_wheels([])


@pytest.mark.parametrize("conflict", [False, True])
def test_command_line_exit_status(tmp_path, conflict):
    files = (
        ["worldenergydata/__init__.py"] if conflict else ["worldenergydata/eia/a.py"]
    )
    artifact = wheel(tmp_path, "worldenergydata-eia", files)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(artifact)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert bool(result.returncode) is conflict
    assert ("namespace root" in result.stderr) is conflict


@pytest.mark.parametrize("file_first", [False, True])
@pytest.mark.parametrize("file_placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize("child_placement", ["", "purelib", "platlib"])
def test_file_ancestor_conflicts_are_rejected(
    tmp_path, file_first, file_placement, child_placement
):
    """Both sorted processing orders must reject incompatible destinations."""
    file_name, child_name = ("a", "z") if file_first else ("z", "a")
    file_prefix = f"a-0.1.0.data/{file_placement}/" if file_placement else ""
    child_prefix = f"z-0.1.0.data/{child_placement}/" if child_placement else ""
    parent = wheel(tmp_path, file_name, [file_prefix + "worldenergydata/eia"])
    child = wheel(tmp_path, child_name, [child_prefix + "worldenergydata/eia/a.py"])
    errors = checker.check_wheels([parent, child])
    assert any("file/directory conflict at worldenergydata/eia" in e for e in errors)


def test_shared_implied_directories_are_allowed(tmp_path):
    first = wheel(tmp_path, "a", ["worldenergydata/eia/a.py"])
    second = wheel(tmp_path, "z", ["worldenergydata/eia/b.py"])
    assert checker.check_wheels([first, second]) == []
