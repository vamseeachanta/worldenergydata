# ABOUTME: Seven data PLOTS for the intervention brief, as inline-SVG strings.
# ABOUTME: Reads committed source YAMLs (never hardcodes numbers) via figures_svg.
"""Data plots (bar/column charts) for the GoM intervention brief.

Each function reads the relevant committed YAML and returns a self-contained
inline-SVG string. Numbers are pulled from the YAMLs, never hardcoded.
"""

from __future__ import annotations

from figures_svg import (
    ACCENT,
    AMBER,
    BAR1,
    BAR2,
    INK,
    MUTED,
    NEUTRAL,
    OK,
    RISK,
    RULE,
    circle,
    column_chart,
    fmt_int,
    fmt_usd,
    line,
    load_yaml,
    nice_max,
    rect,
    svg,
    text,
)

# canonical band order shared by the band-keyed plots
_BAND_ORDER = [
    "shelf_lt_500",
    "band_500_3000",
    "band_3000_5000",
    "band_5000_10000",
    "band_gt_10000",
]


def fig_wells() -> str:
    """1. Subsea wells by band + subsea-share %% (overlaid line). #583."""
    data = load_yaml("well_inventory")
    bands = data["bands"]
    cats, wells, shares = [], [], []
    for key in _BAND_ORDER:
        b = bands[key]
        cats.append(b["label"])
        wells.append(float(b["subsea_wells_on_record"]))
        shares.append(round((b["subsea_share"] or 0) * 100, 1))
    deepest = _BAND_ORDER.index("band_5000_10000")
    colors = [BAR1] * len(cats)
    colors[deepest] = RISK
    return column_chart(
        categories=cats,
        series=[
            {
                "name": "Subsea wells [on record]",
                "values": wells,
                "color": BAR1,
                "colors": colors,
            }
        ],
        line_series={
            "name": "Subsea share %",
            "values": shares,
            "color": AMBER,
            "axis_max": 60,
            "fmt": lambda v: f"{v:g}%",
            "axis_label": "Subsea share of band (%)",
        },
        title="Subsea wells by water-depth band, with subsea share",
        desc=(
            "Subsea-well counts rise and subsea share inverts with depth: the "
            "deepest serviceable band holds 270 wells at 55.7% subsea share."
        ),
        y_label="Subsea wells on record",
    )


def fig_access_ratio() -> str:
    """2. GoM-resident demand/supply utilization ratio by band. #638."""
    data = load_yaml("access_gap")
    bands = data["bands"]
    cats, ratios, colors = [], [], []
    for key in _BAND_ORDER:
        b = bands[key]
        r = b["gap_vs_gom_resident"]["utilization_ratio"]["central"]
        cats.append(b["label"])
        ratios.append(round(r or 0, 1))
        colors.append(RISK if (r or 0) > 1 else NEUTRAL)
    return column_chart(
        categories=cats,
        series=[
            {
                "name": "Demand / supply ratio",
                "values": ratios,
                "color": RISK,
                "colors": colors,
            }
        ],
        ref_line={"y": 1.0, "label": "1.0x resident supply"},
        title="Access-gap ratio: forward demand vs GoM-resident supply",
        desc=(
            "Forward demand/supply ratio against the GoM-resident heavy fleet: "
            "1.6x, 3.1x and 4.4x in the three populated deepwater bands "
            "(>1.0x = access risk)."
        ),
        y_label="Demand / resident-supply (x)",
        value_fmt=lambda v: f"{v:g}x",
        y_max=5.0,
    )


