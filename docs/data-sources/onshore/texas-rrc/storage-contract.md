# Texas RRC Storage Contract

Texas RRC heavy data belongs outside git under:

`/mnt/ace/worldenergydata/data/modules/texas_rrc`

The repository stores source catalogs, loaders, validators, tests, and report
builders. Raw downloads, normalized outputs, curated field-atlas outputs, and
manifests live under `/mnt/ace`.

## Directory Layout

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/
  raw/
    production/pdq/
    wellbore/query/
    permits/drilling/
    completions/
    directional_surveys/
    gis/wells/
    gis/pipelines/
    reference/field_lease_operator/
    validation/rrc_ewa_lease_query/
    validation/patchops_rrc/
  normalized/
    production/pdq/
    wellbore/query/
    permits/drilling/
    completions/
    directional_surveys/
    gis/wells/
    gis/pipelines/
    reference/field_lease_operator/
    validation/rrc_ewa_lease_query/
    validation/patchops_rrc/
  curated/
    production/field_atlas/
    well_lifecycle/spine/
    well_lifecycle/permits/
    well_lifecycle/completions/
    well_lifecycle/directional_surveys/
    infrastructure/well_layers/
    infrastructure/pipeline_layers/
    reference/field_lease_operator/
    validation/rrc_ewa_lease_query/
    validation/patchops_rrc/
```

## Path Rules

All raw, normalized, and curated paths in the machine-readable source catalog
must be absolute and must remain under
`/mnt/ace/worldenergydata/data/modules/texas_rrc`.

The source catalog is a contract, not a downloader. Later refresh code will use
the catalog to decide where source snapshots and manifests are written.

## Source-of-Record Rule

Official Texas RRC public bulk datasets are the durable source of record.
PatchOps and RRC EWA web-form queries may be used to validate joins, inspect
nearby pipelines, and prototype geometry or production lookups, but curated
outputs must be reproducible from official RRC snapshots stored under `/mnt/ace`.
