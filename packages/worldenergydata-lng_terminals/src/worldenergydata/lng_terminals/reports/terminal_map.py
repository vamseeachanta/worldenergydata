"""Interactive global map of LNG terminals using Plotly."""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import REPORTS_DIR
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)

# Color mapping for terminal types
_TYPE_COLORS = {
    "onshore_export": "#e74c3c",  # Red
    "onshore_import": "#3498db",  # Blue
    "fsru": "#2ecc71",  # Green
    "flng": "#f39c12",  # Orange
    "onshore_liquefaction": "#9b59b6",  # Purple
}

# Symbol mapping for terminal status
_STATUS_SYMBOLS = {
    "operational": "circle",
    "under_construction": "diamond",
    "planned": "square",
    "proposed": "triangle-up",
    "decommissioned": "x",
    "mothballed": "triangle-down",
}


class TerminalMap:
    """Generate interactive Plotly map of LNG terminals."""

    def __init__(self, terminals: list[LNGTerminal]) -> None:
        self.terminals = [t for t in terminals if t.latitude and t.longitude]
        self._skipped = len(terminals) - len(self.terminals)
        if self._skipped:
            logger.warning(f"Skipped {self._skipped} terminals without coordinates")

    def generate(self, output_path: Path | None = None) -> Path:
        """Generate interactive HTML map.

        Args:
            output_path: Output file path. Defaults to reports dir.

        Returns:
            Path to generated HTML file.
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError(
                "plotly is required for map generation. "
                "Install with: pip install plotly"
            )

        if output_path is None:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = REPORTS_DIR / "terminal_map.html"

        fig = go.Figure()

        # Group by terminal type for color coding
        type_groups: dict[str, list[LNGTerminal]] = {}
        for t in self.terminals:
            key = t.terminal_type.value
            type_groups.setdefault(key, []).append(t)

        for ttype, group in sorted(type_groups.items()):
            lats = [t.latitude for t in group]
            lons = [t.longitude for t in group]
            texts = [
                f"<b>{t.terminal_name}</b><br>"
                f"Country: {t.country}<br>"
                f"Type: {t.terminal_type.value}<br>"
                f"Status: {t.status.value}<br>"
                f"Capacity: {t.capacity_mtpa or 'N/A'} MTPA<br>"
                f"Operator: {t.operator or 'N/A'}"
                for t in group
            ]
            sizes = [max(6, min(20, (t.capacity_mtpa or 1) * 0.5)) for t in group]

            fig.add_trace(
                go.Scattergeo(
                    lat=lats,
                    lon=lons,
                    text=texts,
                    hoverinfo="text",
                    mode="markers",
                    name=ttype.replace("_", " ").title(),
                    marker={
                        "size": sizes,
                        "color": _TYPE_COLORS.get(ttype, "#95a5a6"),
                        "opacity": 0.8,
                        "line": {"width": 0.5, "color": "black"},
                    },
                )
            )

        fig.update_layout(
            title="Global LNG Terminals",
            geo={
                "showland": True,
                "landcolor": "rgb(243, 243, 243)",
                "showocean": True,
                "oceancolor": "rgb(204, 229, 255)",
                "showcountries": True,
                "countrycolor": "rgb(204, 204, 204)",
                "projection_type": "natural earth",
            },
            height=700,
            margin={"l": 0, "r": 0, "t": 40, "b": 0},
        )

        fig.write_html(str(output_path), include_plotlyjs="cdn")
        logger.info(f"Map generated: {output_path} ({len(self.terminals)} terminals)")
        return output_path
