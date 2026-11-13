# ABOUTME: Link-graph gate (issue #850) — builds the public site in-process to a
# ABOUTME: tmp dir, then asserts existence, resolution, exact trails, reachability.

import csv
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

_cb_spec = importlib.util.spec_from_file_location(
    "catalog_badges_ig", REPO / "scripts" / "catalog_badges.py"
)
cb = importlib.util.module_from_spec(_cb_spec)
_cb_spec.loader.exec_module(cb)

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
        if rel == "capabilities/index.html":
            assert sn.MARKER not in text, rel
            continue
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
POSTER_PAGE_RE = re.compile(r"^lifecycle/[^/]+_lifecycle\.html$")


def _data_driven_edges(text, page_rel=None):
    """Hrefs embedded in the poster's FIELD JSON payload (rendered by JS)."""
    is_poster_page = page_rel is not None and POSTER_PAGE_RE.match(page_rel)
    m = FIELD_JSON_RE.search(text)
    if not m:
        if is_poster_page:
            raise AssertionError(f"{page_rel}: missing FIELD JSON")
        return []
    try:
        field = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        if is_poster_page:
            raise AssertionError(f"{page_rel}: invalid FIELD JSON") from exc
        return []
    edges = [
        field.get("wellsHref"),
        field.get("assetsHref"),
        field.get("economics_href"),
        field.get("benchmark_href"),
    ]
    edges += [c.get("href") for c in field.get("norms", [])]
    return [e.split("#")[0] for e in edges if e]


def test_data_driven_edges_include_economics_and_benchmark(public):
    text = (public / "lifecycle/big_foot_lifecycle.html").read_text()
    edges = set(_data_driven_edges(text, "lifecycle/big_foot_lifecycle.html"))

    assert "../economics-big_foot.html" in edges
    assert "../benchmark.html" in edges


def test_data_driven_edges_fail_closed_for_malformed_poster_field_json():
    with pytest.raises(AssertionError, match="missing FIELD JSON"):
        _data_driven_edges("<html></html>", "lifecycle/big_foot_lifecycle.html")

    with pytest.raises(AssertionError, match="invalid FIELD JSON"):
        _data_driven_edges(
            "const FIELD = {\n  nope\n};",
            "lifecycle/big_foot_lifecycle.html",
        )


def test_data_driven_edges_resolve(public):
    bad = []
    for rel, _k, _c in scoped_pages():
        text = (public / rel).read_text()
        for target in _data_driven_edges(text, rel):
            f = _resolve(public, rel, target)
            if f.is_dir():
                f = f / "index.html"
            if not f.exists():
                bad.append((rel, target))
    assert not bad, f"unresolved data-driven targets: {bad}"


def test_bfs_reachability_from_capabilities(public):
    scoped = {p for p, _k, _c in scoped_pages()}
    start = "capabilities/insights.html"
    seen = {start}
    q = deque([start])
    href_re = re.compile(r"""href=["']([^"'#]+)""", re.IGNORECASE)
    stub = (public / "capabilities/index.html").read_text(encoding="utf-8")
    stub_links = re.findall(r"""href=["']([^"']+)["']""", stub, re.IGNORECASE)
    assert stub_links, "redirect stub links absent"
    assert all(
        target == "https://www.aceengineer.com/capabilities/" for target in stub_links
    ), stub_links
    while q:
        cur = q.popleft()
        f = public / cur
        if not f.exists() or f.suffix != ".html":
            continue
        base = posixpath.dirname(cur)
        text = f.read_text()
        for target in href_re.findall(text) + _data_driven_edges(text, cur):
            if target.startswith(("http", "mailto:", "data:", "//")) or "${" in target:
                continue
            nxt = posixpath.normpath(posixpath.join(base, target))
            if (public / nxt).is_dir():
                nxt = posixpath.join(nxt, "index.html")  # dir hrefs land on index
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    unreachable = sorted(scoped - seen)
    assert not unreachable, f"orphaned (unreachable from insights): {unreachable}"


def test_fixed_hrefs_regression(public):
    pa = (public / "decommissioning/pa-liability-wave.html").read_text()
    assert "../../docs/intervention-db" not in pa
    assert "../intervention-db/intervention-stats-brief.html" in pa
    ins = (public / "capabilities/insights.html").read_text()
    assert "../../scripts/build_pages.py" not in ins


