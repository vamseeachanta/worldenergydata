MAJOR

**Findings**

- `scripts/legal/legal-sanity-scan.sh:1` - required scanner is still untracked. `git status --short --branch` reports `?? scripts/legal/`, and the focused `git diff -- scripts/legal/legal-sanity-scan.sh ...` produced no scanner diff. The script exists and is executable because `scripts/legal/legal-sanity-scan.sh` ran successfully, but the final branch diff would not carry the scanner unless this untracked directory is added. That leaves the prior MAJOR not durably fixed.

**Verified**

- Legal scan command evidence: `legal-sanity-scan: PASS`.
- Summary HTML source-atlas link fix looks correct in the focused diff:
  - same-root rows get `../../` hrefs via `packages/.../dossiers/html.py:111`.
  - rows carrying `source_link_not_relative_to_output_root` render escaped text, not a misleading href, at `packages/.../dossiers/html.py:109-110`.
  - per-field pages avoid links when `source_field_atlas_href` is absent at `packages/.../dossiers/html.py:130-133`.

**Commands Run**

- `git status --short --branch`
- `git diff --stat`
- `git diff -- scripts/legal/legal-sanity-scan.sh packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md`
- `scripts/legal/legal-sanity-scan.sh`
- `rg -n source_field_atlas_report_path packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers tests/unit/texas_rrc`

I did not run pytest, full-repo scans, or `scripts/legal/legal-sanity-scan.sh --all`.
