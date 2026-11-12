"""The EIA dependency declaration must agree with its locked dependency graph."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


def test_eia_requests_dependency_is_locked():
    root = Path(__file__).resolve().parents[2]
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    package = next(p for p in lock["package"] if p["name"] == "worldenergydata-eia-us")
    assert {"name": "requests"} in package["dependencies"]
    requirement = {"name": "requests", "specifier": ">=2.32.0,<3.0"}
    assert requirement in package["metadata"]["requires-dist"]
    declaration = tomllib.loads(
        (root / "packages/worldenergydata-eia_us/pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    assert "requests" + requirement["specifier"] in declaration["project"]["dependencies"]
    assert any(p["name"] == "requests" for p in lock["package"])
