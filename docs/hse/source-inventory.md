# HSE source inventory

## Summary

The inventory lists 38 health, safety and environment data sources: what each is, its terms and format, whether it is held, and how it is refreshed. On 2026-11-12 the holdings covered 6 sources in full and 5 in part or as links; 11 are pulled by the monthly runner, 7 need a manual download and 11 wait for a decision on an account, a payment or the terms.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| Initial | 2026-11-12 | Inventory written so every source, its terms and its refresh state are recorded in one place. |

## Record

The record is [`data/modules/hse/source_inventory.yml`](../../data/modules/hse/source_inventory.yml). It complements the [source registry](source-registry.md), which holds the storage policy for the offshore evidence set. A value of "not confirmed" means the check could not be made on the date given. In the table below a dash means that nothing is held, so there is no count or date.

| Field | Meaning |
|---|---|
| `access` | `public_bulk` machine-readable download; `public_docs` public PDF or HTML only; `blocked` public, but the site refused non-browser clients on the check date; `login` free registration; `paid` paywall, membership or internal-use-only terms |
| `held` | `yes`, `partial`, `links_only` or `no`, with `held_where`, `held_records` and `held_latest_date` where known |
| `held_records_basis` | How each count was obtained and when. Held files are on external storage, not in git, so a count can be repeated only there |
| `refresh` | `monthly` (in `config/hse/monthly_sources.yml`), `manual` or `none`, with the script and the date of the last pull |
| `decision` | `owner` when the source needs an account, a payment or a terms decision; nothing is signed up for or scraped until then |

## Sources

