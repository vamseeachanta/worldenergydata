"""Report classification, reproducibility and publication agreement."""

import importlib.util
import os
import subprocess
from pathlib import Path, PureWindowsPath

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
    assert {
        p
        for p in observed
        if rows[p]["classification"] not in {"current", "unverified"}
    } == set()


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


class WindowsOrderedPath(type(Path())):
    """Use Windows path ordering while reading the native temporary tree."""

    def __lt__(self, other):
        return PureWindowsPath(self.as_posix()) < PureWindowsPath(other.as_posix())


class WindowsHtmlPath(type(Path())):
    """Emulate case-insensitive HTML glob matches over the native test tree."""

    def glob(self, pattern):
        candidates = super().glob(pattern[:-5] + ".*")
        return (path for path in candidates if path.suffix.lower() == ".html")

    def rglob(self, pattern):
        candidates = super().rglob(pattern[:-5] + ".*")
        return (path for path in candidates if path.suffix.lower() == ".html")


@pytest.mark.parametrize("path_type", [Path, WindowsHtmlPath])
def test_inventory_requires_lowercase_html_suffix(tmp_path, path_type):
    module = inventory_module()
    paths = [
        "reports/completion/index.html",
        "reports/completion/uppercase.HTML",
        "reports/completion/mixed.Html",
        "reports/ordinary.html",
        "reports/unselected.HTML",
    ]
    originals = {path: put(tmp_path, path).read_bytes() for path in paths}
    rows = module.classify_tree(path_type(tmp_path), BUILDER)
    assert {row["path"]: row["classification"] for row in rows} == {
        "reports/completion/index.html": "current",
        "reports/ordinary.html": "undetermined",
    }
    assert {path: (tmp_path / path).read_bytes() for path in paths} == originals


@pytest.mark.parametrize("path_type", [Path, WindowsOrderedPath])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_portable_inventory_bytes(tmp_path, path_type, newline):
    """Issue #1355: derive exact bytes independently from literal fixture rows.

    Repository-relative string order is Zebra.html, alpha.html, alpha/card.html, zulu.html:
    uppercase Z precedes lowercase a, and '.' precedes '/'. Every fixture is
    unselected, with no replacement or demo/test token: see the final rule in
    docs/modules/repository-architecture.md, 'Report classification rules'.
    LF and CRLF report inputs are equivalent; names differ beyond case so the
    fixture also works on case-insensitive filesystems.
    """
    module = inventory_module()
    paths = [
        "reports/zulu.html",
        "reports/alpha/card.html",
        "reports/alpha.html",
        "reports/Zebra.html",
    ]
    originals = {}
    for path in paths:
        target = put(tmp_path, path)
        target.write_bytes(("<!doctype html>" + newline).encode("utf-8"))
        originals[path] = target.read_bytes()
    root = path_type(tmp_path)
    expected = (
        b"path,classification,evidence\n"
        b"reports/Zebra.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/alpha.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/alpha/card.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/zulu.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
    )
    assert module.inventory_bytes(root, BUILDER) == expected
    assert {path: (tmp_path / path).read_bytes() for path in paths} == originals


@pytest.mark.parametrize("autocrlf", ["false", "true"])
@pytest.mark.parametrize("inherited_git", [False, True])
def test_inventory_checkout_is_lf(autocrlf, inherited_git, tmp_path, monkeypatch):
    """Issue #1355: checkout conversion must retain the exact committed LF blob.

    cat-file --filters applies checkout conversion without changing the tree
    or index. Its expected bytes are the committed blob, independently read
    without filters. Both autocrlf settings must produce that same LF payload.
    """
    if inherited_git:
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            monkeypatch.setenv(key, str(tmp_path / key))
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"}
    }
    path = "docs/modules/report-inventory.csv"
    blob = subprocess.check_output(
        ["git", "show", f"HEAD:{path}"], cwd=ROOT, env=environment
    )
    checkout = subprocess.check_output(
        [
            "git",
            "-c",
            f"core.autocrlf={autocrlf}",
            "cat-file",
            "--filters",
            f"HEAD:{path}",
        ],
        cwd=ROOT,
        env=environment,
    )
    assert b"\r" not in checkout
    assert checkout == blob


@pytest.mark.parametrize("change", ["crlf", "content", "order"])
def test_check_preserves_byte_equality(tmp_path, monkeypatch, change):
    """Issue #1355 requires byte equality, including row order and line endings.

    Each mutation independently changes the canonical bytes: CRLF adds CR;
    content substitutes a classification; order reverses the two data rows.
    --check must reject each without writing; --write must restore LF bytes.
    """
    module = inventory_module()
    put(tmp_path, "reports/a.html")
    put(tmp_path, "reports/z.html")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "BUILDER", BUILDER)
    canonical = (
        b"path,classification,evidence\n"
        b"reports/a.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/z.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
    )
    if change == "crlf":
        changed = canonical.replace(b"\n", b"\r\n")
    elif change == "content":
        changed = canonical.replace(b"undetermined", b"current")
    else:
        header, first, second = canonical.splitlines(keepends=True)
        changed = header + second + first
    target = put(tmp_path, module.INVENTORY)
    target.write_bytes(changed)
    assert module.main(["--check"]) == 1
    assert target.read_bytes() == changed
    assert module.main(["--write"]) == 0
    assert target.read_bytes() == canonical
    assert module.main(["--check"]) == 0
