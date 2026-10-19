# Operator aggregation report-review policy

This list supports the public HSE aggregation contract in
[issue 420](https://github.com/vamseeachanta/worldenergydata/issues/420) and
[issue 416](https://github.com/vamseeachanta/worldenergydata/issues/416).
It is an optional report-review aid, not a commit hook, CI gate, legal clearance,
or proof of anonymity. Repository-wide identifier gates remain retired.

## Source and coverage

`operator_names` transcribes the first twenty rows of BSEE's
[Production by Operator Ranked by Volume](https://www.data.bsee.gov/Production/Files/Rank%20File%20Oil%202024.pdf),
PDRANKOP, edition 01-Oct-2026, page 1, January–December 2024, ordered by Total Oil.
The row count is the policy scope requested in issue 420, not an engineering
acceptance limit. This is an oil ranking, not a gas ranking or combined-energy
ranking. BSEE publishes this URL as a changing report; the edition identifies
the transcription used here. No production quantities are copied.

Source-truncated labels are retained as printed. `operator_aliases` includes
shortened public names from those rows, spacing variants of Exxon Mobil, and
BP America, WPX, EOG and OXY explicitly requested in issue 420. The latter are
policy additions, not assertions of ranking, ownership or corporate succession.
A complete historical alias inventory is not established. Unlisted names,
misspellings, encoded text and indirect identifiers require manual review.

## Schema

The YAML mirrors the workspace list's section-of-entry format:

| Field | Meaning |
| --- | --- |
| `version` | Local schema version |
| `sources` | Public source title, edition where applicable, and URL |
| `default_severity` | `block` or `warn`; omitted means `block` |
| Rule sections | Lists of mappings, each containing a `pattern` |
| `pattern` | Nonempty literal text by default |
| `case_sensitive` | Boolean; omitted means false |
| `severity` | `block` or `warn`; omitted inherits the default |
| `regex` | Boolean extension; true explicitly enables Python regular expressions |

Table 1. Policy metadata and rule fields.

Literal rules are escaped before compilation. Word boundaries prevent short
names matching inside longer words. Placeholder rules match a single-letter
label following `operator` or `company`, ignoring case. Shared metadata,
including `exclusions`, is accepted; exclusions are deliberately not applied
inside the explicitly selected report directory. There is no whole-file bypass.

## Usage and results

Run from the repository with Python and PyYAML available:

```sh
bash scripts/legal/check-operator-aggregation.sh \
  --workspace-denylist ../workspace-hub/.legal-deny-list.yaml
```

The workspace policy path is required explicitly, so worktrees and standalone
checkouts cannot silently omit that half of the union. `--reports` selects a
report directory (default `reports/hse/`). `--operator-denylist` permits a
specific local policy version. Both lists are validated before any scanning.

Every regular file under the report directory is read as UTF-8, including
machine-readable sidecars. Linked inputs, unreadable or binary files, invalid
policies, missing directories and empty directories produce an input error.
The checker does not decode HTML entities, inspect images, or extract PDFs;
those require separate review. It reports relative file locations and line
numbers, without matched text, rule descriptions or source-list contents.

Exit status is zero for no blocking matches (warnings may remain), one for
blocking matches, and two for invalid or unreadable input. These are CLI status
codes, not engineering criteria. Existing historical reports are not rewritten
by this tool. Findings require contextual review before publication; absence of
matches does not establish aggregation quality or statistical validity.
