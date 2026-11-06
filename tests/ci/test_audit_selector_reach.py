"""Hand-enumerated routing examples; no application imports or network access."""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO / f"scripts/ci/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(root, path, text=""):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")
    return destination


@pytest.fixture
def audit():
    return load_script("audit_selector_reach")


def test_reachable_and_orphan_files(audit, tmp_path):
    """By hand: unit/alpha routes to itself; loose has no route or always-on home."""
    put(tmp_path, "tests/unit/alpha/test_ok.py")
    put(tmp_path, "tests/loose/test_orphan.py")
    put(tmp_path, "tests/loose/reverse_test.py")
    put(tmp_path, "tests/loose/helper.py")
    result = audit.audit(tmp_path)
    files = {row["path"]: row for row in result["tests"]}
    assert set(files) == {
        "tests/unit/alpha/test_ok.py",
        "tests/loose/test_orphan.py",
        "tests/loose/reverse_test.py",
    }
    assert files["tests/unit/alpha/test_ok.py"]["reachable"]
    assert not files["tests/loose/test_orphan.py"]["reachable"]
    assert not files["tests/loose/reverse_test.py"]["reachable"]


def test_sources_distinguish_always_on_from_domain_tests(audit, tmp_path):
    """By hand: alpha has a home, testing has only always-on, core requests full."""
    for path in (
        "tests/unit/alpha/test_ok.py",
        "tests/contracts/test_contract.py",
        "src/worldenergydata/alpha/api.py",
        "src/worldenergydata/testing/api.py",
        "src/worldenergydata/base_configs/settings.yml",
        "packages/worldenergydata-alpha/src/worldenergydata/alpha/api.py",
        "packages/empty/README.md",
    ):
        put(tmp_path, path)
    rows = {row["path"]: row for row in audit.audit(tmp_path)["sources"]}
    assert rows["src/worldenergydata/alpha"]["routed_targets"] == ["tests/unit/alpha"]
    assert rows["src/worldenergydata/testing"]["any_targets"]
    assert rows["src/worldenergydata/testing"]["routed_targets"] == []
    assert rows["src/worldenergydata/base_configs"]["scopes"] == ["full"]
    assert rows["packages/empty"]["status"] == "NOT_EVALUATED"
    assert rows["packages/worldenergydata-alpha"]["any_targets"]
    assert rows["packages/worldenergydata-alpha"]["unit_homes"] == ["tests/unit/alpha"]


def test_package_tests_and_full_are_not_mistaken_for_reachability(audit, tmp_path):
    """Core-member tests cause full; other package tests are ignored: neither qualifies."""
    put(tmp_path, "tests/unit/alpha/test_ok.py")
    put(tmp_path, "packages/worldenergydata-core/tests/test_core.py")
    put(tmp_path, "packages/worldenergydata-alpha/tests/test_alpha.py")
    rows = audit.audit(tmp_path)["tests"]
    assert not any(
        row["reachable"] for row in rows if row["path"].startswith("packages/")
    )
    assert audit.contains("tests/unit/alpha/test_ok.py", ["tests/unit/alpha"])
    assert not audit.contains("tests/unit/alphabet/test_ok.py", ["tests/unit/alpha"])


def test_allowlist_is_exact_and_requires_reasons(audit, tmp_path):
    """Listing one existing orphan cannot excuse its newly added sibling."""
    put(tmp_path, "tests/loose/test_old.py")
    allow = put(
        tmp_path, "allow.txt", "tests/loose/test_old.py # reason: legacy routing gap\n"
    )
    assert audit.unlisted(audit.audit(tmp_path), audit.read_allowlist(allow)) == []
    put(tmp_path, "tests/loose/test_new.py")
    assert audit.unlisted(audit.audit(tmp_path), audit.read_allowlist(allow)) == [
        "tests/loose/test_new.py"
    ]
    for invalid in (
        "tests/loose/ # reason: legacy\n",
        "tests/loose/test_old.py\n",
        "tests/loose/test_*.py # reason: legacy\n",
        "../tests/test_old.py # reason: legacy\n",
    ):
        allow.write_text(invalid, encoding="utf-8", newline="\n")
        with pytest.raises(ValueError):
            audit.read_allowlist(allow)


def test_real_tree_has_no_unlisted_orphans(audit, tmp_path):
    """The real inventory must be covered; a synthetic new sibling must fail the guard."""
    result = audit.audit(REPO)
    allow = audit.read_allowlist(REPO / "scripts/ci/selector_reach_allowlist.txt")
    assert audit.unlisted(result, allow) == []
    put(tmp_path, "tests/loose/test_new.py")
    assert audit.unlisted(audit.audit(tmp_path), allow) == ["tests/loose/test_new.py"]


def test_allowlist_reasons_match_pytest_exclusions(audit):
    """Every configured exclusion has an archive reason, rather than a routing claim."""
    import fnmatch
    import shlex

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"
    ]["pytest"]["ini_options"]
    arguments = shlex.split(config["addopts"])
    ignores = [
        item.removeprefix("--ignore=")
        for item in arguments
        if item.startswith("--ignore=")
    ]
    ignores += [
        arguments[i + 1] for i, item in enumerate(arguments[:-1]) if item == "--ignore"
    ]
    archives = 0
    for name, reason in audit.read_allowlist(
        REPO / "scripts/ci/selector_reach_allowlist.txt"
    ).items():
        excluded = any(
            fnmatch.fnmatch(part, pattern)
            for part in Path(name).parts[:-1]
            for pattern in config["norecursedirs"]
        )
        excluded |= any(name == item or name.startswith(item + "/") for item in ignores)
        historical = (
            reason == "reason: excluded by pytest at 254c0c1d; not ignored at 841cb7d4"
        )
        assert historical or (reason == "reason: archived") == excluded
        archives += excluded
    assert archives > 0


