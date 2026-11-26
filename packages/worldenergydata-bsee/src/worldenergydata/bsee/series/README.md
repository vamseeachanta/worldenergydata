# Annual BSEE well series

Each part supplies one observation per group and event year. The part calculates its own counts, shares or medians and supplies the date through which the partial year is observed. Use `depth_band(metres)` for a known water depth. Supply the four band names in `BANDS` order for the depth overlay. The all-depth observation uses the part's pooled population.

The following example takes `observations` with fields `group`, `year` and `value`. Here the group keys are `"All water depths"` and the four band names. An observed zero counts. Use `None` for an empty sample and `availability="unavailable"` when the source cannot establish a value. A mean requires five consecutive, verified, complete calendar-year values.

```python
from worldenergydata.bsee.series import BANDS, make_figure, with_trends, write_figures

annual = with_trends(observations, partial_year=2026)
caption = "Counts use completion year. The 2026 records end on 30 September."
figures = [
    make_figure(
        "1A", "Completions across all water depths", "Completions per year",
        "completions", [("All water depths", "Completions")], caption,
    ),
    make_figure(
        "1B", "Completions by water depth", "Completions per year",
        "completions", [(band, band) for band in BANDS], caption, by_depth=True,
    ),
]
write_figures(
    output_dir, figures, annual.to_dict("records"), xlabel="Completion year",
    partial_label="Partial through 30 September",
    previous=("Permitting and drilling", "../drilling/"),
    next_part=("Production", "../production/"),
)
```

The writer produces the annual CSV, an SVG and self-contained HTML page per figure, and `figures.json`. To render an existing annual CSV with its original numeric precision, omit the rows argument. Use the same `measure` name for charts with comparable units so the writer can assign shared scales.

For a two-window figure, pass `window_definitions` to `make_figure` with one time boundary per plotted group key. For example, a series list of `[("observed", "Observed by file date"), ("five", "Within five years")]` takes `window_definitions={"observed": "through October 2025", "five": "through the fifth anniversary"}`. The first series uses a solid line and the second a dashed line. The writer builds the manifest entries and visible caption from these definitions. It lists missing annual cells by year and legend label, including gaps in a selected calendar. A missing trailing mean alone adds no entry.

The scale covers annual values and trailing means, including a partial year's annual value. It uses the smallest covering top with three to five intervals at a step of 1, 2 or 5 times a power of ten. Two or more figures of the same measure share the group scale when each reaches at least 30% of its rounded top. Other figures use their own scale.

`write_figures` and `render` accept `coordinate_decimals` for SVG coordinates (default 2). The CSV retains the supplied observation precision. The offline page embeds numeric observations. Axis labels, point tooltips and year-table values use fixed-point notation with thousands separators and up to 15 significant digits. Calendar years appear without separators. Check the output with `python -I check_chart_standard.py --require-overlay path/to/figures.json`.
