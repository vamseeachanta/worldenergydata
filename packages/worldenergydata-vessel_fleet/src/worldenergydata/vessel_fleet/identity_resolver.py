"""Vessel identity resolver + dedup over the full fleet corpus (#599).

IMO coverage in the bulk corpus is ~0% (the curated ``drilling_rigs.csv`` has
no IMO column at all, and ``construction_vessels.csv`` is sparse), so the
working dedup key here is **not** IMO. It is the *normalized canonical name*
plus *operator/owner compatibility*, with an *alternate-name (aka) list* to
absorb spelling/marketing variants and renames. IMO/MMSI are used only as a
strong confirmer WHEN present.

Public surface:

* :func:`canonicalize_name` -- normalize a vessel name for matching.
* :func:`resolve_identities` -- cluster records that are the SAME vessel and
  emit ``cluster_id`` / ``match_basis`` / ``confidence`` per cluster.
* :func:`dedupe_catalog` -- collapse clusters to one canonical record and
  return a before/after report (with per-class deltas).
* :func:`load_corpus_records` / :func:`build_identity_crosswalk` -- run the
  resolver over the real curated CSVs + roster + seed and emit the aggregate
  ``data/identity_crosswalk.yml`` summary.

Design is deliberately CONSERVATIVE: when two records share a name but their
operators CONFLICT they are NOT merged (two different vessels can share a
name). When one operator is unknown the pair is treated as compatible.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Name canonicalization --------------------------------------------------

# Generic vessel-class prefixes (marketing / type tags) that are NOT part of a
# vessel's identity. Longest first so "M/V " wins over "MV ".
_PREFIXES: tuple[str, ...] = (
    "M/V ",
    "S/V ",
    "MSV ",
    "MV ",
    "SV ",
    "SS ",
    "MT ",
    "AHTS ",
)

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9 ]")
# A trailing parenthetical operator suffix, e.g. "Skandi Constructor (DOF)".
_TRAILING_PAREN_RE = re.compile(r"\s*\([^()]*\)\s*$")
# A hull-number token: a short alpha run glued to digits, optionally split by a
# hyphen/space, e.g. "Q4000", "Q-4000", "DLV 2000". Conservatively re-glued.
_HULL_SPLIT_RE = re.compile(r"\b([A-Z]{1,3})[\s-]+(\d{3,5})\b")


def canonicalize_name(name: Optional[str]) -> str:
    """Return a normalized canonical form of a vessel name for matching.

    Steps:
      1. Strip a trailing parenthetical operator suffix, e.g.
         ``"Skandi Constructor (DOF)"`` -> ``"Skandi Constructor"``.
      2. Uppercase.
      3. Strip a single leading class/marketing prefix (M/V, MV, MSV, SV, ...).
      4. Re-glue hull-number variants: ``"Q-4000"`` / ``"Q 4000"`` -> ``"Q4000"``
         (conservative -- only short alpha + 3-5 digit runs).
      5. Drop remaining punctuation, collapse whitespace, trim.

    Returns "" for falsy input.
    """
    if not name:
        return ""
    s = str(name).strip()
    # 1. Trailing parenthetical operator suffix (may be repeated/nested-ish).
    prev = None
    while prev != s:
        prev = s
        s = _TRAILING_PAREN_RE.sub("", s).strip()
    s = s.upper()
    # 3. Leading prefix (single pass -- only one class tag is meaningful).
    for prefix in _PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    # 4. Re-glue hull-number variants before punctuation removal so the hyphen
    #    in "Q-4000" does not just become a space.
    s = _HULL_SPLIT_RE.sub(r"\1\2", s)
    # 5. Drop punctuation -> spaces, collapse, trim.
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


# --- Operator compatibility -------------------------------------------------

# Corporate-form / generic descriptor tokens stripped before comparing
# operators, so "Helix Energy Solutions" and "Helix Well Ops" both reduce to a
# set containing "HELIX".
_OPERATOR_STOPWORDS: frozenset[str] = frozenset(
    {
        "INC",
        "LTD",
        "LLC",
        "LP",
        "PLC",
        "CO",
        "CORP",
        "CORPORATION",
        "COMPANY",
        "GROUP",
        "HOLDINGS",
        "AS",
        "ASA",
        "SA",
        "NV",
        "BV",
        "GMBH",
        "AB",
        "THE",
        "AND",
        "OF",
        "ENERGY",
        "SOLUTIONS",
        "SERVICES",
        "SERVICE",
        "OFFSHORE",
        "SUBSEA",
        "MARINE",
        "SHIPPING",
        "CONTRACTORS",
        "CONTRACTOR",
        "INTERNATIONAL",
        "INTL",
        "MANAGEMENT",
        "OPERATIONS",
        "WELL",
        "OPS",
        "DRILLING",
        "PETROLEUM",
    }
)

_OPERATOR_SPLIT_RE = re.compile(r"[^A-Z0-9]+")


def _operator_tokens(*values: Optional[str]) -> set[str]:
    """Distinctive (non-stopword) tokens across operator + owner strings."""
    tokens: set[str] = set()
    for value in values:
        if not value:
            continue
        for tok in _OPERATOR_SPLIT_RE.split(str(value).upper()):
            if tok and tok not in _OPERATOR_STOPWORDS and not tok.isdigit():
                tokens.add(tok)
    return tokens


def operators_compatible(rec_a: dict[str, Any], rec_b: dict[str, Any]) -> bool:
    """True if two records' operator/owner do NOT conflict.

    Compatible when either side has no distinctive operator/owner token, or the
    two token sets intersect. A CONFLICT (return ``False``) requires both sides
    to carry distinctive tokens that are entirely disjoint.
    """
    toks_a = _operator_tokens(rec_a.get("operator"), rec_a.get("owner"))
    toks_b = _operator_tokens(rec_b.get("operator"), rec_b.get("owner"))
    if not toks_a or not toks_b:
        return True
    return bool(toks_a & toks_b)


# --- Union-find -------------------------------------------------------------


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


# --- Identity resolution ----------------------------------------------------


def _record_aka_canon(record: dict[str, Any]) -> set[str]:
    """Canonical forms of a record's alternate names."""
    out: set[str] = set()
    for alt in record.get("aka") or []:
        c = canonicalize_name(alt)
        if c:
            out.add(c)
    return out


