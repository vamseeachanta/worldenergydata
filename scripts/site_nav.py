#!/usr/bin/env python3
"""ABOUTME: Nav-spine helper (issue #850) — one breadcrumb component for every
ABOUTME: published page family, driven by the config/nav_spine.json manifest.

STDLIB-ONLY by contract: the GitHub Pages deploy runs ``scripts/build_pages.py``
on bare Python with no installed dependencies, and build_pages imports this
module. An AST-scan guard test enforces the constraint.

Hrefs are computed for the PUBLIC site layout with ``posixpath.relpath`` from
the page's public directory to each trail node's public path — no hand-counted
``../`` prefixes anywhere.
"""

from __future__ import annotations

import json
import posixpath
import re
from html import escape
from pathlib import Path

MARKER = "<!-- nav-spine -->"

_CRUMB_CSS = (
    "font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;"
    "margin:0 0 10px;opacity:.75"
)


class NavSpineError(RuntimeError):
    """Base class for nav-spine failures (all fail closed)."""


class UnknownPageKeyError(NavSpineError):
    pass


class MissingAnchorError(NavSpineError):
    pass


class AmbiguousAnchorError(NavSpineError):
    pass


def default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "nav_spine.json"


def load_manifest(path: str | Path | None = None) -> dict:
    p = Path(path) if path else default_manifest_path()
    with open(p, encoding="utf-8") as fh:
        doc = json.load(fh)
    if "pages" not in doc:
        raise NavSpineError(f"manifest {p} has no 'pages' section")
    return doc


def _fmt(template: str, ctx: dict) -> str:
    try:
        return template.format(**ctx)
    except KeyError as exc:
        raise NavSpineError(f"context missing {exc} for template {template!r}") from exc


def page_entry(manifest: dict, key: str) -> dict:
    for entry in manifest["pages"]:
        if entry["key"] == key:
            return entry
    raise UnknownPageKeyError(f"page key {key!r} not in nav_spine manifest")


def trail(manifest: dict, key: str, ctx: dict | None = None) -> list[tuple]:
    """Resolved trail: [(label, public_path), ...] + (leaf_label, None) last."""
    ctx = ctx or {}
    entry = page_entry(manifest, key)
    out = []
    for node in entry["trail"]:
        out.append((_fmt(node["label"], ctx), _fmt(node["path"], ctx)))
    out.append((_fmt(entry["leaf"], ctx), None))
    return out


def render_crumb(manifest: dict, key: str, ctx: dict | None = None) -> str:
    """Marker + one-line breadcrumb div with public-layout relative hrefs."""
    ctx = ctx or {}
    entry = page_entry(manifest, key)
    page_dir = posixpath.dirname(_fmt(entry["public"], ctx))
    parts = []
    for label, node_path in trail(manifest, key, ctx):
        if node_path is None:
            parts.append(f"<span>{escape(label)}</span>")
        else:
            href = posixpath.relpath(node_path, page_dir or ".")
            parts.append(f'<a href="{escape(href)}">{escape(label)}</a>')
    inner = " ▸ ".join(parts)
    return f'{MARKER}<div class="nav-spine" style="{_CRUMB_CSS}">{inner}</div>'


def inject(html: str, crumb: str, anchor: str, mode: str = "after") -> str:
    """Insert ``crumb`` immediately before/after ``anchor``. Fail-closed:

    - page already carries MARKER -> returned unchanged (idempotent);
    - anchor absent -> MissingAnchorError;
    - anchor appears more than once -> AmbiguousAnchorError;
    - unknown mode -> NavSpineError.
    """
    if MARKER in html:
        return html
    count = html.count(anchor)
    if count == 0:
        raise MissingAnchorError(f"anchor {anchor!r} not found")
    if count > 1:
        raise AmbiguousAnchorError(f"anchor {anchor!r} found {count} times")
    if mode == "after":
        return html.replace(anchor, anchor + "\n" + crumb, 1)
    if mode == "before":
        return html.replace(anchor, crumb + "\n" + anchor, 1)
    raise NavSpineError(f"unknown anchor mode {mode!r}")


def inject_for(
    html: str, key: str, ctx: dict | None = None, manifest: dict | None = None
) -> str:
    """Render + inject in one manifest-driven step (generator entry point)."""
    manifest = manifest or load_manifest()
    entry = page_entry(manifest, key)
    crumb = render_crumb(manifest, key, ctx)
    return inject(html, crumb, entry["anchor"], entry.get("anchor_mode", "after"))


def crumb_for(
    key: str, ctx: dict | None = None, manifest_path: str | Path | None = None
) -> str:
    """Convenience one-shot used by the generator scripts."""
    return render_crumb(load_manifest(manifest_path), key, ctx)


_INTERNAL_ATTR = re.compile(
    r"""(?:href|src)=["']([^"'#]+)(?:#([^"']*))?["']""", re.IGNORECASE
)


def internal_targets(html: str) -> list[tuple]:
    """(path, fragment|None) pairs for non-external href/src values.

    Used by the link-graph gate; stdlib regex is sufficient for the
    generated pages (attribute-quoted links only — JS-built links are a
    declared exclusion covered by roster checks).
    """
    out = []
    for m in _INTERNAL_ATTR.finditer(html):
        target, frag = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "data:", "//")):
            continue
        if "${" in target or (frag and "${" in frag):
            continue  # JS template literal (declared exclusion; roster-checked)
        out.append((target, frag))
    return out
