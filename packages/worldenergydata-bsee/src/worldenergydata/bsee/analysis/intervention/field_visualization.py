"""Field visualization module for interactive well maps and schematics (WRK-116 Phase 7).

Generates three visualization outputs from enriched WAR + borehole data:
1. Scattermapbox HTML map of well locations in the Gulf of Mexico
2. Scatter3d HTML showing subsurface well trajectories
3. SVG well casing schematics for individual wells
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from worldenergydata.bsee.data.utils.api_well_normalizer import select_by_api

# -- Color palette for activity categories ------------------------------------

_ACTIVITY_COLORS: dict[str, str] = {
    "drilling": "#1f77b4",  # blue
    "intervention": "#d62728",  # red
    "unknown": "#7f7f7f",  # gray
}

_RIG_TYPE_COLORS: dict[str, str] = {
    "drillship": "#1f77b4",
    "semi_submersible": "#ff7f0e",
    "jack_up": "#2ca02c",
    "wireline_unit": "#d62728",
    "coil_tubing_unit": "#9467bd",
    "lift_boat": "#8c564b",
    "platform_rig": "#e377c2",
    "workover_rig": "#bcbd22",
}


def _wrap_html(title: str, plotly_div: str) -> str:
    """Wrap a Plotly div in a standalone HTML page with CDN script."""
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{title}</title>"
        '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
        "</head><body>"
        f'<h1 style="text-align:center;font-family:sans-serif">{title}</h1>'
        f"{plotly_div}"
        "</body></html>"
    )


def _placeholder_html(title: str, message: str) -> str:
    """Return a placeholder HTML page with a message."""
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{title}</title>"
        "</head><body>"
        f'<h1 style="text-align:center;font-family:sans-serif">{title}</h1>'
        f'<p style="text-align:center;font-family:sans-serif;color:#888">'
        f"{message}</p>"
        "</body></html>"
    )


def _placeholder_svg(message: str) -> str:
    """Return a placeholder SVG with a centered message."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 1000"'
        ' width="600" height="1000">'
        '<rect width="600" height="1000" fill="#f5f5f5"/>'
        f'<text x="300" y="500" text-anchor="middle"'
        f' font-family="sans-serif" font-size="18" fill="#888">'
        f"{message}</text>"
        "</svg>"
    )


