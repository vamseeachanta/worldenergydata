"""Extract explicit DP classes from directly labelled specification lines."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_LABEL = re.compile(r"^[ \t]*DP[ \t]+System(?:[ \t]*:[ \t]*|[ \t]+|$)(.*)$", re.I)
_TOKEN = re.compile(r"(?<![\w-])DP[ \t]*-?[ \t]*(\d+(?:[.,]\d+)?)(?!\w|[.,]\d)", re.I)
_SUPPORTED = {"1", "2", "3"}


def parse_spec_dp(text: str) -> dict[str, int]:
    """Return DP_CLASS only for one supported explicit same-line class.

    DP-3, DP 2 and DP1 are integer class tokens. Classification notation,
    model numbers, neighboring lines and unlabeled mentions provide no class
    evidence. Repeated agreeing statements are accepted; conflicting tokens
    are warned about and omitted. Unsupported tokens never imply class zero.
    """
    tokens: set[str] = set()
    for line in text.splitlines():
        match = _LABEL.match(line)
        if match:
            tokens.update(_TOKEN.findall(match.group(1)))

    if len(tokens) > 1:
        logger.warning("Conflicting DP System classes; DP_CLASS omitted")
        return {}
    if not tokens or not tokens.issubset(_SUPPORTED):
        return {}
    return {"DP_CLASS": int(next(iter(tokens)))}
