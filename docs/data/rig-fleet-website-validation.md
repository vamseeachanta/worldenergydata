# Rig Fleet Contractor Website Validation

> Step 0 for WRK-104. Validated 2026-02-13.

## Summary

Two-pass validation: (1) raw HTTP via `WebFetch`, (2) headless Chrome via Puppeteer for blocked/JS-rendered sites.

| Operator | Fleet URL | Pass 1 (HTTP) | Pass 2 (Puppeteer) | Rigs Named | Spec PDFs | Notes |
|----------|----------|--------------|-------------------|-----------|-----------|-------|
| **Transocean** | deepwater.com/our-fleet/our-rigs | **YES** (200) | N/A | 26 | **26** (image-based) | Static HTML table + PDF links |
| **Borr** | borrdrilling.com/our-fleet | **YES** (200) | N/A | 31 | **31** | Next.js SPA, table in initial HTML |
| **Noble** | noblecorp.com/our-fleet | NO (403) | **YES** (200) | **31** | **28** | Rig cards with WD, design, location |
| **Seadrill** | seadrill.com/fleet/ | NO (JS) | **YES** (200) | **17** | **17** | Explicit type labels, tech sheets |
| **Valaris** | valaris.com/our-fleet | NO (403) | YES (200) | 0 | FSR PDF | Landing page only, needs sub-pages |
| **Nabors** | nabors.com/our-rigs | NO (404) | NO (404) | 0 | 0 | No fleet page found |
| **H&P** | hpinc.com/rig-fleet/flexrig-fleet | NO (JS) | YES (200) | 0 (3 models) | 1 fact sheet | FlexRig model specs only |

**Totals**: 5 of 7 operators accessible. **105 rigs named**, **102 individual spec PDFs** available.

**Decision**: Proceed with Step 4 for Transocean + Borr + Noble + Seadrill (105 rigs). Valaris via sub-page scrape or FSR PDF. H&P FlexRig model specs as rig class templates. Nabors KNOWN_VESSELS only.

## Detailed Findings

### Transocean (deepwater.com) — SCRAPABLE (Pass 1)

- **Fleet page**: `https://www.deepwater.com/our-fleet/our-rigs`
- **Format**: Static HTML table (Name, Type, Water Depth, Spec Sheet)
- **Rigs**: 26 listed (Deepwater Atlas, Titan, Poseidon, Proteus, Thalassa, Asgard, etc.)
- **PDF pattern**: `/documents/RigSpecs/{Rig Name}.pdf` (URL-encoded spaces)
- **PDF quality**: Image-based (PowerPoint-generated), may require OCR for text extraction
- **Detail pages**: None — only PDF links from fleet table
- **CSS selectors**:
  - `table tbody tr` — rig rows
  - `td:nth-child(1)` — rig name
  - `td:nth-child(2)` — rig type
  - `td:nth-child(3)` — water depth
  - `td a[href*="/documents/"]` — PDF download links
- **Rate limit**: 0.5 req/s sufficient
- **Config updated**: `fleet_url` → `https://www.deepwater.com/our-fleet/our-rigs`

### Borr Drilling (borrdrilling.com) — SCRAPABLE (Pass 1)

- **Fleet page**: `https://www.borrdrilling.com/our-fleet`
- **Format**: Next.js SPA, but table data present in initial HTML render
- **Rigs**: 31 jackups (Arabia I-III, Bestla, Forseti, Freyja, Galar, Gerd, Ran, Saga, Thor, etc.)
- **Table columns**: RIG NAME, DESIGN, BUILDER, YEAR BUILT, WATER DEPTH, DOWNLOAD
- **PDF links**: hosted on `api.borrdrilling.com/wp-content/uploads/...`
- **Detail pages**: Links to `api.borrdrilling.com/our_fleet/{slug}/` exist but redirect to homepage (SPA-only)
- **CSS selectors**: Material-UI generated classes (fragile, hash-based like `.css-16nxph9`)
- **Rate limit**: 0.5 req/s sufficient
- **Config updated**: `fleet_url` → `https://www.borrdrilling.com/our-fleet`

### Noble (noblecorp.com) — SCRAPABLE VIA PUPPETEER (Pass 2)

