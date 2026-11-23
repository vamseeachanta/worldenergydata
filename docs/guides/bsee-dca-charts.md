# BSEE monthly decline charts

The [sample QA page](../reports/bsee-dca-sample/index.html) contains two public
Gulf of Mexico API wells and field WR627. The field includes every well in the
retained field extract. A full run requires review of this sample first.

```python
from worldenergydata.bsee.analysis.forecasting.monthly_dca import (
    prepare_monthly, analyze_monthly,
)
from worldenergydata.bsee.analysis.forecasting.monthly_dca_plots import (
    build_dca_figure, export_static,
)

# records: monthly OGOR-A completion rows using the BSEE column names.
# For field mode, use group_by="FIELD_NAME_CODE" and key="WR627".
history = prepare_monthly(records, "API_WELL_NUMBER", "608124003301")
result = analyze_monthly(
    history, economic_limit=1000, terminal_decline=0.06,
    b_max=1.0, fit_months=36, backtest_years=2,
)
build_dca_figure(result).write_html("well-dca.html")
export_static(result, "well-dca")  # well-dca.svg and well-dca.png
```

Oil volumes are barrels. Rates are barrels per calendar day: monthly oil divided
by the actual number of days in that month. Field volume is summed before the
division; dividing by summed completion-days would give a different quantity.
Required columns are `PRODUCTION_DATE` (YYYYMM), `MON_O_PROD_VOL`, `DAYS_ON_PROD`,
`API_WELL_NUMBER`, `LEASE_NUMBER`, `COMPLETION_NAME`, and the grouping column.
Use the existing `OGOR_COLUMN_NAMES` schema for headerless publisher extracts;
map its `BOEM_FIELD` column to `FIELD_NAME_CODE` for field selection.
Negative/nonfinite volumes, inconsistent production days, duplicate
completion-month records, and invalid dates are rejected. Input volumes in
other units require conversion before this API is called.

Reported zero-oil months are retained and marked, then excluded from fitting.
They do not establish a mechanical shut-in cause. Absent months remain missing;
no interpolation or zero-volume inference is performed. Partial field months
are identified where a completion reports before and after an absent month. These
months are excluded from fitting. Completeness beyond each member's first/last
report is not established by this detection; the sample also checks the retained
field/completion filings. All internal missing/partial months withhold EUR.

Fits use elapsed calendar time over the trailing fit window, without removing
elapsed shut-in time. At least six active, complete months are required.
Exponential (b=0), bounded hyperbolic (0≤b≤`b_max`≤1) and harmonic (b=1, only
when `b_max`=1) fits are compared by Gaussian-residual AIC. Least squares is
unweighted in rate space. The fitted initial nominal decline is bounded below
by the terminal decline. Nominal decline is expressed in year⁻¹, with a defined
365.25-day year. The continuous terminal exponential starts when the Arps
instantaneous nominal decline reaches the required terminal value.

Produced oil is the sum of reported barrels, not the integral of the fitted
curve. Remaining oil is the analytical rate integral after the last reporting
boundary until the economic limit. The observed shading uses monthly steps;
the forecast shading follows the model. “Today” means the last reported month,
not the computer clock. EUR denotes **observed-window oil plus remaining oil**;
production before/after the supplied history and reserves qualification are not
independently established. If a limit is not reached within `max_years` (default
60, maximum 100), the result reports a horizon volume and withholds EUR. If the
model is already below the limit, remaining production is zero.

Back-tests repeat fitting using only data at/before the historical cutoff and
the same trailing window, then compare with subsequent reported actuals,
including zero-oil months. The economic limit remains the same explicit
scenario input; the old forecast stops producing after that limit. Missing or
partial actuals are excluded from error scoring. Insufficient training produces
an unavailable panel, not a zero-error result. No accuracy threshold or forecast
uncertainty distribution has been established. Fluid fill, liquid loading,
pump failure, workovers and changing field inventory can mimic decline; review
these against the rate/cumulative and back-test panels before relying on a fit.

The sample uses 1,000 bbl/d well and 5,000 bbl/d field economic-limit scenarios.
Income/cost equality is not established. Its 6% nominal annual terminal decline
is an illustrative input from Pradhan's public example, not a field calibration.
The snapshot was retrieved in October 2026 and ends in June 2026. It is reused
without claiming a live refresh. Source identity, retrieval dates and SHA-256
digests remain with `data/economics/julia_life_to_date/sources.json`; the sample
manifest references that owner and records output digests. Raw records are not
duplicated, and operator names are excluded from the chart and array exports.

To reproduce the sample in an installed uv workspace:

```sh
uv run python scripts/bsee/build_dca_sample.py --output-dir docs/reports/bsee-dca-sample
uv run python -m pytest --noconftest --no-cov tests/unit/bsee/analysis tests/unit/common/test_decline.py -k "monthly_dca or decline"
```

For an isolated source checkout, set `PYTHONPATH` to `src` and the `src` directory
of each required workspace member. The sample HTML loads Plotly from its CDN;
static images and CSV data work offline. Export uses the existing matplotlib
dependency, with no Kaleido/browser installation. Interactive figures can be
embedded by the external explorer; changes to that repository are a follow-up.

The hand-check in the tests uses q=100 exp(−0.2t) bbl/d. A 50 bbl/d limit occurs
at ln(2)/0.2=3.465735903 years. Recovery is
365.25×(100−50)/0.2=91,312.5 bbl.

Sources:

- Arps, J.J. (1945), *Analysis of Decline Curves*, Trans. AIME 160, 228–247,
  [doi:10.2118/945228-G](https://doi.org/10.2118/945228-G).
- [Penn State EME 801, Production Decline for Shale Gas Wells, equations (1)–(2)](https://www.e-education.psu.edu/eme801/sites/www.e-education.psu.edu.eme801/files/Production%20Decline%20for%20Shale%20Gas%20Wells.pdf).
- [Pradhan (2020), Texas A&M MS thesis, section 2.1, page 9](https://blasingame.engr.tamu.edu/0_TAB_Grad/TAB_Grad_Thesis_Archive/MS_073_PRADHAN_Yogashril_Thesis_TAMU_%28Dec_2020%29.pdf).
- [BSEE OGOR-A field definitions](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=ogorA),
  production date, oil volume, days on production, API and field identifiers.
- Akaike (1974), *A New Look at the Statistical Model Identification*,
  IEEE Trans. Automatic Control 19(6), 716–723,
  [doi:10.1109/TAC.1974.1100705](https://doi.org/10.1109/TAC.1974.1100705).

The rate equations reuse `worldenergydata.common.decline`; no vendor-specific
method is implemented. The public university references establish the method
used here. Blue/orange, distinct marks and line styles follow the data
visualization guidance; direct labels accompany the marks in both exports.
