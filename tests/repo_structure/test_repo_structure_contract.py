"""TDD coverage for the repo-structure normalization checker (#394)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
        "git_worktree_paths",
        lambda repo_root: ["scratch/file.txt"],
    )

    result = main(["--config", str(contract)])

    captured = capsys.readouterr()
    assert result == 1
    assert "unknown-root" in captured.out
    assert "scratch/file.txt" in captured.out
