# Explicit riser-fatigue input preflight

The preflight prepares configuration data for the riser-fatigue bridge described
in issue #790. It executes no analysis and does not import digitalmodel. The
existing live card generator does not consume this bundle yet. The offline
summary import in pull request #1476 is a separate result-data interface.

Run the standalone CLI with an explicit input document and a new output file:

```bash
python scripts/demo/_riser_config.py input.json \
  --results-dir results --out prepared.json
```

The output parent directory must exist. Existing output files are preserved,
including when the output names the input. The future results directory is only
recorded; preflight does not create it. Relative results paths are retained, so a
future consumer must resolve them against its intended workflow configuration
directory before execution.

## Input contract

The input is a JSON object with exactly the following fields. There are no
engineering defaults. JSON booleans and numeric strings are rejected as numbers;
numbers must be finite. Duplicate JSON keys are rejected at every object level.

| Field | Required content |
| --- | --- |
| `design_life_years` | Positive design life in years |
| `dff` | Positive design fatigue factor, dimensionless |
| `sn_curve` | Nonempty `curve` and `environment` strings |
| `segments` | Nonempty list of segments with unique identifiers |
| `sources` | Nonempty references keyed by the four fields above |

Table 1. Required top-level fields and their units.

Each segment requires nonempty `id` and `material` strings, positive
`outer_diameter_mm` and `wall_thickness_mm`, and at least one of `wave` or
`viv_cases`. The bore must be positive: outer diameter minus the two walls. This
is a geometry identity, not a standards-derived acceptance limit.

A `wave` object requires nonempty `stress_ranges_MPa` and `cycles` arrays of equal
length, a positive `scf`, and positive `histogram_period_years`. Stress ranges are
positive; cycle counts are nonnegative. The stress concentration factor is
dimensionless. No histogram period or concentration factor is inferred.

`viv_cases` is a nonempty list of objects, each with positive `stress_range_MPa`,
positive `frequency_hz`, and `exposure_fraction` greater than zero and no greater
than one. The exposure is a dimensionless fraction of a year. Hour-based aliases
are deliberately excluded to avoid introducing a calendar conversion here.

Unknown fields, per-segment curve overrides and incomplete contributions are
rejected. Omit an absent loading contribution; an empty contribution does not
stand for an established zero load.

Each source reference shall identify the document, revision or edition, and
section or table covering the supplied values. The `segments` reference shall
cover every supplied segment's dimensions, material, histogram, concentration
factor, period and VIV exposure. Multiple references may be recorded in that
string. Assumptions shall be identified as assumptions. Preflight checks the
presence of reference text only; it cannot authenticate its contents.

## Output and qualification

The JSON bundle contains `workflow_config`, `sources`, `input_sha256` and
`engineering_qualification`. The digest identifies the exact input bytes read
by the CLI. It does not establish source authenticity or protect an edited
bundle. The pure `prepare_riser_config` function returns the same fields except
the input digest, because it receives a parsed object rather than source bytes.

`workflow_config` contains the `riser_fatigue` basename, validated settings and
the caller-supplied results directory. The bundle itself is not an engine input.
A future bridge will need to validate and select that field, resolve paths,
execute the intended workflow, and verify its result contract.

Engineering qualification is always `NOT_EVALUATED`. Curve availability, source
authenticity, loading provenance, geometry applicability, standards compliance,
fatigue life and design acceptance are not established by preflight. No fatigue
equation, S-N coefficient or fatigue-factor default is introduced.

## Sources and test basis

The field contract is read from `digitalmodel`,
`src/digitalmodel/riser_fatigue/workflow.py`, revision
`6476218e8f5af3fa7d16c3dafc60b6a9084c6e6c`: `router`, `_evaluate_segment`,
`_wave_damage` and `_viv_damage`. This is an interface reference, not a citation
for the engineering inputs or a qualified fatigue implementation.

`tests/unit/hse/test_riser_config.py` supplies synthetic adapter inputs and states
independent checks in its docstrings: bore subtraction, matched bin counts and
fractional exposure bounds. These are validation tests rather than published
worked fatigue examples. No engineering conclusion is inferred from them.