def _write(path: str, content: str) -> str:
    """Write content to path, creating parent dirs as needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
    return path


class FieldVisualizationModule:
    """Generate interactive field/lease visualizations."""

    def __init__(
        self,
        enriched_df: pd.DataFrame,
        well_design_data: dict | None = None,
        borehole_df: pd.DataFrame | None = None,
    ) -> None:
        self._enriched = enriched_df.copy()
        self._well_design = well_design_data
        self._borehole = borehole_df.copy() if borehole_df is not None else None

    # -- Public API -----------------------------------------------------------

    def generate_map(self, output_path: str) -> str:
        """Generate a Scattermapbox HTML map of well locations."""
        merged = self._merge_coordinates()
        if merged is None or merged.empty:
            html = _placeholder_html(
                "Well Location Map",
                "No coordinate data available for mapping.",
            )
            return _write(output_path, html)

        merged = merged.dropna(subset=["SURF_LATITUDE", "SURF_LONGITUDE"])
        if merged.empty:
            html = _placeholder_html(
                "Well Location Map",
                "No coordinate data available for mapping.",
            )
            return _write(output_path, html)

        colors = merged["ACTIVITY_CATEGORY"].map(
            lambda c: _ACTIVITY_COLORS.get(c, _ACTIVITY_COLORS["unknown"])
        )

        hover_parts = []
        for col, label in [
            ("API_WELL_NUMBER", "API"),
            ("BUS_ASC_NAME", "Operator"),
            ("RIG_TYPE", "Rig Type"),
            ("WATER_DEPTH", "Water Depth (ft)"),
            ("WELL_STATUS", "Status"),
        ]:
            if col in merged.columns:
                hover_parts.append(label + ": " + merged[col].astype(str))

        hover_text = hover_parts[0] if hover_parts else merged.index.astype(str)
        for part in hover_parts[1:]:
            hover_text = hover_text + "<br>" + part

        fig = go.Figure(
            go.Scattermap(
                lat=merged["SURF_LATITUDE"],
                lon=merged["SURF_LONGITUDE"],
                mode="markers",
                marker=dict(size=8, color=colors),
                text=hover_text,
                hoverinfo="text",
            )
        )
        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=27.5, lon=-90.0),
                zoom=5,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

        plotly_div = fig.to_html(full_html=False, include_plotlyjs=False)
        html = _wrap_html("Well Location Map", plotly_div)
        return _write(output_path, html)

    def generate_3d_view(self, output_path: str) -> str:
        """Generate a Scatter3d HTML showing subsurface well trajectories."""
        merged = self._merge_coordinates()
        required = [
            "SURF_LATITUDE",
            "SURF_LONGITUDE",
            "BH_TOTAL_MD",
            "WATER_DEPTH",
        ]
        if merged is None or merged.empty:
            html = _placeholder_html(
                "3D Subsurface View",
                "No 3D data available for visualization.",
            )
            return _write(output_path, html)

        # Keep rows with all required fields
        valid = merged.dropna(subset=required)
        if valid.empty:
            html = _placeholder_html(
                "3D Subsurface View",
                "No 3D data available for visualization.",
            )
            return _write(output_path, html)

        # De-duplicate to one row per well (take first occurrence)
        wells = valid.drop_duplicates(subset=["API_WELL_NUMBER"], keep="first")

        # Fill optional bottom-hole coordinates with surface if missing
        if "BOTM_LATITUDE" not in wells.columns:
            wells = wells.assign(BOTM_LATITUDE=wells["SURF_LATITUDE"])
        if "BOTM_LONGITUDE" not in wells.columns:
            wells = wells.assign(BOTM_LONGITUDE=wells["SURF_LONGITUDE"])
        wells["BOTM_LATITUDE"] = wells["BOTM_LATITUDE"].fillna(wells["SURF_LATITUDE"])
        wells["BOTM_LONGITUDE"] = wells["BOTM_LONGITUDE"].fillna(
            wells["SURF_LONGITUDE"]
        )

        traces = []
        for _, row in wells.iterrows():
            rig_type = row.get("RIG_TYPE", "unknown")
            color = _RIG_TYPE_COLORS.get(rig_type, "#7f7f7f")
            api = row["API_WELL_NUMBER"]
            total_md = float(row["BH_TOTAL_MD"])
            wd = float(row["WATER_DEPTH"])

            # Surface and bottom points
            x = [float(row["SURF_LONGITUDE"]), float(row["BOTM_LONGITUDE"])]
            y = [float(row["SURF_LATITUDE"]), float(row["BOTM_LATITUDE"])]
            z = [-wd, -total_md]

            traces.append(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="lines+markers",
                    line=dict(color=color, width=4),
                    marker=dict(size=3, color=color),
                    name=f"{api} ({rig_type})",
                    hovertext=[
                        f"{api}<br>Surface<br>WD: {wd:.0f} ft",
                        f"{api}<br>TD: {total_md:.0f} ft",
                    ],
                    hoverinfo="text",
                )
            )

        fig = go.Figure(data=traces)
        fig.update_layout(
            scene=dict(
                xaxis_title="Longitude",
                yaxis_title="Latitude",
                zaxis_title="Depth (ft, negative)",
                zaxis=dict(autorange="reversed"),
            ),
            margin=dict(l=0, r=0, t=40, b=0),
            showlegend=True,
        )

        plotly_div = fig.to_html(full_html=False, include_plotlyjs=False)
        html = _wrap_html("3D Subsurface View", plotly_div)
        return _write(output_path, html)

    def generate_well_schematic(self, api_well_number: str, output_path: str) -> str:
        """Generate an SVG well casing schematic for a single well."""
        well_info = self._get_well_info(api_well_number)
        if well_info is None:
            svg = _placeholder_svg(f"No data available for {api_well_number}")
            return _write(output_path, svg)

        water_depth = well_info.get("water_depth", 0.0)
        total_depth = well_info.get("total_depth", 0.0)
        casing_data = well_info.get("casing_data")

        svg = self._build_svg(api_well_number, water_depth, total_depth, casing_data)
        return _write(output_path, svg)

    # -- Private helpers ------------------------------------------------------

    def _merge_coordinates(self) -> pd.DataFrame | None:
        """Merge enriched_df with borehole_df on API_WELL_NUMBER."""
        if self._borehole is None or self._borehole.empty:
            return None
        if self._enriched.empty:
            return None

        coord_cols = ["API_WELL_NUMBER"]
        for col in [
            "SURF_LATITUDE",
            "SURF_LONGITUDE",
            "BOTM_LATITUDE",
            "BOTM_LONGITUDE",
            "BH_TOTAL_MD",
            "WELL_BORE_TVD",
            "WATER_DEPTH",
        ]:
            if col in self._borehole.columns:
                coord_cols.append(col)

        bh = self._borehole[coord_cols].copy()
        # Avoid column clash on WATER_DEPTH -- prefer borehole version
        if "WATER_DEPTH" in bh.columns and "WATER_DEPTH" in self._enriched.columns:
            bh = bh.rename(columns={"WATER_DEPTH": "BH_WATER_DEPTH"})

        merged = self._enriched.merge(bh, on="API_WELL_NUMBER", how="inner")
        # Resolve water depth: prefer enriched, fall back to borehole
        if "WATER_DEPTH" in merged.columns and "BH_WATER_DEPTH" in merged.columns:
            merged["WATER_DEPTH"] = merged["WATER_DEPTH"].fillna(
                merged["BH_WATER_DEPTH"]
            )
        elif "BH_WATER_DEPTH" in merged.columns:
            merged["WATER_DEPTH"] = merged["BH_WATER_DEPTH"]

        return merged

    def _get_well_info(self, api: str) -> dict | None:
        """Gather well information from all available sources."""
        # Check borehole data first
        bh_row = None
        if self._borehole is not None and "API_WELL_NUMBER" in self._borehole.columns:
            match = select_by_api(self._borehole, api)
            if not match.empty:
                bh_row = match.iloc[0]

        # Check enriched data
        enr_row = None
        if "API_WELL_NUMBER" in self._enriched.columns:
            match = select_by_api(self._enriched, api)
            if not match.empty:
                enr_row = match.iloc[0]

        if bh_row is None and enr_row is None:
            return None

        water_depth = 0.0
        total_depth = 0.0

        if bh_row is not None:
            wd = bh_row.get("WATER_DEPTH")
            if pd.notna(wd):
                water_depth = float(wd)
            td = bh_row.get("BH_TOTAL_MD")
            if pd.notna(td):
                total_depth = float(td)

        if water_depth == 0.0 and enr_row is not None:
            wd = enr_row.get("WATER_DEPTH")
            if pd.notna(wd):
                water_depth = float(wd)

        # Look up casing data from well_design_data
        casing_data = None
        if self._well_design and "casing_program" in self._well_design:
            cp = self._well_design["casing_program"]
            if isinstance(cp, dict) and "by_interval_type" in cp:
                casing_data = cp

        return {
            "water_depth": water_depth,
            "total_depth": total_depth,
            "casing_data": casing_data,
        }

    def _build_svg(
        self,
        api: str,
        water_depth: float,
        total_depth: float,
        casing_data: dict | None,
    ) -> str:
        """Build an SVG well schematic string."""
        vb_w, vb_h = 600, 1000
        margin_top, margin_bottom = 80, 40
        margin_left, margin_right = 100, 50
        draw_h = vb_h - margin_top - margin_bottom
        draw_w = vb_w - margin_left - margin_right

        # Scale: map depth range [0, max_depth] to [margin_top, margin_top+draw_h]
        max_depth = max(total_depth, water_depth, 1.0)

        def y_of(depth: float) -> float:
            return margin_top + (depth / max_depth) * draw_h

        center_x = margin_left + draw_w / 2
        bore_half_w = 15

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {vb_w} {vb_h}" '
            f'width="{vb_w}" height="{vb_h}">'
        )
        # Background
        parts.append(f'<rect width="{vb_w}" height="{vb_h}" fill="#fafafa"/>')

        # Title
        parts.append(
            f'<text x="{vb_w / 2}" y="30" text-anchor="middle" '
            f'font-family="sans-serif" font-size="16" font-weight="bold">'
            f"Well Schematic: {api}</text>"
        )

        # Water column (blue rectangle)
        if water_depth > 0:
            wd_y = y_of(water_depth)
            parts.append(
                f'<rect x="{margin_left}" y="{margin_top}" '
                f'width="{draw_w}" height="{wd_y - margin_top}" '
                f'fill="#cce5ff" opacity="0.5"/>'
            )
            parts.append(
                f'<text x="{margin_left - 10}" y="{wd_y}" '
                f'text-anchor="end" font-family="sans-serif" font-size="11" '
                f'fill="#0066cc">{water_depth:.0f} ft (WD)</text>'
            )

        # Wellbore line (surface to TD)
        if total_depth > 0:
            td_y = y_of(total_depth)
            parts.append(
                f'<line x1="{center_x}" y1="{margin_top}" '
                f'x2="{center_x}" y2="{td_y}" '
                f'stroke="#333" stroke-width="3"/>'
            )
            parts.append(
                f'<text x="{margin_left - 10}" y="{td_y}" '
                f'text-anchor="end" font-family="sans-serif" font-size="11" '
                f'fill="#333">{total_depth:.0f} ft (TD)</text>'
            )

        # Depth scale on left
        tick_interval = self._tick_interval(max_depth)
        depth = tick_interval
        while depth < max_depth:
            ty = y_of(depth)
            parts.append(
                f'<line x1="{margin_left - 5}" y1="{ty}" '
                f'x2="{margin_left}" y2="{ty}" stroke="#999" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{margin_left - 8}" y="{ty + 4}" '
                f'text-anchor="end" font-family="sans-serif" font-size="9" '
                f'fill="#999">{depth:.0f}</text>'
            )
            depth += tick_interval

        # Casing strings (if design data available)
        if casing_data is not None:
            self._draw_casing(parts, casing_data, center_x, bore_half_w, y_of)

        # Depth labels summary at bottom
        parts.append(
            f'<text x="{vb_w / 2}" y="{vb_h - 15}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11" fill="#666">'
            f"Water Depth: {water_depth:.0f} ft | "
            f"Total Depth: {total_depth:.0f} ft</text>"
        )

        parts.append("</svg>")
        return "\n".join(parts)

    @staticmethod
    def _tick_interval(max_depth: float) -> float:
        """Choose a readable tick interval for the depth scale."""
        if max_depth <= 1000:
            return 200.0
        if max_depth <= 5000:
            return 1000.0
        if max_depth <= 20000:
            return 5000.0
        return 10000.0

    @staticmethod
    def _draw_casing(
        parts: list[str],
        casing_data: dict,
        center_x: float,
        bore_half_w: float,
        y_of,
    ) -> None:
        """Draw casing strings as nested rectangles (best-effort)."""
        by_interval = casing_data.get("by_interval_type")
        if by_interval is None or not isinstance(by_interval, pd.DataFrame):
            return
        if by_interval.empty:
            return

        # Simple representation: draw concentric rectangles
        depth_stats = casing_data.get("depth_stats", {})
        max_setting = depth_stats.get("max_setting_depth", 0.0)
        if max_setting <= 0:
            return

        # Draw a single representative casing outline
        casing_y = y_of(max_setting)
        top_y = y_of(0)
        half_w = bore_half_w + 8
        parts.append(
            f'<rect x="{center_x - half_w}" y="{top_y}" '
            f'width="{half_w * 2}" height="{casing_y - top_y}" '
            f'fill="none" stroke="#666" stroke-width="2" '
            f'stroke-dasharray="6,3"/>'
        )
