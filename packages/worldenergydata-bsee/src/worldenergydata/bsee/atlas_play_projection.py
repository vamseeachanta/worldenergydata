"""Pure proposed play updates from qualified Atlas results; no publication or I/O.

The caller supplies attribution from ``atlas.attribute_fields`` and a manifest
keyed by table identity (including independent identity-confirmation tables).
Each manifest entry has ``source``, ``version``, a 64-digit ``sha256`` and
``row_ids``: CSV row numbers for 2023sands, PLAY_NUMBER for 2023plays,
BOEM_CHRONOZONE for 2023chronozones, and source row identifiers otherwise.
Digests and public-source assertions are caller evidence, not verified bytes.
Existing registry empty strings mean unset, matching ``load_fields`` defaults.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, TypeGuard

from worldenergydata.common.fields_registry import FieldsRegistry

Row = dict[str, Any]


def _text(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def _source_valid(source: Row | None) -> bool:
    return (
        isinstance(source, dict)
        and all(_text(source.get(key)) for key in ("source", "version"))
        and isinstance(source.get("sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None
        and isinstance(source.get("row_ids"), list)
        and bool(source["row_ids"])
        and all(
            _text(row) or (type(row) is int and row > 0) for row in source["row_ids"]
        )
    )


def _confirmed(result: Row) -> bool:
    evidence = result.get("evidence", {})
    return (
        result.get("join_basis") == "confirmed_boem_field"
        and evidence.get("code_match", {}).get("value") is True
        and evidence.get("code_match", {}).get("source_field") == "2023sands.BOEM_FIELD"
        and any(
            evidence.get(key, {}).get("value") is True
            and _text(evidence[key].get("source_field"))
            for key in ("name_match", "lease_block_match")
        )
    )


def _sources_available(result: Row, sources: dict[str, Row]) -> bool:
    required = ("2023sands", "2023plays", "2023chronozones")
    if not all(_source_valid(sources.get(table, {})) for table in required):
        return False
    play = result["plays"][0]
    if play["number"] not in sources["2023plays"]["row_ids"]:
        return False
    if any(
        sand["csv_row"] not in sources["2023sands"]["row_ids"]
        or sand["chronozone"] not in sources["2023chronozones"]["row_ids"]
        for sand in result["sand_rows"]
    ):
        return False
    return any(
        evidence.get("value") is True
        and _source_valid(
            sources.get((evidence.get("source_field") or "").split(".")[0], {})
        )
        for key in ("name_match", "lease_block_match")
        for evidence in [result.get("evidence", {}).get(key, {})]
    )


def _disposition(result: Row, sources: dict[str, Row]) -> str:
    status = result.get("status")
    if status != "attributed":
        return status if status in ("unmatched", "ambiguous") else "unqualified_status"
    if not _confirmed(result):
        return "unconfirmed_identity"
    if result.get("qualifiers"):
        return "qualified_candidates"
    plays = result.get("plays", [])
    if not plays:
        return "no_play"
    if len(plays) != 1:
        return "multiple_plays"
    if not all(_text(plays[0].get(key)) for key in ("number", "code", "description")):
        return "incomplete_play"
    sands = result.get("sand_rows", [])
    if not sands or any(
        type(sand.get("csv_row")) is not int
        or sand["csv_row"] < 2
        or not all(
            _text(sand.get(key))
            for key in ("sn_formsand", "boem_field", "play_number", "chronozone")
        )
        or sand["play_number"] != plays[0]["number"]
        for sand in sands
    ):
        return "incomplete_sand_evidence"
    if not _sources_available(result, sources):
        return "unavailable_source_evidence"
    return "proposed"


def project_plays(
    attributions: list[Row],
    registry: FieldsRegistry,
    source_manifest: dict[str, Row],
    existing_plays: dict[str, str | None] | None = None,
) -> Row:
    """Return canonical-id-keyed proposals and separately retained unresolved rows.

    Only exact registered ids are accepted; names are never matched here.
    Duplicate resolved ids raise ValueError, even when candidates disagree.
    Non-null explicit existing values take precedence; otherwise registry values
    are preserved. Conflicts are reported only against qualified proposals.
    Rejected candidates keep null unless a pre-existing value must be preserved.
    Output owns deep copies of all candidate/source evidence, in stable order.
    """
    proposals: dict[str, Row] = {}
    unresolved: list[Row] = []
    for result in attributions:
        field_id = result.get("field_id")
        field = registry.by_id(field_id) if _text(field_id) else None
        proposal = {
            "field_id": field_id,
            "play": None,
            "disposition": "unresolved_identity",
            "attribution": deepcopy(result),
            "sources": deepcopy(source_manifest),
        }
        if field is None:
            unresolved.append(proposal)
        else:
            field_id = field.canonical_id
            if field_id in proposals:
                raise ValueError(f"Duplicate canonical id: {field_id}")
            disposition = _disposition(result, source_manifest)
            candidate = (
                result["plays"][0]["code"] if disposition == "proposed" else None
            )
            current = (existing_plays or {}).get(field_id)
            if current is None:
                current = field.play or None
            if current is not None:
                disposition = (
                    "existing_play_preserved"
                    if candidate is None
                    else (
                        "already_populated"
                        if current == candidate
                        else "existing_play_conflict"
                    )
                )
            proposal.update(
                play=current if current is not None else candidate,
                disposition=disposition,
            )
            proposals[field_id] = proposal
    return {
        "proposals": {key: proposals[key] for key in sorted(proposals)},
        "unresolved": sorted(
            unresolved, key=lambda row: json.dumps(row, sort_keys=True)
        ),
    }