def resolve_identities(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cluster records that describe the SAME physical vessel.

    Each input record is a dict with any of: ``name``, ``operator``,
    ``owner``, ``imo``, ``mmsi``, ``aka`` (list of alternate names),
    ``source``. (A ``class`` field, if present, is carried through.)

    Records are merged when ANY holds (conservatively, never across an operator
    conflict for the name/aka rules):

      * exact IMO match                         -> confidence ``high``
      * canonical-name match AND operators
        compatible                              -> confidence ``medium``
      * one record's canonical name appears in
        another's aka list (operators
        compatible)                             -> confidence ``low``

    Returns a list of cluster dicts::

        {
            "cluster_id": int,
            "canonical_name": str,
            "members": [<original record>, ...],
            "match_basis": ["imo", "canonical_name+operator", "aka", ...],
            "confidence": "high" | "medium" | "low",
            "imo": <confirmed IMO or None>,
        }
    """
    n = len(records)
    uf = _UnionFind(n)
    canon = [canonicalize_name(r.get("name")) for r in records]
    aka_canon = [_record_aka_canon(r) for r in records]
    # Per-edge match basis, keyed by the union root after the fact is awkward;
    # instead record bases on the lower-index endpoint and re-aggregate.
    basis_edges: list[tuple[int, int, str]] = []

    # 1. IMO match (strong confirmer).
    by_imo: dict[str, list[int]] = {}
    for i, r in enumerate(records):
        imo = r.get("imo")
        if imo:
            by_imo.setdefault(str(imo).strip(), []).append(i)
    for group in by_imo.values():
        for j in group[1:]:
            uf.union(group[0], j)
            basis_edges.append((group[0], j, "imo"))

    # 2. canonical-name match + compatible operator.
    by_canon: dict[str, list[int]] = {}
    for i, c in enumerate(canon):
        if c:
            by_canon.setdefault(c, []).append(i)
    for group in by_canon.values():
        for a_idx in range(len(group)):
            for b_idx in range(a_idx + 1, len(group)):
                i, j = group[a_idx], group[b_idx]
                if operators_compatible(records[i], records[j]):
                    uf.union(i, j)
                    basis_edges.append((i, j, "canonical_name+operator"))

    # 3. aka match: one record's canonical name in another's aka list.
    canon_owner: dict[str, list[int]] = by_canon
    for j, akas in enumerate(aka_canon):
        if not akas:
            continue
        for alt_canon in akas:
            for i in canon_owner.get(alt_canon, []):
                if i == j:
                    continue
                if operators_compatible(records[i], records[j]):
                    uf.union(i, j)
                    basis_edges.append((i, j, "aka"))

    # Aggregate clusters.
    members: dict[int, list[int]] = {}
    for i in range(n):
        members.setdefault(uf.find(i), []).append(i)

    root_basis: dict[int, set[str]] = {}
    for i, j, b in basis_edges:
        root_basis.setdefault(uf.find(i), set()).add(b)

    clusters: list[dict[str, Any]] = []
    for cid, (root, idxs) in enumerate(sorted(members.items())):
        member_recs = [records[i] for i in idxs]
        bases = sorted(root_basis.get(root, set()))
        confidence = (
            "singleton" if len(member_recs) == 1 else _cluster_confidence(bases)
        )
        imo = next((r.get("imo") for r in member_recs if r.get("imo")), None)
        # Canonical name: prefer the longest non-empty canonical among members
        # (the operator-prefixed BSEE variants are usually longer but the seed
        # short hull token is the true identity -> prefer the shortest that is
        # still in another member's aka, else the most common).
        canonical = _pick_canonical(member_recs)
        clusters.append(
            {
                "cluster_id": cid,
                "canonical_name": canonical,
                "members": member_recs,
                "member_count": len(member_recs),
                "match_basis": bases,
                "confidence": confidence,
                "imo": str(imo).strip() if imo else None,
            }
        )
    return clusters


def _cluster_confidence(bases: list[str]) -> str:
    if "imo" in bases:
        return "high"
    if "canonical_name+operator" in bases:
        return "medium"
    return "low"


def _pick_canonical(member_recs: list[dict[str, Any]]) -> str:
    """Choose the cluster's canonical name.

    Use the shortest non-empty canonical form among members, breaking ties
    alphabetically. The shortest form is the clean identity (the bare hull token
    "Q4000"); operator-prefixed variants like "HELIX Q4000" or "MSV Q4000" are
    longer and are preserved in ``ALTERNATE_NAMES`` instead.
    """
    canons = [canonicalize_name(r.get("name")) for r in member_recs]
    nonempty = [c for c in canons if c]
    if not nonempty:
        return ""
    return min(nonempty, key=lambda c: (len(c), c))


# --- Catalog dedup ----------------------------------------------------------

_MERGE_SCALAR_FIELDS = ("operator", "owner", "imo", "mmsi", "source", "class")


def dedupe_catalog(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse identity clusters to one canonical record each.

    Returns ``(deduped, report)``. Each deduped record carries
    ``CANONICAL_NAME``, the union of all member names as ``ALTERNATE_NAMES``,
    ``match_basis`` / ``confidence`` / ``member_count`` and the merged scalar
    fields. The report records before/after totals, dupes collapsed, and a
    per-class delta (using each record's optional ``class`` field).
    """
    clusters = resolve_identities(records)
    deduped: list[dict[str, Any]] = []
    for cluster in clusters:
        deduped.append(_collapse_cluster(cluster))

    report = _build_report(records, deduped, clusters)
    return deduped, report


