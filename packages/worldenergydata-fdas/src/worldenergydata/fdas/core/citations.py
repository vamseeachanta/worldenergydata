"""Explicit royalty inputs using the calculation-output citation contract v1.

No statutory or lease-specific rate is supplied by this module. A caller owns
the source selection and applicability decision; resolution verifies metadata
and the stated fraction, not the legal interpretation of a source document.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from pathlib import Path

import yaml


class CitationResolutionError(ValueError):
    """Evidence cannot be resolved; the source identifier is always reported."""

    def __init__(self, code_id: str, reason: str):
        super().__init__(f"{code_id}: {reason}")
        self.code_id = code_id
        self.reason = reason


@dataclass(frozen=True)
class Citation:
    """Sidecar identity matching the v1 calculation-output citation contract."""

    code_id: str
    publisher: str
    revision: str
    section: str
    wiki_path: str
    note: str = ""
    source_sibling: str = "generic"
    source_project: str | None = None

    def __post_init__(self):
        for field in (
            "code_id",
            "publisher",
            "revision",
            "section",
            "wiki_path",
            "source_sibling",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a nonempty string")
        if self.source_project is not None and (
            not isinstance(self.source_project, str) or not self.source_project.strip()
        ):
            raise ValueError("source_project must be a nonempty string or None")
        segments = self.wiki_path.split("/")
        if (
            not self.wiki_path.startswith("wikis/")
            or "\\" in self.wiki_path
            or any(part in ("", ".", "..", "sources") for part in segments)
        ):
            raise ValueError("wiki_path must identify a nonsource page under wikis/")


def _read_evidence(citation: Citation, wiki_root: Path) -> dict:
    """Resolve only within the explicitly supplied root, including symlinks."""
    try:
        root = Path(wiki_root).resolve()
        page = (root / citation.wiki_path).resolve()
        if not page.is_relative_to(root):
            raise ValueError("outside_root")
        if "sources" in page.relative_to(root).parts:
            raise ValueError("source_page")
        lines = page.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != "---":
            raise ValueError("frontmatter_missing")
        end = lines.index("---", 1)
        frontmatter = "\n".join(lines[1:end])
        node = yaml.compose(frontmatter)
        if not isinstance(node, yaml.MappingNode):
            raise TypeError("frontmatter_not_mapping")
        if any(not isinstance(key, yaml.ScalarNode) for key, _ in node.value):
            raise ValueError("frontmatter_nonscalar_key")
        keys = [key.value for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError("frontmatter_duplicate_key")
        metadata = yaml.safe_load(frontmatter)
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
        yaml.YAMLError,
    ) as exc:
        # Do not leak the resolved filesystem path through the public error.
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        raise CitationResolutionError(citation.code_id, reason) from None
    for field in (
        "code_id",
        "publisher",
        "revision",
        "source_sibling",
        "source_project",
    ):
        if metadata.get(field) != getattr(citation, field):
            raise CitationResolutionError(
                citation.code_id, f"frontmatter_mismatch:{field}"
            )
    return metadata


@dataclass(frozen=True)
class CitedRoyalty:
    """Required fraction of gross revenue, bound to caller-selected evidence."""

    rate: float
    citation: Citation

    def __post_init__(self):
        # A dimensionless fraction lies in [0, 1]; these are domain boundaries.
        if (
            isinstance(self.rate, bool)
            or not isinstance(self.rate, Real)
            or not isfinite(self.rate)
            or not 0 <= self.rate <= 1
        ):
            raise ValueError("royalty rate must be a finite fraction in [0, 1]")
        if not isinstance(self.citation, Citation):
            raise TypeError("citation must be a Citation")

    def validate(self, wiki_root: Path) -> None:
        """Fail closed on missing, mismatched or ambiguous rate evidence."""
        metadata = _read_evidence(self.citation, wiki_root)
        value = metadata.get("royalty_rate")
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(value)
            or value != self.rate
        ):
            raise CitationResolutionError(
                self.citation.code_id, "royalty_rate_mismatch"
            )
