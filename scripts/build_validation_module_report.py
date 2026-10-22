#!/usr/bin/env python3
"""Build the single-file validation report from public inputs and module calls.

Rebuild from the repository root:
PYTHONPATH=src uv run --no-project --with pandas --with PyYAML python scripts/build_validation_module_report.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path

from worldenergydata.validation import DataValidator
from worldenergydata.validation.schemas import DataType, FieldSchema, ValidationSchema

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/reports/modules/wvalidation"
STYLE_SOURCE = "docs/data-sources/metocean-open-observations.html"
CALCULATION_SOURCES = sorted(
    str(path.relative_to(ROOT))
    for path in (ROOT / "src/worldenergydata/validation").glob("*.py")
)
DATE = "2026-10-21"
CHANGES = {
    "report": "Validation module analysis",
    "revisions": [
        {
            "revision": "A",
            "date": DATE,
            "changes": [
                "The inclusive range workflow is demonstrated against a public exclusive-boundary example.",
                "Schema-interface limits and the evidence needed for wider use are identified.",
            ],
        }
    ],
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_basis() -> dict:
    return json.loads((DEST / "basis.json").read_text(encoding="utf-8"))


def house_style() -> str:
    """Reuse the existing documentation stylesheet without changing its rules."""
    exemplar = (ROOT / STYLE_SOURCE).read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", exemplar, re.S)[1]


def make_schema() -> ValidationSchema:
    """Explicitly map the public bounds to the module's inclusive range fields."""
    public = load_basis()["public_example"]["schema"]
    schema = ValidationSchema(name="NumericRangeExample")
    schema.add_field(
        FieldSchema(
            name="value",
            data_type=DataType.FLOAT,
            required=True,
            nullable=False,
            min_value=public["minimum"],
            max_value=public["exclusiveMaximum"],
            unit="dimensionless",
        )
    )
    return schema


def calculate() -> dict:
    """Call the module; do not infer validation results from a report formula."""
    schema = make_schema()
    cases = []
    for index, source in enumerate(load_basis()["public_example"]["cases"], start=1):
        accepted, errors = DataValidator(schema, strict=False).validate(
            {"value": source["value"]}
        )
        cases.append(
            {
                "case": index,
                "value": source["value"],
                "accepted": accepted,
                "errors": len(errors),
                "reference_accepted": source["reference_accepted"],
                "error_types": [type(error).__name__ for error in errors],
            }
        )
    batch_valid, errors = DataValidator(schema, strict=False).validate(
        [{"value": case["value"]} for case in cases]
    )
    disagreements = sum(
        case["accepted"] != case["reference_accepted"] for case in cases
    )
    return {
        "minimum": schema.fields["value"].min_value,
        "maximum": schema.fields["value"].max_value,
        "cases": cases,
        "records": len(cases),
        "accepted": sum(case["accepted"] for case in cases),
        "rejected": sum(not case["accepted"] for case in cases),
        "reference_accepted": sum(case["reference_accepted"] for case in cases),
        "disagreements": disagreements,
        "disagreement_percent": round(100 * disagreements / len(cases), 1),
        "batch_valid": batch_valid,
        "batch_errors": len(errors),
        "batch_error_rows": [error.row_index for error in errors],
    }


def report_numbers(result: dict) -> dict:
    """Register every displayed worked-example number, including repeated values."""
    numbers = {
        "summary-accepted": result["accepted"],
        "summary-records": result["records"],
        "summary-disagreements": result["disagreements"],
        "input-minimum": result["minimum"],
        "input-maximum": result["maximum"],
        "result-records": result["records"],
        "result-accepted": result["accepted"],
        "result-rejected": result["rejected"],
        "result-reference": result["reference_accepted"],
        "result-disagreements": result["disagreements"],
        "result-percent": result["disagreement_percent"],
        "result-errors": result["batch_errors"],
    }
    for case in result["cases"]:
        for field in ("case", "value", "errors"):
            numbers[f"case-{case['case']}-{field}"] = case[field]
    return numbers


def fmt(value: float) -> str:
    return f"{value:g}".replace("-", "−")


def number(key: str, numbers: dict) -> str:
    return f'<span data-number="{key}">{fmt(numbers[key])}</span>'