def test_cli_writes_json_and_table(audit, tmp_path, capsys):
    """The output contains the sole orphan and the same JSON record as the API."""
    import json

    put(tmp_path, "tests/loose/test_orphan.py")
    output = tmp_path / "result.json"
    assert audit.main(["--root", str(tmp_path), "--json", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == audit.audit(tmp_path)
    assert "tests/loose/test_orphan.py | orphan" in capsys.readouterr().out


def test_source_probes_exclude_build_outputs(audit, tmp_path):
    """Only the source/config inputs remain after unrelated local builds."""
    for name in (
        "src/worldenergydata/alpha/api.py",
        "src/worldenergydata/alpha/settings.yml",
        "src/worldenergydata/alpha/build/api.py",
    ):
        put(tmp_path, name)
    track_fixture(tmp_path)
    for name in (
        "src/worldenergydata/alpha/__pycache__/api.pyc",
        "src/worldenergydata/alpha/alpha.egg-info/PKG-INFO",
        "src/worldenergydata/alpha/build/generated.py",
        "src/worldenergydata/alpha/dist/generated.py",
    ):
        put(tmp_path, name)
    assert audit.audit(tmp_path)["sources"][0]["probes"] == [
        "src/worldenergydata/alpha/api.py",
        "src/worldenergydata/alpha/build/api.py",
        "src/worldenergydata/alpha/settings.yml",
    ]


def test_build_outputs_cannot_add_source_groups(audit, tmp_path):
    """A top-level build directory must not add inventory rows or source probes."""
    put(tmp_path, "src/worldenergydata/alpha/api.py")
    track_fixture(tmp_path)
    before = audit.audit(tmp_path)
    put(tmp_path, "src/worldenergydata/build/generated.py")
    put(tmp_path, "src/worldenergydata/alpha.egg-info/PKG-INFO")
    assert audit.audit(tmp_path) == before


def track_fixture(root):
    """Create an index-only fixture; no commit or identity setting is needed."""
    import os
    import subprocess

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"}
    }
    for arguments in (("init", "-q"), ("add", "-f", "--", ".")):
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )


def test_legitimate_build_directories_remain_in_test_inventory(audit, tmp_path):
    """Directory names cannot conceal a new orphan from the exact-file guard."""
    put(tmp_path, "tests/loose/build/test_new.py")
    put(tmp_path, "tests/unit/alpha/dist/test_new.py")
    result = audit.audit(tmp_path)
    assert [r["path"] for r in result["tests"]] == [
        "tests/loose/build/test_new.py",
        "tests/unit/alpha/dist/test_new.py",
    ]
    assert audit.unlisted(result, {}) == ["tests/loose/build/test_new.py"]


def test_namespace_cache_and_links_are_not_test_homes(audit, tmp_path):
    """Cached namespaces cannot add fabricated unit homes after an import."""
    put(tmp_path, "packages/alpha/src/worldenergydata/alpha/api.py")
    put(tmp_path, "tests/unit/alpha/test_api.py")
    before = audit.audit(tmp_path)
    put(tmp_path, "packages/alpha/src/worldenergydata/__pycache__/api.pyc")
    put(tmp_path, "tests/unit/__pycache__/test_fake.py")
    assert audit.audit(tmp_path)["sources"] == before["sources"]


def test_reparse_points_are_links_without_junction_api(audit, tmp_path, monkeypatch):
    """Windows reparse metadata remains decisive without Path.is_junction."""
    from types import SimpleNamespace

    put(tmp_path, "junction/api.py")
    monkeypatch.setattr(Path, "is_symlink", lambda p: False)
    monkeypatch.setattr(Path, "is_junction", lambda p: False, raising=False)
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: SimpleNamespace(st_reparse_tag=0xA0000003),
    )
    assert audit._linked(tmp_path / "junction")


def test_nonlink_reparse_files_remain_in_inventory(audit, tmp_path, monkeypatch):
    """A reparse attribute alone does not establish a symlink or junction."""
    import stat
    from types import SimpleNamespace

    put(tmp_path, "placeholder.py")
    monkeypatch.setattr(Path, "is_symlink", lambda p: False)
    monkeypatch.setattr(Path, "is_junction", lambda p: False, raising=False)
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: SimpleNamespace(
            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
            st_reparse_tag=0x9000001A,
        ),
    )
    assert not audit._linked(tmp_path / "placeholder.py")


def test_inventory_does_not_follow_linked_directories(audit, tmp_path, monkeypatch):
    """Symlinks and directory junctions cannot add external inventory inputs."""
    put(tmp_path, "src/worldenergydata/alpha/api.py")
    put(tmp_path, "src/worldenergydata/alpha/junction/extra.py")
    monkeypatch.setattr(
        Path, "is_junction", lambda p: p.name == "junction", raising=False
    )
    (tmp_path / "src/worldenergydata/alpha/linked").symlink_to(
        tmp_path / "src/worldenergydata/alpha/junction", target_is_directory=True
    )
    assert audit.audit(tmp_path)["sources"][0]["probes"] == [
        "src/worldenergydata/alpha/api.py"
    ]
