# Public liftboat database

The initial collection contains 74 named records, eight with technical
specifications, and four incident records. The seed crosswalk accounts for all
158 rows marked `RIG_TYPE=lift_boat` in the packaged drilling rig CSV: 105 labels
map to 72 named records and 53 remain unresolved. Two historical vessels appear
only because an NTSB report describes their casualties. These are historical
observations, not a current vessel register or a complete casualty census.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-27 | Add attributed specifications, seed identity crosswalk and public incident records so unknown values and source limits remain visible. |

## Load and query

```python
from worldenergydata.vessel_fleet import LiftboatLoader

database = LiftboatLoader()
vessels = database.load()  # list of dictionaries; CSV strings retained
vessel = database.get_by_name("SEACOR POWER")
incidents = database.incidents_for(vessel["liftboat_id"])
assert vessel == database.get_by_name("DIXIE ENDEAVOR LIFT BOAT")
assert incidents[0]["fatalities"] == "13"
```

`load_incidents()` includes anonymous reports. `load_seed_crosswalk()` includes
unresolved labels. `manifest` exposes source metadata; `tables` returns all three
tables. Returned dictionaries are independent copies. A custom data directory
can be passed to `LiftboatLoader(data_dir=...)` and must contain the same files.
Loading is offline, package relative, and independent of the working directory.

Only case and whitespace are ignored in name queries. Seed aliases are explicit
crosswalk entries; fuzzy matches are never used to join casualties. The reported
rename from Dixie Endeavor to SEACOR Power is supported by NTSB section 1.5.1.1.
Unverified seed names have low confidence. Equipment suffix removal and name-token
normalization do not establish a verified physical identity. Typos, generic
district labels, ambiguous references and truncated names remain unresolved.
Distinct historical names may still denote the same hull; an identity register
is needed to resolve those cases. No uniqueness claim extends beyond the recorded
keys, normalized names and populated IMO numbers.

## Files and schema

Data ships inside the existing package at
`src/worldenergydata/vessel_fleet/_data/liftboats/`:

| File | Key | Purpose |
| --- | --- | --- |
| `liftboats.csv` | `liftboat_id` | One named record per curated identity |
| `incidents.csv` | `incident_id` | One record per reported event in this collection |
| `seed_crosswalk.csv` | `seed_name` | Every selected seed label and its resolution |
| `manifest.json` | Source and table identifiers | URLs, terms, timestamps, byte sizes, SHA-256, counts and coverage gaps |

Every observation column has adjacent `_source` and `_confidence` columns. Source
references use `manifest-source-id#locator`, with a report page, section or exact
seed label as the locator. Page locators identify printed report pages; section
and seed-label locators are evidence annotations. Empty observations have
empty source and confidence cells. Structural keys are assigned identifiers,
rather than sourced observations. A blank foreign key means identity is unknown.
Crosswalk resolution is a documented curation judgement, with evidence and
confidence; it does not create an incident.

| Vessel field | Unit or interpretation |
| --- | --- |
| `vessel_name`, `imo_number` | Published name and IMO number when verified |
| `leg_length_ft`, `leg_count` | Feet and number of legs |
| `deck_area_sq_ft` | Advertised open deck area in square feet |
| `variable_deck_load_lb` | Variable deck load in pounds, only when explicitly reported |
| `deck_cargo_capacity_lb` | Advertised maximum deck cargo in pounds, recorded separately |
| `main_crane_capacity`, `main_crane_capacity_unit` | Largest advertised single-crane capacity, preserving the source ton definition |
| `water_depth_rating_ft` | Advertised maximum working water depth in feet |
| `class_society`, `flag` | As reported; no claim of current certification or registration |
| `year_built`, `builder`, `design` | Explicit construction information; blanks otherwise |

No variable deck load or design values were found in the selected sources.
Maximum deck cargo is not substituted for variable deck load. No source clearly
defines the crane capacity's ton basis at the cited entry, so the unit remains
`ton (unspecified)` and no conversion is made. Crane capacity is not a load chart
assessment at a specified radius. USCG classification/certification entries on
operator sheets are not recorded as a classification society. Generic seed hull
dimensions and observed activity water depths are not copied into specifications.

Incident columns record the vessel name, incident date, report date, agency,
report number, phase, conditions, failure mode, injuries, fatalities,
`missing_presumed_dead`, and notes. Phases may be `transit`, `jacking`, `preload`,
`elevated`, or `storm`; an unstated phase remains blank. Severe weather can be
recorded in conditions while the phase remains transit. Phase assignments are
interpretations of the narrative and have medium confidence. The BSEE alert's
operating phase is not inferred from its description of well testing.

`fatalities` includes people reported missing and presumed dead. The separate
missing count is a subset, not an additional death toll. SEACOR Power has
13 fatalities, including seven missing presumed dead, and four nonfatal injuries
(two serious and two minor). An unreported count is blank, never zero.
Dates use ISO format. A report's publication/adoption date is distinct from the
incident date and from the date its bytes were retrieved.

