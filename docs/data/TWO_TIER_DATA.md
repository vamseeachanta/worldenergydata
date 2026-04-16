# Two-Tier Data Architecture

## Why

The full dataset (~12 GB) was too large for git. It was slimmed to ~400 MB by
moving large binary and raw files to a local mount, keeping only small processed
files in the repository.

## How

`scripts/setup-data-link.sh` creates a symlink from the repo's `data/` directory
to the external storage mount:

```
data/ -> /mnt/ace/worldenergydata/data/
```

The `DataResolver` (`src/worldenergydata/common/data_resolver.py`) resolves
paths in this order:

1. `WED_DATA_ROOT` env var (explicit override)
2. Symlink at `data/` (convention on dev machines)
3. Plain `data/` directory (fallback for CI or lightweight dev)

## What lives where

| Location | Contents | Size |
|---|---|---|
| **Git repo** `data/modules/` | Processed CSVs, catalogs, small datasets | ~400 MB |
| **Mount** `/mnt/ace/.../data/modules/bsee/` | BSEE binary files, zipped archives | ~2.7 GB |
| **Mount** `/mnt/ace/.../data/modules/hse/` | HSE raw OSHA CSV files | ~6.7 GB |

## CI / testing

No symlink or external mount is needed in CI. Tests that depend on the symlink
use `@pytest.mark.skipif` guards and degrade gracefully. Set `WED_DATA_ROOT` to
a temp directory to test the resolver without external data.

See `tests/integration/test_data_symlink.py` for the full verification suite.

## Reference

`RELOCATION-LOG.md` on `/mnt/ace/worldenergydata/` documents the original file
moves and checksums.
