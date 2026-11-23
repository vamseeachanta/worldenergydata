"""Deduplicate LNG terminal records from multiple sources.

Matches on fuzzy name similarity, exact country match, and optional
coordinate proximity.  When duplicates are found the most complete
record (most non-None fields) is kept.
"""

from __future__ import annotations

import logging
import math
import re
import unicodedata

from ..config import get_config
from ..models.terminal import LNGTerminal

# Words stripped from names before comparison
_STRIP_WORDS = {
    "lng",
    "terminal",
    "liquefaction",
    "plant",
    "facility",
    "project",
    "regasification",
}

# Known aliases: canonical slug -> list of alternative name fragments
_MANUAL_ALIASES: dict[str, list[str]] = {
    "sabine-pass-lng": ["sabine pass", "sabine pass liquefaction"],
    "corpus-christi-lng": ["corpus christi", "corpus christi liquefaction"],
    "cameron-lng": ["cameron"],
    "ras-laffan": ["qatargas", "rasgas", "qatar lng"],
    "north-west-shelf": ["nws", "north west shelf lng", "karratha"],
    "nigeria-lng": ["nlng", "bonny island lng"],
    "bontang-lng": ["badak lng", "bontang"],
}

logger = logging.getLogger(__name__)


class Deduplicator:
    """Deduplicate LNG terminal records from multiple sources."""

    def __init__(self) -> None:
        config = get_config()
        self._threshold = config.processing.fuzzy_match_threshold
        self._proximity_km = config.processing.coordinate_proximity_km

    # -- Public API --------------------------------------------------------

    def deduplicate(self, terminals: list[LNGTerminal]) -> list[LNGTerminal]:
        """Remove duplicate terminal records.

        Groups terminals that likely refer to the same facility,
        then keeps the most complete record from each group.
        """
        if not terminals:
            return []

        groups: list[list[LNGTerminal]] = []

        for terminal in terminals:
            matched = False
            for group in groups:
                if self._is_duplicate(terminal, group[0]):
                    group.append(terminal)
                    matched = True
                    break
            if not matched:
                groups.append([terminal])

        results = []
        for group in groups:
            best = max(group, key=self._completeness_score)
            if len(group) > 1:
                logger.info(
                    "Merged %d records for '%s'",
                    len(group),
                    best.terminal_name,
                )
            results.append(best)

        logger.info(
            "Dedup: %d -> %d terminals (%d duplicates removed)",
            len(terminals),
            len(results),
            len(terminals) - len(results),
        )
        return results

    # -- Duplicate detection -----------------------------------------------

    def _is_duplicate(self, a: LNGTerminal, b: LNGTerminal) -> bool:
        """Check if two terminals refer to the same facility."""
        if a.country != b.country:
            return False

        name_a = self._normalize_name(a.terminal_name)
        name_b = self._normalize_name(b.terminal_name)

        # Don't merge when names differ only by a trailing number
        if self._differ_only_by_number(name_a, name_b):
            return False

        if self._alias_match(name_a, name_b):
            return True

        similarity = self._string_similarity(name_a, name_b)
        if similarity >= self._threshold:
            return True

        if all([a.latitude, a.longitude, b.latitude, b.longitude]):
            dist = self._haversine_km(
                a.latitude,
                a.longitude,
                b.latitude,
                b.longitude,
            )
            if dist < self._proximity_km and similarity > 0.5:
                return True

        return False

    # -- Name helpers ------------------------------------------------------

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize terminal name for comparison."""
        normalized = unicodedata.normalize("NFKD", name.lower())
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        words = ascii_only.split()
        words = [w for w in words if w not in _STRIP_WORDS]
        return " ".join(words).strip()

    @staticmethod
    def _alias_match(name_a: str, name_b: str) -> bool:
        """Check if names match via the manual alias table."""
        for canonical, aliases in _MANUAL_ALIASES.items():
            all_names = [canonical.replace("-", " ")] + aliases
            a_hit = any(name_a in alt or alt in name_a for alt in all_names)
            b_hit = any(name_b in alt or alt in name_b for alt in all_names)
            if a_hit and b_hit:
                return True
        return False

    @staticmethod
    def _differ_only_by_number(a: str, b: str) -> bool:
        """Return True when names are identical except for a trailing number.

        Examples that return True:
            "delfin flng vessel 2" vs "delfin flng vessel 3"
            "train 1" vs "train 2"
        """
        m_a = re.match(r"^(.+?)\s*(\d+)\s*$", a)
        m_b = re.match(r"^(.+?)\s*(\d+)\s*$", b)
        if m_a and m_b:
            base_a, num_a = m_a.group(1).rstrip(), m_a.group(2)
            base_b, num_b = m_b.group(1).rstrip(), m_b.group(2)
            if base_a == base_b and num_a != num_b:
                return True
        return False

    # -- String similarity -------------------------------------------------

    @staticmethod
    def _string_similarity(a: str, b: str) -> float:
        """Bigram Jaccard similarity between two strings.

        Returns a value between 0.0 and 1.0.
        """
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0

        def _bigrams(s: str) -> set[str]:
            return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}

        set_a = _bigrams(a)
        set_b = _bigrams(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    # -- Geo helpers -------------------------------------------------------

    @staticmethod
    def _haversine_km(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Haversine distance in km between two WGS-84 points."""
        R = 6371.0
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))

    # -- Scoring -----------------------------------------------------------

    @staticmethod
    def _completeness_score(terminal: LNGTerminal) -> int:
        """Count non-None fields as a proxy for record completeness."""
        score = 0
        for field_name in type(terminal).model_fields:
            value = getattr(terminal, field_name)
            if value is not None:
                score += len(value) if isinstance(value, list) else 1
        return score
