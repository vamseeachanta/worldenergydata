# OpenLane artifact report replay

The sample replays an evidence inventory without executing OpenLane, OpenROAD,
or a PDK. It deliberately has no physical-design results. All metric categories
are `NOT_EVALUATED`; the report demonstrates missing-evidence handling and maps
the expected artifacts to semiconductor role keywords.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Add deterministic evidence reporting before collecting physical-design results. |

## Replay from a fresh checkout

Only the Python standard library is required. From the repository root:

```sh
python3 scripts/eda/report.py docs/examples/eda/manifest.json
```

Standard output is the committed [sample report](report.md), byte for byte.
Redirect output to a separate destination when saving a new report. The command
reads evidence and writes standard output; it never launches an EDA tool or
modifies the manifest or artifacts. Do not redirect output over an input file.

## Slices

- Slice 1: deterministic Markdown reporting, explicit evidence gaps, artifact
  explanations and role keywords; a committed manifest and replay report.
- Slice 2: explicit selection of finite numeric values from OpenLane's final
  metrics JSON, including user-supplied units and analysis basis.
- Slice 3: artifact inventory with SHA-256 digests, optional expected-digest
  verification, and relative-path confinement to the evidence directory.

These slices cover report infrastructure. RTL selection, functional simulation,
flow configuration, a pinned container/PDK environment and a real RTL-to-GDS run
remain later work. No timing, area, power, DRC/LVS or manufacturing qualification
is claimed by the sample.

## Manifest contract

The [sample manifest](manifest.json) is intentionally empty evidence. Copy it
beside a retained run's evidence before populating it. Paths resolve relative to
the manifest directory, independently of the current working directory.

Only these top-level objects are accepted:

| Object | Allowed fields | Meaning |
| --- | --- | --- |
| `provenance` | `openlane_version`, `container_image_digest`, `pdk_revision`, `standard_cell_library` | Nonempty text or null; record exact run identifiers from retained evidence. |
| `artifacts` | `rtl`, `config`, `metrics`, `timing`, `power`, `drc`, `lvs`, `def`, `gds`, `log` | Each entry is null or an object containing `path` and optional `sha256`. |
| `observations` | `timing`, `area`, `power`, `drc`, `lvs` | Each entry is null or an object containing nonempty `key`, `unit`, and `basis`. |

Omitted entries and null entries mean evidence has not been supplied.
Unknown fields, duplicate JSON keys, invalid types, ambiguous paths, paths that
escape the evidence directory through symlinks, and invalid digests are errors.
Artifact paths use forward slashes without empty, current-directory or parent
segments. Directories are not file artifacts. Missing files are `NOT_EVALUATED`;
a missing file with an expected digest is an integrity error. SHA-256 digests are
lowercase hexadecimal, as returned by Python's `hashlib.sha256().hexdigest()`.

For example, populate the metrics artifact with:

```json
{
  "artifacts": {
    "metrics": {"path": "final/metrics.json"}
  }
}
```

An observation selects an exact, top-level JSON key in that metrics artifact.
Choose the key from the actual output of the retained tool version; no guessed
key aliases, corner aggregation, rounding or unit conversion are used. For
example, an observation has this shape, with every placeholder replaced by
information read from the retained run:

```json
{
  "observations": {
    "timing": {
      "key": "EXACT_KEY_FROM_RETAINED_METRICS",
      "unit": "UNIT_FROM_RETAINED_OUTPUT",
      "basis": "Analysis stage, corner, constraints and source report"
    }
  }
}
```

Record area scope (cell/core/die), timing corner and setup/hold basis, power
activity assumptions and corner, and the specific DRC/LVS checker in `basis`.
The reporter cannot verify that a supplied unit or basis is correct. It copies
finite numeric data with decimal precision preserved: nulls, booleans, strings and non-finite numbers are
errors when selected. A missing selected key remains `NOT_EVALUATED`.

`PRESENT` means a file exists and its bytes were hashed. `REPORTED` means a
selected number was read. Neither means a design passed a check. Even a reported
zero DRC or LVS count requires the corresponding completed-tool report and
qualified rule deck before making a signoff claim. Provenance is recorded text,
not an authenticated environment. A matching digest establishes byte agreement,
not correctness or origin. Keep evidence immutable during replay; this utility
does not create a snapshot or inspect artifact formats.

## Sources and later flow setup

The following public sources were opened on 2026-10-19. They are rolling
references, not a pinned tool release or an execution record.

- [OpenLane Newcomers](https://openlane2.readthedocs.io/en/latest/getting_started/newcomers/index.html):
  Run directory, Final Results and Signoff Steps describe per-step logs,
  final metrics JSON, DEF/GDS views, STA, DRC and LVS evidence.
- [OpenLane Docker installation](https://openlane2.readthedocs.io/en/latest/getting_started/common/docker_installation/index.html):
  environment setup for later execution using bundled open-source tools.
- [OpenLane step reference](https://openlane2.readthedocs.io/en/latest/reference/step_config_vars.html):
  tool/checker descriptions; review against the selected release before choosing
  metric keys or qualification criteria.
- [Python JSON decoding](https://docs.python.org/3/library/json.html#json.load):
  `parse_float` supports decimal-preserving metric parsing.
- [Python hashlib Usage](https://docs.python.org/3/library/hashlib.html#usage):
  SHA-256 API and the published digest vector used by the tests.

Before a live demonstration, select a small RTL design, test its logic, provide
explicit timing requirements, and follow the upstream container instructions.
Record the exact OpenLane version, container image digest, PDK revision and
standard-cell library. Retain the resolved configuration, final metrics,
corner-specific timing/power reports, DRC/LVS reports, DEF/GDS and completion
logs under the evidence directory. No default numerical requirements or
acceptance limits are supplied here. Do not substitute this report for signoff.

## Verification

The isolated tests need pytest and do not require the application dependencies:

```sh
uv run --no-project --with pytest python -m pytest tests/unit/eda/test_report.py \
  --noconftest --override-ini addopts= -q -rA -p no:cacheprovider
```

The command disables the application-wide coverage arguments and conftest
because this standalone script uses no application modules. It runs every test
of the new reporter. Expected values come from a published SHA-256 example,
explicit literal fixtures, or the slack hand calculation in the test docstring.
