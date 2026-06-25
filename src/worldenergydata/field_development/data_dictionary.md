# `field_concept` Data Dictionary

The contract for the offshore field-development playbook (epic #567, issue #568).
The Pydantic model in `models.py` is the **source of truth**;
`schema/field_concept.schema.json` is generated from it (see `export_schema.py`)
and kept in sync by a unit test.

`name` is the only required field. Every other field is optional: a concept is
built up incrementally as the playbook reasons about it. Enums serialize to the
lower_snake_case string `value`s shown below.

## Identity
| Field | Type | Units | Notes |
|---|---|---|---|
| `schema_version` | str | — | Semver of this contract (currently `1.0.0`). |
| `name` | str | — | **Required.** Field/project name. |
| `operator` | str | — | Operating company. |
| `region` | str | — | Basin / geographic area. |

## Reservoir / fluid
| Field | Type | Units | Notes |
|---|---|---|---|
| `recoverable_reserves_mmboe` | float | MMboe | Recoverable reserves. |
| `fluid_type` | enum | — | `oil`, `gas`, `condensate`, `gas_condensate`. |
| `api_gravity` | float | °API | 0–100. |
| `gor_scf_stb` | float | scf/stb | Gas-oil ratio. |
| `viscosity_cp` | float | cP | Live-oil viscosity. |
| `wax_appearance_temp_c` | float | °C | WAT — flow-assurance driver. |
| `sour` | bool | — | H2S/CO2 present. |
| `hpht` | bool | — | High pressure / high temperature. |
| `reservoir_distribution` | enum | — | `compact_stacked`, `distributed` — drives dry-vs-wet tree. |

## Production
| Field | Type | Units | Notes |
|---|---|---|---|
| `plateau_rate_boed` | float | boe/d | Field plateau production rate. |
| `per_well_rate_boed` | float | boe/d | Per-well rate. |
| `num_wells` | int | count | Producer/injector well count. |
| `num_trees` | int | count | Trees (= `num_wells` for wet-tree concepts). |
| `num_manifolds` | int | count | Subsea manifolds. |
| `water_injection` | bool | — | Water injection planned. |
| `gas_injection` | bool | — | Gas injection / reinjection planned. |
| `field_life_years` | float | years | Expected producing life. |

## Location / physical
| Field | Type | Units | Notes |
|---|---|---|---|
| `water_depth_m` | float | m | Dominant concept gate (briefing §A2). |
| `distance_to_host_km` | float | km | To nearest existing host (tieback pivot). |
| `host_spare_capacity` | bool | — | Host has spare processing/slot capacity. |
| `distance_to_shore_km` | float | km | For subsea-to-shore / export. |
| `seabed_terrain` | str | — | Free text (e.g. flat, rugose, slope). |

## Concept / architecture (recommended or selected)
| Field | Type | Units | Notes |
|---|---|---|---|
| `concept_type` | enum | — | `fixed_jacket`, `compliant_tower`, `tlp`, `spar`, `semisub_fps`, `fpso`, `flng`, `subsea_tieback`, `subsea_to_shore`, `nui`. |
| `tree_type` | enum | — | `dry` (TLP/Spar) or `wet` (subsea). |
| `tieback_distance_km` | float | km | Required > 0 for `subsea_tieback`. |
| `topology` | enum | — | `satellite`, `cluster`, `daisy_chain`, `pigging_loop`. |
| `flowline_diameter_in` | float | in | Nominal flowline diameter. |
| `flowline_material` | enum | — | `rigid`, `flexible`, `pipe_in_pipe`. |
| `riser_type` | enum | — | `scr`, `slwr`, `flexible`, `hybrid_tower`, `ttr`. |

## Environment / regulatory
| Field | Type | Units | Notes |
|---|---|---|---|
| `metocean_regime` | enum | — | `benign`, `harsh_persistent`, `hurricane_cyclone`. |

## Commercial
| Field | Type | Units | Notes |
|---|---|---|---|
| `oil_price_usd_bbl` | float | $/bbl | Price-deck assumption. |
| `gas_price_usd_mmbtu` | float | $/MMBtu | Price-deck assumption. |
| `discount_rate` | float | fraction | e.g. `0.10`; must be in `[0, 1)`. |

## Timeline
| Field | Type | Units | Notes |
|---|---|---|---|
| `year_concept` | int | year | Concept-select year. |
| `year_feed` | int | year | FEED start year. |
| `year_fid` | int | year | Final investment decision. |
| `year_first_oil` | int | year | First oil/gas. |

## Provenance
| Field | Type | Units | Notes |
|---|---|---|---|
| `data_source` | str | — | Source attribution (per repo data rules), e.g. `"SubseaIQ (og-website-db, ~2014)"` or `"BSEE OGOR-A"`. |

## Validation layers
1. **Per-field (Pydantic, raises at construction):** required `name`, non-negative
   magnitudes/counts, `api_gravity` ∈ (0,100), `discount_rate` ∈ [0,1),
   unknown fields forbidden.
2. **Cross-field sanity gate (`sanity.py`, returns `SanityViolation` list):**
   - `wet_tree_well_tree_mismatch` — wet-tree concept with `num_trees != num_wells`.
   - `tieback_missing_distance` — `subsea_tieback` without positive `tieback_distance_km`.
   - `depth_outside_host_envelope` — `water_depth_m` outside the concept's band
     (`HOST_DEPTH_ENVELOPES_M`, briefing §A3).
   - `tree_type_concept_conflict` — `tree_type` disagrees with a concept that fixes it.

   Returning violations (not raising) lets the Phase-2 LLM concept-completion gate
   (#577) inspect and repair before re-checking.