def chart(result: dict) -> str:
    """Offline interactive SVG: one numeric quantity against the source-case order."""
    low = min(case["value"] for case in result["cases"])
    high = max(case["value"] for case in result["cases"])
    span = high - low

    def y(value):
        return 265 - (value - low) / span * 200

    parts = [
        '<svg id="limit-chart" viewBox="0 0 800 340" width="100%" role="img" '
        'aria-labelledby="chart-title chart-description">',
        '<title id="chart-title">Numeric value against source case</title>',
        '<desc id="chart-description">Both inclusive module limits are drawn. '
        "Points give the module and public-example acceptance on hover or focus.</desc>",
        '<path d="M80 40 V285 H760" fill="none" stroke="currentColor"/>',
        '<text x="20" y="25">Value (dimensionless)</text>',
        '<text x="300" y="330">Source case (source order)</text>',
    ]
    for label, value in (
        ("minimum", result["minimum"]),
        ("maximum", result["maximum"]),
    ):
        parts.append(
            f'<line data-limit="{label}" x1="80" x2="760" y1="{y(value):.2f}" '
            f'y2="{y(value):.2f}" stroke="#183041" stroke-dasharray="6 4"/>'
            f'<text x="85" y="{y(value) - 9:.2f}">{label.capitalize()} '
            f"{fmt(value)} (dimensionless)</text>"
        )
    for index, case in enumerate(result["cases"]):
        mismatch = case["accepted"] != case["reference_accepted"]
        status = (
            "The boundary differs."
            if mismatch
            else (
                "The case is accepted." if case["accepted"] else "The case is rejected."
            )
        )
        color = "#9a6700" if mismatch else "#147367" if case["accepted"] else "#a12835"
        tooltip = (
            f"Case {case['case']}; component: numeric range; demand: {fmt(case['value'])}; "
            f"limits: {fmt(result['minimum'])} inclusive to {fmt(result['maximum'])} inclusive; "
            f"units: dimensionless. {status} "
            f"Public example: {'accepted' if case['reference_accepted'] else 'rejected'}."
        )
        x = 130 + index * 115
        parts.append(
            f'<circle tabindex="0" cx="{x}" cy="{y(case["value"]):.2f}" r="8" '
            f'fill="{color}" data-tooltip="{escape(tooltip)}"><title>{escape(tooltip)}</title></circle>'
            f'<text x="{x - 4}" y="306">{case["case"]}</text>'
        )
    parts.append(
        '</svg><p id="chart-detail" aria-live="polite">Focus or hover over a point for its criteria.</p>'
    )
    return "\n".join(parts)


INTERACTIONS = r"""
const calculation = JSON.parse(document.getElementById('calculation').textContent);
const revisions = JSON.parse(document.getElementById('change-data').textContent).revisions;
document.querySelectorAll('[data-tooltip]').forEach(point => {
  const detail = () => { document.getElementById('chart-detail').textContent = point.dataset.tooltip; };
  point.addEventListener('mouseenter', detail);
  point.addEventListener('focus', detail);
  point.addEventListener('click', detail);
});
document.getElementById('previous-revision').addEventListener('change', event => {
  const list = document.getElementById('change-list');
  list.replaceChildren();
  const entries = event.target.value === 'A' ? ['No engineering changes since the selected revision.'] : revisions[0].changes;
  entries.forEach(text => { const item = document.createElement('li'); item.textContent = text; list.append(item); });
});
let comments = [];
let commentFile;
const renderComments = () => {
  const list = document.getElementById('comment-list');
  list.replaceChildren();
  comments.forEach(comment => {
    const item = document.createElement('li');
    item.textContent = `${comment.section}: ${comment.text}`;
    list.append(item);
  });
};
document.getElementById('comment-form').addEventListener('submit', event => {
  event.preventDefault();
  const text = document.getElementById('comment-text');
  if (!text.value.trim()) return;
  comments.push({section: document.getElementById('comment-section').value, text: text.value.trim()});
  text.value = '';
  renderComments();
  document.getElementById('comment-status').textContent = 'Comments are unsaved. Save the comment file before closing.';
});
document.getElementById('save-comments').addEventListener('click', async () => {
  const payload = JSON.stringify({report: 'Validation module analysis', revision: 'A', comments}, null, 2) + '\n';
  const status = document.getElementById('comment-status');
  try {
    if ('showSaveFilePicker' in window) {
      commentFile = commentFile || await window.showSaveFilePicker({suggestedName: 'index.comments.json', types: [{description: 'Comment file', accept: {'application/json': ['.json']}}]});
      const writer = await commentFile.createWritable();
      await writer.write(payload);
      await writer.close();
      status.textContent = 'Comments are saved to the selected file.';
    } else {
      const url = URL.createObjectURL(new Blob([payload], {type: 'application/json'}));
      const link = document.createElement('a'); link.href = url; link.download = 'index.comments.json'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = 'A comment file download was requested. Place it beside the report; confirm the download before closing.';
    }
  } catch (error) { status.textContent = 'Comments remain unsaved. Select a writable comment file and save again.'; }
});
document.getElementById('load-comments').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    if (parsed.report !== 'Validation module analysis' || parsed.revision !== 'A' || !Array.isArray(parsed.comments) || !parsed.comments.every(item => typeof item.section === 'string' && typeof item.text === 'string')) throw new Error('Invalid comments');
    if (comments.length && !window.confirm('Replace the comments currently displayed with the selected file?')) return;
    comments = parsed.comments; commentFile = undefined; renderComments();
    document.getElementById('comment-status').textContent = 'Comments are loaded. Select the comment file again when saving.';
  } catch (error) { document.getElementById('comment-status').textContent = 'The comment file was not loaded. Select a comment file for this report revision.'; }
});
"""


