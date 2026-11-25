# Part 2 · Permitting and drilling · r15

The November BSEE refresh gives **2,895 Gulf new-well permits** for 2005 through partial-year 2026, including **47 for 2026**, and **2,913 qualifying well starts** in the complete spud years 2005 to 2025. The permit counts, rig and depth shares, mapped wells, and duration statistics match r12. Seven input and exclusion counts changed. The comparison gives the r12 value, r15 value and signed difference for each aggregate and article reading. Share differences are in percentage points. Blank values denote unavailable statistics. [Comparison CSV](data/r12-vs-r15.csv)

## Source dates

| BSEE archive | r12 file date | r15 HTTP Last-Modified (GMT) | r15 retrieval (UTC) | Use |
| --- | --- | --- | --- | --- |
| APDRawData.zip | 2 Nov 2026 for counts, 12 Nov for the column check | 24 Nov 2026 10:30:59 | 25 Nov 2026, 03:58:26 to 03:58:28 | First Gulf New Well permits and APD column check |
| BoreholeRawData.zip | 12 Nov 2026 | 23 Nov 2026 10:31:21 | 23 Nov 2026, 18:54:40 | Map, annual starts, recorded drilling intervals and region lookup |
| eWellAPMRawData.zip | 12 Nov 2026 | 23 Nov 2026 10:36:24 | 23 Nov 2026, 18:54:44 | Operation classifications and operator-estimated durations |

The BSEE archive receipts were taken from the retained manifests for `2026-11-23-series-basis` and `2026-11-25-apd`. For APD, `retrieved_utc` records the end of the manifest's two-second retrieval window. The EIA WTI annual means use the same repository monthly snapshot as r12. Its pin covers the LF-normalized repository bytes. The WTI receipt identifies the mirror commit and its verification time. Its HTTP modification time and source file date were unrecorded. [Source receipts](data/sources.csv) · [WTI provenance](../../../data/wti-monthly.PROVENANCE.md)

## Counting basis

Only the BSEE inputs changed. The [r12 counting rules](../issue2_public_data_r12/counting-rules.md) apply throughout.

- **Permits.** The historical selector takes the Gulf New Well permit with the lowest numeric `SN_APD` for each API well number. Its requested spud year determines the cohort. Rigs follow the six named types and Other. Water depth is converted from feet at 0.3048 m/ft, with edges at 100, 500 and 1,500 m going to the deeper band. The 2026 count covers the 24 November file. [Permit selector](../rawdata_fact_check/count_rawdata.py)
- **Drilling.** The r12 map and annual series use original, uncancelled Gulf boreholes by actual spud year. The two historical map periods, 17 five-year windows, three-year trailing means and annual WTI means retain their original definitions. [r12 derivation](../issue2_public_data_r12/derive_r12.py) · [r12 table functions](../issue2_public_data_r12/build_r12.py)
- **Durations.** The r12 appendix retains the r9 tables for recorded spud-to-total-depth intervals and operator-estimated APM days. Those tables, including the repeat-key sensitivity check, are regenerated from the November 23 archives. [Duration and map rules](../issue2_public_data_r9/build_r9.py)

The record audit partitions each main source member into rows kept and rows excluded, with one reason per excluded row. APD keeps 2,895 of 20,273 rows. Borehole keeps 2,913 of 57,520 for the map and spud cohort. APM keeps 80,542 of 102,177 for duration estimates. For each stage and depth band, the duration table records the separate day exclusions. The historical exclusions table also includes diagnostics that overlap the selection counts. [Record counts](data/record-counts.csv) · [Day statistics](data/days-summary.csv) · [Historical audit](data/exclusions.csv)

## Rerun

From the repository root, place the three named ZIPs together in one directory. `source-pins.json` records each file's URL, BSEE Last-Modified date and SHA-256. BSEE replaces these files in place, so a later download carries a later date and fails the pins; the producer then stops and names the file and both digests.

```bash
export BSEE_R15_DATA_DIR="$PWD/.tmp/bsee-r15-inputs"
mkdir -p "$BSEE_R15_DATA_DIR"
for f in BoreholeRawData eWellAPMRawData APDRawData; do
  curl -fsSL -o "$BSEE_R15_DATA_DIR/$f.zip" "https://www.data.bsee.gov/Well/Files/$f.zip"
done
```

The pinned repository input `data/wti-monthly.csv` requires an LF checkout, including on Windows. Run the CSV producer and its tests from the same shell. With `BSEE_R15_DATA_DIR` set, the tests regenerate every CSV in a temporary directory and compare the bytes with the delivered tables.

```sh
article=examples/bsee/issue2_public_data_r15
uv run --no-project --python 3.11 --with pandas==2.3.3 --with matplotlib==3.10.6 \
  python -B "$article/derive_r15.py" --data-dir "$BSEE_R15_DATA_DIR"
uv run --no-project --python 3.11 --with pandas==2.3.3 --with matplotlib==3.10.6 --with pytest==8.4.2 \
  python -B -m pytest --noconftest -o addopts='' -q "$article/tests"
```

The producer verifies the four source pins before deriving the 21 r12 table names, the record reconciliation and the comparison. It reads local inputs only. A digest mismatch names the file, expected SHA-256 and actual SHA-256, and leaves the existing CSVs in place.
