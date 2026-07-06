# ABOUTME: Link-graph gate (issue #850) — builds the public site in-process to a
# ABOUTME: tmp dir, then asserts existence, resolution, exact trails, reachability.

import importlib.util
import json
import posixpath
import re
from collections import deque
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

_sn_spec = importlib.util.spec_from_file_location(
    "site_nav_ig", REPO / "scripts" / "site_nav.py"
)
sn = importlib.util.module_from_spec(_sn_spec)
_sn_spec.loader.exec_module(sn)

MANIFEST = sn.load_manifest(REPO / "config" / "nav_spine.json")
FACTS = json.loads((REPO / "reports/lower_tertiary/lifecycle/_facts.json").read_text())
WELLS = json.loads(
    (REPO / "reports/lower_tertiary/lifecycle/wells/_wells.json").read_text()
)
NAMES = {f["id"]: f["name"] for f in FACTS}
STAGES = ("drill", "complete", "produce", "workover", "abandon")


@pytest.fixture(scope="module")
def public(tmp_path_factory):
    """Build the whole site in-process with PUBLIC redirected (seam precedent:
    tests/test_build_pages.py)."""
    spec = importlib.util.spec_from_file_location(
        "build_pages_linkgraph", REPO / "scripts" / "build_pages.py"
    )
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    out = tmp_path_factory.mktemp("public_linkgraph") / "public"
    bp.PUBLIC = out
    bp.ASSETS = out / "assets"
    bp.build()
    return out


def scoped_pages():
    """Expand manifest patterns to concrete (public_relpath, key, ctx)."""
    pages = []
    for f in FACTS:
        pages.append(
            (
                f"lifecycle/{f['id']}_lifecycle.html",
                "poster",
                {"field_id": f["id"], "field_name": f["name"]},
            )
        )
    for w in WELLS["wells"]:
        pages.append(
            (
                f"lifecycle/wells/{w['field_id']}_{w['slot']}_well.html",
                "well",
                {
                    "field_id": w["field_id"],
                    "slot": w["slot"],
                    "field_name": WELLS["fields"][w["field_id"]]["display_name"],
                },
            )
        )
    for s in STAGES:
        pages.append(
            (
                f"lifecycle/norms/{s}.html",
                "norms",
                {"stage": s, "stage_title": s.title()},
            )
        )
    static = {
        "capabilities": "capabilities/index.html",
        "insights": "capabilities/insights.html",
        "atlas": "field-atlas/index.html",
        "gallery": "lifecycle/index.html",
        "wells_index": "lifecycle/wells/index.html",
        "assets_stones": "lifecycle/assets/stones_assets.html",
        "drilling_insights": "drilling-insights.html",
        "devtype": "region-devtype-comparison.html",
        "all_regions": "all-regions-atlas.html",
        "pa_wave": "decommissioning/pa-liability-wave.html",
        "regional_liability": "decommissioning/regional-liability.html",
        "intervention_brief": "intervention-db/intervention-stats-brief.html",
    }
    for key, path in static.items():
        pages.append((path, key, {}))
    return pages


def test_manifest_scoped_pages_exist(public):
    missing = [p for p, _k, _c in scoped_pages() if not (public / p).exists()]
    assert not missing, f"scoped pages absent from fresh build: {missing}"


def test_marker_once_and_exact_trail_per_page(public):
    bad = []
    for rel, key, ctx in scoped_pages():
        text = (public / rel).read_text()
        if text.count(sn.MARKER) != 1:
            bad.append((rel, f"marker x{text.count(sn.MARKER)}"))
            continue
        crumb = sn.render_crumb(MANIFEST, key, ctx)
        if crumb not in text:
            bad.append((rel, "crumb != manifest trail"))
    assert not bad, bad


def _resolve(public, page_rel, target):
    base = posixpath.dirname(page_rel)
    return public / posixpath.normpath(posixpath.join(base, target))


def test_zero_unresolved_internal_targets_and_fragments(public):
    bad = []
    for rel, _k, _c in scoped_pages():
        text = (public / rel).read_text()
        for target, frag in sn.internal_targets(text):
            f = _resolve(public, rel, target)
            if not f.exists():
                bad.append((rel, target))
            elif frag and f.suffix == ".html":
                if f'id="{frag}"' not in f.read_text():
                    bad.append((rel, f"{target}#{frag} (missing id)"))
    assert not bad, f"unresolved internal targets: {bad}"


FIELD_JSON_RE = re.compile(r"const FIELD = (\{.*?\n\});", re.S)


def _data_driven_edges(text):
    """Hrefs embedded in the poster's FIELD JSON payload (rendered by JS)."""
    m = FIELD_JSON_RE.search(text)
    if not m:
        return []
    try:
        field = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    edges = [field.get("wellsHref"), field.get("assetsHref")]
    edges += [c.get("href") for c in field.get("norms", [])]
    return [e.split("#")[0] for e in edges if e]


def test_bfs_reachability_from_capabilities(public):
    scoped = {p for p, _k, _c in scoped_pages()}
    start = "capabilities/index.html"
    seen = {start}
    q = deque([start])
    href_re = re.compile(r"""href=["']([^"'#]+)""", re.IGNORECASE)
    while q:
        cur = q.popleft()
        f = public / cur
        if not f.exists() or f.suffix != ".html":
            continue
        base = posixpath.dirname(cur)
        text = f.read_text()
        for target in href_re.findall(text) + _data_driven_edges(text):
            if target.startswith(("http", "mailto:", "data:", "//")) or "${" in target:
                continue
            nxt = posixpath.normpath(posixpath.join(base, target))
            if (public / nxt).is_dir():
                nxt = posixpath.join(nxt, "index.html")  # dir hrefs land on index
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    unreachable = sorted(scoped - seen)
    assert not unreachable, f"orphaned (unreachable from capabilities): {unreachable}"


def test_fixed_hrefs_regression(public):
    pa = (public / "decommissioning/pa-liability-wave.html").read_text()
    assert "../../docs/intervention-db" not in pa
    assert "../intervention-db/intervention-stats-brief.html" in pa
    ins = (public / "capabilities/insights.html").read_text()
    assert "../../scripts/build_pages.py" not in ins


def test_hand_authored_fixes_survive_clean_build(public):
    for rel in (
        "capabilities/index.html",
        "capabilities/insights.html",
        "lifecycle/assets/stones_assets.html",
        "intervention-db/intervention-stats-brief.html",
    ):
        assert sn.MARKER in (public / rel).read_text(), rel


def test_roster_poster_targets_exist(public):
    roster = json.loads((REPO / "reports/field-atlas/_roster.json").read_text())
    entries = roster if isinstance(roster, list) else roster.get("fields", [])
    missing = [
        e["lifecycle_id"]
        for e in entries
        if e.get("lifecycle_id")
        and not (public / f"lifecycle/{e['lifecycle_id']}_lifecycle.html").exists()
    ]
    assert not missing, f"roster lifecycle_ids without posters: {missing}"
