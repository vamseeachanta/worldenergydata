"""Stable source bindings and identity closure for portfolio cost maps."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel

from worldenergydata.cost.timeseries.portfolio_schema import (
    ProjectIdentity,
    ProjectSourceBinding,
)

PROJECT_SOURCE = Path("data/modules/cost/curated/sanctioned_projects.csv")
PROJECT_CROSSWALK = Path(
    "data/modules/cost/curated/portfolio_project_source_crosswalk.v2.csv"
)
PROJECT_IDENTITIES = Path("data/modules/cost/curated/portfolio_project_identity.v2.csv")
ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class ProjectIdentityResult:
    sources: tuple[ProjectSourceBinding, ...]
    identities: tuple[ProjectIdentity, ...]
    live_labels: frozenset[str]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _models(path: Path, model: type[ModelT]) -> tuple[ModelT, ...]:
    return tuple(model.model_validate(row) for row in _rows(path))


def _unique(values: Iterable[str], message: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise ValueError(message)


def _live_project_rows(root: Path) -> dict[str, dict[str, str]]:
    rows = _rows(root / PROJECT_SOURCE)
    live = {canonical_json({"PROJECT": row["PROJECT"]}): row for row in rows}
    if len(live) != len(rows):
        raise ValueError("live project locator collision")
    return live


def _validate_project_sources(
    sources: tuple[ProjectSourceBinding, ...], live: dict[str, dict[str, str]]
) -> None:
    _unique((row.source_project_key for row in sources), "duplicate source project key")
    _unique((row.locator_json for row in sources), "duplicate project locator")
    if {row.locator_json for row in sources if row.active} != set(live):
        raise ValueError("project source binding set does not equal live projects")
    for binding in sources:
        if digest_text(binding.locator_json) != binding.locator_sha256:
            raise ValueError("project locator hash mismatch")
        if (
            digest_text(canonical_json(live[binding.locator_json]))
            != binding.source_row_sha256
        ):
            raise ValueError("project source row hash mismatch")


def _validate_project_identities(
    identities: tuple[ProjectIdentity, ...], sources: tuple[ProjectSourceBinding, ...]
) -> None:
    source_by_key = {row.source_project_key: row for row in sources}
    _unique((row.project_id for row in identities), "duplicate project ID")
    _unique(
        (row.source_project_key for row in identities), "duplicate project source FK"
    )
    if {row.source_project_key for row in identities if row.active} != set(
        source_by_key
    ):
        raise ValueError("project identity set does not equal source bindings")
    for identity in identities:
        source = source_by_key[identity.source_project_key]
        label = json.loads(source.locator_json)["PROJECT"]
        if identity.display_label != label:
            raise ValueError("project identity label mismatch")
        if identity.created_source_sha256 != source.source_row_sha256:
            raise ValueError("project identity source hash mismatch")


def validate_project_identities(root: Path) -> ProjectIdentityResult:
    """Prove one stable active identity exists for each live project row."""

    live = _live_project_rows(root)
    sources = _models(root / PROJECT_CROSSWALK, ProjectSourceBinding)
    identities = _models(root / PROJECT_IDENTITIES, ProjectIdentity)
    _validate_project_sources(sources, live)
    _validate_project_identities(identities, sources)
    big_foot = next(row for row in identities if row.display_label == "Big Foot")
    if (big_foot.project_id, big_foot.source_project_key) != (
        "prj-000001",
        "src-prj-000001",
    ):
        raise ValueError("Big Foot project identity must remain stable")
    return ProjectIdentityResult(
        sources, identities, frozenset(row["PROJECT"] for row in live.values())
    )
