# Cross-country field-development benchmark — generated artifact

**Both files in this directory are generated. Do not hand-edit them.** An edit
is silently reverted by the next regeneration, and the repo looks correct in the
meantime — that is exactly how Australia went missing (see
[#831](https://github.com/vamseeachanta/worldenergydata/issues/831)).

## Regenerating

From the repo root:

```bash
python -m worldenergydata.production.unified.benchmark_report
```

This rewrites both files below. It is CI-safe — the default `RegionRouter`
resolves to fixture/mock adapters, so no 300MB BSEE binary and no network access
are required.

Generator: `packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py`

### When to re-run

Re-run and re-commit both files whenever:

- a region adapter gains real data or its fixtures change
  ([#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Spain
  per-field density and
  [#842](https://github.com/vamseeachanta/worldenergydata/issues/842) Keathley
  Canyon ingest are the expected triggers);
- a region is added to or removed from `RegionRouter`;
- `cross_basin._FISCAL_REGIMES` changes.

### Checking for staleness

Regenerate into a temp directory and diff against the committed files. They
should be byte-identical apart from `meta.generated_utc`, which is a wall-clock
stamp. Any other difference means the committed artifact is stale.

### Rendering a presentation change from retained facts

For a theme or navigation change, render the retained facts without querying
adapters or recalculating economics. Set `RENDER_OUTPUT` to a file in an existing
temporary directory outside the repository, then run from the repository root:

```bash
python - <<'PY'
import json
import os
from pathlib import Path

from worldenergydata.production.unified.benchmark_report import render_benchmark_html

facts = Path("reports/field_benchmark/_facts.json")
original = facts.read_bytes()
output = Path(os.environ["RENDER_OUTPUT"])
output.write_text(render_benchmark_html(json.loads(original)), encoding="utf-8")
assert facts.read_bytes() == original
PY
```

Compare the rendered table cells, row provenance and status summary with the
committed page before copying the output to `index.html`. Keep `_facts.json`
byte-identical. This workflow preserves the data vintage and its limitations;
it does not refresh sources or reconcile the separate economics representations.
The page links its retained facts locally; external dataset publication remains
a separate change. Its explicit light/dark themes also follow system preference.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The published page. Fully self-contained — inline CSS, zero external assets. Copied verbatim to `public/field_benchmark/` by `scripts/build_pages.py`. |
| `_facts.json` | The whole benchmark dict serialized, including per-row economics and the provenance maps. Also copied verbatim to `public/`. |
| `README.md` | This file. Never published — `build_pages.py` copies only the two files above. |

## Status vocabulary

Two independent axes. Do not conflate them.

**Row-level `provenance`** — only ever `real` or `seed`:

- `real` — every source tag for the region is in the `_REAL_SOURCES` allowlist
  in `benchmark_report.py`. Fail-closed: any unrecognised, blank, or `*_mock`
  tag makes the whole region `seed`, so an unknown source can never be upgraded
  to real by naming luck.
- `seed` — illustrative synthetic data from the region adapter. Not measured
  regulatory production.

**Region-level `region_status`** — `real`, `seed`, or `screening-only`:

- `screening-only` — the region is registered in `RegionRouter`, but its adapter
  returned no production rows. It contributes **no rows at all**; no
  zero-economics row is ever fabricated for it. Australia is currently the only
  one.

`region_status` also carries a `fiscal_regime_source` sibling map recording, per
region, whether its royalty/tax figures come from that country's own regime
(`country-specific`) or from the generic placeholder default
(`generic-default`). Spain published a placeholder 36.25% government take until
[#831](https://github.com/vamseeachanta/worldenergydata/issues/831) gave it its
own regime — the map exists so that can be spotted rather than inferred.

Fiscal coefficients throughout are simplified public approximations. They are
**not** legal or financial advice.
