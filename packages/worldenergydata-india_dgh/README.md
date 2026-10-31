# worldenergydata-india_dgh

`india_dgh` domain of the **worldenergydata** namespace: India upstream data from
the Directorate General of Hydrocarbons (DGH) and the Petroleum Planning &
Analysis Cell (PPAC), both under the Ministry of Petroleum and Natural Gas.
Layout follows the other region members (ADR 0001, `packages/worldenergydata-<domain>`).

```python
from worldenergydata.india_dgh import load_awarded_blocks, load_basins, load_production

blocks = load_awarded_blocks()   # 175 rows: OALP-I to IX (172) and SCBM-2022 (3)
basins = load_basins()           # 26 sedimentary basins, Category I/II/III
production = load_production()   # 960 rows: crude by company group, gas by state/onshore/offshore
```

## Tables

| Table | Rows | Coverage | Source |
| --- | ---: | --- | --- |
| `awarded_blocks.csv` | 175 | OALP rounds I-IX (172 blocks), Special CBM round 2022 (3 blocks) | DGH award-list PDFs, parsed with pdfplumber |
| `basins.csv` | 26 | 7 Category-I, 5 Category-II, 14 Category-III, as of 27 Jan 2023 | DGH "Basins and Categories" page |
| `production.csv` | 960 | Crude oil by ONGC, OIL, JVC/Private: annual FY1998-99 to FY2021-22, monthly Apr-May 2022. Natural gas gross production by state, onshore, onshore CBM and offshore: monthly FY2012-13 to FY2018-19 and FY2021-22 (96 months), with national net production | PPAC XLS |

### Awarded blocks: fields and their basis

| Column | Meaning | Basis |
| --- | --- | --- |
| `round`, `round_family` | `OALP-I`... `OALP-IX`, `SCBM-2022`; `OALP` or `CBM` | Award list title |
| `block_name` | HELP block code, hyphen form, e.g. `KG-UDWHP-2022/1` | Award list |
| `basin` | Basin name from the block-code prefix, in the names of `basins.csv` | `basin_basis` = `block_code` |
| `basin_published` | Basin as printed in the award list (rounds IV-IX only) | Award list |
| `basin_category` | I, II or III as printed beside the block (rounds IV-IX only) | Award list |
| `acreage_type` | `onland`, `shallow_water`, `deep_water`, `ultra_deep_water` | `acreage_type_basis`: `source_table` where the list prints the type (IV, VIII), else `block_code` (ONHP, OSHP, DWHP, UDWHP) |
| `area_km2` | Area in sq. km | `area_basis`: `award_list` (IV, VIII, SCBM) or `offer_list` (8 IX blocks from the IX offer list); otherwise missing |
| `awardee` | Company or consortium as printed | Award list |
| `contract_signed` | Revenue Sharing Contract signing date | Only where the document states it: IV (2 Jan 2020), VII (28 Jun 2022), IX (15 Apr 2025) |
| `source_id`, `source_page` | Manifest id and PDF page | |

Rounds I-III print block and H1 bidder only. Area is missing for 147 of 175
blocks; it is never estimated. Awardee strings are not normalized; operator and
participating-interest splits are not established for consortium awards.

## Sources and terms

Every input file is listed in `src/worldenergydata/india_dgh/data/source_manifest.json`
with its original government URL, the Internet Archive capture used, size and
SHA-256. Copies are committed under `data/modules/india_dgh/raw/` (17 files,
2.6 MB). `scripts/india_dgh/build_tables.py` rebuilds every table from those
files and stops on any digest mismatch; `scripts/india_dgh/fetch_sources.py`
re-downloads them one at a time with a pause between requests.

| Publisher | Terms | Reuse |
| --- | --- | --- |
| DGH, https://dghindia.gov.in | Copyright policy: "Material featured on this website may be reproduced free of charge. However, the material has to be reproduced accurately and not to be used in a derogatory manner or in a misleading context. Wherever the material is being published or issued to others, the source must be prominently acknowledged." | Permitted with attribution; not for third-party copyright material |
| PPAC, https://ppac.gov.in/terms-conditions | Same wording as DGH | Permitted with attribution |

Attribution for any republication: "Source: Directorate General of Hydrocarbons
(DGH) and Petroleum Planning & Analysis Cell (PPAC), Ministry of Petroleum and
Natural Gas, Government of India."

**Retrieval route.** On 31 Oct 2026 the DGH, PPAC and MoPNG origin servers did
not accept TCP connections from the build host (connect timeout; a second
egress was refused). The bytes are therefore Internet Archive captures of the
original URLs; capture timestamps are in the manifest. The cause (likely
geo-filtering of non-Indian addresses) is not established. A re-fetch from an
Indian network should confirm the digests against the origin.

### Not used

| Source | Reason |
| --- | --- |
| National Data Repository, https://www.ndrdgh.gov.in | Data access needs registration and is sold (DGH NDR price list, 30 Aug 2019: for example 3D seismic US$20 per sq. km). Not used. |
| PPAC current historical downloads | The "Download Historical Report" button requires sign-in. Not used. |
| data.gov.in | Origin unreachable from the build host; API needs a registered key. Datasets identified, not ingested. |
| MoPNG Monthly Production Report (PDF) | Company and onshore/offshore crude by month; MoPNG terms not retrieved. Next candidate. |
| OALP-X offer list (XLSX, 25 blocks, 182,589.21 sq. km) | Blocks on offer, not awarded; bids close 15 Nov 2026. |

## Limitations

- The basin category is DGH's 27 Jan 2023 grouping; DGH states the grouping
  is dynamic. Award lists print the category current at each round.
- Crude oil by onshore and offshore is not in the PPAC XLS series used here.
- Monthly crude by company covers only April and May 2022.
- Gas production is by state, not by company.
- Provisional PPAC values are flagged (`provisional`); a later capture supersedes
  an earlier one for the same period.
