# ABOUTME: Check the monthly cron wrapper without launching any downloads.
# ABOUTME: Require an explicit external destination before invoking the runner.

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is unavailable")
def test_output_root_is_required(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment.pop("WED_HSE_SOURCES_ROOT", None)
    environment.pop("REPO_ROOT", None)
    script = str(ROOT / "scripts/cron/hse-monthly-refresh.sh")
    result = subprocess.run(
        [script] if os.name != "nt" else ["bash", script],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "WED_HSE_SOURCES_ROOT" in result.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is unavailable")
@pytest.mark.parametrize("override", [False, True])
def test_runner_resolves_root_outside_checkout(tmp_path: Path, override: bool) -> None:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    fake_uv = binary_dir / "uv"
    fake_uv.write_text(
        '#!/usr/bin/env bash\npwd > "$CWD_FILE"\n'
        'printf "%s\\n" "$@" > "$ARGS_FILE"\nexit 0\n'
    )
    fake_uv.chmod(0o755)
    root = tmp_path / "external sources"
    args_file, cwd_file = tmp_path / "args.txt", tmp_path / "cwd.txt"
    environment = dict(
        os.environ,
        WED_HSE_SOURCES_ROOT=str(root),
        PATH=str(binary_dir) + os.pathsep + os.environ.get("PATH", ""),
        ARGS_FILE=str(args_file),
        CWD_FILE=str(cwd_file),
    )
    environment.pop("REPO_ROOT", None)
    checkout = tmp_path / "override" if override else ROOT
    if override:
        checkout.mkdir()
        environment["REPO_ROOT"] = str(checkout)
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/cron/hse-monthly-refresh.sh")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert Path(cwd_file.read_text().strip()).resolve() == checkout.resolve()
    assert args_file.read_text().splitlines() == [
        "run",
        "python",
        "scripts/hse/refresh_hse_sources.py",
        "--config",
        "config/hse/monthly_sources.yml",
        "--output-root",
        str(root),
        "--json",
    ]
    lines = (root / "refresh.log").read_text().splitlines()
    assert len(lines) == 1
    assert lines[0].endswith("hse-monthly-refresh exit=0")


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is unavailable")
def test_runner_code_is_logged_and_preserved(tmp_path: Path) -> None:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    fake_uv = binary_dir / "uv"
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$ARGS_FILE"\nexit 1\n'
    )
    fake_uv.chmod(0o755)
    root = tmp_path / "external sources"
    args_file = tmp_path / "args.txt"
    environment = dict(
        os.environ,
        REPO_ROOT=str(ROOT),
        WED_HSE_SOURCES_ROOT=str(root),
        PATH=str(binary_dir) + os.pathsep + os.environ.get("PATH", ""),
        ARGS_FILE=str(args_file),
    )
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/cron/hse-monthly-refresh.sh")],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert (root / "refresh.log").read_text().endswith("hse-monthly-refresh exit=1\n")
    assert args_file.read_text().splitlines() == [
        "run",
        "python",
        "scripts/hse/refresh_hse_sources.py",
        "--config",
        "config/hse/monthly_sources.yml",
        "--output-root",
        str(root),
        "--json",
    ]
