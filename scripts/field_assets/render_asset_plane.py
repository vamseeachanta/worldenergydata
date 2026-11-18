"""Render a supplied asset hierarchy without publishing or acquiring data.

``render_asset_plane(record)`` accepts field ``id``, ``name`` and optional
``nodes``. Each node requires ``id``, ``parent_id`` (null for a facility),
``kind`` (facility/asset/component) and ``name``. Assets belong to facilities;
components belong to assets or components. Node ``sources`` are observations,
not installation or engineering claims. Sources are lists of {label, href}.
Optional ``capability`` metadata has label, state and its own sources; state is
available/unavailable/unverified. Missing evidence leaves capability state unknown.
Text must be nonblank strings, ids use ASCII letters/digits/underscore/hyphen,
and links must be HTTPS or relative paths without traversal. No units, counts,
geometry, engineering results or source authenticity are inferred.
"""

import re
from html import escape
from unicodedata import category
from urllib.parse import unquote, urlsplit


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonblank text")
    if any(category(c) == "Cc" for c in value):
        raise ValueError("Control character in text")
    return escape(value, quote=True)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise ValueError("Expected a stable identifier")
    return value


def _link(value):
    _text(value)
    if any(c.isspace() or category(c) == "Cc" for c in value):
        raise ValueError("Whitespace or control character in link")
    # Parse before decoding so escaped delimiters cannot change URL structure.
    url = urlsplit(value)
    if any(re.search(r"%(?![0-9A-Fa-f]{2})", part) for part in url):
        raise ValueError("Malformed percent escape in link")
    decoded = [unquote(part) for part in url]
    for position, part in enumerate(decoded):
        if any(
            category(c) == "Cc" or (c.isspace() and not (position >= 2 and c == " "))
            for c in part
        ):
            raise ValueError("Whitespace or control character in link")
    # A decoded literal percent is safe unless it starts another escape sequence.
    if any("\\" in part or re.search(r"%[0-9A-Fa-f]{2}", part) for part in decoded):
        raise ValueError("Ambiguous link encoding")
    path = decoded[2]
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
        or not path
        or path.startswith("/")
        or any(part in {".", ".."} for part in path.split("/"))
        or ":" in path
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
        return "Capability state unknown: no metadata supplied"
    if not isinstance(value, dict):
        raise ValueError("Capability must be metadata")
    label = _text(value.get("label"))
    state = value.get("state")
    if state not in ("available", "unavailable", "unverified"):
        raise ValueError("Unknown capability state")
    sources = _sources(value.get("sources"))
    if not sources:
        return "Capability state unknown: source evidence missing"
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
            raise ValueError(f"Duplicate node id: {ident}")
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
    allowed = {
        "facility": (None,),
        "asset": ("facility",),
        "component": ("asset", "component"),
    }
    for node in index.values():
        parent = node["parent_id"]
        if parent is not None and parent not in index:
            raise ValueError(f"Dangling parent id: {node['id']}")
        parent_kind = index[parent]["kind"] if parent is not None else None
        if parent_kind not in allowed[node["kind"]]:
            raise ValueError("Invalid parent kind")
    # Iterative traversal keeps deeply nested components independent of recursion limits.
    parts = []
    visited = set()
    stack = [(ident, False) for ident in sorted(children[None], reverse=True)]
    while stack:
        ident, closing = stack.pop()
        if closing:
            parts.append("</ol></li>")
        else:
            visited.add(ident)
            parts.append(f'<li class="card" id="node-{ident}">{content[ident]}<ol>')
            stack.append((ident, True))
            stack.extend(
                (child, False) for child in sorted(children[ident], reverse=True)
            )
    # Each node has one parent; a cycle therefore cannot be reached from a root.
    if len(visited) != len(index):
        ident = min(index.keys() - visited)
        raise ValueError(f"Cycle in hierarchy: {ident}")
    inventory = (
        "<ol>" + "".join(parts) + "</ol>" if nodes else "<p>Inventory unavailable</p>"
    )
    return (
        f'<main class="wrap asset-plane" data-field-id="{field_id}"><h1>{name} — assets</h1>'
        "<p>Capability metadata is descriptive; no analysis or qualification is implied.</p>"
        f"{inventory}</main>"
    )
