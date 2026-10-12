# WTI monthly snapshot provenance

Source: U.S. Energy Information Administration, Cushing WTI spot price.
Monthly values are an unweighted average of the daily closing spot prices
for a given product over the specified time period. Units: Dollars per Barrel.
Source: [Spot Prices for Crude Oil and Petroleum Products](https://www.eia.gov/dnav/pet/PET_PRI_SPT_S1_M.htm); retrieved 2026-10-12.
The mirror labels each month with the 15th; this date represents the
month's average, rather than a price observed on that day.
Mirror documentation: [date conventions](https://github.com/datasets/oil-prices); retrieved 2026-10-11.

CSV SHA-256 as retrieved: `c45da80c522345e9c6e4631cf6dfe566b49099ec4ceba284671c110703d15473`
CSV size as retrieved (bytes): 8786
CSV SHA-256 as committed: `65a086d437474d707f7215d4c60b39c3b447ff488ec12be900cb1a0213d573ec`
CSV size as committed (bytes): 8296
Coverage: 1986-01 through 2026-09 (489 rows).

The snapshot is content-identical; line endings normalised to LF as
required by the repository's mixed-line-ending hook. The only difference
is removal of 490 CR bytes.
Parsed-values SHA-256 as retrieved: `0b8fa92201194488781607ebadaa26b7c8c339003f51c194b898cfc8dac0d6e0`
Parsed-values SHA-256 as committed: `0b8fa92201194488781607ebadaa26b7c8c339003f51c194b898cfc8dac0d6e0`
The parsed-values hash is SHA-256 of the UTF-8 bytes of
`json.dumps(rows, ensure_ascii=False, separators=(",", ":"))`, where rows
contains every csv.reader row, header first, as lists of unchanged strings.
V30 workbook rows remain authoritative; the snapshot supplies extension months only after the workbook's last month.
The July 2025 overlap criterion is within $0.01 of $68.39.

## EIA origin comparison

Difference is mirror minus EIA. Missing means not established.

| Month | Mirror (USD/bbl) | EIA (USD/bbl) | Difference (USD/bbl) |
| --- | ---: | ---: | ---: |
| 2025-07 | 68.39 | 68.39 | 0.00 |
| 2025-08 | 64.86 | 64.86 | 0.00 |
| 2025-09 | 63.96 | 63.96 | 0.00 |
| 2025-10 | 60.89 | 60.89 | 0.00 |
| 2025-11 | 60.06 | 60.06 | 0.00 |
| 2025-12 | 57.97 | 57.97 | 0.00 |
| 2026-01 | 60.04 | 60.04 | 0.00 |
| 2026-02 | 64.51 | 64.51 | 0.00 |
| 2026-03 | 91.38 | 91.38 | 0.00 |
| 2026-04 | 100.32 | 100.32 | 0.00 |

## Recorded source evidence and emitter inputs

```json
{
  "baseline_limitation": "The pinned series freezes current upstream values; agreement with historical golden-baseline revenue or NPV has not been established. Baselines are not regenerated.",
  "comparison_criterion": "Exact price agreement for every month from 2025-07 through 2026-04",
  "eia_download": {
    "retention": "Local research evidence only; not committed",
    "retrieved_at_utc": "2026-10-11T20:07:12.840048+00:00",
    "sha256": "6387b6404192ba6a6e9d2d98ec6c2f0ed940fb54aeb6dbc3358ade03177497da",
    "size_bytes": 55808,
    "status": 200,
    "url": "https://www.eia.gov/dnav/pet/hist_xls/RWTCm.xls"
  },
  "eia_listing": {
    "retrieved_at_utc": "2026-10-11T20:06:57.670895+00:00",
    "sha256": "a8fe525325e2d724512d9d03c7c305a54b362cbbdc6f2deae65963ed049a5460",
    "size_bytes": 20487,
    "status": 200,
    "url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RWTC&f=M"
  },
  "eia_observations_usd_per_barrel": {
    "2025-07": 68.39,
    "2025-08": 64.86,
    "2025-09": 63.96,
    "2025-10": 60.89,
    "2025-11": 60.06,
    "2025-12": 57.97,
    "2026-01": 60.04,
    "2026-02": 64.51,
    "2026-03": 91.38,
    "2026-04": 100.32
  },
  "eia_terms": {
    "retrieved_at_utc": "2026-10-11T20:06:22.243851+00:00",
    "sha256": "28ef6560399ba7c7b9c171ba1eef1f3de5a44540ef5e1173eb935e5a36463d5d",
    "size_bytes": 52528,
    "status": 200,
    "url": "https://www.eia.gov/about/copyrights_reuse.cfm",
    "wording": "U.S. government publications are in the public domain and are not subject to copyright protection. You may use and/or distribute any of our data, files, databases, reports, graphs, charts, and other information products that are on our website or that you receive through our email distribution service."
  },
  "line_ending_normalisation": {
    "cr_bytes_removed": 490,
    "retrieved_parsed_values_sha256": "0b8fa92201194488781607ebadaa26b7c8c339003f51c194b898cfc8dac0d6e0"
  },
  "live_fetcher_evidence": {
    "retrieved_at_utc": "2026-10-11T20:10:30.872028+00:00",
    "sha256": "c45da80c522345e9c6e4631cf6dfe566b49099ec4ceba284671c110703d15473",
    "size_bytes": 8786,
    "status": 200,
    "url": "https://raw.githubusercontent.com/datasets/oil-prices/main/data/wti-monthly.csv"
  },
  "mirror_license_file": {
    "retrieved_at_utc": "2026-10-11T20:06:32.921600+00:00",
    "sha256": "88d9b4eb60579c191ec391ca04c16130572d7eedc4a86daa58bf28c6e14c9bcd",
    "size_bytes": 1210,
    "status": 200,
    "url": "https://raw.githubusercontent.com/datasets/oil-prices/908994d7f61a7a3e3449f2c7e3a2dca6db4a89b3/LICENSE",
    "wording": "This is free and unencumbered software released into the public domain.\n\nAnyone is free to copy, modify, publish, use, compile, sell, or\ndistribute this software, either in source code form or as a compiled\nbinary, for any purpose, commercial or non-commercial, and by any\nmeans.\n\nIn jurisdictions that recognize copyright laws, the author or authors\nof this software dedicate any and all copyright interest in the\nsoftware to the public domain. We make this dedication for the benefit\nof the public at large and to the detriment of our heirs and\nsuccessors. We intend this dedication to be an overt act of\nrelinquishment in perpetuity of all present and future rights to this\nsoftware under copyright law.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND,\nEXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF\nMERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.\nIN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR\nOTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,\nARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR\nOTHER DEALINGS IN THE SOFTWARE.\n\nFor more information, please refer to <http://unlicense.org>\n"
  },
  "mirror_listing": {
    "retrieved_at_utc": "2026-10-11T20:05:53.881713+00:00",
    "sha256": "646d52bbc1b811208f10adfd8ecac5a9cb7982d9196ac74d5f2bb5f63dd45058",
    "size_bytes": 287152,
    "status": 200,
    "url": "https://github.com/datasets/oil-prices"
  },
  "mirror_snapshot": {
    "retrieved_at_utc": "2026-10-11T20:06:35.244491+00:00",
    "sha256": "c45da80c522345e9c6e4631cf6dfe566b49099ec4ceba284671c110703d15473",
    "size_bytes": 8786,
    "status": 200,
    "url": "https://raw.githubusercontent.com/datasets/oil-prices/main/data/wti-monthly.csv"
  },
  "mirror_terms": {
    "retrieved_at_utc": "2026-10-11T20:05:53.881713+00:00",
    "url": "https://github.com/datasets/oil-prices#license",
    "wording": "All the additional work made to build this Data Package is made available under the Public Domain Dedication and License v1.0 whose full text can be found at: http://www.opendatacommons.org/licenses/pddl/1.0/"
  },
  "pinned_commit_verification": {
    "retrieved_at_utc": "2026-10-11T20:07:15.120100+00:00",
    "sha256": "c45da80c522345e9c6e4631cf6dfe566b49099ec4ceba284671c110703d15473",
    "size_bytes": 8786,
    "status": 200,
    "url": "https://raw.githubusercontent.com/datasets/oil-prices/908994d7f61a7a3e3449f2c7e3a2dca6db4a89b3/data/wti-monthly.csv"
  },
  "robots": [
    {
      "retrieved_at_utc": "2026-10-11T20:05:51.128423+00:00",
      "sha256": "12bc55582b1ddb8eb3300d9cb26b0421c9fc80193fc77e5f04862e934f8097db",
      "size_bytes": 16739,
      "status": 200,
      "url": "https://github.com/robots.txt"
    },
    {
      "retrieved_at_utc": "2026-10-11T20:06:04.289746+00:00",
      "sha256": "0e3264650ea99daf72b4aa98233e64b3d1583b1480c2a3755857c41a20743c16",
      "size_bytes": 718,
      "status": 200,
      "url": "https://www.eia.gov/robots.txt"
    }
  ],
  "source_price_basis": {
    "label_retrieved_at_utc": "2026-10-11T20:05:53.881713+00:00",
    "label_url": "https://github.com/datasets/oil-prices",
    "label_wording": "Monthly: the 15th of the month (e.g. 1987-05-15 represents the May 1987 average).",
    "retrieved_at_utc": "2026-10-12T20:55:50.148603+00:00",
    "sha256": "a416a5215705b86680069aab524b83cdd0be02478f0cea6de6db2a6bf0e70aea",
    "size_bytes": 18781,
    "status": 200,
    "title": "Spot Prices for Crude Oil and Petroleum Products",
    "units": "Crude Oil in Dollars per Barrel",
    "url": "https://www.eia.gov/dnav/pet/PET_PRI_SPT_S1_M.htm",
    "wording": "Weekly, monthly, and annual prices are calculated by EIA from daily data by taking an unweighted average of the daily closing spot prices for a given product over the specified time period."
  },
  "source_series": "EIA Cushing, OK WTI Spot Price FOB, monthly",
  "upstream_commit": "908994d7f61a7a3e3449f2c7e3a2dca6db4a89b3"
}
```

## Refresh and reproduce

Fetch the listed public mirror only after reviewing its terms. Use one
connection, a 15-second timeout, a 1,000,000-byte limit and a 2-second pause.
Record new source metadata and repeat the keyless EIA comparison before
replacing the pin. Extract the JSON block to `wti-source-evidence.json`.
Regenerate this sidecar with:

```sh
python -m worldenergydata.lower_tertiary.wti_prices --snapshot data/wti-monthly.csv --metadata wti-source-evidence.json --provenance data/wti-monthly.PROVENANCE.md
```
