"""Report semantics and exported array readback."""

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.forecasting.monthly_dca import (
    analyze_monthly,
    prepare_monthly,
)
from worldenergydata.bsee.analysis.forecasting.monthly_dca_plots import (
    build_dca_figure,
    export_static,
)


def example():
    dates = pd.date_range("2018-01-31", periods=72, freq="ME")
    t = (dates - dates[0]).days.to_numpy() / 365.25
    rates = 1000 * np.exp(-0.3 * t)
    df = pd.DataFrame(
        {
            "PRODUCTION_DATE": dates.strftime("%Y%m"),
            "API_WELL_NUMBER": "608124003301",
            "LEASE_NUMBER": "G20351",
            "COMPLETION_NAME": "A",
            "MON_O_PROD_VOL": rates * dates.days_in_month,
            "DAYS_ON_PROD": dates.days_in_month,
        }
    )
    df.loc[40, ["MON_O_PROD_VOL", "DAYS_ON_PROD"]] = 0
    return analyze_monthly(
        prepare_monthly(df, "API_WELL_NUMBER", "608124003301"),
        economic_limit=50,
        terminal_decline=0.06,
    )


def test_plot_encodes_requested_marks_and_panels():
    result = example()
    fig = build_dca_figure(result)
    traces = {trace.name: trace for trace in fig.data}
    assert traces["Reported oil"].mode == "markers"
    assert traces["Zero oil / shut-in"].marker.symbol == "x"
    assert traces["Forecast"].line.dash == "dash"
    assert traces["Remaining oil"].fill == "tozeroy"
    assert traces["Produced oil"].fill == "tozeroy"
    assert traces["Old forecast"].line.dash == "dash"
    assert fig.layout.showlegend is False
    assert fig.layout.xaxis.type == "date"
    assert fig.layout.xaxis2.title.text == "Cumulative oil (million bbl)"
    annotations = " ".join(a.text for a in fig.layout.annotations)
    for label in ["Today", "Economic limit", "Limit reached", "EUR", "bbl/d"]:
        assert label in annotations
    np.testing.assert_allclose(traces["Forecast"].y, result.forecast_rates)


def test_interactive_title_escapes_external_labels():
    result = example()
    result.history.label = "<script>alert(1)</script>"
    assert "<script>" not in build_dca_figure(result).layout.title.text


def test_static_exports_svg_and_png(tmp_path):
    export_static(example(), tmp_path / "sample")
    assert "<svg" in (tmp_path / "sample.svg").read_text(encoding="utf-8")
    assert (tmp_path / "sample.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
