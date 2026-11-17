"""Render a supplied asset hierarchy without publishing or acquiring data.

``render_asset_plane(record)`` accepts field ``id``, ``name`` and optional
``nodes``. Each node requires ``id``, ``parent_id`` (null for a facility),
``kind`` (facility/asset/component) and ``name``. Assets belong to facilities;
components belong to assets or components. Node ``sources`` are observations,
not installation or engineering claims. Sources are lists of {label, href}.
Optional ``capability`` metadata has label, state and its own sources; state is
available/unavailable/unverified. Missing evidence is visibly unavailable.
Text must be nonblank strings, ids use ASCII letters/digits/underscore/hyphen,
and links must be HTTPS or relative paths without traversal. No units, counts,
geometry, engineering results or source authenticity are inferred.
"""

import re
from html import escape
from urllib.parse import unquote, urlsplit


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonblank text")
    return escape(value, quote=True)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise ValueError("Expected a stable identifier")
    return value


def _link(value):
    _text(value)
    decoded = unquote(value)
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in decoded):
        raise ValueError("Whitespace or control character in link")
    if "\\" in decoded or "%" in decoded:
        raise ValueError("Ambiguous link encoding")
    url = urlsplit(decoded)
    if url.scheme == "https":
        if (
            not url.hostname
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", url.hostname)
            or url.username is not None
            or url.password is not None
        ):
            raise ValueError("Invalid HTTPS link")
        _ = url.port  # Validate an explicitly supplied port as well.
    elif (
        url.scheme
        or url.netloc
        or not url.path
        or decoded.startswith("/")
        or any(part in {".", ".."} for part in url.path.split("/"))
        or ":" in url.path
    ):
        raise ValueError("Expected HTTPS or a repository-relative link")
    return escape(value, quote=True)


def _sources(value):
    if value is None:
        value = []
    if not isinstance(value, list) or any(not isinstance(s, dict) for s in value):
        raise ValueError("Sources must be a list of references")
    return " · ".join(
        f'<a href="{_link(s.get("href"))}">{_text(s.get("label"))}</a>' for s in value
    )


def _capability(value):
    if value is None:
        return "Capability unavailable: no metadata supplied"
    if not isinstance(value, dict):
        raise ValueError("Capability must be metadata")
    label = _text(value.get("label"))
    state = value.get("state")
    if state not in ("available", "unavailable", "unverified"):
        raise ValueError("Unknown capability state")
    sources = _sources(value.get("sources"))
    if not sources:
        return "Capability unavailable: source evidence missing"
    return f'<span class="tag" data-state="{state}">Capability {state}: {label}</span> · {sources}'


def render_asset_plane(record: dict) -> str:
    """Return deterministic HTML; malformed hierarchy or metadata raises ValueError.

    Siblings sort by stable id. An absent/null/empty node list means unavailable
    inventory, never an established zero. Evidence links are syntax-checked only.
    Caller-owned records are never modified; this function performs no I/O.
    """
    if not isinstance(record, dict):
        raise ValueError("Expected a field record")
    field_id = _identifier(record.get("id"))
    name = _text(record.get("name"))
    nodes = record.get("nodes")
    if nodes is None:
        nodes = []
    if not isinstance(nodes, list) or any(not isinstance(n, dict) for n in nodes):
        raise ValueError("Nodes must be a list of records")
    index, children, content = {}, {None: []}, {}
    for node in nodes:
        ident = _identifier(node.get("id"))
        if ident in index:
            raise ValueError("Duplicate node id")
        if "parent_id" not in node:
            raise ValueError("Explicit parent_id required")
        parent = node["parent_id"]
        if parent is not None:
            _identifier(parent)
        if node.get("kind") not in ("facility", "asset", "component"):
            raise ValueError("Unknown hierarchy kind")
        index[ident] = node
        children.setdefault(parent, []).append(ident)
        children.setdefault(ident, [])
        sources = _sources(node.get("sources"))
        observation = (
            f"Observation sources: {sources}"
            if sources
            else "Observation unavailable: source evidence missing"
        )
        content[ident] = (
            f'<p class="n">{node["kind"].title()}: {_text(node.get("name"))}</p>'
            f'<p class="meta">{observation}</p>'
            f'<p>{_capability(node.get("capability"))}</p>'
        )
    for ident, node in index.items():
        chain, cursor = set(), ident
        while cursor is not None:
            if cursor not in index:
                raise ValueError("Dangling parent id")
            if cursor in chain:
                raise ValueError("Cycle in hierarchy")
            chain.add(cursor)
            cursor = index[cursor]["parent_id"]
        parent = node["parent_id"]
        parent_kind = index[parent]["kind"] if parent is not None else None
        allowed = {
            "facility": (None,),
            "asset": ("facility",),
            "component": ("asset", "component"),
        }
        if parent_kind not in allowed[node["kind"]]:
            raise ValueError("Invalid parent kind")
    # Iterative traversal keeps deeply nested components independent of recursion limits.
    parts = []
    stack = [(ident, False) for ident in sorted(children[None], reverse=True)]
    while stack:
        ident, closing = stack.pop()
        if closing:
            parts.append("</ol></li>")
        else:
            parts.append(f'<li class="card" id="node-{ident}">{content[ident]}<ol>')
            stack.append((ident, True))
            stack.extend(
                (child, False) for child in sorted(children[ident], reverse=True)
            )
    inventory = (
        "<ol>" + "".join(parts) + "</ol>" if nodes else "<p>Inventory unavailable</p>"
    )
    return (
        f'<main class="wrap asset-plane" data-field-id="{field_id}"><h1>{name} — assets</h1>'
        "<p>Capability metadata is descriptive; no analysis or qualification is implied.</p>"
        f"{inventory}</main>"
    )