- **Pass 1**: HTTP 403 (Cloudflare WAF blocked raw requests)
- **Pass 2**: HTTP 200 via Puppeteer headless Chrome — full fleet page rendered
- **Fleet page**: `https://www.noblecorp.com/our-fleet`
- **Format**: Card-based grid layout, one card per rig with photo, name, design, water depth, location, availability
- **Rigs**: 31 named (Ocean Apex, Noble BlackHawk, BlackHornet, BlackLion, BlackRhino, Bob Douglas, Courage, Deliverer, Developer, Discoverer, Don Taylor, Endeavor, Faye Kozack, Gerry de Souza, Globetrotter I & II, GreatWhite, Innovator, Integrator, Interceptor, Intrepid, Invincible, Patriot, Resolve, Sam Croft, Stanley Lafosse, Tom Madden, Valiant, Venturer, Viking, Voyager)
- **Rig type classification** (inferred from water depth + design):
  - Drillships (12,000 ft WD): BlackHawk, BlackHornet, BlackLion, BlackRhino, Bob Douglas, Don Taylor, Sam Croft, Tom Madden (Gusto P10000); Faye Kozack, Stanley Lafosse (Samsung 96K); Gerry de Souza (Samsung 12000 DH); Valiant, Venturer, Viking, Voyager (Ship-shaped Samsung 96K)
  - Semisubmersibles (1,500-10,000 ft WD): Ocean Apex, Courage, Endeavor, GreatWhite, Developer, Deliverer, Discoverer, Globetrotter I/II, Patriot
  - Jackups (350-492 ft WD): Innovator, Integrator, Interceptor, Intrepid, Invincible, Resolve
- **Spec PDFs**: 28 individual PDFs on `s201.q4cdn.com` (e.g., `apex-specification-sheet-revised.pdf`)
- **Detail pages**: Per-rig pages at `noblecorp.com/our-fleet/fleet/fleet-details/2024/{name}/default.aspx`
- **FSR page**: `noblecorp.com/investors/reports-and-filings/fleet-status-report/default.aspx`
- **Data**: `data/modules/vessel_fleet/raw/contractor_scrape/noble.json`

### Seadrill (seadrill.com) — SCRAPABLE VIA PUPPETEER (Pass 2)

- **Pass 1**: HTTP 200 but Divi WordPress theme is JS-rendered — no rig data in static HTML
- **Pass 2**: HTTP 200 via Puppeteer — full fleet page rendered with rig cards
- **Fleet page**: `https://www.seadrill.com/fleet/`
- **Format**: Card-based layout with filter dropdowns (rig type, ownership, availability)
- **Rigs**: 17 named with explicit type labels:
  - Drillships (13): Sonangol Libongos, Sonangol Quenguela, West Auriga, West Capella, West Carina, West Gemini, West Jupiter, West Neptune, West Polaris, West Saturn, West Tellus, West Vela
  - Semisubmersibles (3): Sevan Louisiana, West Aquarius, West Eclipse, West Phoenix
  - Jackups (1): West Elara
- **Ownership**: 15 Seadrill Limited, 2 Sonadrill Holding Ltd (JV)
- **Tech sheet PDFs**: 17 individual PDFs at `seadrill.com/wp-content/uploads/` (e.g., `West_Capella-V2.pdf`)
- **FSR PDF**: `seadrill.com/wp-content/uploads/2025/08/Seadrill-Fleet-Status-Report-August-6-2025-vF.pdf`
- **Data**: `data/modules/vessel_fleet/raw/contractor_scrape/seadrill.json`

### Valaris (valaris.com) — PARTIAL (landing page only)

- **Pass 1**: HTTP 403 (Cloudflare WAF)
- **Pass 2**: HTTP 200 via Puppeteer — but fleet page is a **category landing page only**
- **Fleet page**: `https://www.valaris.com/our-fleet`
- **Format**: 4 clickable tiles (Drillships, Semisubmersibles, Jackups, Managed Platforms) with marketing text
- **Rigs**: No individual rig names on this page
- **Fleet composition** (from marketing text):
  - 12 of 13 drillships are 7th generation assets, dual derricks, two BOPs
  - 2 semisubmersibles (one DP, one moored in Australia)
  - "One of the world's largest jackup fleets", HPHT-capable, North Sea harsh environment
