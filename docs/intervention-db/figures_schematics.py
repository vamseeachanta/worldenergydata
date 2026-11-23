# ABOUTME: Two hand-built concept SCHEMATICS for the intervention brief (inline SVG).
# ABOUTME: Depth-band serviceability cross-section + riser-vs-riserless concept.
"""Hand-built SVG schematics for the GoM intervention brief.

Pure vector markup, grounded in the committed YAMLs (band depths, asset
water-depth ratings, GoM-resident counts). No external assets.
"""

from __future__ import annotations

from figures_svg import (
    ACCENT,
    AMBER,
    BAR1,
    BAR2,
    INK,
    MUTED,
    OK,
    RISK,
    RULE,
    circle,
    line,
    load_yaml,
    rect,
    svg,
    text,
)

_SEA = "#cfe2ef"
_SEABED = "#caa874"
_HULL = "#23323f"


def _vessel(
    cx: float, deck_y: float, w: float, label: str = "", fill: str = _HULL
) -> str:
    """A small surface-vessel glyph centred on cx with deck at deck_y."""
    hw = w / 2
    hull = (
        f'<path d="M {cx - hw:.1f} {deck_y:.1f} '
        f"L {cx + hw:.1f} {deck_y:.1f} "
        f"L {cx + hw * 0.7:.1f} {deck_y + 12:.1f} "
        f'L {cx - hw * 0.7:.1f} {deck_y + 12:.1f} Z" fill="{fill}"/>'
    )
    derrick = (
        f'<path d="M {cx - 7:.1f} {deck_y:.1f} L {cx:.1f} {deck_y - 18:.1f} '
        f'L {cx + 7:.1f} {deck_y:.1f}" fill="none" stroke="{fill}" stroke-width="2"/>'
    )
    out = hull + derrick
    if label:
        out += text(
            cx, deck_y - 23, label, size=9, fill=INK, anchor="middle", weight="bold"
        )
    return out


def _tree(cx: float, bed_y: float, fill: str = BAR1, label: str = "") -> str:
    """A subsea tree glyph sitting on the seabed at bed_y."""
    out = rect(cx - 9, bed_y - 12, 18, 12, fill=fill, rx=2)
    out += rect(cx - 4, bed_y - 18, 8, 6, fill=fill, rx=1)
    if label:
        out += text(cx, bed_y + 14, label, size=8.5, fill=MUTED, anchor="middle")
    return out


