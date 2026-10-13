"""Prove test-session tree preservation in disposable Git repositories."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_metadata_inventory_checks_every_input_module(tmp_path, monkeypatch):
    """An omitted input module must fail the existing inventory assertion."""
    from tests import test_metadata

    input_root = tmp_path / "inputs"
    output_root = tmp_path / "outputs"
    for name in ("present", "omitted"):
        (input_root / "data" / "modules" / name).mkdir(parents=True)
    generator = tmp_path / "omitting_generator.py"
    generator.write_text(
        "import argparse\nfrom pathlib import Path\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--output-root', type=Path)\n"
        "root = parser.parse_args().output_root / 'data/modules/present'\n"
        "root.mkdir(parents=True)\n"
        "(root / '_metadata.json').write_text('{}', encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(test_metadata, "REPO_ROOT", input_root)
    monkeypatch.setattr(test_metadata, "MODULES_DIR", output_root / "data" / "modules")
    monkeypatch.setattr(test_metadata, "GENERATE_SCRIPT", generator)
    with pytest.raises(AssertionError, match="Missing _metadata.json in omitted"):
        test_metadata.TestGenerateMetadata().test_metadata_json_created_for_each_module(
            output_root
        )


def _git(root, *args, input_text=None):
    """Run Git against the fixture without inherited repository bindings."""
    env = _child_environment()
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    return result.stdout.strip()


def _child_environment():
    """Keep child Git and pytest state independent of the caller."""
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "PYTEST_ADDOPTS",
    ):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]
    )
    return env


def _fixture_repository(tmp_path, body, fixtures=""):
    """Build a minimal fixture HEAD without changing Git identity/configuration."""
    root = tmp_path / "case"
    root.mkdir()
    shutil.copyfile(REPO_ROOT / "tests/conftest.py", root / "conftest.py")
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "seed.txt").write_text("original", encoding="utf-8")
    (root / "test_sample.py").write_text(
        f"from pathlib import Path\ndef test_sample({fixtures}):\n    " + body + "\n",
        encoding="utf-8",
    )
    _git(root, "init", "-q")
    _git(root, "add", "--", "conftest.py", "pytest.ini", "seed.txt", "test_sample.py")
    tree = _git(root, "write-tree")
    # Synthetic fixture objects need no configured developer or runner identity.
    commit = _git(
        root,
        "hash-object",
        "-t",
        "commit",
        "-w",
        "--stdin",
        input_text=(
            f"tree {tree}\n"
            "author Fixture <fixture> 0 +0000\n"
            "committer Fixture <fixture> 0 +0000\n\n"
            "test: initialize disposable tree\n\n"
            "Co-Authored-By: Codex <noreply@openai.com>\n"
        ),
    )
    _git(root, "update-ref", "HEAD", commit)
    return root


def _session(root, tmp_path, *options, bindings=None):
    """Run the copied repository hooks inside the fixture repository."""
    env = _child_environment()
    env.update(bindings or {})
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=" + str(tmp_path / "run-temp"),
            *options,
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=3600,
        check=False,
    )


def test_guard_rejects_new_file(tmp_path):
    """A successful test which creates a file must fail its session."""
    root = _fixture_repository(tmp_path, "Path('created.txt').write_text('new')")
    result = _session(root, tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "new: created.txt" in output


def test_guard_rejects_changed_tracked_file(tmp_path):
    """A successful test which changes tracked bytes must fail its session."""
    root = _fixture_repository(tmp_path, "Path('seed.txt').write_text('changed')")
    result = _session(root, tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "changed: seed.txt" in output


def test_guard_accepts_clean_session(tmp_path):
    """A read-only test session must pass."""
    root = _fixture_repository(
        tmp_path, "assert Path('seed.txt').read_text() == 'original'"
    )
    result = _session(root, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_guard_preserves_existing_work_and_rejects_new_write(tmp_path):
    """The switch excludes pre-existing work while retaining new-write failures."""
    root = _fixture_repository(tmp_path, "Path('created.txt').write_text('new')")
    (root / "seed.txt").write_text("developer work", encoding="utf-8")
    result = _session(root, tmp_path, "--allow-existing-tree-changes")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "new: created.txt" in output
    assert "changed: seed.txt" not in output


def test_guard_switch_accepts_only_existing_work(tmp_path):
    """The switch permits a read-only session in an already modified tree."""
    root = _fixture_repository(
        tmp_path, "assert Path('seed.txt').read_text() == 'developer work'"
    )
    (root / "seed.txt").write_text("developer work", encoding="utf-8")
    result = _session(root, tmp_path, "--allow-existing-tree-changes")
    assert result.returncode == 0, result.stdout + result.stderr


def test_guard_rejects_deleted_tracked_file(tmp_path):
    """A deleted tracked path must be named by the failing session."""
    root = _fixture_repository(tmp_path, "Path('seed.txt').unlink()")
    result = _session(root, tmp_path)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "deleted: seed.txt" in result.stdout + result.stderr


def test_guard_rejects_staged_change(tmp_path):
    """Staging modified bytes must not hide a difference from HEAD."""
    root = _fixture_repository(
        tmp_path,
        "Path('seed.txt').write_text('changed'); "
        "__import__('subprocess').run(['git', 'add', '--', 'seed.txt'], check=True)",
    )
    result = _session(root, tmp_path)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "changed: seed.txt" in result.stdout + result.stderr


def test_guard_switch_preserves_existing_untracked_file(tmp_path):
    """Existing untracked work is excluded, while new output still fails."""
    root = _fixture_repository(tmp_path, "Path('created.txt').write_text('new')")
    (root / "developer.txt").write_text("existing", encoding="utf-8")
    result = _session(root, tmp_path, "--allow-existing-tree-changes")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "new: created.txt" in output
    assert "new: developer.txt" not in output


def test_guard_checks_parallel_session_once(tmp_path):
    """Two workers produce one controlling-process preservation report."""
    root = _fixture_repository(tmp_path, "Path('created.txt').write_text('new')")
    result = _session(root, tmp_path, "-n", "2", "--dist=each")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert output.count("new: created.txt") == 1


def test_guard_bounds_path_list(tmp_path):
    """The report lists at most 50 paths and counts its omitted paths."""
    root = _fixture_repository(
        tmp_path,
        "[Path(f'created-{number:03}.txt').write_text('new') for number in range(51)]",
    )
    result = _session(root, tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert (
        len([line for line in output.splitlines() if line.startswith("  new: ")]) == 50
    )
    assert "1 additional path(s) not shown" in output


def test_guard_rejects_unlisted_report(tmp_path):
    """A report outside the exact declared exceptions still fails."""
    root = _fixture_repository(
        tmp_path, "Path('test-results-unknown.xml').write_text('new')"
    )
    result = _session(root, tmp_path)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "new: test-results-unknown.xml" in result.stdout + result.stderr


def test_guard_clears_inherited_git_bindings(tmp_path):
    """A child guard checks its fixture and preserves caller files and metadata."""
    caller_head = _git(REPO_ROOT, "rev-parse", "HEAD")
    caller_index = Path(_git(REPO_ROOT, "rev-parse", "--git-path", "index"))
    if not caller_index.is_absolute():
        caller_index = REPO_ROOT / caller_index
    before_index = hashlib.sha256(caller_index.read_bytes()).hexdigest()
    source = REPO_ROOT / "tests/conftest.py"
    before_source = hashlib.sha256(source.read_bytes()).hexdigest()
    root = _fixture_repository(tmp_path, "Path('created.txt').write_text('new')")
    bindings = {
        "GIT_DIR": _git(REPO_ROOT, "rev-parse", "--absolute-git-dir"),
        "GIT_WORK_TREE": str(REPO_ROOT),
        "GIT_COMMON_DIR": _git(REPO_ROOT, "rev-parse", "--git-common-dir"),
        "GIT_INDEX_FILE": str(caller_index),
    }
    result = _session(root, tmp_path, bindings=bindings)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "new: created.txt" in result.stdout + result.stderr
    assert _git(REPO_ROOT, "rev-parse", "HEAD") == caller_head
    assert hashlib.sha256(caller_index.read_bytes()).hexdigest() == before_index
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before_source


def test_guard_accepts_declared_junit_file(tmp_path):
    """Only the JUnit file declared for this session is exempted."""
    root = _fixture_repository(tmp_path, "assert True")
    result = _session(root, tmp_path, "--junitxml=declared.xml")
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert (root / "declared.xml").is_file()
    assert "new: declared.xml" not in output


@pytest.mark.parametrize(
    "kind,destination",
    [
        ("json", "declared.json"),
        ("html", "declared-html"),
        ("annotate", "declared-annotate"),
        (None, None),
    ],
)
def test_guard_accepts_declared_coverage_output(tmp_path, kind, destination):
    """Coverage file and directory destinations, plus data, are session outputs."""
    pytest.importorskip("pytest_cov", reason="Coverage integration requires pytest-cov")
    root = _fixture_repository(tmp_path, "assert True")
    options = ["--cov=test_sample"]
    if kind is not None:
        options.append(f"--cov-report={kind}:{destination}")
    result = _session(root, tmp_path, *options)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    if destination is not None:
        assert (root / destination).exists()
    assert (root / ".coverage").is_file()
    assert "Repository tree preservation failed" not in output


def test_guard_accepts_declared_benchmark_file(tmp_path):
    """The benchmark option's opened output file is exempted."""
    pytest.importorskip(
        "pytest_benchmark", reason="Benchmark integration requires pytest-benchmark"
    )
    root = _fixture_repository(
        tmp_path, "assert benchmark(lambda: 1) == 1", fixtures="benchmark"
    )
    result = _session(root, tmp_path, "--benchmark-json=declared.json")
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert '"benchmarks":' in (root / "declared.json").read_text(encoding="utf-8")
    assert "new: declared.json" not in output


def test_guard_declared_output_does_not_hide_other_files(tmp_path):
    """A declared report does not exempt a neighbouring unrequested file."""
    root = _fixture_repository(tmp_path, "Path('created.txt').write_text('new')")
    result = _session(root, tmp_path, "--junitxml=declared.xml")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "new: created.txt" in output
    assert "new: declared.xml" not in output


def test_guard_rejects_formerly_listed_report(tmp_path):
    """A formerly excepted shard name fails unless this session declares it."""
    root = _fixture_repository(
        tmp_path, "Path('test-results-unit-ci.xml').write_text('new')"
    )
    result = _session(root, tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "new: test-results-unit-ci.xml" in output
