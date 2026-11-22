# Survey archive integrity

The well-path demo reads directional surveys as text after checking the complete
ZIP against a required SHA-256 digest. It does not read or write pickle caches.
This prevents downloaded or legacy cached objects from executing through Python
unpickling. The selected digest identifies the approved archive version.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-22 | Document verified text loading and an offline example to replace unpickling. |
| 1 | 2026-10-24 | Validate every CSV record width before table construction to reject absent fields. |
| 2 | 2026-11-22 | Add a raw-station envelope that retains provenance and unresolved depth units for database inputs. |

## Inputs and method

Supply `--survey-sha256` with the digest of an independently reviewed, trusted
archive. A digest calculated from the same unreviewed download establishes no
independent trust. The public dataset changes, so the demo supplies no built-in
pin. Record and review the digest through a trusted channel before running:

```bash
uv run python scripts/bsee/demo_well_path_julia.py --survey-sha256 "$SURVEY_SHA256"
```

The demo downloads the fixed HTTPS source only when the ZIP is absent. HTTP
errors and redirects stop acquisition. Every invocation checks the digest,
including when a ZIP already exists. Verification and parsing use the same open
file, avoiding a second path lookup between those operations. The archive must
contain exactly one `dsptsdelimit.txt` member; it is opened directly without
extracting archive paths.

The text is headerless. Column order is pinned to
`WellData._get_column_names_for_dsptsdelimit_file` in
`packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/well_data.py`.
Identifiers remain strings, direction codes are stripped and checked, and numeric
columns must parse as numbers. The first record remains data. Invalid digests,
mismatched archives and incompatible schemas raise errors before rendering.
Every CSV record must contain all 13 fields before the table is constructed.
This rejects mixed valid and short records that pandas could otherwise pad with
missing values. An explicitly empty optional coordinate field remains accepted;
an absent field is a schema error. Quoted fields follow CSV record boundaries,
including quoted line breaks, and width errors identify the record number.
Existing geometry validation still rejects missing critical numeric inputs.

Legacy `dsptsdelimit.bin` files are ignored and left untouched. A failed or
interrupted download is retained for inspection; a subsequent invocation refuses
its mismatched digest. Retain the suspect file separately before providing a
verified replacement. Automatic cache conversion would require unpickling and is
not supported. No derived text or binary cache is created.

## Offline worked example

The following example runs from the repository root with pandas and httpx
installed. It creates a synthetic archive under the configured temporary folder
and leaves it available for inspection. The digest calculation represents a
trusted local fixture; it is not a method of approving network data.

```python
import hashlib
import importlib.util
import tempfile
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "survey_demo", "scripts/bsee/demo_well_path_julia.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

folder = Path(tempfile.mkdtemp(prefix="survey-example-"))
demo.DSPTS_DIR = str(folder)
demo.DSPTS_ZIP = str(folder / "dsptsdelimit.ZIP")
# Synthetic inputs, following the repository's raw-table column order:
row = "000000000001,10,0,100,N,20,0,E,99,1,2,-90,28\n"
with zipfile.ZipFile(demo.DSPTS_ZIP, "w") as archive:
    archive.writestr("dsptsdelimit.txt", row + row)
approved_digest = hashlib.sha256(Path(demo.DSPTS_ZIP).read_bytes()).hexdigest()
frame = demo.load_surveys(approved_digest)
print(frame["API_WELL_NUMBER"].tolist())
print(frame["SURVEY_POINT_MD"].tolist())
```

Answer: the identifier list is `['000000000001', '000000000001']` and the measured
depth list is `[100, 100]`. These expectations follow by direct transcription:
two input rows give two records; the first field retains its leading zeros, and
the fourth field in each row is the numeric value `100`. No trajectory equation
or engineering acceptance limit is added by this loader.

## Raw-station envelope

`worldenergydata.bsee.data.survey_envelope.build_survey_envelope` accepts exact
retained UTF-8, headerless CSV bytes and explicit metadata. It verifies SHA-256
before decoding those same immutable bytes and returns JSON-compatible schema
version 1 (`bsee.dsptsdelimit.v1`). The following separate synthetic example
performs no archive download or geometry calculation:

```python
import hashlib

from worldenergydata.bsee.data.survey_envelope import build_survey_envelope

raw = (b"000000000001,10,0,200,N,20,0,E,199,1,2,-90,28\n"
       b"000000000001,11,0,100,S,21,0,W,99,,,,\n")
envelope = build_survey_envelope(
    raw,
    api12="000000000001",
    source_url="https://example.org/synthetic.csv",
    retrieved_at="2026-10-01T12:00:00Z",
    declared_sha256=hashlib.sha256(raw).hexdigest(),
    data_kind="synthetic",
)
assert envelope["readiness"] == "not_qualified"
assert envelope["stations"][1]["values"]["DELTA_X"] is None
```

The interface requires `data_kind="source"` or `"synthetic"`; synthetic input
must remain labelled synthetic. Every record must have all 13 fields and the
same declared 12-digit identifier. `source_row` counts logical CSV records from
one, including quoted multiline records. Source order, leading zeros, padding
and nonempty decoded cell strings are retained. CSV quoting is decoded; the
original bytes must be retained separately to reproduce their exact spelling.
Only explicitly blank optional numeric cells (`DELTA_X`, `DELTA_Y`,
`SURF_LONGITUDE`, `SURF_LATITUDE`) become null. Critical numbers must be present;
all supplied numbers must parse as finite Python floats. There is no locale or
thousands-separator conversion. Direction codes must decode to N/S and E/W.

Depth units remain `unresolved`. Angular fields and geographic positions and
differences follow the source schema's degree/arcminute meanings; `DELTA_X` and
`DELTA_Y` remain longitude/latitude differences, never linear offsets. No datum,
coordinate, trajectory, physical-range check or engineering suitability is
inferred. The builder performs no file writes or network calls. The URL and
explicit offset-aware retrieval timestamp are caller declarations; syntax
checks do not establish acquisition chronology, source rights or freshness.
A URL and matching digest alone cannot establish engineering suitability.
The full multi-regulator database, casing/tubing integration, rig registry and
site publication remain subsequent work under #681.

## Sources and limits

- [Python pickle documentation, security warning](https://docs.python.org/3/library/pickle.html),
  accessed 2026-10-22: unpickling untrusted data can execute arbitrary code.
- [Python hashlib documentation, hash objects](https://docs.python.org/3/library/hashlib.html#hash-objects),
  accessed 2026-10-22: SHA-256 digest construction and hexadecimal representation.
- The repository raw-table schema named above defines the survey column order.

A matching digest proves agreement with the supplied pin; its trust depends on
how that pin was obtained. It does not establish data accuracy, freshness or
valid field geometry. The offline tests do not certify the current public
archive. Full archive parsing is repeated on each run. Resource limits for
unusually large archives and migration of other package loaders remain separate
work. Existing trajectory mathematics, geographic approximations, well selection
and packaged-data loaders are unchanged.
