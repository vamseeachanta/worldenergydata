# Pipeline risers: public source pull and riser segment table

Public pipeline, platform and riser sources for the Gulf of America, fetched on
20 Nov 2026, and a table of the pipeline segments that BSEE permit text names
as risers.

## What is here

| File | What it is |
|---|---|
| `source_manifest.json` | BSEE files: Pipeline Masters, Pipeline Permits, Pipeline Location with Appurtenance, Pipeline Histories, ROW Descriptions, the Pipelines and Platforms mapping layers, the Scanned Documents index, Decommissioning Cost Estimates and Platform Structures, with their layout and code pages (17 files, 35.8 MB). |
| `../research_reports/source_manifest.json` | BSEE Technical Assessment Program reports 572, 531 and 622 on riser design, SCR integrity and marine growth (3 PDFs, 4.3 MB). |
| `../../pipeline_safety/netl_offshore_pipelines/source_manifest.json` | US DOE (NETL) "U.S. Offshore Pipeline and Reported Incident Datasets", DOI 10.18141/2280823, CC BY (8 files, 557.6 MB). |
| `riser_segments.csv` | One row per segment with a riser mention in its permit submittals (1,475 segments). |
| `riser_static_check_candidates.csv` | Segments with outside diameter, a plausible wall thickness stated in permit text, and water depth. |
| `riser_segments_summary.json` | Counts by riser type, size, water-depth band, product, status and readiness tier; term counts for comparison with the road map. |

Each manifest entry gives the source URL, retrieval time, size, SHA-256,
publisher last-modified date, terms and schema notes (zip members, header
fields and line counts). Raw files are kept outside git in the external raw
store; only manifests and the small derived tables are committed.

## Rebuild

```bash
# fetch (sequential, per-host pauses, generic User-Agent, write-once)
python3 -I scripts/bsee/fetch_fielddev_public_sources.py --raw-root <raw-store> --retrieval 2026-11-20
# re-hash held files against the manifests
python3 -I scripts/bsee/fetch_fielddev_public_sources.py --raw-root <raw-store> --verify
# build the riser table
python3 -I scripts/bsee/build_riser_segments.py --raw-dir <raw-store>/bsee_pipeline/2026-11-20
```

Both scripts use the Python standard library only.

## How the riser table is built

- A permit submittal is a riser submittal when its description says "riser",
  "steel catenary", "SCR" or "TTR". Type words (steel catenary or SCR,
  flexible riser, lazy wave, hybrid riser, riser tower or free standing, top
  tension or TTR) set `riser_types`. A mention is not proof of an installed
  riser.
- Segment attributes come from the latest Pipeline Masters record, with the
  permits segment file as fallback: status, product, size code, minimum and
  maximum water depth, segment length (federal portion), MAOP, dates,
  operator code, and origin and destination area and block.
- `od_in`: whole-number size codes are read as nominal pipe size and
  converted to outside diameter with the API 5L table below 14 in (for
  example 06 to 6.625 in, 10 to 10.75 in); 14 in and above are taken as the
  outside diameter. Range codes such as 04-10 are left blank. This is an
  assumption.
- `wt_in_stated`: wall thickness stated in riser submittal text, 0.2 to 2.0 in.
  `wt_in_plausible` keeps values with D/t between 8 and 60. The stated value
  may describe the flowline rather than the riser section.
- `floating_host_types_in_end_blocks`: SEMI, SPAR, TLP, MTLP or FPSO
  structures in the origin or destination block (Platform Structures). It
  shows a likely host, not a confirmed connection.

Readiness tiers for a static riser check with the digitalmodel catenary
riser tools (inputs: outside diameter, wall thickness, water depth, length or
offset, material and contents):

| Tier | Meaning | Segments |
|---|---|---|
| A | Steel or unspecified type, with OD, plausible stated wall and water depth | 5 |
| B | OD and water depth; wall thickness must be assumed | 906 (457 in 1,000 ft or more) |
| C | Flexible riser only; needs vendor cross-section properties | 27 |
| D | OD or water depth missing | 403 |
| E | Umbilical or cable product code | 134 |

Riser length and hang-off geometry are not in any BSEE file; a static check
takes length or offset from water depth and an assumed top angle.

## Public-text rule

The derived tables carry BSEE codes only (operator code, area and block,
product and status codes). Permit free text, facility names and company names
are read for matching and are not written out.

## Not fetched

- The all-versions location raw file is already held (15 Oct 2026; see
  `data/modules/pipeline/screening/sources.json`).
- The scanned pipeline maps and ROW PDFs: only the index was fetched; the
  scans are per-segment image files.
- Paid and sign-in sources: the File Request System (Login.gov) and the
  Public Information Ordering System.
