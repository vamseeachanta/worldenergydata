# Reusable prompts

Issue 2 public data article ("Gulf of Mexico well permits: a public US data file"), revision 12. This folder holds
in full what Appendix A of the article summarises. `build_r12.py` writes this file from
`inputs/prompts-template.md`.

Purpose:

- Rerun the article's counts and map on the latest public BSEE files with your own AI assistant.
- Adapt them to another region, other years or other water-depth bands, and check the result against the
  values below.

## What you need to run this

- Data required: the BSEE permit and borehole files listed under "Data set" below, the Natural Earth land outline
  for the map, and the repository's monthly WTI price file for the oil-price line.
- Data required to adapt: the same files for another BSEE region, another range of years or other band edges.
- Paid or behind an account: none. The files download free without an account; Python, pandas and matplotlib are
  free.
- Changes over time: BSEE lists the files as updated daily, so a later download gives different counts; the file
  dates below fix the published values.

## Reproduce the published result

Give this prompt to your assistant:

> Count each well once, at its first New Well permit in the Gulf of Mexico region, by requested spud year, rig
> type and water-depth band, from the Application for Permit to Drill file of 2 November 2026. The bands are under
> 100 m, 100 to 500 m, 500 to 1,500 m, and 1,500 m and deeper, from feet at 0.3048 m per foot, with a depth on an
> edge in the deeper band. From the borehole file of 12 November 2026, take the original, not cancelled Gulf of Mexico
> boreholes spudded in each year from 2005 to 2025: map their surface locations by water-depth band in every
> five-year window, one year apart, and count them by year and band with a three-year trailing rolling average.
> Plot the annual mean of the monthly Cushing WTI spot price beside the counts, without fitting a cause. Use the
> rules in counting-rules.md. Do not use cost data.

- Piece: Gulf of Mexico well permits: a public US data file, Deckhand newsletter issue 2, revision 12 of
  18 November 2026.
- Code: [build_r12.py](../build_r12.py) builds the page; [derive_r12.py](../derive_r12.py) derives the yearly
  wells of Figure 1 from the borehole file under the revision 9 rule of
  [build_r9.py](../../issue2_public_data_r9/build_r9.py). The permit counting script is
  [rawdata_fact_check](https://github.com/vamseeachanta/worldenergydata/tree/f5af5b6da87710bb395552f9cda5e34d1f324479/examples/bsee/rawdata_fact_check)
  at commit f5af5b6d, merged into the main branch on 16 November 2026.
- Software: Python 3.14.3, pandas 3.1.1 and matplotlib 3.11.2. Interactive charts load Plotly 2.35.2 from its release address with an integrity check;
  without it, each chart shows its static image. The permit counting script needs only the Python 3.10 or later
  standard library.
- Check values: 2,895 wells with permits; band totals 1,476 (under 100 m), 175 (100 to 500 m), 589 (500 to
  1,500 m) and 655 (1,500 m and deeper). Mapped wells: 1,584 (2005 to 2009) and 246 (2021 to 2025). New wells started: 410 (2005), 87 (2015), 43 (2025).

## Adapt it to your project

Change the region code, the range of years, the band edges, the window length and the rolling-average length.
The checks that still apply: each well is counted once; the rig-type counts add up to the band totals; the
window counts equal the sum of their years; every exclusion is counted.

## Data set

The public data set for this page is two BSEE files from the
[BSEE Data Center raw data page](https://www.data.bsee.gov/Main/RawData.aspx) (US Department of the Interior),
US federal government data listed as updated daily, plus the Natural Earth land outline (public domain) and the
EIA WTI price (US government data, public domain).

- Application for Permit to Drill ([APDRawData.zip](https://www.data.bsee.gov/Well/Files/APDRawData.zip)), file of 2 November 2026, downloaded 3 November 2026, SHA-256 `b4ab66063de5a95c78d0e4d33d220ea806ef07f114bd2add6efa9e8561d299c0`: permit type, requested spud date, water depth, rig name and rig type.
- Boreholes ([BoreholeRawData.zip](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip)), file of 12 November 2026, downloaded 13 November 2026, SHA-256 `41d201b17c9982484fe781f797c1e621529e4d5469178d3c978843a316ae444e`: region, well-name suffix, spud date, status, water depth and surface location.
- Map land outline: Natural Earth 1:50m land ([ne_50m_land.geojson](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/f1890d9f152c896d250a77557a5751a93d494776/geojson/ne_50m_land.geojson), version 5.1.2, public domain), downloaded 13 November 2026, SHA-256 `e874b27a51d146452be360cafb3cc50c86001074a67d534113e6534682f9826b`.
- Oil price: US Energy Information Administration, Cushing WTI spot price, monthly, as the repository snapshot [data/wti-monthly.csv](https://github.com/vamseeachanta/worldenergydata/blob/37e36be7c19d7e121d2d1208aff61ca9e6b1bb59/data/wti-monthly.csv) (retrieved 12 October 2026; provenance in [wti-monthly.PROVENANCE.md](https://github.com/vamseeachanta/worldenergydata/blob/37e36be7c19d7e121d2d1208aff61ca9e6b1bb59/data/wti-monthly.PROVENANCE.md)); annual means in data/wti-annual.csv.

The days from drilling to abandonment, and their prompt, moved with section 3 to the series'
plugging-and-abandonment article: see [../../plug_abandonment_article/](../../plug_abandonment_article/).

To have a study of your own public offshore data done for you, write to support@aceengineer.com.
