"""
Chart interaction components for interactive dashboard.

This module provides event handling for chart clicks, hovers, selections,
and context menus.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ChartInteractions:
    """Handle chart interaction events."""

    def __init__(self):
        """Initialize chart interactions."""
        self.selected_points = []
        self.hover_data = {}

    def handle_click(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle click events on charts."""
        if not event_data or "points" not in event_data:
            return {}

        point = event_data["points"][0]

        return {
            "well_id": point.get("customdata", ""),
            "date": point.get("x", ""),
            "value": point.get("y", 0),
            "series": point.get("curveNumber", 0),
        }

    def handle_hover(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hover events on charts."""
        if not event_data or "points" not in event_data:
            return {}

        point = event_data["points"][0]

        return {
            "tooltip": f"Value: {point.get('y', 0):.2f}",
            "x": point.get("x", ""),
            "y": point.get("y", 0),
        }

    def handle_selection(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle selection events on charts."""
        if not event_data or "points" not in event_data:
            return {"selected": []}

        selected = []
        for point in event_data["points"]:
            selected.append(
                {
                    "x": point.get("x", ""),
                    "y": point.get("y", 0),
                    "index": point.get("pointIndex", 0),
                }
            )

        self.selected_points = selected
        return {"selected": selected}

    def create_context_menu(self, menu_items: List[str]) -> Dict[str, Any]:
        """Create context menu for chart interactions."""
        return {
            "items": [
                {
                    "label": item,
                    "action": f'handle_{item.lower().replace(" ", "_")}',
                    "icon": self._get_menu_icon(item),
                }
                for item in menu_items
            ]
        }

    def _get_menu_icon(self, item: str) -> str:
        """Get icon for menu item."""
        icons = {
            "Export": "💾",
            "Zoom": "🔍",
            "Reset": "↺",
            "Filter": "🔽",
            "Settings": "⚙️",
        }
        return icons.get(item, "•")


# Export main components
__all__ = [
    "ChartInteractions",
]
