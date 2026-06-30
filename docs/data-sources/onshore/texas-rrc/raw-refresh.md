# Texas RRC Raw Refresh

Raw Texas RRC snapshots are refreshed from official RRC source URLs only. The
current refresh implementation supports official GoDrive single-file datasets.
Official GoDrive directory datasets remain in the catalog, but are skipped until
directory fanout and pagination handling are implemented. The default storage
root is:

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

Each refresh attempt writes a JSON manifest under `manifests/` with:

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