The loader rejects altered table bytes, malformed CSV widths, missing or unknown
provenance, invalid confidence, invalid dates/counts/dimensions, duplicate keys,
duplicate normalized names or IMO numbers, incorrect IMO check digits, and
dangling foreign keys. Confidence is qualitative:

- `high`: explicitly reported government evidence; not independent certification.
- `medium`: operator specifications or conservative interpretation/normalization.
- `low`: historical seed label without independently confirmed physical identity.

## Sources, terms and retrieval

All sources below were retrieved on 2026-10-27. The manifest records UTC retrieval
timestamps and SHA-256 of the actual source bytes. Only curated factual values
are included; original documents, photographs, contact details and illustrations
are not redistributed.

| Source | Use | Terms and limits |
| --- | --- | --- |
| [BSEE well activity portal](https://www.data.bsee.gov/Well/WellActivity/Default.aspx) and existing packaged `drilling_rigs.csv` | Select historical `lift_boat` seed labels | [BSEE public-information terms](https://www.bsee.gov/disclaimer); seed digest identifies the existing repository file, not a fresh portal export |
| [NTSB MIR-22/26](https://www.ntsb.gov/investigations/AccidentReports/Reports/MIR2226.pdf) | Vessel particulars, SEACOR Power casualty, and explicitly labelled historical summaries for Amay S and AVCO V | US federal factual report; third-party attributed material is excluded; [NTSB website policy](https://www.ntsb.gov/about/Pages/privacy.aspx) is a privacy policy, not an additional open licence |
| [RAM I, III, IV, V and VI specification](https://ariesmarine.com/wp-content/uploads/Class130RamIRamIIIRamIVRamVandRamVI.pdf) | RAM I specifications | Operator copyright; no express open licence found; factual extraction only |
| [RAM VII specification](https://ariesmarine.com/wp-content/uploads/Class145RamVII.pdf) | RAM VII specifications | Operator copyright; factual extraction only |
| [RAM VIII, X and XI specification](https://ariesmarine.com/wp-content/uploads/Class175RamVIIIRamXandRamXI.pdf) | Three vessels' specifications | Operator copyright; factual extraction only |
| [RAM XII and XIV specification](https://ariesmarine.com/wp-content/uploads/Class200RamXIIandRamXIV.pdf) | Two vessels' specifications | Operator copyright; factual extraction only |
| [BSEE Safety Alert 498](https://www.bsee.gov/sites/bsee.gov/files/2025-04/BSEE%20Safety%20Alert%20498%20-%20Explosion%20and%20Fire%20Incident_3APR25.pdf) | Anonymous liftboat explosion/fire and two injuries | [BSEE public-information terms](https://www.bsee.gov/disclaimer); incident date and vessel identity are not supplied |

The operator sheets are undated; retrieval does not establish current status.
The source pages remain the authority for their terms. The manifest's
`terms_url` is the publisher's source or policy page, not evidence of a blanket
licence for third-party content. Dataset use does not replace vessel certificates,
stability manuals, crane charts or a competent engineering assessment.

## Retrieve pinned raw documents

No raw document is committed, including the two documents exceeding 1 MB.
The manifest records each raw filename, byte size and SHA-256. To fetch all six
public documents into a separately managed data directory:

```bash
python -m worldenergydata.vessel_fleet.source_fetch "${LIFTBOAT_RAW_DIR:?set a raw-source directory}"
```

Use `--source ntsb-mir2226` to fetch just that source. The destination must be
explicit. Curl is used serially over HTTPS; no login or credentials are needed.
Verified files are reused. A differing digest or a retained `.part` file stops
the fetch without overwriting it. Retrieval receipts include URL, UTC time,
HTTP status and digest. Upstream revisions require a reviewed manifest and
curation update. The script does not automatically archive or upload documents.

## Coverage gaps

- The [USCG marine casualty report index](https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-Reports/)
  and [USCG public casualty library](https://www.uscg.mil/foia/FOIA_Library/MarineCasualtyInvestigations/)
  returned HTTP 403. No independently retrieved USCG reports are included.
- The original MAR-85/10 and MAR-91/02 report URLs returned HTML page-not-found
  content with HTTP 200. The two historical records explicitly cite the
  summaries in MIR-22/26 instead. AVCO V's incident date stays blank because
  that summary and its bibliography disagree by one day.
- The anonymous BSEE record has no vessel foreign key. Zero deaths and an
  elevated phase are not inferred from silence.
- The shared source catalog and domain index references were unavailable.
  This collection makes no claim that those indexes lack related datasets.

Follow-up work should retrieve accessible USCG reports, resolve ambiguous seed
identities using registration evidence, and add explicitly stated variable deck
loads and dated specifications. Current coverage cannot support incident rates,
population-wide statistics or comparisons between operators.

## Tests

`tests/unit/vessel_fleet/loaders/test_liftboat_loader.py` checks schema,
provenance, seed coverage, joins, blanks and corrupt-input rejection.
`tests/unit/vessel_fleet/test_liftboat_source_fetch.py` checks downloads,
digest mismatches, retained partial files and resumption without live requests.
Existing loader public API tests cover the package exports.
