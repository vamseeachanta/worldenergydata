"""
ABOUTME: Interactive Gulf of Mexico field production map using Plotly scatter_mapbox.
ABOUTME: GomFieldMap renders field bubbles sized by cumulative production, colored by era.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import plotly.graph_objects as go


VALID_GEOLOGICAL_ERAS = frozenset(
    ["oligocene", "eocene", "paleocene", "miocene", "pliocene", "unknown"]
)

VALID_STATUSES = frozenset(["producing", "inactive", "decommissioned"])

VALID_COLOR_BY = frozenset(
    ["geological_era", "operator", "water_depth", "production"]
)

ERA_COLORS = {
    "oligocene": "#8B0000",
    "eocene": "#FF4500",
    "paleocene": "#FF8C00",
    "miocene": "#2E86AB",
    "pliocene": "#52B788",
    "unknown": "#9E9E9E",
}


@dataclass
class FieldMapConfig:
    color_by: str = "geological_era"
    size_by: str = "cumulative_oil_bbl"
    show_water_depth_contours: bool = False
    mapbox_style: str = "open-street-map"
    title: str = "Gulf of Mexico BSEE Field Production"


@dataclass
class FieldRecord:
    field_name: str
    lat: float
    lon: float
    water_depth_m: float
    geological_era: str
    operator: str
    cumulative_oil_bbl: float
    cumulative_gas_mcf: float
    peak_rate_bopd: float
    first_production_year: int
    status: str


# Built-in GoM field catalog (40+ fields)
_GOM_FIELD_CATALOG: list[dict] = [
    # Deep water (>300m) — Miocene era
    dict(field_name="Atlantis", lat=28.0, lon=-90.0, water_depth_m=2150,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=525_000_000,
         cumulative_gas_mcf=900_000_000, peak_rate_bopd=200_000,
         first_production_year=2007, status="producing"),
    dict(field_name="Thunder Horse", lat=28.2, lon=-88.5, water_depth_m=1850,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=710_000_000,
         cumulative_gas_mcf=1_200_000_000, peak_rate_bopd=250_000,
         first_production_year=2008, status="producing"),
    dict(field_name="Mars", lat=28.5, lon=-89.8, water_depth_m=900,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=950_000_000,
         cumulative_gas_mcf=2_000_000_000, peak_rate_bopd=220_000,
         first_production_year=1996, status="producing"),
    dict(field_name="Na Kika", lat=27.2, lon=-89.6, water_depth_m=2340,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=280_000_000,
         cumulative_gas_mcf=800_000_000, peak_rate_bopd=100_000,
         first_production_year=2003, status="producing"),
    dict(field_name="Auger", lat=27.1, lon=-91.9, water_depth_m=870,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=400_000_000,
         cumulative_gas_mcf=900_000_000, peak_rate_bopd=90_000,
         first_production_year=1994, status="producing"),
    dict(field_name="Ursa", lat=28.7, lon=-89.5, water_depth_m=1220,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=430_000_000,
         cumulative_gas_mcf=750_000_000, peak_rate_bopd=150_000,
         first_production_year=1999, status="producing"),
    dict(field_name="Holstein", lat=27.2, lon=-90.6, water_depth_m=1310,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=190_000_000,
         cumulative_gas_mcf=400_000_000, peak_rate_bopd=55_000,
         first_production_year=2004, status="producing"),
    dict(field_name="Shenzi", lat=27.0, lon=-91.3, water_depth_m=1335,
         geological_era="miocene", operator="BHP", cumulative_oil_bbl=310_000_000,
         cumulative_gas_mcf=500_000_000, peak_rate_bopd=100_000,
         first_production_year=2009, status="producing"),
    dict(field_name="Mad Dog", lat=27.5, lon=-91.0, water_depth_m=1370,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=360_000_000,
         cumulative_gas_mcf=600_000_000, peak_rate_bopd=130_000,
         first_production_year=2005, status="producing"),
    dict(field_name="Great White", lat=27.0, lon=-90.5, water_depth_m=2700,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=120_000_000,
         cumulative_gas_mcf=200_000_000, peak_rate_bopd=50_000,
         first_production_year=2010, status="producing"),
    # Lower Tertiary — Oligocene/Eocene/Paleocene
    dict(field_name="Tiber", lat=27.5, lon=-91.5, water_depth_m=1259,
         geological_era="eocene", operator="BP", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2099, status="inactive"),
    dict(field_name="Anchor", lat=27.0, lon=-90.0, water_depth_m=1524,
         geological_era="paleocene", operator="Chevron", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2024, status="producing"),
    dict(field_name="Cascade", lat=26.5, lon=-90.0, water_depth_m=2500,
         geological_era="oligocene", operator="Petrobras", cumulative_oil_bbl=65_000_000,
         cumulative_gas_mcf=120_000_000, peak_rate_bopd=35_000,
         first_production_year=2012, status="producing"),
    dict(field_name="Chinook", lat=26.4, lon=-89.9, water_depth_m=2560,
         geological_era="paleocene", operator="Murphy", cumulative_oil_bbl=45_000_000,
         cumulative_gas_mcf=90_000_000, peak_rate_bopd=25_000,
         first_production_year=2012, status="producing"),
    dict(field_name="Jack", lat=27.2, lon=-92.0, water_depth_m=2133,
         geological_era="eocene", operator="Chevron", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2016, status="inactive"),
    dict(field_name="St. Malo", lat=27.1, lon=-92.1, water_depth_m=2133,
         geological_era="paleocene", operator="Chevron", cumulative_oil_bbl=90_000_000,
         cumulative_gas_mcf=150_000_000, peak_rate_bopd=40_000,
         first_production_year=2014, status="producing"),
    dict(field_name="Buckskin", lat=27.3, lon=-91.8, water_depth_m=1830,
         geological_era="eocene", operator="Chevron", cumulative_oil_bbl=15_000_000,
         cumulative_gas_mcf=30_000_000, peak_rate_bopd=20_000,
         first_production_year=2019, status="producing"),
    dict(field_name="Moccasin", lat=27.6, lon=-91.6, water_depth_m=1860,
         geological_era="oligocene", operator="Chevron", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2099, status="inactive"),
    # Shelf / shallow — Pliocene / Miocene
    dict(field_name="Eugene Island", lat=28.5, lon=-91.5, water_depth_m=200,
         geological_era="pliocene", operator="Shell", cumulative_oil_bbl=600_000_000,
         cumulative_gas_mcf=5_000_000_000, peak_rate_bopd=60_000,
         first_production_year=1971, status="inactive"),
    dict(field_name="Ship Shoal", lat=28.8, lon=-91.0, water_depth_m=120,
         geological_era="pliocene", operator="W&T Offshore", cumulative_oil_bbl=450_000_000,
         cumulative_gas_mcf=3_500_000_000, peak_rate_bopd=50_000,
         first_production_year=1968, status="inactive"),
    dict(field_name="South Timbalier", lat=29.0, lon=-90.5, water_depth_m=90,
         geological_era="pliocene", operator="W&T Offshore", cumulative_oil_bbl=200_000_000,
         cumulative_gas_mcf=2_000_000_000, peak_rate_bopd=30_000,
         first_production_year=1965, status="decommissioned"),
    dict(field_name="East Cameron", lat=29.2, lon=-92.0, water_depth_m=60,
         geological_era="pliocene", operator="Talos Energy", cumulative_oil_bbl=150_000_000,
         cumulative_gas_mcf=1_500_000_000, peak_rate_bopd=20_000,
         first_production_year=1960, status="inactive"),
    dict(field_name="West Cameron", lat=29.3, lon=-92.5, water_depth_m=50,
         geological_era="pliocene", operator="Talos Energy", cumulative_oil_bbl=80_000_000,
         cumulative_gas_mcf=800_000_000, peak_rate_bopd=12_000,
         first_production_year=1958, status="decommissioned"),
    dict(field_name="Vermilion", lat=29.1, lon=-92.3, water_depth_m=80,
         geological_era="pliocene", operator="W&T Offshore", cumulative_oil_bbl=120_000_000,
         cumulative_gas_mcf=1_200_000_000, peak_rate_bopd=18_000,
         first_production_year=1962, status="inactive"),
    dict(field_name="Mississippi Canyon 20", lat=28.9, lon=-89.4, water_depth_m=350,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=75_000_000,
         cumulative_gas_mcf=150_000_000, peak_rate_bopd=30_000,
         first_production_year=1990, status="inactive"),
    dict(field_name="Green Canyon 18", lat=27.8, lon=-91.2, water_depth_m=600,
         geological_era="miocene", operator="ExxonMobil", cumulative_oil_bbl=90_000_000,
         cumulative_gas_mcf=200_000_000, peak_rate_bopd=40_000,
         first_production_year=1993, status="producing"),
    dict(field_name="Pompano", lat=28.4, lon=-88.9, water_depth_m=420,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=130_000_000,
         cumulative_gas_mcf=350_000_000, peak_rate_bopd=45_000,
         first_production_year=1994, status="producing"),
    dict(field_name="Brutus", lat=28.6, lon=-89.3, water_depth_m=910,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=115_000_000,
         cumulative_gas_mcf=280_000_000, peak_rate_bopd=48_000,
         first_production_year=2001, status="producing"),
    dict(field_name="Caesar", lat=27.9, lon=-90.3, water_depth_m=1645,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=55_000_000,
         cumulative_gas_mcf=100_000_000, peak_rate_bopd=30_000,
         first_production_year=2012, status="producing"),
    dict(field_name="Tonga", lat=27.8, lon=-90.1, water_depth_m=1220,
         geological_era="miocene", operator="Murphy", cumulative_oil_bbl=70_000_000,
         cumulative_gas_mcf=120_000_000, peak_rate_bopd=28_000,
         first_production_year=2011, status="producing"),
    dict(field_name="Kodiak", lat=27.3, lon=-90.7, water_depth_m=1400,
         geological_era="miocene", operator="BP", cumulative_oil_bbl=80_000_000,
         cumulative_gas_mcf=140_000_000, peak_rate_bopd=35_000,
         first_production_year=2010, status="producing"),
    dict(field_name="Kaskida", lat=27.6, lon=-91.2, water_depth_m=1800,
         geological_era="eocene", operator="BP", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2099, status="inactive"),
    dict(field_name="Heidelberg", lat=26.9, lon=-91.5, water_depth_m=1615,
         geological_era="miocene", operator="Anadarko", cumulative_oil_bbl=50_000_000,
         cumulative_gas_mcf=80_000_000, peak_rate_bopd=35_000,
         first_production_year=2016, status="producing"),
    dict(field_name="Lucius", lat=27.4, lon=-91.7, water_depth_m=2100,
         geological_era="miocene", operator="Anadarko", cumulative_oil_bbl=90_000_000,
         cumulative_gas_mcf=160_000_000, peak_rate_bopd=45_000,
         first_production_year=2015, status="producing"),
    dict(field_name="Gunflint", lat=28.3, lon=-88.7, water_depth_m=1820,
         geological_era="miocene", operator="Murphy", cumulative_oil_bbl=40_000_000,
         cumulative_gas_mcf=70_000_000, peak_rate_bopd=18_000,
         first_production_year=2016, status="producing"),
    dict(field_name="Marmalard", lat=28.8, lon=-89.1, water_depth_m=400,
         geological_era="miocene", operator="Murphy", cumulative_oil_bbl=30_000_000,
         cumulative_gas_mcf=60_000_000, peak_rate_bopd=12_000,
         first_production_year=2018, status="producing"),
    dict(field_name="Leon", lat=28.1, lon=-90.8, water_depth_m=1000,
         geological_era="miocene", operator="ExxonMobil", cumulative_oil_bbl=20_000_000,
         cumulative_gas_mcf=40_000_000, peak_rate_bopd=15_000,
         first_production_year=2017, status="producing"),
    dict(field_name="Constellation", lat=26.8, lon=-89.8, water_depth_m=2200,
         geological_era="oligocene", operator="ExxonMobil", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2099, status="inactive"),
    dict(field_name="Swordfish", lat=28.0, lon=-91.4, water_depth_m=1100,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=25_000_000,
         cumulative_gas_mcf=50_000_000, peak_rate_bopd=10_000,
         first_production_year=2014, status="producing"),
    dict(field_name="Vito", lat=28.4, lon=-89.7, water_depth_m=1200,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=60_000_000,
         cumulative_gas_mcf=100_000_000, peak_rate_bopd=30_000,
         first_production_year=2023, status="producing"),
    dict(field_name="Whale", lat=27.8, lon=-91.7, water_depth_m=3050,
         geological_era="miocene", operator="Shell", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2025, status="inactive"),
    dict(field_name="Sparta", lat=27.0, lon=-91.0, water_depth_m=1700,
         geological_era="eocene", operator="Equinor", cumulative_oil_bbl=0,
         cumulative_gas_mcf=0, peak_rate_bopd=0,
         first_production_year=2099, status="inactive"),
]


def _compute_bubble_sizes(
    fields: list[FieldRecord],
    size_by: str,
    min_size: float = 8.0,
    max_size: float = 60.0,
) -> list[float]:
    """Scale field attribute to bubble sizes in [min_size, max_size]."""
    if size_by == "uniform":
        return [20.0] * len(fields)

    attr_map = {
        "cumulative_oil_bbl": "cumulative_oil_bbl",
        "peak_rate": "peak_rate_bopd",
    }
    attr = attr_map.get(size_by, "cumulative_oil_bbl")
    values = [getattr(f, attr, 0) for f in fields]
    max_val = max(values) if values else 1
    if max_val == 0:
        return [min_size] * len(fields)
    return [
        min_size + (v / max_val) * (max_size - min_size)
        for v in values
    ]


def _get_color_sequence(fields: list[FieldRecord], color_by: str) -> list[str]:
    """Return a color string for each field based on color_by strategy."""
    if color_by == "geological_era":
        return [ERA_COLORS.get(f.geological_era, "#9E9E9E") for f in fields]
    if color_by == "water_depth":
        depths = [f.water_depth_m for f in fields]
        max_d = max(depths) if depths else 1
        return [
            f"rgb({int(30 + 200 * d / max_d)}, {int(100 - 80 * d / max_d)}, 200)"
            for d in depths
        ]
    if color_by == "production":
        vals = [f.cumulative_oil_bbl for f in fields]
        max_v = max(vals) if vals else 1
        return [
            f"rgb(200, {int(200 - 180 * v / max_v)}, 50)"
            for v in vals
        ]
    # operator: cycle through a palette
    operators = sorted({f.operator for f in fields})
    palette = [
        "#E63946", "#457B9D", "#2A9D8F", "#E9C46A",
        "#F4A261", "#264653", "#A8DADC", "#8338EC",
    ]
    op_color = {op: palette[i % len(palette)] for i, op in enumerate(operators)}
    return [op_color.get(f.operator, "#9E9E9E") for f in fields]


class GomFieldMap:
    """Interactive map of Gulf of Mexico BSEE field production data."""

    def __init__(self, config: FieldMapConfig = None):
        self.config = config or FieldMapConfig()

    def load_fields(self) -> list[FieldRecord]:
        """Return built-in catalog of 40+ GoM fields with coordinates."""
        return [FieldRecord(**entry) for entry in _GOM_FIELD_CATALOG]

    def plot(
        self,
        fields: list[FieldRecord] = None,
        config: FieldMapConfig = None,
    ) -> go.Figure:
        """Return Plotly Figure with scatter_mapbox bubble map."""
        cfg = config or self.config
        if fields is None:
            fields = self.load_fields()

        sizes = _compute_bubble_sizes(fields, cfg.size_by)
        colors = _get_color_sequence(fields, cfg.color_by)

        hover_texts = [
            (
                f"<b>{f.field_name}</b><br>"
                f"Operator: {f.operator}<br>"
                f"Era: {f.geological_era.capitalize()}<br>"
                f"Water depth: {f.water_depth_m:.0f} m<br>"
                f"Cum. oil: {f.cumulative_oil_bbl / 1e6:.1f} MMbbl<br>"
                f"Status: {f.status}"
            )
            for f in fields
        ]

        trace = go.Scattermap(
            lat=[f.lat for f in fields],
            lon=[f.lon for f in fields],
            mode="markers",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.8,
                sizemode="diameter",
            ),
            text=hover_texts,
            hoverinfo="text",
            name="GoM Fields",
        )

        fig = go.Figure(trace)
        fig.update_layout(
            title=cfg.title,
            map=dict(
                style=cfg.mapbox_style,
                center=dict(lat=27.5, lon=-90.5),
                zoom=5,
            ),
            margin=dict(l=0, r=0, t=40, b=0),
            height=700,
        )
        return fig

    def plot_production_timeline(
        self,
        field_name: str,
        production_df: pd.DataFrame = None,
    ) -> go.Figure:
        """Return Plotly time-series for a single field's production history."""
        if production_df is None:
            # Build a synthetic decline curve from catalog data
            fields = self.load_fields()
            match = next((f for f in fields if f.field_name == field_name), None)
            if match and match.first_production_year < 2050:
                start_year = match.first_production_year
            else:
                start_year = 2000
            peak = (match.peak_rate_bopd * 365 if match else 1_000_000)
            years = list(range(start_year, 2025))
            # Simple hyperbolic decline
            oil_values = [
                peak * (1 / (1 + 0.3 * i) ** 2)
                for i in range(len(years))
            ]
            production_df = pd.DataFrame({"year": years, "oil_bbl": oil_values})

        fig = go.Figure(
            go.Scatter(
                x=production_df["year"],
                y=production_df["oil_bbl"],
                mode="lines+markers",
                name=field_name,
                line=dict(width=2, color="#2E86AB"),
                marker=dict(size=6),
            )
        )
        fig.update_layout(
            title=f"{field_name} — Annual Production History",
            xaxis_title="Year",
            yaxis_title="Oil Production (bbl/year)",
            height=400,
        )
        return fig

    def export_html(self, fig: go.Figure, output_path: str) -> str:
        """Write standalone HTML file. Returns path."""
        if not output_path.endswith(".html"):
            output_path = output_path + ".html"
        fig.write_html(output_path, include_plotlyjs=True)
        return output_path

    def field_summary_table(self, fields: list[FieldRecord] = None) -> pd.DataFrame:
        """Return DataFrame with field, operator, era, cum_oil_mmbbl, status."""
        if fields is None:
            fields = self.load_fields()
        records = [
            {
                "field": f.field_name,
                "operator": f.operator,
                "era": f.geological_era,
                "cum_oil_mmbbl": round(f.cumulative_oil_bbl / 1e6, 2),
                "status": f.status,
            }
            for f in fields
        ]
        return pd.DataFrame(records)
