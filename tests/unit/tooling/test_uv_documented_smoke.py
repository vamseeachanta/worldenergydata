"""Exercise the uv-workspace-layout-smoke example in docs/development/uv_usage.md.

The required paths and expected output below come from that named example.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_REQUIRED_FILES = (
    "pyproject.toml",
    "packages/worldenergydata-core/pyproject.toml",
)


def _documented_smoke():
    root = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "docs/development/uv_usage.md").is_file()
    )
    guide = (root / "docs/development/uv_usage.md").read_text(encoding="utf-8")
    examples = re.findall(
        r"^```bash\n(# Example: uv-workspace-layout-smoke\n.*?)\n```$",
        guide,
        flags=re.MULTILINE | re.DOTALL,
    )
    (example,) = examples
    return example


def _layout(root, *, include_member=True):
    root.mkdir()
    for name in _REQUIRED_FILES:
        if not include_member and name != "pyproject.toml":
            continue
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Layout-only fixture.\n", encoding="utf-8")


def _snapshot(root):
    return {
        path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }, {path.relative_to(root) for path in root.rglob("*") if path.is_dir()}


def _run_smoke(root, runtime):
    uv = shutil.which("uv")
    assert uv is not None, "The documented example requires an installed uv executable"
    runtime.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "PATH": str(Path(uv).parent) + os.pathsep + env.get("PATH", ""),
            "UV_OFFLINE": "1",
            "UV_PYTHON": sys.executable,
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_CACHE_DIR": env.get("UV_CACHE_DIR", str(runtime / "uv-cache")),
            "UV_PYTHON_INSTALL_DIR": str(runtime / "python"),
            "UV_PROJECT_ENVIRONMENT": str(runtime / "venv"),
            "UV_TOOL_DIR": str(runtime / "tools"),
            "XDG_CACHE_HOME": str(runtime / "cache"),
            "TMPDIR": str(runtime),
            "TMP": str(runtime),
            "TEMP": str(runtime),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return subprocess.run(
        ["bash", "-c", _documented_smoke()],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_documented_uv_layout_smoke(tmp_path):
    root = tmp_path / "workspace"
    _layout(root)
    before = _snapshot(root)

    result = _run_smoke(root, tmp_path / "runtime")

    # The named example declares successful execution and this exact marker.
    assert result.returncode == 0, result.stderr
    assert result.stdout == "workspace-layout-ok\n"
    assert _snapshot(root) == before


def test_documented_uv_layout_smoke_rejects_missing_member(tmp_path):
    root = tmp_path / "workspace"
    _layout(root, include_member=False)
    before = _snapshot(root)

    result = _run_smoke(root, tmp_path / "runtime")

    assert result.returncode != 0
    assert "Missing workspace files: packages/worldenergydata-core/pyproject.toml" in (
        result.stderr
    )
    assert "workspace-layout-ok" not in result.stdout
    assert _snapshot(root) == before
