# Reusable prompt: offshore mega-project cost inflation over time (r1)

This prompt lets your team rebuild the comparison of public offshore cost indexes with consumer prices, the three boom and bust cycles, and the escalation range a project met for each sanction year, then rerun the escalation with your own cost weights, spend profile and execution window. To have a study of your own project's cost escalation done for you instead, see below.

## What you need to run this

- Data required: nine monthly series from FRED (US Bureau of Labor Statistics price indexes and the US Energy Information Administration Brent price), listed with their SHA-256 in `sources.csv`; the quoted Upstream Capital Costs Index values in `data/modules/cost/curated/cost_component_timeseries.csv`.
- Data required to adapt: your project's cost split by category (equipment, fabrication, steel, drilling, installation and services, engineering), its execution window in years, and its spend profile if you have one.
- Paid or behind an account: nothing. The S&P Global Upstream Capital Costs Index is licensed; only the values printed in press articles are used, each with its citation.
- Changes over time: the price indexes gain a month each month and the latest months are revised; the 2026 values are part-year. Rerun `fetch_sources.py` to refresh, then rebuild.

## Reproduce the published result

Give this prompt to your assistant:

> In the public repository github.com/vamseeachanta/worldenergydata, at the commit named in Appendix B of the article "Offshore mega-project cost inflation over time" (r1), run `python examples/costing/megaproject_inflation/fetch_sources.py --check`, then `python examples/costing/megaproject_inflation/build_article.py --pin <that commit>`, and `python -m pytest tests/unit/cost/test_megaproject_inflation.py`. Report the check values below from `examples/costing/megaproject_inflation/out/results.json` and say whether each matches.

- Piece and version: "Offshore mega-project cost inflation over time", r1, 17 Nov 2026.
- Software: Python 3.10 or later, standard library only for the build; pytest for the tests.
- Data set: the files in `examples/costing/megaproject_inflation/data/`, retrieved from FRED on 17 Nov 2026 (times and SHA-256 in `sources.csv`).
- Check values: consumer prices rose 87.0 % from 2000 to 2025; the capital blend grew 0.79 % a year above consumer prices; over an 8-year window the escalation above consumer prices has P50 0.7 % and P90 22.8 %; the 8 quoted sector-index values of 2008 to 2013 sit 18.8 % to 24.7 % above the capital blend.

A fresh download (without `--check`) gives the same values only while the series are not revised; the saved files reproduce the published result exactly.

## Adapt it to your project

Give this prompt to your assistant:

> In examples/costing/megaproject_inflation/inflation.py, set BLEND_WEIGHTS to my project's cost split: <equipment>, <yard fabrication>, <steel plate>, <steel pipe>, <drilling>, <installation and services>, <engineering>, summing to 1. Then compute the escalation above consumer prices for a <N>-year window for every sanction year the data covers, and report P10, P50 and P90, the worst and best sanction years, and the contingency P90 minus P50 in percentage points.

- Inputs to change: `BLEND_WEIGHTS`, the window length `N`, and `spend_profile` if your spend is not bell-shaped.
- Checks that still apply: the weights sum to 1 (the code refuses otherwise); every series hash matches `sources.csv`; the tests in `tests/unit/cost/test_megaproject_inflation.py` pass; a window is used only when every year of it is a full year of data.

Data: US Bureau of Labor Statistics producer and consumer price indexes and US Energy Information Administration Brent prices, public domain, retrieved through FRED, Federal Reserve Bank of St. Louis, on 17 Nov 2026; Upstream Capital Costs Index values as quoted in press articles, read 14 Jul 2026.

To have a study of your own project's cost escalation done for you, write to support@aceengineer.com.
