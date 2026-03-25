# Module: vessel_fleet

## Purpose
Provides global offshore vessel fleet data collection, enrichment, and storage,
covering construction vessels (lay barges, crane vessels, pipe-lay ships) and
drilling equipment (risers, BOPs, flex joints) through web scraping, PDF spec
extraction, and classification society data sources.

## Key Classes / Functions
- `ConstructionVesselLoader` (`loaders/`): Orchestrates ingestion of
  construction vessel records from multiple collector sources; deduplicates
  and validates before writing to storage
- `DrillingRiserLoader` (`loaders/`): Ingests drilling riser component
  records (riser joints, telescopic joints, flex joints, LMRPs, BOPs)
  from PDF spec sheets and web pages
- `ConstructionVesselEntry` (`models/construction_vessel.py`): Core data model
  for a construction vessel: IMO number, name, flag, owner, capabilities
  (water depth, lift capacity, lay modes), vessel type, and dimensions
- `DrillingRigEntry` (`models/drilling_rig.py`): Drilling rig specification
  model: rig type (drillship/semi), water depth rating, hook load, derrick,
  and certification status
- `RiserJointEntry`, `TelescopicJointEntry`, `FlexJointEntry`,
  `LMRPEntry`, `BOPEntry` (`models/drilling_riser.py`): Component-level
  models for drilling riser equipment with manufacturer, OD, working pressure,
  and API/DNV certification fields
- `ConstructionVesselSchema`, `BOPSchema`, `RiserJointSchema`,
  `FlexJointSchema`, `LMRPSchema`, `TelescopicJointSchema` (`schemas/`):
  Marshmallow/Pydantic schemas for serialisation and input validation
- `BakerHughesCollector` (`collectors/baker_hughes_collector.py`): Scrapes
  Baker Hughes rig count and fleet data
- `BOEMCollector` (`collectors/boem_collector.py`): Fetches BOEM offshore
  installation and vessel activity records for GOM
- `ClassificationCollector` (`collectors/classification_collector.py`):
  Retrieves vessel class certificates from DNV GL, ABS, and Lloyd's Register
- `EquasisCollector` (`collectors/equasis_collector.py`): Equasis vessel
  inspection and ownership history scraper
- `SpecPDFCollector` (`collectors/spec_pdf_collector.py`): Downloads and
  parses vessel specification PDFs using pdfplumber; extracts structured
  equipment tables
- `Router` (`router.py`): Dispatches collection requests to the appropriate
  collector based on vessel category and data source priority
- `Deduplicator` (`dedup/`): IMO-number and fuzzy-name deduplication across
  collector outputs before storage
- `QualityChecker` (`quality/`): Validates required fields, flags implausible
  values (e.g. water depth > 12 000 m), and assigns confidence scores

## Data Sources
- Equasis: https://www.equasis.org/; vessel ownership and inspection history;
  requires registration; JSON/HTML
- BOEM GOM installations: https://www.boem.gov/; CSV/GIS; public; quarterly
- Baker Hughes rig count: https://rigcount.bakerhughes.com/; weekly; Excel
- DNV GL / ABS / Lloyd's vessel finders: HTML scrape; public; updated daily
- Manufacturer spec PDFs: various vendor websites; static; collected on demand

## Integration Points
- **Depends on**: `worldenergydata.common` (date helpers, unit conversion),
  `worldenergydata.bsee` (GOM installation cross-reference)
- **Used by**: `worldenergydata.marine_safety` (vessel capability vs sea
  state operability), `worldenergydata.analysis` (fleet availability
  and market intelligence), `worldenergydata.reporting` (fleet status reports)

## Status
Active — construction vessel and drilling riser loaders/models implemented;
collector framework implemented; classification and Equasis collectors partial;
AIS real-time tracking planned
