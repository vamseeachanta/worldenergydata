"""LNG Terminals Module - Global LNG terminal dataset with engineering design data."""

__version__ = "1.0.0"

from worldenergydata.lng_terminals.query import (
    LngTerminalClient,
    LngTerminalQuery,
    LngTerminalResult,
)

__all__ = [
    "LngTerminalClient",
    "LngTerminalQuery",
    "LngTerminalResult",
]