def render(result: dict) -> str:
    """Write the report as a single narrative, with calculation values interpolated."""
    basis = load_basis()
    numbers = report_numbers(result)

    def n(key):
        return number(key, numbers)

    rows = []
    for case in result["cases"]:
        prefix = "case-" + str(case["case"])
        module_status = "Accepted" if case["accepted"] else "Rejected"
        reference_status = "Accepted" if case["reference_accepted"] else "Rejected"
        rows.append(
            f'<tr><td>{n(prefix + "-case")}</td><td>{n(prefix + "-value")}</td>'
            f"<td>{module_status}</td><td>{reference_status}</td>"
            f'<td>{n(prefix + "-errors")}</td><td>[1]; module call</td></tr>'
        )
    case_rows = "\n".join(rows)
    tests = basis["existing_tests"]
    evidence_labels = {
        "tests/test_validation_framework.py": "Framework workflow",
        "tests/unit/test_validation_framework.py": "Framework unit workflow",
        "tests/unit/validation/test_base.py": "Result containers and base interfaces",
        "tests/unit/validation/test_exceptions.py": "Exception interface",
        "tests/unit/validation/test_rules.py": "Static and wrapper rules",
        "tests/unit/validation/test_schema.py": "Dataclass schemas",
        "tests/unit/validation/test_schemas.py": "Object schemas",
        "tests/unit/validation/test_validators.py": "Record validators",
    }
    evidence_rows = "\n".join(
        f'<tr><td>{evidence_labels[item["path"]]}</td><td>{item["passed"]}</td>'
        f'<td><code>{item["sha256"]}</code></td></tr>'
        for item in tests["files"]
    )
    evidence_locators = "".join(
        f'<li>{evidence_labels[item["path"]]}: <code>{item["path"]}</code>.</li>'
        for item in tests["files"]
    )
    sources = "\n".join(
        f'<li id="ref-{index}"><a href="{source["url"]}">{escape(source["title"])}</a>. '
        f'{escape(source["edition"])}; {escape(source["clauses"])}. '
        f'Accessed {source["retrieved_at"]}; HTTP {source["http_status"]}. '
        f'Response digest: <code>{source["response_sha256"]}</code>.</li>'
        for index, source in enumerate(basis["sources"], start=1)
    )
    fingerprints = "\n".join(
        f"<li><code>{path}</code>: <code>{digest(ROOT / path)}</code>.</li>"
        for path in CALCULATION_SOURCES
    )
    changes = "".join(
        f"<li>{escape(text)}</li>" for text in CHANGES["revisions"][0]["changes"]
    )
    headings = [
        ("summary", "Executive summary"),
        ("introduction", "Introduction"),
        ("basis", "Basis and criteria"),
        ("interfaces", "Inputs and outputs"),
        ("method", "Theory and method"),
        ("results", "Worked example"),
        ("validation", "Validation evidence"),
        ("recommendations", "Limits and recommendations"),
        ("references", "References"),
        ("appendix", "Appendix"),
    ]
    contents = "".join(
        f'<li><a href="#{key}">{title}</a></li>' for key, title in headings
    )
    options = "".join(
        f'<option value="{title}">{title}</option>' for _, title in headings
    )
    return f"""<!doctype html>
<html lang="en" data-revision="A">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Validation module analysis</title><style>{house_style()}</style></head>
<body class="hs-doc"><main>
<h1>Validation module analysis</h1>
<p>Draft for maintainer review</p>
<nav aria-label="Contents"><ol>{contents}</ol></nav>
<section class="report-section" id="summary"><h2>1 Executive summary</h2>
<p>The validation module is a schema and rule framework for screening energy records. Analysis is performed to determine the behaviour of its numeric range workflow; key results are summarized below.</p>
<ul><li>The inclusive range workflow is available for bounded finite numeric records.
<ul><li>{n('summary-accepted')} of {n('summary-records')} public-example records are accepted by the module.</li>
<li>{n('summary-disagreements')} acceptance differs from the public example at its exclusive upper limit; use of an inclusive limit is required for this workflow.</li></ul></li>
<li>Use beyond this workflow requires a stated data contract.
<ul><li>Application checks are required for schema imports, null handling and cross-field execution before a dataset is accepted.</li>
<li>Engineering acceptance is NOT_EVALUATED; schema acceptance establishes only the checks actually executed.</li></ul></li></ul>
</section>
<aside id="revision-history"><h2>Revision history</h2>
<table><thead><tr><th>Revision</th><th>Date</th><th>What changed and why</th></tr></thead>
<tbody><tr><td>A</td><td>{DATE}</td><td>The inclusive numeric workflow and its evidence are documented to define the boundary of use.</td></tr></tbody></table></aside>
<section class="report-section" id="introduction"><h2>2 Introduction</h2>
<p>Record screening is performed before downstream energy analysis. Required fields, types, ranges, text patterns, dates and selected cross-field relationships are represented by schemas and rules [3].</p>
<p>The main workflow is demonstrated through the public record validator with explicit schema types. The public range example is used as a boundary comparison, with its exclusive upper bound preserved as the reference [1]. No physical structure, environmental load or engineering solver is represented.</p>
<h3>2.1 Workflow schematic</h3>
<p>The software boundary is shown below. Bounds are supplied by the data contract; no physical geometry or mesh is applicable.</p>
<pre aria-label="Data validation workflow">Finite numeric records + required field + inclusive bounds
                         ↓
             Field and type checks
                         ↓
              Inclusive range check
                         ↓
       Acceptance flag + contextual errors
                         ↓
    Downstream analysis only after contract review</pre>
<h3>2.2 Not covered</h3>
<p>Predefined production, well, lease, financial and configuration schemas, direct field-rule wrappers, schema registration, file parsing and date relationships are inventoried but are not demonstrated as complete workflows. Similar validation names outside this package are outside this report.</p>
</section>
<section class="report-section" id="basis"><h2>3 Basis and criteria</h2>
<p>The numeric example is taken from the public schema documentation [1]. The inclusion and exclusion criteria are defined by the validation specification draft [2]; the module is not presented as an implementation of that specification.</p>
<p>The reference lower bound is {n('input-minimum')} and its exclusive upper bound is {n('input-maximum')}, both dimensionless. The same magnitudes are assigned to the module's inclusive bounds so that the semantic difference is exposed. The example is software data, with no physical operating limit inferred.</p>
<p>Each input and each expected reference outcome is recorded in the data register [3]. No fitted coefficient, material constant, engineering threshold or assumed physical value is used. A physical acceptance criterion remains NOT_EVALUATED until a cited application basis is supplied.</p>
</section>
<section class="report-section" id="interfaces"><h2>4 Inputs and outputs</h2>
<p>Records are supplied as a dictionary, a list of dictionaries or a pandas data frame. A schema name, field definitions and optional cross-field rules are supplied to the record validator [3].</p>
<p>The return value is an acceptance flag and a list of validation exceptions. Non-strict mode accumulates errors; strict mode raises at the first encountered error. Field, value, rule and zero-based row position are available on the exceptions. A formatted text report is also available. Error counts are issue counts and are not generally rejected-record counts.</p>
<h3>4.1 Compatible interface used here</h3>
<p>The following imports select the same schema enumeration used by numeric dispatch. Field types from the alternate schema interface have matching labels but distinct identities; they are not treated as interchangeable.</p>
<pre>from worldenergydata.validation import DataValidator
from worldenergydata.validation.schemas import DataType, FieldSchema, ValidationSchema

schema = ValidationSchema(name="NumericRangeExample")
schema.add_field(FieldSchema(
    name="value", data_type=DataType.FLOAT,
    required=True, nullable=False,
    min_value=lower_bound, max_value=upper_bound,
))
accepted, errors = DataValidator(schema, strict=False).validate(records)</pre>
<p>The displayed bound symbols are supplied from the public example. The complete calculation is identified in the reference register [3].</p>
<h3>4.2 Other output interface</h3>
<p>Direct rule and predefined data-frame validators return a result object with errors, warnings, information and metadata. That interface differs from the record validator's tuple and exception interface. Its generic schema validate method returns an empty result; adding fields alone does not execute field checks through that method [3].</p>
</section>
<section class="report-section" id="method"><h2>5 Theory and method</h2>
<p>Range validation is performed by testing an inequality after field type checking. The finite numeric input is denoted x, the lower bound L and the upper bound U; all have the same units [2].</p>
<p>The inclusive condition is L ≤ x ≤ U. The public example uses L ≤ x &lt; U. The lower inequality follows the minimum keyword; the upper inequalities follow maximum and exclusiveMaximum respectively [2]. No scaling factor or empirical equation is introduced.</p>
<p>Each published input is passed separately to the module. The complete set is also passed as a batch so that row positions and aggregated errors are recorded. Counts are formed from returned flags and exceptions; the disagreement percentage is the number of differing flags divided by the number of inputs, expressed as a percentage. Reference flags are taken from the published example, rather than calculated by a second call to the module [1, 3].</p>
<p>Cross-field checks are performed only when all field checks in the batch have produced no errors. An invalid field in any record therefore prevents cross-field checks for the entire batch [3].</p>
</section>
<section class="report-section" id="results"><h2>6 Worked example</h2>
<p>The public example is evaluated using the module's inclusive range fields. The source-case order and reference outcomes are preserved; the upper-bound disagreement is exposed in the table and chart [1, 3].</p>
<table><thead><tr><th>Quantity</th><th>Value</th><th>Unit</th><th>Source</th></tr></thead><tbody>
<tr><td>Input records</td><td>{n('result-records')}</td><td>records</td><td>Module calls [3]</td></tr>
<tr><td>Module accepted</td><td>{n('result-accepted')}</td><td>records</td><td>Module calls [3]</td></tr>
<tr><td>Module rejected</td><td>{n('result-rejected')}</td><td>records</td><td>Module calls [3]</td></tr>
<tr><td>Reference accepted</td><td>{n('result-reference')}</td><td>records</td><td>Public example [1]</td></tr>
<tr><td>Different acceptance flags</td><td>{n('result-disagreements')}</td><td>records</td><td>Flag comparison [3]</td></tr>
<tr><td>Different acceptance flags</td><td>{n('result-percent')}</td><td>% of reference cases</td><td>Flag comparison [3]</td></tr>
<tr><td>Batch errors</td><td>{n('result-errors')}</td><td>issues</td><td>Module batch call [3]</td></tr>
</tbody></table><p>Table 6.1. Counts describe this finite numeric example only.</p>
{chart(result)}
<p>Figure 6.1. Value against case order. Green: the case is accepted. Red: the case is rejected. Amber: the boundary differs. Dashed lines show both inclusive module limits; the public upper limit is exclusive.</p>
<table><thead><tr><th>Case</th><th>Value (dimensionless)</th><th>Module</th><th>Public reference</th><th>Errors (issues)</th><th>Source</th></tr></thead><tbody>{case_rows}</tbody></table>
<p>Table 6.2. Inputs retain the source's integer precision. The upper-bound case is accepted by the module and rejected by the public reference.</p>
<p>For the differing case, an explicit exclusive-boundary check is required before acceptance under the public example's contract [2]. The module result is left unchanged in this analysis.</p>
</section>
<section class="report-section" id="validation"><h2>7 Validation evidence</h2>
<p>The repository's existing tests are used as evidence of checked software behaviour. The recorded focused execution passed {tests['passed']} tests with {tests['failed']} failures; the file-level counts and fingerprints are listed in the appendix [3].</p>
<p>Existing tests cover schema construction, exception context, result aggregation, required fields, type and range checks, text and date checks, cross-field relationships, file inputs and schema management. The public demonstration contains illustrative energy records; it is not a measured benchmark. No field-measurement acceptance benchmark is established by the inspected validation package, its focused tests or its demonstration [3].</p>
<p>Report tests compare every tagged worked-example number and the embedded chart data with fresh module calls. Separate literal anchors check the lower boundary, upper-bound discrepancy and total accepted and rejected counts. The headline accepted count is recomputed from the displayed inputs. Integer comparisons are exact; displayed percentages use a half-unit tolerance in the last displayed digit.</p>
<p>The generated report is compared with a fresh build using displayed precision. Calculation-source fingerprints detect a change requiring regeneration. These tests establish calculation consistency and the stated boundary cases; they do not establish general conformance or engineering acceptance.</p>
</section>
<section class="report-section" id="recommendations"><h2>8 Limits and recommendations</h2>
<p>Use is limited to contracts whose checks have been exercised explicitly. The following controls are derived from the implementation and the public range criteria [2, 3].</p>
<h3>8.1 Limits of use</h3>
<p>The alternate schema enumeration can bypass numeric dispatch in the record validator. Numeric strings and booleans can pass its numeric type checks; nulls and non-finite values require caller checks. Range checks do not perform unit conversion. A missing required key can contribute multiple issues, and unknown cross-field rule types are silently ignored. Precision, scale, default values and named custom-validator declarations are stored without enforcement in the demonstrated record workflow.</p>
<p>Object-style cross-field rules in predefined data-frame schemas differ from the dictionary rules expected by the record validator. Several predefined column names and metadata field names also differ. File extension support does not establish data-contract compatibility; file workflows are not qualified by this example. Dataset values are logged by the existing validator, so logging configuration is part of application data handling.</p>
<h3>8.2 Recommendations</h3>
<ol><li>Use the demonstrated schema imports and add an application regression that rejects a value outside each supplied limit. Unify the schema enumeration before documenting the two interfaces as interchangeable [3].</li>
<li>When the data contract has an exclusive bound, apply a separate strict inequality check before accepting the data. Trigger rejection at equality to the exclusive upper bound, as required by the public reference [2].</li>
<li>Require finite numeric values and explicit units before range checking. Add regression cases for nulls, numeric strings and booleans before extending use to those input categories [3].</li>
<li>Record whether cross-field checks actually executed, reject unknown rule types and qualify each predefined schema through its intended entry point before using it as an acceptance gate [3].</li>
<li>Supply a cited dataset contract and measured reference records before using schema acceptance to support engineering acceptance. Keep the physical result NOT_EVALUATED until that basis is available.</li></ol>
</section>
<section class="report-section" id="references"><h2>9 References</h2>
<p>The example and mathematical criteria are supplied by the public references. The implementation and execution evidence are identified by repository locators.</p>
<h3>9.1 Source register</h3><ol>{sources}
<li id="ref-3">Repository calculation, tests and public demonstration. Exact locators are listed below; all reported example outcomes are obtained by module calls.</li></ol>
<h3>9.2 Locators and rebuild</h3>
<ul><li>[1] Numeric types, Range example: the current example with minimum and exclusiveMaximum; public input transcription and access receipts: <code>docs/reports/modules/wvalidation/basis.json</code>.</li>
<li>[2] Validation specification draft 2020-12: clauses 6.2.2 (maximum), 6.2.3 (exclusiveMaximum), 6.2.4 (minimum).</li>
<li>[3] Implementation: <code>src/worldenergydata/validation/</code>; main workflow: <code>validators.py</code>, <code>schemas.py</code> and <code>rules.py</code>. Alternate interface: <code>schema.py</code>. Result containers: <code>base.py</code>. Exception interface: <code>exceptions.py</code>.</li>
<li>[3] Public illustrative energy demonstration: <code>tests/demo_validation.py</code>. Existing focused test files and their fingerprints appear in Table 10.1. Calculation consistency and literal anchors: <code>tests/unit/reports/test_validation_module_report.py</code>.</li>
<li>[3] Report calculation: <code>scripts/build_validation_module_report.py</code>. Layout and inlined stylesheet exemplar: <code>{STYLE_SOURCE}</code>; the requested document body class is applied.</li></ul>
<pre>PYTHONPATH=src uv run --no-project --with pandas --with PyYAML python scripts/build_validation_module_report.py</pre>
<p>The source receipts record the responses used to transcribe the public example; network access is not required to rebuild this report.</p>
<details><summary>Existing-test source locators</summary><ul>{evidence_locators}</ul></details>
<details><summary>Recorded existing-test command</summary><pre>{escape(tests['command'])}</pre></details>
<details><summary>Calculation-source fingerprints</summary><ul>{fingerprints}</ul></details>
</section>
<section class="report-section" id="appendix"><h2>10 Appendix</h2>
<p>The data register and quality evidence are recorded here to bound the conclusions. Counts describe the recorded focused execution, rather than an estimate of repository-wide test coverage.</p>
<h3>10.1 Data register</h3>
<table><thead><tr><th>Item</th><th>Basis</th><th>Use or missing evidence</th><th>Source</th></tr></thead><tbody>
<tr><td>Range bounds and inputs</td><td>Public example, transcribed without changing its reference flags</td><td>Dimensionless software example</td><td>[1], Table 6.2</td></tr>
<tr><td>Inclusive mapping</td><td>Declared comparison choice</td><td>The bound magnitude is mapped without importing exclusive semantics</td><td>[2], Table 6.1</td></tr>
<tr><td>Physical acceptance limit</td><td>NOT_EVALUATED</td><td>A cited application contract is required</td><td>Section 8.2</td></tr>
<tr><td>Field benchmark</td><td>NOT_EVALUATED</td><td>Measured records with expected outcomes are required</td><td>Section 7</td></tr>
<tr><td>Assumed physical data</td><td>None</td><td>No physical computation is performed</td><td>Section 3</td></tr>
</tbody></table>
<h3>10.2 Quality pre-flight evidence</h3>
<p>Table 10.1 records actual passed test cases per source file. Content digests identify the test files used for that execution.</p>
<table><thead><tr><th>Test source</th><th>Passed (tests)</th><th>Source digest</th></tr></thead><tbody>{evidence_rows}</tbody></table>
<p>Table 10.1. Existing validation tests; every listed test passed.</p>
<p>The module import, public-example calculation, literal anchors, number consistency, report rebuild, section links, inlined stylesheet and text checks are exercised by the report tests. Embedded controls are exercised without a browser: chart details, revision filtering, comment saving, loading and invalid-file handling are checked. The complete repository suite is outside the focused module scope. Browser rendering and native file-picker behaviour require manual review. Field-data acceptance remains NOT_EVALUATED because measured reference data are absent.</p>
</section>
<aside id="changes"><h2>Engineering changes</h2>
<label for="previous-revision">Last revision read</label>
<select id="previous-revision"><option value="none">No previous revision</option><option value="A">A</option></select>
<ul id="change-list">{changes}</ul></aside>
<aside id="comments"><h2>Comments</h2>
<p>Select the report section and enter a comment. Save the comment file beside this report as <code>index.comments.json</code>. In browsers without a file picker, move the downloaded comment file beside the report. Comments stay in memory until saved; the HTML report is not modified.</p>
<form id="comment-form"><label for="comment-section">Section</label>
<select id="comment-section">{options}</select>
<label for="comment-text">Comment</label><textarea id="comment-text" required rows="4" cols="45"></textarea>
<button type="submit">Add comment</button></form>
<ol id="comment-list"></ol><button id="save-comments" type="button">Save comments beside report</button>
<label for="load-comments">Load saved comments</label><input id="load-comments" type="file" accept=".json,application/json">
<p id="comment-status" aria-live="polite">No comments have been added.</p></aside>
<script id="calculation" type="application/json">{json.dumps(result, ensure_ascii=False, allow_nan=False)}</script>
<script id="change-data" type="application/json">{json.dumps(CHANGES, ensure_ascii=False)}</script>
<script>{INTERACTIONS}</script>
</main></body></html>
"""


def build(output: Path = DEST) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(
        render(calculate()), encoding="utf-8", newline="\n"
    )
    (output / "changes.json").write_text(
        json.dumps(CHANGES, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEST)
    build(parser.parse_args().output)
