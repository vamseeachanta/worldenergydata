"""TDD coverage for the repo-structure normalization checker (#394)."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.maintenance import verify_repo_structure
from scripts.maintenance.verify_repo_structure import (
    RepoStructureViolation,
    load_contract,
    main,
    root_for,
    validate_paths,
)


def _contract(tmp_path: Path, overrides: dict | None = None) -> Path:
    payload = {
        "allowed_roots": [
            "src",
            "tests",
            "docs",
            "config",
            "scripts",
            "README.md",
            "pyproject.toml",
        ],
        "ignored_roots": [".git", ".venv", "__pycache__"],
        "generated_artifact_roots": ["reports", "results", "output", "logs"],
        "temporary_exceptions": {
            "reports": {
                "category": "durable-evidence",
                "owner": "worldenergydata maintainers",
                "review_date": "2026-06-30",
                "follow_up": "https://github.com/vamseeachanta/worldenergydata/issues/394",
                "justification": (
                    "Tracked report artifacts require a dedicated generated-evidence "
                    "migration issue before relocation or deletion."
                ),
            }
        },
    }
    if overrides:
        payload.update(overrides)
    path = tmp_path / "repo_structure.yml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_checker_rejects_unapproved_root_entry(tmp_path: Path) -> None:
    contract = load_contract(_contract(tmp_path))

    violations = validate_paths(
        ["src/worldenergydata/__init__.py", "scratch.txt"], contract
    )

    assert (
        RepoStructureViolation("unknown-root", "scratch.txt", "scratch.txt")
        in violations
    )


def test_checker_rejects_generated_root_without_exception(tmp_path: Path) -> None:
    contract = load_contract(_contract(tmp_path, {"temporary_exceptions": {}}))

    violations = validate_paths(["reports/demo.html"], contract)

    assert (
        RepoStructureViolation(
            "generated-root-missing-exception", "reports", "reports/demo.html"
        )
        in violations
    )


def test_checker_rejects_placeholder_exception_metadata(tmp_path: Path) -> None:
    contract = load_contract(
        _contract(
            tmp_path,
            {
                "temporary_exceptions": {
                    "reports": {
                        "category": "durable-evidence",
                        "owner": "TBD",
                        "review_date": "TODO",
                        "follow_up": "https://github.com/vamseeachanta/worldenergydata/issues/394",
                        "justification": "TODO",
                    }
                }
            },
        )
    )

    violations = validate_paths(["reports/demo.html"], contract)

    assert (
        RepoStructureViolation("invalid-exception-metadata", "reports", "reports")
        in violations
    )


def test_checker_rejects_generated_path_not_listed_in_exception(tmp_path: Path) -> None:
    contract = load_contract(
        _contract(
            tmp_path,
            {
                "temporary_exceptions": {
                    "reports": {
                        "category": "durable-evidence",
                        "owner": "worldenergydata maintainers",
                        "review_date": "2026-06-30",
                        "follow_up": "https://github.com/vamseeachanta/worldenergydata/issues/394",
                        "justification": (
                            "Tracked report artifacts require explicit path-level "
                            "classification before relocation or deletion."
                        ),
                        "allowed_paths": ["reports/REPORT_SUMMARY.md"],
                    }
                }
            },
        )
    )

    violations = validate_paths(["reports/new-report.html"], contract)

    assert (
        RepoStructureViolation(
            "generated-path-not-classified", "reports", "reports/new-report.html"
        )
        in violations
    )


def test_current_contract_accepts_approved_roots_and_exceptions() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    contract = load_contract(repo_root / "config" / "repo_structure.yml")
    paths = subprocess.check_output(
        ["git", "ls-files"], cwd=repo_root, text=True
    ).splitlines()

    violations = validate_paths(paths, contract)

    assert violations == []


def test_tracked_root_files_have_no_unknown_root_violations(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(key, raising=False)
    contract = load_contract(repo_root / "config" / "repo_structure.yml")
    root_files = [
        path
        for path in verify_repo_structure.git_tracked_paths(repo_root)
        if "/" not in path
    ]

    assert "MANIFEST.in" in root_files

    violations = validate_paths(root_files, contract)

    assert not [
        violation for violation in violations if violation.code == "unknown-root"
    ]


def test_root_for_preserves_leading_dot_roots() -> None:
    assert root_for(".github/workflows/ci.yml") == ".github"
    assert root_for(".claude/settings.json") == ".claude"
    assert root_for("./.planning/plan-approved/394.md") == ".planning"


def test_pre_commit_wires_repo_structure_checker() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    precommit = (repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "repo-structure-contract" in precommit
    assert "scripts/maintenance/verify_repo_structure.py" in precommit


def test_cli_reports_violations_for_explicit_paths(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/maintenance/verify_repo_structure.py",
            "--config",
            str(contract),
            "--path",
            "scratch.txt",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "unknown-root" in result.stdout
    assert "scratch.txt" in result.stdout


def test_parse_git_status_paths_unquotes_renamed_paths_with_spaces() -> None:
    paths = verify_repo_structure.parse_git_status_paths(
        'R  "old name.txt" -> "new folder/new name.txt"\n'
    )

    assert paths == ["new folder/new name.txt"]


def test_default_cli_includes_nonignored_worktree_paths(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    contract = _contract(tmp_path)
    monkeypatch.setattr(
        verify_repo_structure, "git_tracked_paths", lambda repo_root: []
    )
    monkeypatch.setattr(
        verify_repo_structure,
        "git_worktree_status_entries",
        lambda repo_root: [
            verify_repo_structure.WorktreeStatusEntry("??", "scratch/file.txt")
        ],
    )

    result = main(["--config", str(contract)])

    captured = capsys.readouterr()
    assert result == 1
    assert "unknown-root" in captured.out
    assert "scratch/file.txt" in captured.out


def test_deleted_generated_artifact_is_rejected_even_when_classified(
    tmp_path: Path,
) -> None:
    contract = load_contract(
        _contract(
            tmp_path,
            {
                "temporary_exceptions": {
                    "reports": {
                        "category": "durable-evidence",
                        "owner": "worldenergydata maintainers",
                        "review_date": "2026-06-30",
                        "follow_up": "https://github.com/vamseeachanta/worldenergydata/issues/394",
                        "justification": (
                            "Tracked report artifacts require explicit path-level "
                            "classification before relocation or deletion."
                        ),
                        "allowed_paths": ["reports/REPORT_SUMMARY.md"],
                    }
                }
            },
        )
    )

    violations = verify_repo_structure.validate_worktree_status_entries(
        [verify_repo_structure.WorktreeStatusEntry(" D", "reports/REPORT_SUMMARY.md")],
        contract,
    )

    assert (
        RepoStructureViolation(
            "generated-artifact-deletion-or-relocation",
            "reports",
            "reports/REPORT_SUMMARY.md",
        )
        in violations
    )


def test_renamed_generated_artifact_is_rejected_as_relocation(tmp_path: Path) -> None:
    contract = load_contract(
        _contract(
            tmp_path,
            {
                "temporary_exceptions": {
                    "reports": {
                        "category": "durable-evidence",
                        "owner": "worldenergydata maintainers",
                        "review_date": "2026-06-30",
                        "follow_up": "https://github.com/vamseeachanta/worldenergydata/issues/394",
                        "justification": (
                            "Tracked report artifacts require explicit path-level "
                            "classification before relocation or deletion."
                        ),
                        "allowed_paths": ["reports/old.md", "reports/new.md"],
                    }
                }
            },
        )
    )

    entries = verify_repo_structure.parse_git_status_entries(
        'R  "reports/old.md" -> "reports/new.md"\n'
    )
    violations = verify_repo_structure.validate_worktree_status_entries(
        entries, contract
    )

    assert (
        RepoStructureViolation(
            "generated-artifact-deletion-or-relocation",
            "reports",
            "reports/old.md -> reports/new.md",
        )
        in violations
    )


def _retirement_entry() -> dict:
    """Return a synthetic retirement with a binary-content digest."""
    return {
        "path": "reports/example.txt",
        "sha256": hashlib.sha256(b"committed\x00content\xff").hexdigest(),
        "date": "2026-10-13",
        "reason": "The generated example is retained in a verified dataset.",
        "disposition": {
            "kind": "cold-store",
            "dataset_path": "generated/example",
            "digest_list": "sha256.txt",
        },
        "follow_up": "https://github.com/vamseeachanta/worldenergydata/pull/394",
    }


def _fixture_git(root: Path, *args: str) -> bytes:
    """Run Git solely against the disposable repository."""
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.STDOUT)


def _fixture_commit(root: Path) -> None:
    """Commit synthetic evidence without changing any Git configuration."""
    _fixture_git(root, "add", "-u")
    _fixture_git(root, "add", "config")
    if (root / "reports").exists():
        _fixture_git(root, "add", "reports")
    _fixture_git(
        root,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "test fixture",
    )


@pytest.fixture
def retirement_repo(tmp_path: Path, monkeypatch):
    """Create an isolated repository with one committed generated artifact."""
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    _fixture_git(tmp_path, "init")
    (tmp_path / "config").mkdir()
    contract_path = _contract(tmp_path / "config")
    contract_path.rename(tmp_path / "config/repo_structure.yml")
    payload = yaml.safe_load((tmp_path / "config/repo_structure.yml").read_text())
    payload["temporary_exceptions"]["reports"]["allowed_paths"] = [
        "reports/example.txt"
    ]
    (tmp_path / "config/repo_structure.yml").write_text(yaml.safe_dump(payload))
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/example.txt").write_bytes(b"committed\x00content\xff")
    _fixture_commit(tmp_path)
    return tmp_path


def _write_register(root: Path, entries: object) -> None:
    """Write the register beside the disposable contract."""
    (root / "config/generated_retirements.yml").write_text(
        yaml.safe_dump({"retirements": entries}), encoding="utf-8"
    )


def _set_allowed_paths(root: Path, paths: list[str]) -> None:
    """Change classification solely in the disposable repository."""
    target = root / "config/repo_structure.yml"
    payload = yaml.safe_load(target.read_text())
    payload["temporary_exceptions"]["reports"]["allowed_paths"] = paths
    target.write_text(yaml.safe_dump(payload), encoding="utf-8")


def _assert_checker(capsys, expected: set[str], result: int = 1) -> None:
    """Assert the complete set of violation codes from the real CLI."""
    assert main([]) == result
    output = capsys.readouterr().out
    codes = {
        line.split(":", 1)[0][2:]
        for line in output.splitlines()
        if line.startswith("- ")
    }
    assert codes == expected


@pytest.mark.parametrize("staged", [True, False], ids=["staged", "unstaged"])
def test_retirement_deletion_reads_head_and_status_end_to_end(
    retirement_repo: Path, capsys, staged: bool
) -> None:
    """Matching HEAD bytes authorize staged and unstaged fixture deletions."""
    if staged:
        _fixture_git(retirement_repo, "rm", "reports/example.txt")
    else:
        (retirement_repo / "reports/example.txt").unlink()
    _set_allowed_paths(retirement_repo, [])
    _write_register(retirement_repo, [_retirement_entry()])
    _assert_checker(capsys, set(), 0)


def test_retirement_digest_is_computed_from_head(retirement_repo: Path, capsys) -> None:
    """A digest of different bytes cannot authorize a retirement."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _set_allowed_paths(retirement_repo, [])
    entry = _retirement_entry()
    entry["sha256"] = hashlib.sha256(b"other content").hexdigest()
    _write_register(retirement_repo, [entry])
    _assert_checker(capsys, {"retirement-digest-mismatch"})