def test_hand_authored_fixes_survive_clean_build(public):
    for rel in (
        "capabilities/insights.html",
        "lifecycle/assets/stones_assets.html",
        "intervention-db/intervention-stats-brief.html",
    ):
        assert sn.MARKER in (public / rel).read_text(), rel


def test_independent_regulator_posters_retain_explorer_targets(public):
    explorer = _explorer(public)
    for fact in FACTS:
        assert (public / f"lifecycle/{fact['id']}_lifecycle.html").exists()
        assert fact["id"] in explorer["fields"]


# --- Explorer shell contract (issue #946) ----------------------------------

EXPLORER_HREF_KEYS = ("wellsHref", "assetsHref", "economics_href", "benchmark_href")


def _explorer(public):
    return json.loads((public / "lifecycle/_explorer.json").read_text())


def test_explorer_sidecar_published_and_covers_all_posters(public):
    explorer = _explorer(public)
    assert set(explorer["fields"]) == {f["id"] for f in FACTS}
    assert explorer["wells"]["wells"], "wells contract embedded"


def test_wells_rollout_fields_and_no_null_strings(public):
    # #948: exactly the 7 producing LT fields carry a wells drill-down, and
    # every generated well page is free of "null"/"None"/"nan" leakage or NaN.
    explorer = _explorer(public)
    with_wells = {
        fid: f["wellsCount"]
        for fid, f in explorer["fields"].items()
        if f.get("wellsHref")
    }
    assert set(with_wells) == {
        "big_foot",
        "jack_st_malo",
        "stones",
        "julia",
        "shenandoah",
        "cascade_chinook",
        "anchor",
    }
    embedded = explorer["wells"]["wells"]
    assert len(embedded) == sum(with_wells.values()) == 56
    assert "NaN" not in json.dumps(explorer)
    bad = []
    for page in (public / "lifecycle/wells").glob("*_well.html"):
        text = page.read_text()
        for token in (">None<", ">nan<", "None ppg", "nan ft", "NaN"):
            if token in text:
                bad.append((page.name, token))
    assert not bad, f"null/NaN leakage in well pages: {bad}"


def test_underwriting_risk_signals(public):
    # #949: HPHT badge for the 9 fields with reservoir HPHT data (not big_foot);
    # facility-decommissioning badge for exactly the 3 name-matched LT facilities.
    import importlib.util as _il

    _hs = _il.spec_from_file_location(
        "hpht_risk_ig", REPO / "src/worldenergydata/field_development/hpht_risk.py"
    )
    hr = _il.module_from_spec(_hs)
    _hs.loader.exec_module(hr)

    fields = _explorer(public)["fields"]
    hpht = {k: v["risk"]["hpht"] for k, v in fields.items() if v["risk"]["hpht"]}
    decom = {
        k: v["risk"]["decommissioning"]
        for k, v in fields.items()
        if v["risk"]["decommissioning"]
    }
    assert set(hpht) == {
        "anchor",
        "cascade_chinook",
        "jack_st_malo",
        "julia",
        "kaskida",
        "north_platte",
        "shenandoah",
        "stones",
        "tiber",
    }
    assert fields["big_foot"]["risk"]["hpht"] is None
    assert decom == {}
    assert all(
        field["risk"]["decommissioning_status"]
        == "withheld_pending_redistribution_review"
        for field in fields.values()
    )
    # Parity: severity recomputed from each field's reservoir matches the sidecar.
    facts = {f["id"]: f for f in FACTS}
    for fid, sig in hpht.items():
        assert hr.classify_hpht(facts[fid]["reservoir"])["severity"] == sig["severity"]
    # Julia's subsea-system pressure must NOT be rendered as an exceedance.
    assert hpht["julia"]["exceedance_pct"] is None
    assert hpht["anchor"]["exceedance_pct"] == 25


def test_concept_fdp_links(public):
    # #759: the concept.fdp_href is a JS-built link the data-driven edge extractor
    # does NOT auto-catch, so assert it explicitly. All LT fields now have an FDP
    # page; every href must resolve in the published tree (issue #962).
    import re as _re

    fields = _explorer(public)["fields"]
    with_fdp = {
        fid: c["concept"]["fdp_href"]
        for fid, c in fields.items()
        if c["concept"]["fdp_href"]
    }
    assert set(with_fdp) == set(fields)
    for fid, href in with_fdp.items():
        assert _re.fullmatch(
            r"\.\./field-development/portfolio/[a-z_-]+\.html", href
        ), href
        assert (
            public / "field-development/portfolio" / href.rsplit("/", 1)[1]
        ).exists()
    for fid, f in fields.items():
        c = f["concept"]
        assert c["fdp_issue"] == 962
        if fid not in with_fdp:
            assert c["fdp_href"] is None  # placeholder, not a dead link
    # Milestone split (review correction): 7 first-oil / 3 sanctioned.
    labels = [f["concept"]["milestone"]["label"] for f in fields.values()]
    assert labels.count("First oil") == 7 and labels.count("Sanctioned") == 3


