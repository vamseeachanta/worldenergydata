# Data Outputs Site (GitHub Pages)

A static site that publishes worldenergydata's deterministic analysis outputs as
browsable HTML, hosted free on GitHub Pages. No server, no login, no API key.

## Good practices adopted (and where they come from)

These are borrowed from public upstream-data "copilot" projects and adapted to a
**static** site, which fits our data better than a hosted app:

| Practice | How we do it here |
|----------|-------------------|
| **Deterministic core, AI as narrative only** | All numbers are computed by unit-tested domain code and frozen into `reports/`. `scripts/build_pages.py` only renders them — it performs no calculation, so it can never change a sanctioned number. |
| **No API key / no server** | Pure static HTML. A static site has nothing to call, so "works without a key" is true by construction (and free + permanent vs. a hosted dyno). |
| **Certified core, byte-identical** | The economics page renders the **sanctioned V30** report; terminal NPV reconciles to the baseline (residual $0.0000) and is shown as-is, never reframed value-positive. |
| **Honest about missing data** | Every page carries a visible "Data limits & honest caveats" disclosure (e.g. water-depth/HPHT absent from structured OGOR-A; wells without surveys are omitted, not interpolated). |
| **Public-data provenance** | Each page states its source (BSEE OGOR-A / Well Activity Reports) and the specific model that produced its numbers. |
| **Feedback call-to-action** | Footer links to open an issue for errors or missing views. |
| **No fragile dependencies** | The generator is stdlib-only (no `pip`/`uv` resolution at build time), so it runs identically locally and in CI. |

## Build locally

```bash
python scripts/build_pages.py   # writes public/ (gitignored; rebuilt in CI)
# open public/index.html in a browser
```

## How it's hosted

`.github/workflows/pages.yml` rebuilds the site from `reports/` on every push to
`main` and deploys via the official Pages actions. The built `public/` directory
is **not** committed — CI regenerates it, so what ships always matches source.

**One-time enable (repo admin):** Settings → Pages → Build and deployment →
Source = **GitHub Actions**.

## Current scope

Julia (lease G20351) Lower-Tertiary subsea development: field economics (V30 NPV)
and 3D well paths. Add a page by dropping a new report into `reports/` and a
render block into `scripts/build_pages.py`.
