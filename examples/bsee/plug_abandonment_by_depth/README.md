# Plugging and abandonment by water depth

Part 6 of *Life of a Gulf of America well* uses the 23 November 2026 BSEE snapshot to count wells by their latest status, measure time in temporary abandonment and compare that stock with the annual pace of permanent abandonment. Of 37,513 eligible Gulf wells, 2,896 were temporarily abandoned. The median time in that status was 13.3 years for the 2,360 wells under 100 m and 2.5 years for the 42 wells in at least 1,500 m. [Status counts](output/status_by_band.csv) · [Temporary abandonment ages](output/ta_by_band.csv)

| Water depth (m) | Wells | Permanently abandoned (PA) | Temporarily abandoned (TA) | Completed (COM) | Other | PA wells/year, 2021 to 2025 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Under 100 | 32,040 | 27,069 | 2,360 | 2,359 | 252 | 371.0 |
| 100 to under 500 | 3,000 | 2,165 | 415 | 408 | 12 | 24.2 |
| 500 to under 1,500 | 1,511 | 948 | 79 | 443 | 41 | 34.6 |
| 1,500 and deeper | 899 | 441 | 42 | 367 | 49 | 12.4 |
| No reported depth | 63 | 61 | 0 | 2 | 0 | 0.0 |
| **All depths** | **37,513** | **30,684** | **2,896** | **3,579** | **354** | **442.2** |

*Table 1. Status on 23 November 2026 and mean annual PA count over five complete calendar years.* [Annual PA counts and rates](output/pa_pace_by_band.csv)

## Which wells and which depths count

1. Keep boreholes with `REGION_CODE = G` (55,586 of 57,520 records). The first ten digits of the API number identify a well and retain leading zeros. Of 38,291 Gulf well IDs, exclude 762 for which all bores were cancelled (`CNL`), then 16 with no dated spud. All 54,808 bores of the remaining wells are eligible to supply status and depth, including cancelled or unspudded siblings.
2. For each well, select the latest dated `BOREHOLE_STAT_DT`. Every eligible well has a dated status. On a tie, select the last tied row in source-file order. Read both `BOREHOLE_STAT_CD` and `WATER_DEPTH` from that row. All codes outside PA, TA and COM count as Other, including CNL. Of 49 wells with tied latest dates, 47 have different raw statuses among tied rows and 11 have different reported depths. Choosing the first tied row would give 30,657 PA, 2,898 TA, 3,575 COM and 383 Other. Taking depth from the earliest-spudded bore instead, with the first row breaking spud-date ties, would move 30 wells between bands.
3. Convert feet to metres by multiplying by 0.3048 before assigning a band, with no intermediate rounding. A depth exactly at 100, 500 or 1,500 m enters the deeper band. Missing and zero depths form a separate group. All 63 such winning rows in this snapshot report zero feet. They contribute to all-depth totals and annual bars.
4. TA age is the number of days from the current TA effective date to the snapshot date, divided by 365.25. The ten-year count includes ages of exactly ten years. Quartiles use linear interpolation. The earlier comparison did not specify the calendar divisor, interpolation method, tie-break or which bore supplied depth. An empty age distribution gives blank CSV cells and nulls in the headline index.

The rebuild prints the tie counts, alternative status totals and number of wells that change depth band under the earliest-spud rule.

## Annual pace and limits

Each currently PA well counts once, in the year its latest status took effect. The annual chart covers 1960 to 2025. Its 29,917 wells include 50 without reported depth across 19 years. Each year's bars reconcile to an independent all-depth count. For 2005 to 2025 the plotted bands also equal the annual counts in the pace table. Years with no observations in a band have a true zero. [Plotted counts](output/pa_per_year_by_band.csv) · [Annual PA chart (SVG)](output/pa_per_year_by_band.svg) · [PNG](output/pa_per_year_by_band.png)

Rates use the complete years 2021 to 2025 or 2016 to 2025. The 2026 partial year is excluded. Dividing the TA stock on 23 November 2026 by the respective all-depth rates of 442.2 and 422.4 PA wells/year gives 6.5 and 6.9 years of activity. Some wells proceed directly to PA, so the ratio cannot predict a clearance date. A zero rate leaves the ratio undefined. The pace table repeats the fixed-window measures on each annual row. The 2025 row is the lookup for those values in the headline index. [Pace table](output/pa_pace_by_band.csv) · [Headline values and row keys](output/numbers.json)