| Source | Authority | Access | Held | Records held | Latest date held | Refresh | Last pull | Decision |
|---|---|---|---|---|---|---|---|---|
| [`bsee_incident_investigations`](https://www.data.bsee.gov/Other/Files/IncInvRawData.zip) | US Bureau of Safety and Environmental Enforcement (BSEE) | public_bulk | yes | 1987 | 2026-01-08 | monthly | 2026-11-12 | none |
| [`bsee_incs`](https://www.data.bsee.gov/Company/Files/INCSRawData.zip) | US Bureau of Safety and Environmental Enforcement (BSEE) | public_bulk | yes | 51872 | not confirmed | monthly | 2026-11-12 | none |
| [`bsee_incident_statistics`](https://www.bsee.gov/stats-facts/offshore-incident-statistics) | US Bureau of Safety and Environmental Enforcement (BSEE) | public_docs | partial | not confirmed | not confirmed | monthly | 2026-11-12 | none |
| [`bsee_investigation_reports`](https://www.bsee.gov/what-we-do/incident-investigations/offshore-incident-investigations/district-investigation-reports) | US Bureau of Safety and Environmental Enforcement (BSEE) | public_docs | links_only | 4 | 2023-06-19 | monthly | 2026-11-12 | none |
| [`bsee_safety_alerts`](https://www.bsee.gov/guidance-and-regulations/guidance/safety-alerts-program) | US Bureau of Safety and Environmental Enforcement (BSEE) | public_docs | no | - | - | monthly | 2026-11-12 | none |
| [`phmsa_pipeline_incidents`](https://www.phmsa.dot.gov/data-and-statistics/pipeline/distribution-transmission-gathering-lng-and-liquid-accident-and-incident-data) | US Pipeline and Hazardous Materials Safety Administration (PHMSA) | blocked | partial | 2795 | 2017-01-09 | manual | 2026-05-05 | none |
| [`uscg_misle`](https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-and-Pollution-Data-for-Researchers/) | US Coast Guard | blocked | no | - | - | manual | none | none |
| [`uscg_cgmix`](https://cgmix.uscg.mil/IIR/IIRSearch.aspx) | US Coast Guard | public_docs | partial | 15 | 2024-10-12 | none | not confirmed | none |
| [`uscg_boating_accidents`](https://www.uscgboating.org/statistics/accident_statistics.php) | US Coast Guard | public_bulk | yes | 63340 | 2012-12-31 | none | 2025-10-05 | none |
| [`noaa_incident_news`](https://incidentnews.noaa.gov/) | US NOAA Office of Response and Restoration | public_bulk | yes | 4797 | 2025-09-29 | none | 2025-10-05 | none |
| [`ntsb_marine`](https://www.ntsb.gov/Pages/carol.aspx) | US National Transportation Safety Board | login | no | - | - | manual | none | owner |
| [`uscg_nrc`](https://nrc.uscg.mil/) | US Coast Guard National Response Center | blocked | no | - | - | manual | 2026-11-12 | none |
| [`csb`](https://www.csb.gov/investigations/completed-investigations/) | US Chemical Safety and Hazard Investigation Board | public_docs | no | - | - | monthly | 2026-11-12 | none |
| [`osha`](https://enforcedata.dol.gov/views/data_catalogs.php) | US Occupational Safety and Health Administration | public_bulk | yes | not confirmed | not confirmed | manual | 2026-02-16 | none |
| [`epa_tri`](https://www.epa.gov/toxics-release-inventory-tri-program) | US Environmental Protection Agency | public_bulk | yes | 51487 | not confirmed | manual | 2026-02-10 | none |
| [`uk_hse_offshore_statistics`](https://www.hse.gov.uk/offshore/statistics.htm) | UK Health and Safety Executive | public_docs | no | - | - | monthly | 2026-11-12 | none |
| [`uk_hcr`](https://oeuk.org.uk/industry-support/hse/hydrocarbon-release/) | Offshore Energies UK (current); UK HSE (archived) | public_docs | no | - | - | none | none | owner |
| [`uk_maib`](https://www.gov.uk/maib-reports) | UK Marine Accident Investigation Branch | public_bulk | no | - | - | monthly | 2026-11-12 | none |
| [`opred_pon1`](https://itportal.energysecurity.gov.uk/irs/publications/pon1/) | UK Offshore Petroleum Regulator for Environment and Decommissioning | public_docs | links_only | - | - | none | none | none |
| [`step_change_in_safety`](https://www.stepchangeinsafety.com/alerts-learnings) | Step Change in Safety | public_docs | no | - | - | none | none | owner |
| [`havtil_rnnp`](https://www.havtil.no/en/explore-technical-subjects2/rnnp/) | Havtil (Norwegian Ocean Industry Authority, formerly PSA) | public_docs | no | - | - | monthly | 2026-11-12 | none |
| [`emsa_emcip`](https://www.emsa.europa.eu/emcip.html) | European Maritime Safety Agency | public_docs | no | - | - | monthly | 2026-11-12 | none |
| [`eu_offshore_safety_reports`](https://energy.ec.europa.eu/topics/energy-security/safety-offshore-oil-and-gas-operations_en) | European Commission | public_docs | no | - | - | none | none | none |
| [`dmaib`](https://dmaib.com/reports/) | Danish Maritime Accident Investigation Board | public_docs | no | - | - | none | none | none |
| [`helcom`](https://helcom.fi/baltic-sea-trends/maritime/accidents/) | Baltic Marine Environment Protection Commission (HELCOM) | public_docs | no | - | - | none | none | owner |
| [`nopsema`](https://www.nopsema.gov.au/about/planning-and-reporting/industry-and-nopsema-performance-reports) | NOPSEMA | public_docs | no | - | - | none | none | none |
| [`atsb_marine`](https://www.atsb.gov.au/) | Australian Transport Safety Bureau | public_docs | no | - | - | none | none | none |
| [`tsb_canada_marsis`](https://www.tsb.gc.ca/eng/stats/marine/data-6.html) | Transportation Safety Board of Canada | blocked | no | - | - | manual | 2026-11-12 | none |
| [`cnloer`](https://www.cnlopb.ca/incidents/) | Canada-Newfoundland and Labrador Offshore Energy Regulator | public_docs | no | - | - | none | none | none |
| [`brazil_anp_incidents`](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/incidentes-seguranca-operacional) | Brazil ANP | public_bulk | no | - | - | none | none | owner |
| [`imo_gisis`](https://gisis.imo.org/Public/MCI/Default.aspx) | International Maritime Organization | login | no | - | - | none | none | owner |
| [`iogp`](https://data.iogp.org/) | International Association of Oil and Gas Producers | login | no | - | - | none | none | owner |
| [`iadc_isp`](https://iadc.org/health-safety-environment/incident-statistics-program/) | International Association of Drilling Contractors | paid | no | - | - | none | none | owner |
| [`imca_safety_flashes`](https://www.imca-int.com/resources/safety/safety-flashes/) | International Marine Contractors Association | public_docs | no | - | - | monthly | 2026-11-12 | none |
| [`itopf`](https://www.itopf.org/knowledge-resources/data-statistics/oil-tanker-spill-statistics-2025/) | ITOPF | public_docs | no | - | - | none | none | none |
| [`oreda`](https://oreda.com/) | OREDA | paid | no | - | - | none | none | owner |
| [`dnv_woad`](https://www.dnv.com/) | DNV | paid | no | - | - | none | none | owner |
| [`sintef_blowout`](https://www.sintef.no/) | SINTEF | paid | no | - | - | none | none | owner |

## Gaps

- No scheduler entry ran any HSE refresh before this inventory; the held BSEE copy was 269 days old on the check date (2026-02-16 to 2026-11-12).
- Counts of held records come from the held files and databases on the check date; each entry states its basis. The trial download of 2026-11-12 was not retained.
- Machine-readable causes are held for pipelines only. For the other equipment classes the causes are in investigation reports, held as links.
- `phmsa_pipeline_incidents`: public, but automated download was refused on 2026-11-12; a browser download is needed.
- `uscg_misle`: public, but automated download was refused on 2026-11-12; a browser download is needed.
- `uscg_nrc`: public, but automated download was refused on 2026-11-12; a browser download is needed.
- `tsb_canada_marsis`: public, but automated download was refused on 2026-11-12; a browser download is needed.
- Sources marked `owner` are not collected.