- **Sub-fleet pages** (need Phase 2 scrape):
  - `valaris.com/our-fleet/drillships/default.aspx`
  - `valaris.com/our-fleet/semisubmersibles/default.aspx`
  - `valaris.com/our-fleet/jackups/default.aspx`
  - `valaris.com/our-fleet/managed-platforms/default.aspx`
- **FSR PDF**: `s23.q4cdn.com/956522167/files/doc_downloads/2025/10/10232025-Fleet-Status-Report_FINAL.pdf`
- **Investor presentation**: `s23.q4cdn.com/956522167/files/doc_financials/2025/q2/Valaris-Investor-Presentation-July-2025.pdf`
- **Data**: `data/modules/vessel_fleet/raw/contractor_scrape/valaris.json`

### Nabors (nabors.com) — NOT FOUND

- **Pass 1**: HTTP 404 on `/rigs`, `/rig-technologies`
- **Pass 2**: HTTP 404 on `/our-rigs`, `/rig-technologies`, `/about`
- Land rig operator (~203 US rigs, 131 international)
- No individual rig listing found online
- Rely on KNOWN_VESSELS (2 rigs) — very sparse

### H&P (hpinc.com) — MODEL SPECS ONLY (Pass 2)

- **Pass 1**: JS-rendered (WordPress + NitroPack), no data in static HTML
- **Pass 2**: HTTP 200 via Puppeteer — FlexRig model specification page rendered
- **Fleet page**: `https://www.hpinc.com/rig-fleet/flexrig-fleet`
- **Format**: Tabbed interface with 3 FlexRig model classes, each with spec table
- **Individual rigs**: NOT listed (typical for land contractors with hundreds of near-identical units)
- **FlexRig model specs captured**:
  - **Flex3** (Skid & Walker): 675K-750K lbs hookload, 7500 psi mud line, TDS-11 HP top drive
  - **Flex5**: 675K-750K lbs hookload, up to 1M lbs setback, 3.64M lbs walking system
  - **Flex3W Arabia**: 1M lbs hookload, 800K lbs setback, 500+ ft single row walking
- **FlexRig Fleet Fact Sheet PDF**: `hpinc.com/wp-content/uploads/2025/08/FlexRig-Fleet.pdf`
- **Other fleet pages** (not scraped): T-Series Fleet, Offshore Drilling
- **Fleet stats**: 3,000+ wells/year, 65,000+M ft drilled/year
- **Data**: `data/modules/vessel_fleet/raw/contractor_scrape/helmerich_payne.json`

## Alternative Data Source: Fleet Status Reports (FSRs)

All major operators publish quarterly Fleet Status Reports as PDFs. These contain:
- Every rig name, type, and water depth rating
- Year built and design/class
- Current contract, operator, location
- Day rate and contract duration
- Availability dates

FSR PDFs are the most complete and current source. They are tabular and can be parsed with `tabula-py` or `pdfplumber`.

**Known FSR PDF locations**:
| Operator | FSR URL Pattern |
|----------|----------------|
| Transocean | `deepwater.com/investors/fleet-status-report` (or `investor.deepwater.com`) |
| Valaris | `s23.q4cdn.com/956522167/files/doc_downloads/2025/10/10232025-Fleet-Status-Report_FINAL.pdf` |
| Noble | `noblecorp.com/investors/reports-and-filings/fleet-status-report/default.aspx` |
| Seadrill | `seadrill.com/wp-content/uploads/2025/08/Seadrill-Fleet-Status-Report-August-6-2025-vF.pdf` |
| Borr | `api.borrdrilling.com/wp-content/uploads/...` |

## Scraping Infrastructure

- **Pass 1 tool**: `WebFetch` (raw HTTP, no JS execution)
- **Pass 2 tool**: `scripts/vessel_fleet/scrape_contractor_fleets.js` (Puppeteer + headless Chrome)
- **Raw data**: `data/modules/vessel_fleet/raw/contractor_scrape/` (JSON + PNG screenshots per operator)
- **Chrome**: Google Chrome 144.0, Puppeteer via `@modelcontextprotocol/server-puppeteer` node_modules