For the end-of-operations (EOR) series, select abandonment operations (`EOR_OPERATION_CD = A`) on eligible Gulf wells. Count each well once per effective calendar year and reached status, PA or TA, across all its bores. One well can appear in both series in one year. Depth follows the same selected bore as for the status table. Three- and five-year trailing means start with observations in 2007. Earlier annual EOR counts are supplied for reference. Among currently PA wells, the share with a BSEE EOR report reaching PA in their effective year was 45.2% in 2005, 96.5% in 2007 and 98.2% across 2010 to 2025. The two series measure different events in files from the same regulator. Only borehole PA counts enter the pace denominator. [Annual EOR and borehole series](output/pa_pace_by_band.csv)

The status table includes each band's share of Gulf PA wells by effective decade, with the 2020s ending at the snapshot date. Multiplying reported depths by 0.95 or 1.05 tests sensitivity to a systematic depth difference. For example, the 415 TA wells at 100 to under 500 m become 361 or 482. Changes are relative to the original count in each band. Individual depth uncertainties are unavailable. [Depth sensitivity](output/status_by_band.csv)

The snapshot cannot reconstruct the TA stock in past years or all spells before permanent abandonment. It provides no basis for determining lease expiry or well-specific plugging deadlines. Permit-based well life uses a separate population of surviving bores and falls outside this analysis. A separate well-detail supplement was unavailable.

## Figures and comparison records

| Figure | Values | Rendered figure |
| --- | --- | --- |
| Current status share within each reported-depth band | [Status table](output/status_by_band.csv) | [SVG](output/status_share_by_band.svg) · [PNG](output/status_share_by_band.png) |
| Median and middle 50% of current TA ages within each reported-depth band | [Age table](output/ta_by_band.csv) | [SVG](output/ta_age_by_band.svg) · [PNG](output/ta_age_by_band.png) |
| Annual PA wells, including those without reported depth | [Annual table](output/pa_per_year_by_band.csv) | [SVG](output/pa_per_year_by_band.svg) · [PNG](output/pa_per_year_by_band.png) |

*Table 2. Source tables for the three figures.*

The build recalculates 114 earlier comparison values before applying the series depth bands. The earlier bands include the upper boundaries of 200, 400, 800 and 1,000 m. For example, a depth just above 200 m enters the band labelled “201 to 400 m”. The comparison values are transcribed in the calculation, so reruns require no article file or document parsing. All 114 match at the recorded precision. Before writing the final output, the build verifies the SHA-256 of the regenerated comparison CSV against the digest of the reference CSV. This check also runs when rebuilding into an empty directory. The comparison CSV includes both the unrounded calculation and the difference at that precision. Share differences are in percentage points. The checks record the number read, retained and dropped at each filter, population and year totals, and readback of tables and figures. [Comparison CSV](output/r4-reproduction.csv) · [Build checks](output/checks.txt)

## Rerun from the pinned BSEE archives

Run these commands from this example directory. BSEE replaces files in place at these URLs. If a later download has different bytes, its SHA-256 will fail the pin and the build will stop. Reproduction then requires a retained copy that matches the recorded digest. [BSEE raw data index](https://www.data.bsee.gov/Main/RawData.aspx)

```sh
mkdir -p bsee-inputs
curl -fL https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip -o bsee-inputs/BoreholeRawData.zip
curl -fL https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip -o bsee-inputs/eWellEORRawData.zip
uv run --python 3.11.15 derive.py --data-dir bsee-inputs
```

The script declares the package versions used to generate the tables, checks and figures in `output/`. To use an existing archive directory, set `BSEE_W1_DATA_DIR` and omit `--data-dir`. Use `--output` to write the results to a separate directory. The figures use the DejaVu Sans font bundled with Matplotlib.

| BSEE archive | BSEE Last-Modified | SHA-256 |
| --- | --- | --- |
| [BoreholeRawData.zip](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip) | Mon, 23 Nov 2026 10:31:21 GMT | `72fa55e55fd28db26c59e52b3a43c7d053f9d12a6d06b0a0f6a46ef541c66a5c` |
| [eWellEORRawData.zip](https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip) | Mon, 23 Nov 2026 10:36:30 GMT | `b67c61826ea90aa51d7e1f01c2df94bba6e869665a7992cd5438ea538ee603bc` |

*Table 3. BSEE HTTP Last-Modified headers and SHA-256 digests of the archives collected on 23 November 2026. The analysis also checks the member digests for the borehole table `mv_boreholes_all.txt` and the EOR table `mv_eor_mainquery.txt`.* [Machine-readable input pins](source_pins.json)

| ZIP member | SHA-256 |
| --- | --- |
| `BoreholeRawData/mv_boreholes_all.txt` | `24ae892cfca23127f6398a4b8c32c96a6e560ca095afcf480829a92247117f68` |
| `eWellEORRawData/mv_eor_mainquery.txt` | `f6ac748318b2d48d690ad9e0e4d2fcbb1842f2917b9b4448680b6e6c8f6724c6` |

*Table 4. SHA-256 of the two source tables inside the pinned archives.*
