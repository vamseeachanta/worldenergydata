# Operator aggregation report-review policy

This list supports the public HSE aggregation contract in
[issue 420](https://github.com/vamseeachanta/worldenergydata/issues/420) and
[issue 416](https://github.com/vamseeachanta/worldenergydata/issues/416).
It is an optional report-review aid, not a commit hook, CI gate, legal clearance,
or proof of anonymity. Repository-wide identifier gates remain retired.

## Source and coverage

`operator_names` transcribes the first twenty rows of BSEE's
[Production by Operator Ranked by Volume](https://www.data.bsee.gov/Production/Files/Rank%20File%20Oil%202024.pdf),
PDRANKOP, edition 15-Oct-2026, page 1, January–December 2024, ordered by Total Oil.
The row count is the policy scope requested in issue 420, not an engineering
acceptance limit. This is an oil ranking, not a gas ranking or combined-energy
ranking. BSEE publishes this URL as a changing report. The edition was retrieved
on 22-Oct-2026, and all twenty selected labels were compared in source order.
No archived copy of the earlier cited edition was verified; the citation now
identifies the retrieved report. No production quantities are copied.

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
| `case_sensitive` | Boolean; omitted means false; literals also accept uppercase |
| `severity` | `block` or `warn`; omitted inherits the default |
| `regex` | Boolean extension; true explicitly enables Python regular expressions |
| `description` | Optional descriptive metadata; never printed |

Table 1. Policy metadata and rule fields.

Literal words are escaped and joined by one or more whitespace characters,
including line breaks, tabs and non-breaking spaces. Word boundaries prevent
short names matching inside longer words. Case-sensitive literals match their
as-written or all-uppercase spelling to retain detection in headings and tables.
Single-word aliases exclude lowercase terms, including those before a hyphen.
The ambiguous bridge-plug abbreviation produces a warning rather than a block.
Full operator names and multiword aliases still block regardless of case.
Lowercase single-word aliases are intentionally outside automatic detection;
warnings and indirect references require contextual review.

Placeholder rules match an uppercase single-letter or numeric label following
`operator`, `operators`, `company` or `companies`; only the keyword ignores case.
Quotes, Markdown emphasis, and a separating hyphen or colon are supported.
Lowercase letters and mixed alphanumeric labels remain outside this rule.
Unknown rule fields are rejected; descriptive metadata is permitted.
Shared metadata, including `exclusions`, is accepted; exclusions are deliberately
not applied inside the explicitly selected report directory. There is no whole-file bypass.

## Usage and results

Run from the repository with Python and PyYAML available:

```sh
bash scripts/legal/check-operator-aggregation.sh \
  --workspace-denylist ../workspace-hub/.legal-deny-list.yaml
```

The workspace policy path is required explicitly, so worktrees and standalone
checkouts cannot silently omit that half of the union. `--reports` selects a
report directory (default `reports/hse/`). `--operator-denylist` permits a
specific local policy version. Both lists are validated before any scanning;
each must supply at least one rule. An empty section is permitted only when
another section in the same policy supplies rules.

Every regular file under the report directory is read as UTF-8, including
machine-readable sidecars. Linked inputs, unreadable or binary files, invalid
policies, missing directories and empty directories produce an input error.
HTML entities are decoded in `.html` and `.htm` files, retaining physical source
line numbers. Other formats are scanned as text. Images, PDFs, names split by
HTML elements and multiply encoded content require separate review.
The checker reports relative file locations and line numbers, without matched
text, rule descriptions or source-list contents.

Exit status is zero for no blocking matches (warnings may remain), one for
blocking matches, and two for invalid or unreadable input. These are CLI status
codes, not engineering criteria. Existing historical reports are not rewritten
by this tool. Findings require contextual review before publication; absence of
matches does not establish aggregation quality or statistical validity.
The Phase 1A and Phase 1B memo scans remain a separate acceptance criterion
under issue 420; this policy does not establish that those memos pass.