def test_retirement_entry_for_tracked_path_is_rejected(
    retirement_repo: Path, capsys
) -> None:
    """An entry cannot precede the deletion it authorizes."""
    _set_allowed_paths(retirement_repo, [])
    _write_register(retirement_repo, [_retirement_entry()])
    _assert_checker(capsys, {"retirement-entry-for-tracked-path"})


@pytest.mark.parametrize(
    "classified", [True, False], ids=["classified", "unclassified"]
)
def test_retirement_rename_classifies_new_path(
    retirement_repo: Path, capsys, classified: bool
) -> None:
    """A rename retires its old path and classifies its new path normally."""
    _fixture_git(retirement_repo, "mv", "reports/example.txt", "reports/new.txt")
    _set_allowed_paths(retirement_repo, ["reports/new.txt"] if classified else [])
    _write_register(retirement_repo, [_retirement_entry()])
    _assert_checker(
        capsys,
        set() if classified else {"generated-path-not-classified"},
        0 if classified else 1,
    )


def test_retirement_leftover_allowed_row_is_rejected(
    retirement_repo: Path, capsys
) -> None:
    """A retired path cannot remain in both policy lists."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _write_register(retirement_repo, [_retirement_entry()])
    _assert_checker(capsys, {"retired-path-still-allowed"})


def test_retirement_independent_errors_accumulate(
    retirement_repo: Path, capsys
) -> None:
    """A wrong digest and leftover classification are both reported."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    entry = _retirement_entry()
    entry["sha256"] = "0" * 64
    _write_register(retirement_repo, [entry])
    _assert_checker(
        capsys, {"retirement-digest-mismatch", "retired-path-still-allowed"}
    )


