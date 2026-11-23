# Texas RRC Raw Refresh

Raw Texas RRC snapshots are refreshed from official RRC source URLs only. The
refresh implementation supports official GoDrive single-file datasets and
official GoDrive directory datasets. The default storage root is:

`/mnt/ace/worldenergydata/data/modules/texas_rrc`

Validation surfaces such as PatchOps and RRC EWA lease-query pages are excluded
from raw refresh. They remain useful for query validation, but curated outputs
must be reproducible from official RRC snapshots.

## Commands

List configured sources and refresh status:

```bash
uv run worldenergydata texas-rrc refresh --list-sources
```

Dry-run one source without network writes:

```bash
uv run worldenergydata texas-rrc refresh --dry-run --source production_pdq
```

Dry-run an official GoDrive directory source and show fanout/selection:

```bash
uv run worldenergydata texas-rrc refresh --dry-run --source well_gis_layers
```

Refresh a directory source by explicit date window:

```bash
uv run worldenergydata texas-rrc refresh \
  --source directional_surveys \
  --since-date 2026-06-01 \
  --through-date 2026-06-30
```

Refresh one direct-source snapshot:

```bash
uv run worldenergydata texas-rrc refresh --source production_pdq
```

Refresh every currently supported direct-source catalog entry:

```bash
uv run worldenergydata texas-rrc refresh --all
```

For test or staging environments, override the output root:

```bash
uv run worldenergydata texas-rrc refresh --dry-run --source production_pdq --output-root /tmp/texas_rrc
```

## Manifest Schema

Each refresh attempt writes a JSON manifest under `manifests/`. Single-file
manifests include:

- `source_id`
- `source_url`
- `download_url`
- `effective_url`
- `retrieved_at`
- `refresh_cadence`
- `raw_path`
- `checksum_sha256`
- `byte_size`
- `status`
- `error`

Downloads are written to `*.part` files and atomically renamed after the byte
size, SHA256 checksum, expected GoDrive filename, and `Content-Length` are
validated. Transient download failures are retried up to three times with
partial-file cleanup before each retry. If a source returns HTML instead of a
data artifact, refresh fails closed and writes an error manifest.

Directory manifests set top-level `raw_path` to the target raw directory,
top-level `checksum_sha256` to `null`, and top-level `byte_size` to the sum of
selected files. They also include `artifacts`, with one record per selected
file:

- `filename`
- `raw_path`
- `effective_url`
- `retrieved_at`
- `source_modified_label`
- `source_size_label`
- `checksum_sha256`
- `byte_size`
- `status`
- `error`

Directory refreshes stage files under `.staging-<source>-<timestamp>` inside
the target raw directory. Staged files are promoted only after every selected
file downloads and validates. If any file fails, staging is removed and
existing final raw files are left unchanged.

## Directory Selection

Default selection is source-specific:

| Source | Default |
|---|---|
| `completion_data` | latest `MM-DD-YYYY.zip` filename |
| `directional_surveys` | latest `MM-DD-YYYY.zip` filename |
| `well_gis_layers` | all `well*.zip` files, including `wellFED.zip` |
| `pipeline_gis_layers` | all `pipeline*.zip` files |

Use `--selection latest`, `--selection all`, or date-window options to override
directory defaults where appropriate. Date-window options apply only to
directory sources.
