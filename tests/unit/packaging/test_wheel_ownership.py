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
@pytest.mark.parametrize(
    "shared", ["worldenergydata/common/a.py", "external/a.py", "tool.py"]
)
def test_overlapping_installed_files_are_rejected(tmp_path, placement, shared):
    """The named library file is the intersection, including .data spreading."""
    prefix = f"worldenergydata_eia-0.1.0.data/{placement}/" if placement else ""
    core = wheel(tmp_path, "worldenergydata-core", [shared])
    domain = wheel(tmp_path, "worldenergydata-eia", [prefix + shared])
    errors = checker.check_wheels([core, domain])
    assert any("overlap" in error and shared in error for error in errors)


@pytest.mark.parametrize("file_placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize("child_placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize("file_first", [False, True])
@pytest.mark.parametrize(
    "parent, child",
    [
        ("worldenergydata", "worldenergydata/eia/a.py"),
        ("worldenergydata/eia", "worldenergydata/eia/a.py"),
        ("worldenergydata/eia", "worldenergydata/eia/data/a.py"),
        ("external", "external/a.py"),
        ("tool.py", "tool.py/data/a.py"),
    ],
)
def test_file_directory_conflicts_are_rejected(
    tmp_path, file_placement, child_placement, file_first, parent, child
):
    """A file cannot occupy a parent directory required by another wheel."""
    file_name, child_name = ("a", "z") if file_first else ("z", "a")
    file_prefix = f"{file_name}-0.1.0.data/{file_placement}/" if file_placement else ""
    child_prefix = (
        f"{child_name}-0.1.0.data/{child_placement}/" if child_placement else ""
    )
    file_wheel = wheel(tmp_path, file_name, [file_prefix + parent])
    child_wheel = wheel(tmp_path, child_name, [child_prefix + child])
    errors = checker.check_wheels([file_wheel, child_wheel])
    assert any(
        "file/directory conflict" in error
        and parent in error
        and file_wheel.name in error
        and child_wheel.name in error
        for error in errors
    )


@pytest.mark.parametrize("placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize(
    "first, second",
    [
        ("worldenergydata/common/a.py", "worldenergydata/common/b.py"),
        ("worldenergydata/eia", "worldenergydata/eia_us/a.py"),
        ("worldenergydata/eia/a.py", "worldenergydata/eia_extra"),
    ],
)
def test_shared_parents_and_similarly_prefixed_siblings_are_valid(
    tmp_path, placement, first, second
):
    """Shared parents and distinct path components have no file intersection."""
    prefix = f"worldenergydata_eia-0.1.0.data/{placement}/" if placement else ""
    core = wheel(tmp_path, "worldenergydata-core", [first])
    domain = wheel(tmp_path, "worldenergydata-eia", [prefix + second])
    assert checker.check_wheels([core, domain]) == []


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


def test_disjoint_non_namespace_libraries_and_metadata_are_valid(tmp_path):
    core = wheel(tmp_path, "worldenergydata-core", ["external/__init__.py", "tool.py"])
    domain = wheel(
        tmp_path,
        "worldenergydata-eia",
        [
            "private_pkg/__init__.py",
            "other_tool.py",
            "worldenergydata_eia-0.1.0.dist-info/NOTICE",
        ],
    )
    with ZipFile(core, "a") as archive:
        archive.writestr("worldenergydata_core-0.1.0.dist-info/NOTICE", "")
    assert checker.check_wheels([core, domain]) == []


@pytest.mark.parametrize("first_placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize("second_placement", ["", "purelib", "platlib"])
def test_unrelated_metadata_paths_are_owned(
    tmp_path, first_placement, second_placement
):
    """Only each wheel's own top-level metadata is exempt from ownership."""
    shared = "shared.dist-info/notice"
    first_prefix = f"a-0.1.0.data/{first_placement}/" if first_placement else ""
    second_prefix = f"z-0.1.0.data/{second_placement}/" if second_placement else ""
    first = wheel(tmp_path, "a", [first_prefix + shared])
    second = wheel(tmp_path, "z", [second_prefix + shared])
    assert any(
        "overlap" in error and shared in error
        for error in checker.check_wheels([first, second])
    )


@pytest.mark.parametrize("placement", ["purelib", "platlib"])
def test_relocated_own_metadata_directory_is_library_payload(tmp_path, placement):
    shared = "a-0.1.0.dist-info/notice"
    first = wheel(tmp_path, "a", [f"a-0.1.0.data/{placement}/" + shared])
    second = wheel(tmp_path, "z", ["z-0.1.0.data/purelib/" + shared])
    assert any(
        "overlap" in error and shared in error
        for error in checker.check_wheels([first, second])
    )


@pytest.mark.parametrize("placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize("suffix", ["pyc", "abi3.so", "cp311-win_amd64.pyd"])
def test_binary_namespace_initializers_are_rejected(tmp_path, placement, suffix):
    prefix = f"worldenergydata_eia-0.1.0.data/{placement}/" if placement else ""
    domain = wheel(
        tmp_path, "worldenergydata-eia", [prefix + f"worldenergydata/__init__.{suffix}"]
    )
    assert any("namespace root" in error for error in checker.check_wheels([domain]))


def test_nested_and_similarly_named_initializers_are_valid(tmp_path):
    domain = wheel(
        tmp_path,
        "worldenergydata-eia",
        ["worldenergydata/eia/__init__.pyc", "worldenergydata/__init__extra.py"],
    )
    root = wheel(tmp_path, "worldenergydata", ["worldenergydata/__init__.abi3.so"])
    assert checker.check_wheels([root, domain]) == []


@pytest.mark.parametrize("placement", ["", "purelib", "platlib"])
@pytest.mark.parametrize("file_first", [False, True])
@pytest.mark.parametrize("directory_conflict", [False, True])
def test_case_only_library_collisions_are_rejected(
    tmp_path, placement, file_first, directory_conflict
):
    first_name, second_name = ("a", "z") if file_first else ("z", "a")
    first = "worldenergydata/EIA" if directory_conflict else "worldenergydata/EIA/A.py"
    second = "worldenergydata/eia/a.py"
    prefix = f"{second_name}-0.1.0.data/{placement}/" if placement else ""
    first_wheel = wheel(tmp_path, first_name, [first])
    second_wheel = wheel(tmp_path, second_name, [prefix + second])
    expected = "file/directory conflict" if directory_conflict else "overlap"
    assert any(
        expected in error for error in checker.check_wheels([first_wheel, second_wheel])
    )


@pytest.mark.parametrize(
    "filename",
    [
        "worldenergydata/eia/../a.py",
        "../worldenergydata/eia/a.py",
        "member-0.1.0.data/purelib/../worldenergydata/a.py",
        "member-0.1.0.data/data/../a.py",
        "unused/../",
    ],
)
def test_parent_traversal_is_rejected_before_mapping(tmp_path, filename):
    artifact = wheel(tmp_path, "worldenergydata-eia", [filename])
    assert any(
        "parent traversal" in error for error in checker.check_wheels([artifact])
    )


@pytest.mark.parametrize(
    "filename",
    [
        "/worldenergydata/__init__.py",
        "//worldenergydata/__init__.py",
        r"worldenergydata\__init__.py",
        r"\worldenergydata\__init__.py",
        "member-0.1.0.data/data/invalid\\entry",
        "/unused/",
    ],
)
def test_absolute_and_backslash_paths_are_rejected_before_mapping(tmp_path, filename):
    artifact = wheel(tmp_path, "worldenergydata-eia", [filename])
    assert any(
        "invalid archive path" in error for error in checker.check_wheels([artifact])
    )


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
    artifact.write_text("not a ZIP archive", encoding="utf-8", newline="\n")
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
        encoding="utf-8",
        check=False,
    )
    assert bool(result.returncode) is conflict
    assert ("namespace root" in result.stderr) is conflict