def test_retirement_missing_register_is_empty(retirement_repo: Path, capsys) -> None:
    """Regression pin: an absent register preserves the existing policy."""
    _assert_checker(capsys, set(), 0)


def test_retirement_repository_register_exists_and_loads() -> None:
    """The repository supplies a loadable register without pinning its contents."""
    root = Path(__file__).resolve().parents[2]
    register = root / "config/generated_retirements.yml"
    assert register.is_file()
    entries, violations = verify_repo_structure.load_retirements(
        register, load_contract(root / "config/repo_structure.yml")
    )
    assert isinstance(entries, dict)
    assert violations == []


@pytest.mark.parametrize(
    "disposition",
    [
        {"kind": "reproducible", "command": "python scripts/generate_example.py"},
        {
            "kind": "cold-store",
            "dataset_path": "generated/example",
            "digest_list": "sha256.txt",
        },
    ],
    ids=["reproducible", "cold-store"],
)
def test_retirement_dispositions_and_historical_entries(
    retirement_repo: Path, capsys, disposition: dict
) -> None:
    """Merged retirements are checked for form without reading absent HEAD bytes."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _set_allowed_paths(retirement_repo, [])
    entry = _retirement_entry()
    entry["disposition"] = disposition
    _write_register(retirement_repo, [entry])
    _fixture_commit(retirement_repo)
    assert _fixture_git(retirement_repo, "status", "--porcelain") == b""
    _assert_checker(capsys, set(), 0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "ABC"),
        ("sha256", "A" * 64),
        ("sha256", 1),
        ("date", "13-10-2026"),
        ("date", "2026-02-30"),
        ("date", 1),
        ("reason", "TBD"),
        ("reason", "short"),
        ("reason", 1),
        ("path", "src/example.txt"),
        ("path", "/reports/example.txt"),
        ("path", "reports/../example.txt"),
        ("path", "reports//example.txt"),
        ("path", "reports\\example.txt"),
        ("path", 1),
        ("follow_up", "https://example.invalid/issues/1"),
        (
            "follow_up",
            "https://github.com/vamseeachanta/worldenergydata/issues/394/extra",
        ),
        ("follow_up", 1),
        ("disposition", {"kind": "unknown"}),
        ("disposition", {"kind": "cold-store", "digest_list": "sha256.txt"}),
        ("disposition", {"kind": "cold-store", "dataset_path": "generated/example"}),
        ("disposition", {"kind": "reproducible"}),
        ("disposition", {"kind": "reproducible", "command": "TBD"}),
        (
            "disposition",
            {"kind": "reproducible", "command": "generate", "extra": "value"},
        ),
        (
            "disposition",
            {
                "kind": "cold-store",
                "dataset_path": "/store/example",
                "digest_list": "sha256.txt",
            },
        ),
        (
            "disposition",
            {
                "kind": "cold-store",
                "dataset_path": "Z:/example",
                "digest_list": "sha256.txt",
            },
        ),
        (
            "disposition",
            {
                "kind": "cold-store",
                "dataset_path": "https://example.invalid/store",
                "digest_list": "sha256.txt",
            },
        ),
        (
            "disposition",
            {
                "kind": "cold-store",
                "dataset_path": "../example",
                "digest_list": "sha256.txt",
            },
        ),
        (
            "disposition",
            {
                "kind": "cold-store",
                "dataset_path": "generated/example",
                "digest_list": "/sha256.txt",
            },
        ),
        ("disposition", []),
        ("extra", "value"),
    ],
)
def test_retirement_malformed_field_is_rejected(
    retirement_repo: Path, capsys, field: str, value: object
) -> None:
    """Malformed entries cannot exempt a deleted path from existing checks."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _set_allowed_paths(retirement_repo, [])
    entry = _retirement_entry()
    entry[field] = value
    _write_register(retirement_repo, [entry])
    _assert_checker(
        capsys,
        {
            "invalid-retirement-entry",
            "generated-path-not-classified",
            "generated-artifact-deletion-or-relocation",
        },
    )


