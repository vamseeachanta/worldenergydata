"""
ABOUTME: Folium-based alternative map for GoM fields (Leaflet backend).
ABOUTME: FoliumGomMap produces a Leaflet HTML map with CircleMarker bubbles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from worldenergydata.bsee.visualization.field_map import FieldRecord


def _scale_radius(
    value: float, max_value: float, min_r: float = 4, max_r: float = 30
) -> float:
    """Scale a production value to a circle radius."""
    if max_value <= 0:
        return min_r
    return min_r + (value / max_value) * (max_r - min_r)


_ERA_COLORS = {
    "oligocene": "#8B0000",
    "eocene": "#FF4500",
    "paleocene": "#FF8C00",
    "miocene": "#2E86AB",
    "pliocene": "#52B788",
    "unknown": "#9E9E9E",
}


class FoliumGomMap:
    """Leaflet-based interactive map of GoM fields using Folium."""

    def plot(self, fields: list[FieldRecord] = None) -> object:
        """Return folium.Map object. Falls back gracefully if folium not installed."""
        try:
            import folium
        except ImportError:
            return None

        if fields is None:
            from worldenergydata.bsee.visualization.field_map import GomFieldMap

            fields = GomFieldMap().load_fields()

        fmap = folium.Map(location=[27.5, -90.5], zoom_start=6, tiles="OpenStreetMap")

        max_oil = max((f.cumulative_oil_bbl for f in fields), default=1) or 1

        for f in fields:
            radius = _scale_radius(f.cumulative_oil_bbl, max_oil)
            color = _ERA_COLORS.get(f.geological_era, "#9E9E9E")
            popup_html = (
                f"<b>{f.field_name}</b><br>"
                f"Operator: {f.operator}<br>"
                f"Era: {f.geological_era.capitalize()}<br>"
                f"Water depth: {f.water_depth_m:.0f} m<br>"
                f"Cum. oil: {f.cumulative_oil_bbl / 1e6:.1f} MMbbl<br>"
                f"Status: {f.status}"
            )
            folium.CircleMarker(
                location=[f.lat, f.lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f.field_name,
            ).add_to(fmap)

        return fmap

    def export_html(self, folium_map, output_path: str) -> str:
        """Write HTML file. Returns path."""
        if not output_path.endswith(".html"):
            output_path = output_path + ".html"
        folium_map.save(output_path)
        return output_path