def fig_serviceability_schematic() -> str:
    """8. Depth-band x asset serviceability cross-section. #583/#586/#598."""
    inv = load_yaml("well_inventory")["bands"]
    fleet = load_yaml("fleet")
    bac = fleet["by_asset_class"]
    resident = fleet["gom_resident_dedicated_intervention"]["count"]

    W, H = 740, 440
    ml, mr, mt, mb = 92, 250, 88, 40
    px0, px1 = ml, W - mr
    surf_y = mt
    bed_top = mt
    DMAX = 12000.0
    usable_h = H - mt - mb

    def yof(depth):
        return surf_y + (depth / DMAX) * usable_h

    parts = [
        text(
            20,
            22,
            "Depth-band serviceability: who can reach each well",
            size=13,
            fill=ACCENT,
            weight="bold",
        )
    ]

    # water column + sea surface
    parts.append(rect(px0, surf_y, px1 - px0, usable_h, fill=_SEA, opacity=0.55))
    parts.append(line(px0, surf_y, px1, surf_y, stroke=BAR2, width=2))
    parts.append(text(px0 + 4, surf_y - 5, "sea surface", size=8.5, fill=MUTED))

    # depth axis + band breaks
    breaks = [0, 500, 3000, 5000, 10000, 12000]
    band_keys = [
        "shelf_lt_500",
        "band_500_3000",
        "band_3000_5000",
        "band_5000_10000",
        "band_gt_10000",
    ]
    for d in breaks:
        yy = yof(d)
        parts.append(line(ml - 6, yy, px1, yy, stroke=RULE, width=1, dash="3 3"))
        parts.append(
            text(ml - 10, yy + 3.5, f"{d:,} ft", size=8.5, fill=MUTED, anchor="end")
        )

    # highlight access-constrained deepest band 5000-10000
    yhi0, yhi1 = yof(5000), yof(10000)
    parts.append(rect(px0, yhi0, px1 - px0, yhi1 - yhi0, fill=RISK, opacity=0.10))
    parts.append(line(px0, yhi0, px1, yhi0, stroke=RISK, width=1.2))
    parts.append(line(px0, yhi1, px1, yhi1, stroke=RISK, width=1.2))

    # band labels + subsea well counts to the right
    seg = [(0, 500), (500, 3000), (3000, 5000), (5000, 10000), (10000, 12000)]
    for (d0, d1), key in zip(seg, band_keys):
        ymid = (yof(d0) + yof(d1)) / 2
        b = inv[key]
        n = b["subsea_wells_on_record"]
        col = RISK if key == "band_5000_10000" else INK
        parts.append(
            text(px1 + 12, ymid - 2, b["label"], size=9.5, fill=col, weight="bold")
        )
        parts.append(
            text(
                px1 + 12,
                ymid + 11,
                f"{n} subsea wells [on record]",
                size=8.5,
                fill=MUTED,
            )
        )

    # asset reach columns (water-depth ratings from #598)
    rlwi_rating = bac["rlwi_monohull"]["water_depth_capability_ft"]["max"]
    semi_rating = bac["heavy_intervention_semi"]["water_depth_capability_ft"]["max"]
    modu_rating = bac["modu_drillship"]["water_depth_capability_ft"]["max"]
    cols = [
        (
            px0 + (px1 - px0) * 0.20,
            rlwi_rating,
            "RLWI monohull",
            "riserless",
            AMBER,
            "light",
        ),
        (
            px0 + (px1 - px0) * 0.50,
            semi_rating,
            "Helix-class semi",
            "riser",
            OK,
            "heavy",
        ),
        (px0 + (px1 - px0) * 0.80, modu_rating, "MODU", "riser", BAR1, "heavy"),
    ]
    for cx, rating, name, mode, col, kind in cols:
        deck_y = surf_y - 16
        # asset name + rating labelled at the surface (clear of the seabed legend)
        parts.append(_vessel(cx, deck_y, 46, label=name, fill=_HULL))
        parts.append(
            text(
                cx,
                deck_y + 24,
                f"{mode} · ~{int(rating):,} ft",
                size=8,
                fill=col,
                anchor="middle",
            )
        )
        ybot = yof(min(rating, DMAX))
        if mode == "riserless":
            # thin wireline, dashed
            parts.append(line(cx, surf_y, cx, ybot, stroke=col, width=1.6, dash="2 3"))
            parts.append(_tree(cx, ybot, fill=col))
        else:
            # full workover riser, thick solid
            parts.append(line(cx, surf_y, cx, ybot, stroke=col, width=5))
            parts.append(rect(cx - 6, ybot - 10, 12, 10, fill=INK))  # subsea BOP
            parts.append(_tree(cx, ybot, fill=col))

    # legend
    ly = H - 16
    parts.append(line(px0, ly, px0 + 22, ly, stroke=BAR1, width=5))
    parts.append(
        text(
            px0 + 28,
            ly + 3.5,
            "RISER (heavy: MODU / Helix semi — dead well)",
            size=9,
            fill=INK,
        )
    )
    parts.append(
        line(px0 + 320, ly, px0 + 342, ly, stroke=AMBER, width=1.6, dash="2 3")
    )
    parts.append(
        text(
            px0 + 348,
            ly + 3.5,
            "RISERLESS (light: RLWI wireline — live well)",
            size=9,
            fill=INK,
        )
    )

    # GoM-resident annotation, placed inside the highlighted (constrained) band,
    # kept clear of the asset columns to its right
    gy = yof(7400)
    parts.append(
        text(px0 + 8, gy, "access-constrained band", size=8.5, fill=RISK, weight="bold")
    )
    parts.append(
        text(
            px0 + 8,
            gy + 12,
            f"~{resident} GoM-resident units total",
            size=8.5,
            fill=RISK,
            weight="bold",
        )
    )
    parts.append(text(px0 + 8, gy + 23, "(2 Helix semi + 1 RLWI)", size=8, fill=RISK))

    desc = (
        "Water-column cross-section: subsea wells concentrate in the "
        "5,000-10,000 ft band (270 wells) yet only ~3 dedicated intervention "
        "units are GoM-resident. RLWI monohull works riserless on a live well; "
        "MODU and Helix-class semi run a full workover riser on a dead well."
    )
    return svg(
        W, H, "".join(parts), title="Depth-band serviceability cross-section", desc=desc
    )


