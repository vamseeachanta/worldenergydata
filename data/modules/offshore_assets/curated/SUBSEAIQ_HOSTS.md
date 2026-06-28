# SubseaIQ Host Registry

Field-linked host-facility registry, ingested from the SubseaIQ `og_host` table.
Companion artifact: `subseaiq_hosts.csv`. Refs worldenergydata epic #567
(field-development playbook, calibration v2).

## Why this file exists

The in-repo `host_facilities.csv` is keyed by vessel name with **no field link**.
The SubseaIQ `og_host` table's *detailed* records additionally carry the
`Block(s)`, reserves, well counts, and — critically — the **named subsea-tieback
satellite fields** each host produces. That host→satellite relationship is what
the recommendation-engine calibration needs (see
`src/worldenergydata/field_development/host_enrichment.py`).

## Source & provenance

- **Source table:** `og_host.csv` from the SubseaIQ-derived `og-website-db`
  (phpMyAdmin dump of the AceEngineer O&G website DB, generated Aug 2014; data
  ~2009–2014). Much of it is sourced from public SubseaIQ project pages.
- **Licensing:** stale (~2014) and **freely usable** — confirmed for public
  worldenergydata (epic #567). No off-repo restriction.
- **Ingestion:** `scripts/field_development/ingest_subseaiq_hosts.py` parses the
  JSON `data` blob (`"Key : Value"` strings), keeping only detailed records that
  carry a `Block(s)` field link. The 147 FPSO records are vessel-spec-only (no
  field link) and already represented by `host_facilities.csv`, so they are
  skipped — in this data vintage the detailed schema covers **20 GoM spar
  hosts**.

## Contents

20 host records; 13 carry one or more subsea-tieback satellites (37 distinct
satellites, e.g. *Perdido* → *Great White (30); Tobago (1); Silvertip (2)*).
Columns: `host_name, host_concept, general_location, block_raw, bsee_block_key,
water_depth_m, reserves_mmboe, total_wells, dry_tree_wells, wet_tree_wells,
throughput_mboed, tieback_fields`.

`reserves_mmboe` is the table's `Reserves (MBOE)` value read as **MMboe** (its
magnitudes — e.g. Neptune ~75, Holstein ~300 — are field-scale millions).

## How it is used (calibration v2)

1. **Ground-truth correction.** The SubseaIQ facility-join mislabels a tieback
   satellite with its *host's* concept (so *Great White* — a subsea tieback to
   the *Perdido* spar — is recorded as `spar`). `correct_satellite_labels()`
   relabels these to `subsea_tieback` (19 fields in the GoM catalog).
2. **Input enrichment.** A satellite gains a reachable host (`host_spare_capacity`)
   and a screening `distance_to_host_km` (the table records no per-tieback
   offset, so a GoM-typical median stands in — disclosed in `host_enrichment.py`);
   a host field gains its reserves and well count.

This recovers subsea-tieback recall (0 → 19) and lifts back-test top-1 from
~44.5% to ~52% in combination with the basin prior. See
`docs/domains/field-development/calibration-v2.md`.