def test_landman_lease_panel(public):
    # #951: all 10 LT fields carry a landman panel; 20 leases total; field-level
    # blocks only (NO per-lease block — false-precision guard); placeholders link
    # the ingest issue.
    fields = _explorer(public)["fields"]
    total = 0
    for fid, f in fields.items():
        lm = f["landman"]
        assert lm and lm["leases"], fid
        assert lm["blocks"] and lm["ingest_issue"] == 959
        assert "per_lease_block" in lm["pending"]
        for r in lm["leases"]:
            assert "block" not in r  # never a per-lease block
        total += lm["n_leases"]
    assert total == 20, f"expected 20 LT leases, got {total}"
    # Every canonical LT lease resolves through the registry.
    from worldenergydata.common.fields_registry import load_fields

    registry = load_fields()
    for fid, f in fields.items():
        for r in f["landman"]["leases"]:
            assert registry.by_lease(r["lease_num"]) == fid, r["lease_num"]


def test_every_well_has_a_page(public):
    embedded = _explorer(public)["wells"]["wells"]
    missing = [
        f"{w['field_id']}_{w['slot']}"
        for w in embedded
        if not (
            public / f"lifecycle/wells/{w['field_id']}_{w['slot']}_well.html"
        ).exists()
    ]
    assert not missing, f"wells without pages: {missing}"


def test_explorer_hrefs_resolve_from_poster_and_shell_bases(public):
    # Payload hrefs are lifecycle/-relative BY CONTRACT. The shell at
    # field-atlas/ rebases every href against ../lifecycle/ before it reaches
    # the DOM (#946 r1 finding 2) — both resolutions must land on a published
    # file, so a base-handling regression on either side goes red here.
    bad = []
    for fid, f in _explorer(public)["fields"].items():
        targets = [f.get(k) for k in EXPLORER_HREF_KEYS]
        targets += [c.get("href") for c in f.get("norms", [])]
        for t in [t.split("#")[0] for t in targets if t]:
            views = (
                ("poster", _resolve(public, f"lifecycle/{fid}_lifecycle.html", t)),
                (
                    "shell",
                    _resolve(
                        public,
                        "field-atlas/index.html",
                        posixpath.join("../lifecycle", t),
                    ),
                ),
            )
            for label, p in views:
                q = p / "index.html" if p.is_dir() else p
                if not q.exists():
                    bad.append((fid, label, t))
    assert not bad, f"unresolved explorer hrefs: {bad}"


def test_explorer_wells_pages_exist(public):
    missing = [
        f"{w['field_id']}_{w['slot']}"
        for w in _explorer(public)["wells"]["wells"]
        if not (
            public / f"lifecycle/wells/{w['field_id']}_{w['slot']}_well.html"
        ).exists()
    ]
    assert not missing, f"wells in contract without pages: {missing}"


def test_explorer_identity_with_posters(public):
    # Single-sourcing gate: the sidecar serializes the SAME post-enrichment
    # dicts the posters embed (facts_to_field + norms + performance attached
    # in main() — #946 r1 finding 1).
    explorer = _explorer(public)
    for f in FACTS:
        text = (public / f"lifecycle/{f['id']}_lifecycle.html").read_text()
        embedded = json.loads(FIELD_JSON_RE.search(text).group(1))
        assert embedded == explorer["fields"][f["id"]], f["id"]


def test_withheld_atlas_has_one_heading_and_no_embedded_payload(public):
    text = (public / "field-atlas/index.html").read_text()
    assert "held privately pending redistribution-terms review" in text
    assert text.count("<h1") == 1
    assert "const ROSTER" not in text and "const COUNTRIES" not in text


def test_restricted_atlas_feed_is_not_published(public):
    assert not (public / "field-atlas/_atlas_feed.json").exists()


def test_all_regions_report_is_withheld(public):
    text = (public / "all-regions-atlas.html").read_text()
    assert "held privately pending redistribution-terms review" in text
    assert "<table" not in text
