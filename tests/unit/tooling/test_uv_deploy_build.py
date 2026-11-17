"""Check deployment build routing with recording tools in disposable layouts."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_ENTRIES = ("scripts/uv_deploy.sh", "scripts/tools/uv_deploy.sh")
_TOOLS = """#!{python}
import json
import os
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['RECORD'], 'a', encoding='utf-8', newline='\\n') as stream:
    stream.write(json.dumps([name, os.getcwd(), args]) + '\\n')
if name == 'uv' and args in (['sync', '--extra', 'build'],
                             ['build', '--all-packages']):
    sys.exit(int(os.environ['FAIL_CODE'])
             if args[0] == os.environ['FAIL_ACTION'] else 0)
if name == 'ls' and args == ['-la', 'dist/']:
    sys.exit(0)
sys.exit(91)
"""


def _snapshot(root):
    return {
        p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
        for p in root.rglob("*")
        if p.is_file()
    }, {p.relative_to(root) for p in root.rglob("*") if p.is_dir()}


def _fixture(tmp_path):
    root = tmp_path / "workspace with spaces"
    for entry in _ENTRIES:
        target = root / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_ROOT / entry, target)
    for name in ("pyproject.toml", "dist/keep.whl", "build/keep", "keep.egg-info/keep"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture sentinel\n", encoding="utf-8", newline="\n")
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("bash", "dirname"):
        executable = shutil.which(name)
        assert executable is not None, f"Required shell tool missing: {name}"
        (tools / name).symlink_to(executable)
    for name in ("uv", "ls", "rm", "pip", "python", "curl", "git"):
        tool = tools / name
        tool.write_text(
            _TOOLS.format(python=sys.executable), encoding="utf-8", newline="\n"
        )
        tool.chmod(0o755)
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("GIT_") or key in (
            "PYPI_TOKEN",
            "TESTPYPI_TOKEN",
            "BASH_ENV",
        ):
            env.pop(key)
    env.update(
        PATH=str(tools),
        RECORD=str(tmp_path / "record.jsonl"),
        FAIL_ACTION="",
        FAIL_CODE="37",
        UV_OFFLINE="1",
        UV_PYTHON_DOWNLOADS="never",
        # Deliberately inherited bindings shall not redirect either helper.
        GIT_DIR=str(tmp_path / "other.git"),
        GIT_WORK_TREE=str(tmp_path / "other-tree"),
        GIT_COMMON_DIR=str(tmp_path / "other-common"),
    )
    return root, env


@pytest.mark.parametrize("entry", _ENTRIES)
@pytest.mark.parametrize("failure", ("", "sync", "build"))
def test_build_dispatch(tmp_path, entry, failure):
    root, env = _fixture(tmp_path)
    env["FAIL_ACTION"] = failure
    before = _snapshot(root)
    result = subprocess.run(
        ["bash", str(root / entry), "build"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    records = [
        json.loads(line)
        for line in Path(env["RECORD"]).read_text(encoding="utf-8").splitlines()
    ]
    expected = [["uv", str(root), ["sync", "--extra", "build"]]]
    if failure != "sync":
        expected.append(["uv", str(root), ["build", "--all-packages"]])
    if not failure:
        expected.append(["ls", str(root), ["-la", "dist/"]])
    assert records == expected
    assert result.returncode == (37 if failure else 0), result.stderr
    assert ("✅ Build complete!" in result.stdout) == (not failure)
    assert _snapshot(root) == before


def test_compatibility_wrapper_forwards_arguments_and_status(tmp_path):
    root, env = _fixture(tmp_path)
    canonical = root / _ENTRIES[0]
    canonical.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$@" > "$RECORD"\nexit 37\n',
        encoding="utf-8",
        newline="\n",
    )
    before = _snapshot(root)
    arguments = ["a b", "", "*", "--help"]
    result = subprocess.run(
        ["bash", str(root / _ENTRIES[1]), *arguments],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 37, result.stderr
    assert Path(env["RECORD"]).read_text(encoding="utf-8").splitlines() == arguments
    assert _snapshot(root) == before


@pytest.mark.parametrize("entry", _ENTRIES)
def test_help_describes_workspace_build_without_running_tools(tmp_path, entry):
    root, env = _fixture(tmp_path)
    before = _snapshot(root)

    result = subprocess.run(
        ["bash", str(root / entry), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "Build the root and all workspace member distributions" in result.stdout
    assert not Path(env["RECORD"]).exists()
    assert _snapshot(root) == before
