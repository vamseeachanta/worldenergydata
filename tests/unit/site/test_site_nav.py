# ABOUTME: TDD suite for the nav-spine helper (issue #850) — manifest-driven
# ABOUTME: breadcrumbs, fail-closed injection, stdlib-only deploy parity.

import ast
import importlib.util
import posixpath
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HELPER = REPO / "scripts" / "site_nav.py"

spec = importlib.util.spec_from_file_location("site_nav", HELPER)
sn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sn)

MANIFEST = sn.load_manifest(REPO / "config" / "nav_spine.json")

SAMPLE_CTX = {
    "field_id": "big_foot",
    "field_name": "Big Foot",
    "slot": "A004",
    "stage": "drill",
    "stage_title": "Drill",
    "field_slug": "big_foot",
}


def all_keys():
    return [e["key"] for e in MANIFEST["pages"]]


# 1 — every manifest entry yields a complete trail ending in an unlinked leaf


@pytest.mark.parametrize("key", all_keys())
def test_trail_matches_manifest_for_every_scoped_entry(key):
    t = sn.trail(MANIFEST, key, SAMPLE_CTX)
    assert len(t) >= 2  # at least home + leaf
    assert t[0][0] == "worldenergydata" and t[0][1] == "index.html"
    label, path = t[-1]
    assert path is None and label  # leaf unlinked
    for lbl, p in t[:-1]:
        assert lbl and p


# 2 — depth prefixes valid for ALL manifest public paths (synthetic tree)


@pytest.mark.parametrize("key", all_keys())
def test_depth_prefixes_valid_for_all_manifest_public_paths(tmp_path, key):
    entry = sn.page_entry(MANIFEST, key)
    public = entry["public"].format(**SAMPLE_CTX)
    # materialize every node target in a synthetic public tree
    for _, node_path in sn.trail(MANIFEST, key, SAMPLE_CTX)[:-1]:
        f = tmp_path / node_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    crumb = sn.render_crumb(MANIFEST, key, SAMPLE_CTX)
    page_dir = tmp_path / posixpath.dirname(public)
    for target, _frag in sn.internal_targets(crumb):
        resolved = (page_dir / target).resolve()
        assert resolved.exists(), f"{key}: crumb href {target} unresolved"


# 3 — marker exactly once, last node unlinked in rendered HTML


def test_render_last_node_unlinked_marker_once():
    c = sn.render_crumb(MANIFEST, "poster", SAMPLE_CTX)
    assert c.count(sn.MARKER) == 1
    assert c.rstrip().endswith("</span></div>")
    assert "Big Foot</span>" in c
    assert 'href="../index.html"' in c  # home from lifecycle/
    assert 'href="index.html"' in c  # gallery is a sibling in lifecycle/
    assert 'href="../capabilities/index.html"' in c


# 4 — inject fail-closed + idempotent + both modes


def test_inject_fail_closed_and_idempotent():
    crumb = sn.render_crumb(MANIFEST, "gallery", SAMPLE_CTX)
    html = "<body>\n<h1>Gallery</h1>\n</body>"
    out = sn.inject(html, crumb, "<h1", mode="before")
    assert out.index(sn.MARKER) < out.index("<h1")
    assert sn.inject(out, crumb, "<h1", mode="before") == out  # idempotent
    with pytest.raises(sn.MissingAnchorError):
        sn.inject(html, crumb, "<nav-x>")
    with pytest.raises(sn.AmbiguousAnchorError):
        sn.inject("<h2></h2><h2></h2>", crumb, "<h2")
    with pytest.raises(sn.NavSpineError):
        sn.inject(html, crumb, "<h1", mode="sideways")


# 5 — registry sanity: unique keys, unique static leaf labels per family set


def test_registry_labels_unique_and_page_keys_total():
    keys = all_keys()
    assert len(keys) == len(set(keys))
    static_leaves = [e["leaf"] for e in MANIFEST["pages"] if "{" not in e["leaf"]]
    assert len(static_leaves) == len(set(static_leaves))
    # hub-collision regression: the two hubs carry distinct labels
    labels = {n["label"] for n in MANIFEST["nodes"].values()}
    assert "Life-cycle gallery" in labels and "Insights" in labels


# 6 — unknown page key fails closed


def test_page_wrapper_route_keys_explicit():
    with pytest.raises(sn.UnknownPageKeyError):
        sn.render_crumb(MANIFEST, "not-a-route", {})


# 7 — helper is stdlib-only (deploy parity guard)


def test_helper_is_stdlib_only():
    tree = ast.parse(HELPER.read_text())
    allowed = {"json", "posixpath", "re", "html", "pathlib", "__future__"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= allowed, f"non-stdlib imports: {imported - allowed}"


# 8 — missing context key fails closed (no silent blank crumbs)


def test_missing_context_fails_closed():
    with pytest.raises(sn.NavSpineError):
        sn.render_crumb(MANIFEST, "well", {"field_id": "big_foot"})


# 9 — internal_targets parser: externals skipped, fragments captured


def test_internal_targets_parser():
    html = (
        '<a href="a/b.html#frag">x</a><img src="img/p.png">'
        '<a href="https://x.y/z">ext</a><a href="mailto:a@b">m</a>'
    )
    got = sn.internal_targets(html)
    assert ("a/b.html", "frag") in got and ("img/p.png", None) in got
    assert len(got) == 2
