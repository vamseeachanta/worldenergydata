"""Four depth panels with a shared calendar and value scale for the EXP appendix."""

import textwrap
from decimal import Decimal
from xml.etree import ElementTree as ET

from worldenergydata.bsee.half_decade import _COLORS, _FONT, BANDS


def render_panels(figure, groups):
    """Keep the markers, trend paths and offline controls used by the EXP overlays."""
    from lease_charts import draw_series, element, format_tick, label, line_style

    if tuple(figure["labels"]) != tuple(BANDS) or len(figure["groups"]) != len(BANDS):
        raise ValueError(
            "Appendix panels require the four standard depth bands in order"
        )
    series = [groups[key] for key in figure["groups"]]
    years = sorted(series[0])
    if (
        not years
        or years != list(range(years[0], years[-1] + 1))
        or any(sorted(cells) != years for cells in series)
    ):
        raise ValueError("Appendix panels require a common complete calendar")
    partial = {yr for yr in years if series[0][yr]["partial"] == "1"}
    if (partial and partial != {years[-1]}) or any(
        {yr for yr in years if cells[yr]["partial"] == "1"} != partial
        for cells in series
    ):
        raise ValueError("Appendix panels must agree on the partial final year")

    left, right = 68, 764
    top, bottom = 38, 178
    spacing = bottom + 28
    last_baseline = 110 + (len(BANDS) - 1) * spacing + bottom
    notes = [
        line
        for key in ("note", "coverage_note", "scale_note")
        if key in figure
        for line in textwrap.wrap(figure[key], width=76)
    ]
    height = last_baseline + 98 + 22 * len(notes)
    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "role": "img",
            "aria-label": figure["title"],
            "font-family": _FONT,
            "font-size": "16",
            "fill": "#203340",
            "width": "800",
            "height": str(height),
            "viewBox": f"0 0 800 {height}",
        },
    )
    element(root, "title").text = figure["title"]
    element(root, "rect", width="800", height=height, fill="white")
    label(root, 22, 32, figure["title"], font_size=22, font_weight="bold")
    label(
        root,
        22,
        58,
        "Markers show annual values. Thick lines show the 5 year trailing mean.",
    )
    label(root, left, 91, figure["ylabel"], font_weight="bold")
    maximum, step = (figure["y_scale"][key] for key in ("max", "step"))

    def xpos(year):
        return left + (right - left) * (year - years[0]) / max(1, years[-1] - years[0])

    def ypos(value):
        return bottom - (bottom - top) * value / maximum

    for index, (key, band, cells, color) in enumerate(
        zip(figure["groups"], BANDS, series, _COLORS)
    ):
        panel = element(
            root,
            "g",
            transform=f"translate(0 {110 + index * spacing})",
            **{"class": "panel"},
        )
        dash = {"stroke_dasharray": "9 6"} if line_style(key) == "dashed" else {}
        legend = element(panel, "g", data_legend=index)
        element(
            legend,
            "rect",
            x=left - 6,
            y=0,
            width=55 + 9 * len(band),
            height=26,
            fill="white",
        )
        element(
            legend,
            "line",
            x1=left,
            x2=left + 32,
            y1=13,
            y2=13,
            stroke=color,
            stroke_width=3,
            **dash,
        )
        label(legend, left + 38, 18, band, font_weight="bold")
        for i in range(round(maximum / step) + 1):
            tick = Decimal(str(step)) * i
            y = round(ypos(float(tick)), 2)
            element(panel, "line", x1=left, x2=right, y1=y, y2=y, stroke="#cfd9de")
            label(
                panel, left - 9, round(y + 5, 2), format_tick(tick), text_anchor="end"
            )
        draw_series(panel, index, cells, band, color, dash, years, partial, xpos, ypos)
        if index == len(BANDS) - 1:
            ticks = [
                years[0],
                *(y for y in years[1:-1] if y % 5 == 0 and years[-1] - y >= 2),
                years[-1],
            ]
            for year in dict.fromkeys(ticks):
                label(
                    panel,
                    round(xpos(year), 2),
                    bottom + 27,
                    str(year),
                    text_anchor="middle",
                )
            if partial:
                label(panel, right, bottom + 48, "partial", text_anchor="middle")

    label(
        root,
        (left + right) / 2,
        last_baseline + 54,
        "Lease effective year",
        text_anchor="middle",
        font_weight="bold",
    )
    for i, line in enumerate(notes):
        label(root, 22, last_baseline + 86 + i * 22, line)
    return ET.tostring(root, encoding="unicode") + "\n"