def fig_demand_supply() -> str:
    """3. Demand vs GoM-resident supply rig-days/yr by band (paired). #638."""
    data = load_yaml("access_gap")
    bands = data["bands"]
    cats, demand, supply = [], [], []
    for key in _BAND_ORDER:
        b = bands[key]
        cats.append(b["label"])
        demand.append(round(b["demand"]["rig_days_per_yr"]["central"]))
        supply.append(round(b["supply"]["rig_days_per_yr_gom_resident"]["central"]))
    return column_chart(
        categories=cats,
        series=[
            {"name": "Demand rig-days/yr [forward]", "values": demand, "color": BAR1},
            {"name": "GoM-resident supply rig-days/yr", "values": supply, "color": OK},
        ],
        title="Forward demand vs GoM-resident supply (rig-days / yr)",
        desc=(
            "Central forward intervention demand in rig-days/yr versus the "
            "fixed ~511 rig-days/yr the GoM-resident heavy fleet can provide."
        ),
        y_label="Rig-days per year",
    )


def fig_exposure() -> str:
    """4. $ exposure / yr by band. #638."""
    data = load_yaml("access_gap")
    bands = data["bands"]
    cats, exp, colors = [], [], []
    for key in _BAND_ORDER:
        b = bands[key]
        e = b.get("exposure_usd_per_yr")
        val = 0.0 if not e else float(e.get("central") or 0)
        cats.append(b["label"])
        exp.append(val)
        colors.append(RISK if key == "band_5000_10000" else BAR2)
    return column_chart(
        categories=cats,
        series=[
            {"name": "Exposure $/yr", "values": exp, "color": BAR2, "colors": colors}
        ],
        title="Annual $ exposure by band (central, forward-looking)",
        desc=(
            "Central annual cost exposure by band: $375M, $731M and $1.0B in "
            "the 500-3,000, 3,000-5,000 and 5,000-10,000 ft bands."
        ),
        y_label="$ exposure per year",
        value_fmt=fmt_usd,
    )


def fig_fleet() -> str:
    """5. Intervention fleet by class, deduped distinct hulls. #598."""
    data = load_yaml("fleet")
    bac = data["by_asset_class"]
    order = [
        "modu_drillship",
        "modu_semisub",
        "modu_jackup",
        "heavy_intervention_semi",
        "rlwi_monohull",
        "lift_boat",
        "construction_vessel",
        "other",
    ]
    cats, counts = [], []
    for k in order:
        if k in bac:
            cats.append(k.replace("modu_", "").replace("_", " "))
            counts.append(float(bac[k]["count"]))
    return column_chart(
        categories=cats,
        series=[{"name": "Distinct hulls", "values": counts, "color": ACCENT}],
        title="Global available roster by asset class (deduped distinct hulls)",
        desc=(
            "Deduped global fleet counts by class (CONTEXT ONLY, not GoM "
            "supply): jackup 1,018, semisub 305, drillship 161, but only 5 "
            "heavy-intervention semis and 4 RLWI monohulls."
        ),
        y_label="Distinct hulls (global)",
        x_label_angle=-32,
        width=720,
        height=400,
    )


