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
    destination.write_text(text, encoding="utf-8")
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
        allow.write_text(invalid, encoding="utf-8")
        with pytest.raises(ValueError):
            audit.read_allowlist(allow)


def test_real_tree_has_no_unlisted_orphans(audit, tmp_path):
    """The real inventory must be covered; a synthetic new sibling must fail the guard."""
    result = audit.audit(REPO)
    allow = audit.read_allowlist(REPO / "scripts/ci/selector_reach_allowlist.txt")
    assert audit.unlisted(result, allow) == []
    put(tmp_path, "tests/loose/test_new.py")
    assert audit.unlisted(audit.audit(tmp_path), allow) == ["tests/loose/test_new.py"]


def test_cli_writes_json_and_table(audit, tmp_path, capsys):
    """The output contains the sole orphan and the same JSON record as the API."""
    import json

    put(tmp_path, "tests/loose/test_orphan.py")
    output = tmp_path / "result.json"
    assert audit.main(["--root", str(tmp_path), "--json", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == audit.audit(tmp_path)
    assert "tests/loose/test_orphan.py | orphan" in capsys.readouterr().out
