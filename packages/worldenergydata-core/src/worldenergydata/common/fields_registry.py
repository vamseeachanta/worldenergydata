"""CANONICAL field-identity registry — the single source of truth for this repo.

Loads ``config/fields.yml`` and resolves each field by ONE canonical id
(id <-> display name <-> BSEE lease/area-block <-> FDP slug). Every other
field-name mapping in the repo is superseded for identity resolution by this
module + ``config/fields.yml``; do not add parallel mappings, extend the yaml
(and its per-field ``aliases``) instead (epic #754, issue #755).

Resolution API::

    from worldenergydata.common.fields_registry import load_fields

    reg = load_fields()
    reg.by_id("jack_st_malo")            # -> Field | None
    reg.resolve("Jack St Malo")          # -> "jack_st_malo" (case/punct-insensitive)
    reg.by_lease("OCS-G 25806")          # -> "buckskin" (lease-variant tolerant)
    reg.fdp_slug("cascade_chinook")      # -> "chinook"
    reg.all_ids()                        # -> ["big_foot", "anchor", ...]

Fail-closed: unknown alias/lease returns ``None`` (the caller decides). Duplicate
canonical ids, cross-field alias collisions, and cross-field lease collisions
raise ``ValueError`` at load time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Optional

import yaml

# Structured-form guards (mirrored by the contract tests):
LEASE_RE = re.compile(r"^G\d{5}$")
AREA_BLOCK_RE = re.compile(r"^[A-Z]{2}\d{3}$")


def normalize_name(name: str) -> str:
    """Case/punctuation-insensitive key for name/alias resolution.

    Strips every non-alphanumeric character and lowercases, so
    "Cascade/Chinook", "Cascade Chinook" and "cascade chinook" collapse to the
    same key ("cascadechinook").
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def normalize_lease(lease: str) -> str:
    """Canonicalize a BSEE lease string to the stored ``G\\d{5}`` form.

    Uppercases, drops the ``OCS-`` prefix and any internal spaces, so
    "OCS-G 25806", "G 25806", "g25806" and "G25806" all map to "G25806".
    """
    return lease.upper().replace("OCS-", "").replace(" ", "").strip()


@dataclass(frozen=True)
class Field:
    """One canonical field and its identity crosswalk."""

    canonical_id: str
    display_name: str
    aliases: tuple[str, ...]
    region: str
    play: str
    area_blocks: tuple[str, ...]
    leases: tuple[str, ...]
    bsee_block_note: str
    fdp_slug: str
    surfaces: dict
    tier: Optional[str] = None


@dataclass
class FieldsRegistry:
    """In-memory view of ``config/fields.yml`` with resolution indexes."""

    fields: list[Field]
    unmapped_fdp_pages: list[dict] = dc_field(default_factory=list)
    _by_id: dict[str, Field] = dc_field(default_factory=dict, repr=False)
    _name_index: dict[str, str] = dc_field(default_factory=dict, repr=False)
    _lease_index: dict[str, str] = dc_field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for f in self.fields:
            if f.canonical_id in self._by_id:
                raise ValueError(
                    f"Duplicate canonical_id in fields.yml: {f.canonical_id!r}"
                )
            self._by_id[f.canonical_id] = f

            # name/alias index: canonical_id + display_name + aliases all resolve
            # to the field. A key may repeat *within* one field (same id) — that
            # is deduped; a key shared by two DIFFERENT ids is a collision.
            for name in (f.canonical_id, f.display_name, *f.aliases):
                key = normalize_name(name)
                if not key:
                    continue
                existing = self._name_index.get(key)
                if existing is not None and existing != f.canonical_id:
                    raise ValueError(
                        f"Alias collision: {name!r} maps to both "
                        f"{existing!r} and {f.canonical_id!r}"
                    )
                self._name_index[key] = f.canonical_id

            for lease in f.leases:
                key = normalize_lease(lease)
                existing = self._lease_index.get(key)
                if existing is not None and existing != f.canonical_id:
                    raise ValueError(
                        f"Lease collision: {lease!r} maps to both "
                        f"{existing!r} and {f.canonical_id!r}"
                    )
                self._lease_index[key] = f.canonical_id

    # -- resolution API ----------------------------------------------------
    def by_id(self, canonical_id: str) -> Optional[Field]:
        """Return the :class:`Field` for ``canonical_id`` (``None`` if unknown)."""
        return self._by_id.get(canonical_id)

    def resolve(self, name_or_alias: str) -> Optional[str]:
        """Resolve a display name / alias to a canonical id (``None`` if unknown)."""
        if name_or_alias is None:
            return None
        return self._name_index.get(normalize_name(name_or_alias))

    def by_lease(self, lease: str) -> Optional[str]:
        """Resolve a BSEE lease (any input variant) to a canonical id."""
        if lease is None:
            return None
        return self._lease_index.get(normalize_lease(lease))

    def fdp_slug(self, canonical_id: str) -> Optional[str]:
        """Return the FDP portfolio slug for a canonical id (``None`` if unknown)."""
        f = self._by_id.get(canonical_id)
        return f.fdp_slug if f is not None else None

    def all_ids(self) -> list[str]:
        """All canonical ids, in file order."""
        return [f.canonical_id for f in self.fields]


def _default_path() -> Path:
    from worldenergydata.common.data_resolver import _get_project_root

    return _get_project_root() / "config" / "fields.yml"


def load_fields(path: Optional[Path] = None) -> FieldsRegistry:
    """Load and index ``config/fields.yml`` into a :class:`FieldsRegistry`.

    Raises ``ValueError`` on duplicate ids / alias collisions / lease collisions.
    """
    path = Path(path) if path is not None else _default_path()
    data = yaml.safe_load(path.read_text()) or {}
    fields: list[Field] = []
    for raw in data.get("fields", []):
        bsee = raw.get("bsee") or {}
        fields.append(
            Field(
                canonical_id=raw["canonical_id"],
                display_name=raw["display_name"],
                aliases=tuple(raw.get("aliases") or ()),
                region=raw.get("region", ""),
                play=raw.get("play", ""),
                area_blocks=tuple(bsee.get("area_blocks") or ()),
                leases=tuple(bsee.get("leases") or ()),
                bsee_block_note=raw.get("bsee_block_note", ""),
                fdp_slug=raw.get("fdp_slug"),
                surfaces=dict(raw.get("surfaces") or {}),
                tier=raw.get("tier"),
            )
        )
    return FieldsRegistry(
        fields=fields, unmapped_fdp_pages=list(data.get("unmapped_fdp_pages") or [])
    )