def fig_riser_concept() -> str:
    """9. Riser-vs-riserless intervention concept, side by side. #586."""
    W, H = 740, 388
    surf_y = 96
    bed_y = 308
    parts = [
        text(
            20,
            24,
            "Riser vs riserless intervention concept",
            size=13,
            fill=ACCENT,
            weight="bold",
        )
    ]

    for x0, x1, mode in [(20, 360, "light"), (380, 720, "heavy")]:
        cx = (x0 + x1) / 2
        # panel water + seabed
        parts.append(rect(x0, surf_y, x1 - x0, bed_y - surf_y, fill=_SEA, opacity=0.5))
        parts.append(line(x0, surf_y, x1, surf_y, stroke=BAR2, width=2))
        parts.append(rect(x0, bed_y, x1 - x0, 34, fill=_SEABED, opacity=0.7))
        parts.append(text(x0 + 6, surf_y - 6, "sea surface", size=8, fill=MUTED))

        if mode == "light":
            parts.append(
                text(
                    cx,
                    surf_y - 50,
                    "LIGHT — riserless",
                    size=11,
                    fill=AMBER,
                    weight="bold",
                )
            )
            parts.append(_vessel(cx, surf_y - 14, 84, "monohull (RLWI)", fill=_HULL))
            # subsea lubricator atop tree
            parts.append(
                line(cx, surf_y, cx, bed_y - 28, stroke=AMBER, width=1.8, dash="2 3")
            )
            parts.append(
                text(cx + 8, (surf_y + bed_y) / 2, "wireline", size=8.5, fill=AMBER)
            )
            parts.append(
                rect(cx - 7, bed_y - 40, 14, 16, fill=AMBER, rx=2)
            )  # lubricator
            parts.append(
                text(cx + 12, bed_y - 32, "subsea lubricator", size=8, fill=MUTED)
            )
            parts.append(_tree(cx, bed_y, fill=BAR1, label="subsea tree"))
            for tx, s in enumerate(
                [
                    "live well (pressure contained)",
                    "no riser, no subsea BOP",
                    "wireline through lubricator",
                    "light scopes only",
                ]
            ):
                parts.append(
                    text(x0 + 12, bed_y + 50 + tx * 13, "• " + s, size=8.6, fill=INK)
                )
        else:
            parts.append(
                text(
                    cx,
                    surf_y - 50,
                    "HEAVY — full workover riser",
                    size=11,
                    fill=BAR1,
                    weight="bold",
                )
            )
            parts.append(_vessel(cx, surf_y - 14, 96, "MODU / Helix semi", fill=_HULL))
            # full workover riser + subsea BOP
            parts.append(line(cx, surf_y, cx, bed_y - 18, stroke=BAR1, width=6))
            parts.append(
                text(
                    cx + 12, (surf_y + bed_y) / 2, "workover riser", size=8.5, fill=BAR1
                )
            )
            parts.append(rect(cx - 9, bed_y - 26, 18, 16, fill=INK, rx=2))  # subsea BOP
            parts.append(text(cx + 14, bed_y - 18, "subsea BOP", size=8, fill=MUTED))
            parts.append(_tree(cx, bed_y, fill=BAR1, label="subsea tree"))
            for tx, s in enumerate(
                [
                    "dead well (killed / isolated)",
                    "full workover riser + subsea BOP",
                    "tubing pull / recompletion / P&A",
                    "heavy scopes",
                ]
            ):
                parts.append(
                    text(x0 + 12, bed_y + 50 + tx * 13, "• " + s, size=8.6, fill=INK)
                )

    parts.append(line(370, surf_y - 40, 370, bed_y + 36, stroke=RULE, width=1))
    desc = (
        "Side-by-side concept: a light riserless intervention runs wireline "
        "through a subsea lubricator on a live well from a monohull (no riser); "
        "a heavy intervention runs a full workover riser and subsea BOP on a "
        "dead well from a MODU or Helix-class semi."
    )
    return svg(
        W, H, "".join(parts), title="Riser vs riserless intervention concept", desc=desc
    )