@pytest.mark.parametrize("field", list(_retirement_entry()))
def test_retirement_missing_field_is_rejected(
    retirement_repo: Path, capsys, field: str
) -> None:
    """Every schema field is required."""
    entry = _retirement_entry()
    del entry[field]
    _write_register(retirement_repo, [entry])
    _assert_checker(capsys, {"invalid-retirement-entry"})


def test_retirement_duplicate_path_is_rejected(retirement_repo: Path, capsys) -> None:
    """A path has at most one retirement record."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _set_allowed_paths(retirement_repo, [])
    _write_register(retirement_repo, [_retirement_entry(), _retirement_entry()])
    _assert_checker(capsys, {"duplicate-retirement-entry"})


@pytest.mark.parametrize("entries", [None, {}, ["invalid"], [None]])
def test_retirement_wrong_container_type_is_rejected(
    retirement_repo: Path, capsys, entries: object
) -> None:
    """Register and entry containers have a fixed shape."""
    _write_register(retirement_repo, entries)
    _assert_checker(capsys, {"invalid-retirement-entry"})


def test_retirement_unreadable_head_is_not_accepted(
    retirement_repo: Path, capsys
) -> None:
    """A staged deletion with no committed source bytes remains refused."""
    (retirement_repo / "reports/uncommitted.txt").write_text("new")
    _fixture_git(retirement_repo, "add", "reports/uncommitted.txt")
    (retirement_repo / "reports/uncommitted.txt").unlink()
    entry = _retirement_entry()
    entry["path"] = "reports/uncommitted.txt"
    _write_register(retirement_repo, [entry])
    _assert_checker(capsys, {"generated-artifact-deletion-or-relocation"})


def test_retirement_explicit_paths_read_no_status(
    retirement_repo: Path, monkeypatch, capsys
) -> None:
    """Explicit classification never reads working-tree status."""

    def forbidden_status(root):
        raise AssertionError("Explicit paths must not read status")

    monkeypatch.setattr(
        verify_repo_structure, "git_worktree_status_entries", forbidden_status
    )
    assert main(["--path", "src/example.py"]) == 0
    assert capsys.readouterr().out == "Repo structure contract: OK\n"


def test_retirement_preserves_invalid_exception_violation(
    retirement_repo: Path, capsys
) -> None:
    """Retirement metadata does not hide an invalid root exception."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    target = retirement_repo / "config/repo_structure.yml"
    payload = yaml.safe_load(target.read_text())
    payload["temporary_exceptions"]["reports"]["allowed_paths"] = None
    target.write_text(yaml.safe_dump(payload))
    _write_register(retirement_repo, [_retirement_entry()])
    _assert_checker(capsys, {"invalid-exception-metadata"})