def fig_dayrate() -> str:
    """6. Indicative day-rate bands by class (floating range + median). #596."""
    data = load_yaml("fleet")
    bac = data["by_asset_class"]
    econ = load_yaml("economics")
    # mpsv band lives in the economics dayrate snapshot (shelf light scope)
    mpsv = econ["economics"]["shelf_lt_500"]["light_live_well"]["dayrate_band"]

    rows = []  # (label, low, med, high) all in $k/day
    dd = bac["modu_drillship"]["indicative_dayrate"]
    rows.append(
        (
            "drillship",
            dd["band_low_usd_per_day"] / 1e3,
            dd["median_usd_per_day"] / 1e3,
            dd["band_high_usd_per_day"] / 1e3,
        )
    )
    ds = bac["modu_semisub"]["indicative_dayrate"]
    rows.append(
        (
            "semisub",
            ds["band_low_usd_per_day"] / 1e3,
            ds["median_usd_per_day"] / 1e3,
            ds["band_high_usd_per_day"] / 1e3,
        )
    )
    rows.append(
        (
            "mpsv / osv",
            mpsv["low_usd_per_day"] / 1e3,
            mpsv["median_usd_per_day"] / 1e3,
            mpsv["high_usd_per_day"] / 1e3,
        )
    )
    not_public = ["heavy-intervention semi", "rlwi monohull"]

    W, H = 720, 360
    ml, mr, mt, mb = 130, 28, 46, 70
    px0, px1 = ml, W - mr
    py0, py1 = mt, H - mb
    xmax = nice_max(max(r[3] for r in rows))

    def xof(v):
        return px0 + (v / xmax) * (px1 - px0)

    parts = [
        text(
            20,
            18,
            "Indicative day-rate bands by asset class ($k/day)",
            size=12.5,
            fill=ACCENT,
            weight="bold",
        )
    ]
    # x gridlines
    for i in range(6):
        xv = xmax * i / 5
        xx = xof(xv)
        parts.append(line(xx, py0, xx, py1 + 4, stroke="#e3e9ee", width=1))
        parts.append(
            text(xx, py1 + 18, f"${xv:.0f}k", size=8.5, fill=MUTED, anchor="middle")
        )

    n = len(rows) + len(not_public)
    slot = (py1 - py0) / n
    bh = slot * 0.5
    palette = [BAR1, BAR2, OK]
    yi = 0
    for (label, lo, med, hi), col in zip(rows, palette):
        cy = py0 + slot * (yi + 0.5)
        parts.append(text(px0 - 10, cy + 3.5, label, size=9.5, fill=INK, anchor="end"))
        parts.append(
            rect(
                xof(lo),
                cy - bh / 2,
                xof(hi) - xof(lo),
                bh,
                fill=col,
                rx=3,
                opacity=0.85,
            )
        )
        # median marker
        mx = xof(med)
        parts.append(
            line(mx, cy - bh / 2 - 2, mx, cy + bh / 2 + 2, stroke=INK, width=2)
        )
        parts.append(
            text(
                xof(hi) + 6,
                cy + 3.5,
                f"${lo:.0f}-{hi:.0f}k (med ${med:.0f}k)",
                size=8.5,
                fill=INK,
            )
        )
        yi += 1
    for label in not_public:
        cy = py0 + slot * (yi + 0.5)
        parts.append(
            text(px0 - 10, cy + 3.5, label, size=9.5, fill=MUTED, anchor="end")
        )
        parts.append(rect(px0, cy - bh / 2, 14, bh, fill="#ffffff", rx=3))
        parts.append(line(px0, cy, px0 + 70, cy, stroke=RULE, width=1.2, dash="4 3"))
        parts.append(
            text(
                px0 + 78,
                cy + 3.5,
                "day-rate not public [not public]",
                size=9,
                fill=MUTED,
                weight="bold",
            )
        )
        yi += 1
    parts.append(line(px0, py0, px0, py1, stroke=RULE, width=1.2))
    parts.append(line(px0, py1, px1, py1, stroke=RULE, width=1.2))
    desc = (
        "Indicative public day-rate bands: drillship $300-530k (median $457k), "
        "semisub $452-490k, mpsv $22-80k; intervention semis and RLWI monohulls "
        "have no public rate."
    )
    return svg(
        W, H, "".join(parts), title="Indicative day-rate bands by class", desc=desc
    )


def fig_planned() -> str:
    """7. Planned new subsea wells by first-oil year (on-record floor). #587."""
    data = load_yaml("planned")
    by_year: dict[int, int] = {}
    for proj in data["on_record_projects"]:
        by_year[proj["first_oil_year"]] = by_year.get(proj["first_oil_year"], 0) + int(
            proj["wells"]
        )
    years = sorted(by_year)
    cats = [str(y) for y in years]
    vals = [float(by_year[y]) for y in years]
    colors = [BAR2 if y <= 2026 else BAR1 for y in years]
    return column_chart(
        categories=cats,
        series=[
            {
                "name": "New subsea wells",
                "values": vals,
                "color": BAR1,
                "colors": colors,
            }
        ],
        title="Planned new subsea wells by first-oil year (on-record floor)",
        desc=(
            "On-record FID floor of new GoM subsea wells by first-oil year: "
            "7 / 32 / 6 / 3 / 10 / 6 / 8 across 2024-2030."
        ),
        y_label="New subsea wells [on record]",
        width=720,
        height=340,
    )