def _collapse_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    members = cluster["members"]
    merged: dict[str, Any] = {
        "CANONICAL_NAME": cluster["canonical_name"],
        "match_basis": cluster["match_basis"],
        "confidence": cluster["confidence"],
        "member_count": len(members),
    }
    # Merge scalar fields: first non-empty wins (members keep source order).
    for field in _MERGE_SCALAR_FIELDS:
        for r in members:
            val = r.get(field)
            if val not in (None, ""):
                merged.setdefault(field.upper() if field != "class" else "CLASS", val)
                break
    # Representative display name: the first member's raw name.
    merged["VESSEL_NAME"] = next(
        (r.get("name") for r in members if r.get("name")), cluster["canonical_name"]
    )
    # Union of all names + declared aka as ALTERNATE_NAMES.
    alts: list[str] = []
    seen: set[str] = set()
    for r in members:
        candidates: list[str] = []
        if r.get("name"):
            candidates.append(str(r["name"]))
        candidates.extend(str(a) for a in (r.get("aka") or []))
        for name in candidates:
            key = name.strip()
            if key and key != merged["VESSEL_NAME"] and key not in seen:
                seen.add(key)
                alts.append(key)
    merged["ALTERNATE_NAMES"] = alts or None
    # Union of distinct sources contributing to the cluster.
    merged["SOURCES"] = sorted({str(r["source"]) for r in members if r.get("source")})
    return merged


def _build_report(
    records_in: list[dict[str, Any]],
    deduped: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
) -> dict[str, Any]:
    total_in = len(records_in)
    total_out = len(deduped)

    # Per-class before/after (a cluster's class = the merged record's CLASS).
    before_by_class: dict[str, int] = {}
    for r in records_in:
        cls = r.get("class") or "unclassified"
        before_by_class[cls] = before_by_class.get(cls, 0) + 1
    after_by_class: dict[str, int] = {}
    for r in deduped:
        cls = r.get("CLASS") or "unclassified"
        after_by_class[cls] = after_by_class.get(cls, 0) + 1

    per_class_delta = {}
    for cls in sorted(set(before_by_class) | set(after_by_class)):
        before = before_by_class.get(cls, 0)
        after = after_by_class.get(cls, 0)
        per_class_delta[cls] = {
            "before": before,
            "after": after,
            "collapsed": before - after,
        }

    # Per-source contribution (how many input rows each source supplied).
    by_source: dict[str, int] = {}
    for r in records_in:
        src = r.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1

    confidence_counts: dict[str, int] = {}
    for c in clusters:
        confidence_counts[c["confidence"]] = (
            confidence_counts.get(c["confidence"], 0) + 1
        )

    multi = [c for c in clusters if len(c["members"]) > 1]
    return {
        "records_in": total_in,
        "distinct_vessels_out": total_out,
        "duplicates_collapsed": total_in - total_out,
        "clusters_with_multiple_members": len(multi),
        "by_source": dict(sorted(by_source.items())),
        "per_class_delta": per_class_delta,
        "cluster_confidence_counts": dict(sorted(confidence_counts.items())),
    }
