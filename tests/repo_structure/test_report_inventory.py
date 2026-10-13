"""Report classification, reproducibility and publication agreement."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/classify_report_inventory.py"
BUILDER = ROOT / "scripts/build_pages.py"


def inventory_module():
    assert SCRIPT.is_file(), "The reproducible classification script is missing"
    spec = importlib.util.spec_from_file_location("inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(root, path, text="<!doctype html>"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "path,text,replacement,expected",
    [
        ("reports/completion/index.html", "", None, "current"),
        ("reports/completion/report_demo.html", "", None, "current"),
        ("reports/unpublished_demo.html", "", None, "one-off"),
        ("reports/unknown.html", "", None, "undetermined"),
        (
            "reports/old.html",
            '<link rel="successor-version" href="new.html">',
            "reports/new.html",
            "superseded",
        ),
        (
            "reports/old.html",
            '<link rel="successor-version" href="missing.html">',
            None,
            "undetermined",
        ),
        (
            "reports/completion/report_demo.html",
            '<link rel="successor-version" href="new.html">',
            "reports/completion/new.html",
            "superseded",
        ),
        (
            "reports/old.html",
            "Replaced by new.html",
            "reports/new.html",
            "undetermined",
        ),
        (
            "reports/old.html",
            '<link rel="successor-version" href="../../outside.html">',
            None,
            "undetermined",
        ),
    ],
)
def test_rule_order_and_evidence(tmp_path, path, text, replacement, expected):
    module = inventory_module()
    put(tmp_path, "reports/completion/index.html")
    put(tmp_path, path, text)
    if replacement:
        put(tmp_path, replacement)
    rows = {row["path"]: row for row in module.classify_tree(tmp_path, BUILDER)}
    assert rows[path]["classification"] == expected
    if expected == "superseded":
        assert replacement in rows[path]["evidence"]


def test_publication_gate(tmp_path):
    module = inventory_module()
    path = "reports/field-atlas/onepagers/field.html"
    put(tmp_path, path)
    assert (
        module.classify_tree(tmp_path, BUILDER)[0]["classification"] == "undetermined"
    )
    put(tmp_path, "reports/field-atlas/index.html")
    assert all(
        r["classification"] == "current"
        for r in module.classify_tree(tmp_path, BUILDER)
    )


def test_builder_agreement(tmp_path, monkeypatch):
    module = inventory_module()
    from scripts import build_pages as builder

    # Execute the real builder, recording copies; all writes land in tmp_path.
    # Its presentation functions read frozen inputs and perform no network I/O.
    monkeypatch.setattr(builder, "PUBLIC", tmp_path)
    monkeypatch.setattr(builder, "ASSETS", tmp_path / "assets")
    observed = set()
    for name in ("copyfile", "copy2", "copytree"):
        original = getattr(builder.shutil, name)

        def record(src, dst, *args, _original=original, **kwargs):
            source = Path(src)
            inputs = source.rglob("*.html") if source.is_dir() else [source]
            observed.update(
                p.relative_to(ROOT).as_posix()
                for p in inputs
                if p.is_file()
                and p.suffix == ".html"
                and p.is_relative_to(ROOT / "reports")
            )
            return _original(src, dst, *args, **kwargs)

        monkeypatch.setattr(builder.shutil, name, record)
    builder.build()
    assert observed, "No report publication was observed"
    rows = {row["path"]: row for row in module.classify_tree(ROOT, BUILDER)}
    assert {p for p in observed if rows[p]["classification"] != "current"} == set()


def test_committed_csv_matches(capsys):
    module = inventory_module()
    assert module.main(["--check"]) == 0
    assert (
        ROOT / "docs/modules/report-inventory.csv"
    ).read_bytes() == module.inventory_bytes(ROOT)


def test_deterministic_output(tmp_path):
    module = inventory_module()
    put(tmp_path, "reports/z_test.html")
    put(tmp_path, "reports/a.html")
    first = module.inventory_bytes(tmp_path, BUILDER)
    second = module.inventory_bytes(tmp_path, BUILDER)
    assert first == second
    assert b"\r" not in first


def test_check_rejects_stale_csv(tmp_path, monkeypatch):
    module = inventory_module()
    target = put(tmp_path, "docs/modules/report-inventory.csv", "stale")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "BUILDER", BUILDER)
    assert module.main(["--check"]) == 1
    assert target.read_text() == "stale"


def test_removed_domain_is_not_current(tmp_path):
    module = inventory_module()
    source = BUILDER.read_text(encoding="utf-8")
    assert '"hse": build_hse,' in source
    changed_builder = put(
        tmp_path,
        "scripts/build_pages.py",
        source.replace('    "hse": build_hse,\n', ""),
    )
    put(tmp_path, "reports/hse/card.html")
    rows = module.classify_tree(tmp_path, changed_builder)
    assert rows[0]["classification"] == "undetermined"
