"""Subprocess contracts for the independently executable Landman module CLI."""

import json
import os
import site
import subprocess
import sys
from pathlib import Path


MODULE = "worldenergydata.cli.commands.landman"


def _command(*args):
    return [sys.executable, "-m", MODULE, *args]


def _write_network_guard(tmp_path):
    marker = tmp_path / "guard-loaded"
    attempts = tmp_path / "network-attempted"
    imports = tmp_path / "imports.json"
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "\n".join(
            [
                "import atexit, json, socket, sys",
                f"open({str(marker)!r}, 'w').write('loaded')",
                "def blocked(*args, **kwargs):",
                f"    open({str(attempts)!r}, 'w').write(repr(args))",
                "    raise RuntimeError('network disabled')",
                "socket.socket.connect = blocked",
                "socket.create_connection = blocked",
                f"atexit.register(lambda: open({str(imports)!r}, 'w').write(json.dumps(sorted(sys.modules))))",
            ]
        ),
        encoding="utf-8",
    )
    return marker, attempts, imports


def test_module_subprocess_loads_no_network_sitecustomize(tmp_path):
    marker, attempts, imports = _write_network_guard(tmp_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        _command(
            "search",
            "--state",
            "TX",
            "--county",
            "MIDLAND",
            "--type",
            "ownership",
            "--sample",
            "--format",
            "json",
        ),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["resolved_provider"] == "county_records"
    assert marker.read_text(encoding="utf-8") == "loaded"
    assert not attempts.exists()
    loaded = json.loads(imports.read_text(encoding="utf-8"))
    assert not any(name == "pandas" or name.startswith("pandas.") for name in loaded)
    assert not any(name == "numpy" or name.startswith("numpy.") for name in loaded)
    assert not any(name.startswith("worldenergydata.bsee") for name in loaded)
    assert "worldenergydata.cli.main" not in loaded


def test_module_cli_error_is_parseable_and_exits_one(tmp_path):
    result = subprocess.run(
        _command(
            "search",
            "--state",
            "TX",
            "--county",
            "MIDLAND",
            "--type",
            "title",
            "--sample",
            "--format",
            "json",
        ),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["status"] == "error"
    assert payload["failures"][0]["code"] == "LANDMAN_CAPABILITY_UNAVAILABLE"


def test_module_cli_help_registers_full_surface(tmp_path):
    result = subprocess.run(
        _command("--help"),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0
    for command in ("search", "lookup", "county-info", "providers", "status"):
        assert command in result.stdout


def _build_wheel(project: Path, output: Path) -> Path:
    output.mkdir()
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output), str(project)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    wheels = list(output.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def _install_wheels(tmp_path: Path, wheels: list[Path]) -> Path:
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
        check=True,
        timeout=180,
    )
    subprocess.run(
        [
            str(venv / "bin/python"),
            "-m",
            "pip",
            "install",
            "--no-deps",
            *map(str, wheels),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return venv


def _external_purelib(venv: Path) -> Path:
    result = subprocess.run(
        [
            str(venv / "bin/python"),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=True,
    )
    return Path(result.stdout.strip()).resolve()


def _assert_wheel_provenance(
    venv: Path, source_root: Path, cwd: Path, env: dict[str, str]
) -> None:
    probe_code = (
        "import importlib.resources as r, json, pathlib, sys, worldenergydata, "
        "worldenergydata.cli.commands.landman, worldenergydata.landman as lm, "
        "worldenergydata.landman.fixture_schema, worldenergydata.landman.routing; "
        "fixture = r.files('worldenergydata.landman.fixtures').joinpath('county_records_v1.json'); "
        "resolve = lambda value: str(pathlib.Path(value or '.').resolve()); "
        "module_files = [resolve(module.__file__) for name, module in sys.modules.items() "
        "if name.startswith('worldenergydata') and getattr(module, '__file__', None)]; "
        "print(json.dumps({'files': module_files + [resolve(str(fixture))], "
        "'sys_path': [resolve(value) for value in sys.path]}))"
    )
    probe = subprocess.run(
        [str(venv / "bin/python"), "-c", probe_code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=True,
    )
    installed_root = _external_purelib(venv)
    evidence = json.loads(probe.stdout)
    assert all(Path(path).is_relative_to(installed_root) for path in evidence["files"])
    checkout_paths = {
        str(path.resolve())
        for path in (
            source_root,
            source_root / "src",
            source_root / "packages/worldenergydata-core/src",
            source_root / "packages/worldenergydata-landman/src",
        )
    }
    assert checkout_paths.isdisjoint(evidence["sys_path"])


def _external_env(venv: Path, source_root: Path, cwd: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = site.getsitepackages()[0]
    _assert_wheel_provenance(venv, source_root, cwd, env)
    return env


def test_packaged_sample_survives_installed_wheels_outside_checkout(tmp_path):
    root = Path(__file__).parents[3]
    wheels = [
        _build_wheel(root, tmp_path / "root-wheel"),
        _build_wheel(root / "packages/worldenergydata-core", tmp_path / "core-wheel"),
        _build_wheel(
            root / "packages/worldenergydata-landman", tmp_path / "landman-wheel"
        ),
    ]
    venv = _install_wheels(tmp_path, wheels)
    empty = tmp_path / "empty"
    empty.mkdir()
    env = _external_env(venv, root, empty)
    python = venv / "bin/python"
    result = subprocess.run(
        [
            str(python),
            "-m",
            MODULE,
            "search",
            "--state",
            "TX",
            "--county",
            "MIDLAND",
            "--sample",
            "--format",
            "json",
        ],
        cwd=empty,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["resolved_provider"] == "county_records"


def test_touched_python_files_and_functions_meet_limits():
    import ast

    root = Path(__file__).parents[3]
    paths = [
        *root.glob("packages/worldenergydata-landman/src/worldenergydata/landman/*.py"),
        *root.glob(
            "packages/worldenergydata-landman/src/worldenergydata/landman/providers/*.py"
        ),
        *root.glob("src/worldenergydata/cli/commands/landman*.py"),
        root / "tests/unit/landman/test_routing.py",
        root / "tests/unit/landman/test_fixture_provider.py",
        root / "tests/unit/landman/test_issue_924_exceptions.py",
        root / "tests/unit/landman/test_landman.py",
        root / "tests/unit/cli/test_landman_cli.py",
        Path(__file__),
    ]
    touched_names = {
        "routing.py",
        "registry.py",
        "fixture_schema.py",
        "county_records.py",
        "landman.py",
        "exceptions.py",
        "__init__.py",
        "landman_search.py",
        "landman_reference.py",
        "landman_status.py",
        "landman_render.py",
        "test_routing.py",
        "test_fixture_provider.py",
        "test_issue_924_exceptions.py",
        "test_landman.py",
        "test_landman_cli.py",
        "test_landman_module_cli.py",
    }
    paths = {path for path in paths if path.name in touched_names and path.exists()}
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 400, path
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, f"{path}:{node.lineno}"