def test_retirement_relative_versioned_dataset_is_accepted(
    retirement_repo: Path, capsys
) -> None:
    """A relative version directory is not a host reference."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _set_allowed_paths(retirement_repo, [])
    entry = _retirement_entry()
    entry["disposition"]["dataset_path"] = "generated.v1/example"
    _write_register(retirement_repo, [entry])
    _assert_checker(capsys, set(), 0)


@pytest.mark.parametrize("location", ["register", "entry", "disposition"])
def test_retirement_duplicate_yaml_keys_are_rejected(
    retirement_repo: Path, capsys, location: str
) -> None:
    """Duplicate mapping keys cannot hide invalid register content."""
    raw = yaml.safe_dump({"retirements": [_retirement_entry()]})
    if location == "register":
        raw = "retirements: [invalid]\nretirements: []\n"
    elif location == "entry":
        raw = raw.replace("  sha256:", "  sha256: invalid\n  sha256:")
    else:
        raw = raw.replace("    kind:", "    kind: invalid\n    kind:")
    (retirement_repo / "config/generated_retirements.yml").write_text(raw)
    _assert_checker(capsys, {"invalid-retirement-entry"})


def test_retirement_unquoted_invalid_calendar_date_is_rejected(
    retirement_repo: Path, capsys
) -> None:
    """Invalid YAML calendar scalars are reported as register violations."""
    (retirement_repo / "config/generated_retirements.yml").write_text(
        "retirements:\n- date: 2026-02-30\n"
    )
    _assert_checker(capsys, {"invalid-retirement-entry"})


@pytest.mark.parametrize(
    "dataset_path", ["example.invalid./dataset", "192.0.2.1./dataset"]
)
def test_retirement_terminal_dot_host_reference_is_rejected(
    retirement_repo: Path, capsys, dataset_path: str
) -> None:
    """A terminal DNS root dot does not turn a host reference into a dataset."""
    _fixture_git(retirement_repo, "rm", "reports/example.txt")
    _set_allowed_paths(retirement_repo, [])
    entry = _retirement_entry()
    entry["disposition"]["dataset_path"] = dataset_path
    _write_register(retirement_repo, [entry])
    _assert_checker(
        capsys,
        {
            "invalid-retirement-entry",
            "generated-path-not-classified",
            "generated-artifact-deletion-or-relocation",
        },
    )
