"""Deterministic, escaped two-way cost maps and pinned input/output manifests.

No pilot priors or curated scope mappings are promoted automatically. Portfolio
inputs require a separately pinned v2 manifest and exact current input hashes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from html import escape
from pathlib import Path

from .basis import Basis, Contribution, Project
from .intervals import PRECISION, Interval
from .scenarios import Scenario, comparable
from .synthesis import Synthesis, synthesize


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique,
        parse_float=Decimal,
    )


def _preflight(
    path: Path, manifest: Path | None, expected: str | None, root: Path | None
) -> None:
    if manifest is None or expected is None or root is None:
        raise ValueError("portfolio requires pinned v2 manifest, digest and data root")
    if _hash(manifest) != expected:
        raise ValueError("manifest digest mismatch")
    data = _json(manifest)
    if data["contract_version"] != "2.0.0":
        raise ValueError("portfolio requires v2 manifest")
    entries = data["inputs"] + [data["schema"]]
    seen = {}
    for item in entries:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("manifest path must stay under data root")
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError("manifest path escapes data root")
        if relative.as_posix() in seen and seen[relative.as_posix()] != item["sha256"]:
            raise ValueError("conflicting manifest hashes")
        seen[relative.as_posix()] = item["sha256"]
        if _hash(resolved) != item["sha256"]:
            raise ValueError("input digest mismatch")
    if not any((root / name).resolve() == path.resolve() for name in seen):
        raise ValueError("synthesis input is not pinned by manifest")


def _interval(value: dict) -> Interval:
    return Interval(
        Decimal(value["low"]),
        Decimal(value["high"]),
        value.get("low_open", False),
        value.get("high_open", False),
    )


def load_portfolio(
    path: Path,
    *,
    manifest: Path | None = None,
    manifest_sha256: str | None = None,
    data_root: Path | None = None,
) -> tuple[dict, tuple[Synthesis, ...]]:
    data = _json(path)
    if data["schema_version"] != "1.0":
        raise ValueError("unsupported synthesis input schema")
    if data["evidence_status"] == "portfolio":
        _preflight(path, manifest, manifest_sha256, data_root)
    elif data["evidence_status"] != "synthetic":
        raise ValueError("unknown evidence status")
    date.fromisoformat(data["revision_date"])
    quantum = Decimal(data["quantum"])
    scenarios = tuple(
        Scenario(
            s["scenario_id"],
            s["architecture"],
            tuple((k, Decimal(v)) for k, v in s["shares"].items()),
            Decimal(s["unallocated_share"]),
            s["source"],
            s["derivation"],
        )
        for s in data["scenarios"]
    )
    if len({s.scenario_id for s in scenarios}) != len(scenarios):
        raise ValueError("duplicate scenario identity")
    results = []
    ids = set()
    included_awards: dict[str, str] = {}
    for value in data["projects"]:
        project = Project(
            value["project_id"],
            value["architecture"],
            _interval(value["total"]),
            Basis(**value["basis"]),
            tuple(value["requirement_ids"]),
            value["source"],
        )
        if project.project_id in ids:
            raise ValueError("duplicate project identity")
        ids.add(project.project_id)
        rows = tuple(
            Contribution(
                r["award_id"],
                tuple(r["requirement_ids"]),
                _interval(r["amount"]) if r["amount"] is not None else None,
                Basis(**r["basis"]),
                r["disposition"],
                r["value_basis"],
                r["source"],
                r.get("reason", ""),
                r.get("overlap_group"),
            )
            for r in value["contributions"]
        )
        for row in rows:
            if row.disposition == "included" and row.amount is not None:
                previous = included_awards.setdefault(row.award_id, project.project_id)
                if previous != project.project_id:
                    raise ValueError("one award cannot count across multiple projects")
        results.append(
            synthesize(project, rows, comparable(project, scenarios), quantum=quantum)
        )
    if not results:
        raise ValueError("portfolio requires at least one project")
    return data, tuple(sorted(results, key=lambda r: r.project.project_id))


def _bound(value: Decimal, quantum: Decimal, upper: bool) -> str:
    if not value.is_finite():
        return str(value)
    with localcontext() as ctx:
        ctx.prec = max(
            PRECISION, len(value.as_tuple().digits) + abs(value.adjusted()) + 4
        )
        rounded = (value / quantum).to_integral_value(
            rounding=ROUND_CEILING if upper else ROUND_FLOOR
        ) * quantum
        return str(rounded.copy_abs() if rounded == 0 else rounded)


def _bounds(value: Interval | None, quantum: Decimal) -> tuple[str, str, str, str]:
    if value is None:
        return "", "", "", ""
    return (
        _bound(value.low, quantum, False),
        _bound(value.high, quantum, True),
        str(value.low_open).lower(),
        str(value.high_open).lower(),
    )


def _display(value: Interval | None, *, percent: bool = False) -> str:
    if value is None:
        return "unavailable"
    # Presentation policy (portfolio-synthesis.md, 2026): money to 0.1 unit,
    # fractions to 0.1 percent; outward rounding preserves displayed enclosure.
    if percent:
        value = value.multiply(Interval.point(Decimal(100)))
    low, high, _, _ = _bounds(value, Decimal("0.1"))
    text = (
        low
        if low == high
        else (
            f'{"(" if value.low_open else "["}{low}, {high}{")" if value.high_open else "]"}'
        )
    )
    return escape(text) + (" %" if percent else "")


def _anchor(*parts: str) -> str:
    # Hex segments avoid delimiter collisions and URL/DOM decoding differences.
    return "-".join(part.encode("utf-8").hex() for part in parts)


def render_html(data: dict, results: tuple[Synthesis, ...]) -> str:
    out = [
        '<!doctype html><html lang="en"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Portfolio cost synthesis</title><style>",
        "body{font:1rem system-ui;max-width:80rem;margin:2rem auto;padding:1rem}",
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:.5rem;text-align:left}",
        ".observed{border-left:5px solid #17623b;padding:1rem}",
        ".inferred{border-left:5px dashed #805800;padding:1rem}",
        "</style><h1>Portfolio cost synthesis</h1>",
        (
            f'<p>Evidence status: <strong>{escape(data["evidence_status"])}</strong>. '
            "Observed award values and inferred scenarios are separate accounting views.</p>"
        ),
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>",
        f'<tr><td>1</td><td>{escape(data["revision_date"])}</td><td>Initial synthesis to expose residuals and inference.</td></tr>',
        "<tr><td>2</td><td>2026-10-20</td><td>Required real-money years, preserved JSON decimals and identified allocation cases to retain their comparison basis.</td></tr>",
        "<tr><td>3</td><td>2026-10-22</td><td>Added CSV quantity kinds to distinguish requirement allocations from accounting buckets with the same identity.</td></tr></table>",
        (
            "<p>Solid green: observed evidence. Dashed amber: inferred allocations. "
            "Ranges are enclosures, not probability intervals. Marginal ranges are non-additive.</p>"
        ),
    ]
    for result in results:
        p = result.project
        pid = _anchor("project", p.project_id)
        out.append(f'<section id="{pid}"><h2>{escape(p.project_id)}</h2>')
        out.append(
            f"<p>Architecture: {escape(p.architecture)}. Basis: {escape(str(asdict(p.basis)))}.</p>"
        )
        out.append(f"<p>Target source: {escape(p.source)}</p>")
        out.append('<div class="observed"><h3>Observed bottom-up accounting</h3><dl>')
        for label, value in (
            ("Disclosed target", p.total),
            ("Eligible subtotal", result.eligible),
            ("Excluded compatible subtotal", result.excluded),
            ("Overlap compatible subtotal", result.overlap),
            ("Residual", result.residual),
        ):
            out.append(f"<dt>{label}</dt><dd>{_display(value)}</dd>")
        out.append(
            f"<dt>Coverage</dt><dd>{_display(result.coverage, percent=True)}</dd>"
            f"<dt>Residual percentage</dt><dd>{_display(result.residual_fraction, percent=True)}</dd></dl>"
        )
        out.append(
            "<p>Excluded or overlapping values with other bases remain in the ledger "
            "and are omitted from compatible diagnostic subtotals.</p><ul>"
        )
        for r in result.contributions:
            amount = _display(r.amount) if r.amount else "not_public"
            links = " ".join(
                f'<a href="#{_anchor("req", p.project_id, key)}">{escape(key)}</a>'
                for key in r.requirement_ids
                if key in p.requirement_ids
            )
            out.append(
                f"<li>{escape(r.award_id)}: {amount}; {escape(r.disposition)}; "
                f"{escape(r.value_basis)}; {escape(r.reason)}; {links}; "
                f"basis {escape(str(asdict(r.basis)))}; source {escape(r.source)}</li>"
            )
        out.append('</ul></div><div class="inferred"><h3>Top-down scenarios</h3>')
        out.append(
            f"<p>Status: {result.top_down_status}. Allocations are never award disclosures.</p>"
        )
        if not result.allocations:
            out.append(
                "<p>unallocated unavailable; unreconciled variance unavailable: no compatible sourced scenario.</p>"
            )
        for a in result.allocations:
            qualifier = (
                f"limiting case; {a.target_endpoint} endpoint "
                f"{'open' if a.target_open else 'closed'}"
                if a.limiting
                else "point case"
            )
            out.append(
                f"<details><summary>{escape(a.scenario_id)} — {escape(a.derivation)}; "
                f"case {escape(a.case_id)}; target {escape(str(a.total))}; "
                f"{escape(qualifier)}</summary><ul>"
            )
            for key, value in a.amounts:
                out.append(
                    f'<li><a href="#{_anchor("req", p.project_id, key)}">{escape(key)}</a>: '
                    f"{_display(Interval.point(value))}</li>"
                )
            out.append(
                f"</ul><p>Unallocated {_display(Interval.point(a.unallocated))}; "
                f"unreconciled variance {_display(Interval.point(a.unreconciled_variance))}. "
                f"Source: {escape(a.source)}</p></details>"
            )
        out.append("</div><h3>Required work packages → project</h3>")
        for key in p.requirement_ids:
            band = dict(result.bands).get(key)
            award_ids = ", ".join(
                r.award_id for r in result.contributions if key in r.requirement_ids
            )
            out.append(
                f'<article id="{_anchor("req", p.project_id, key)}"><h4>{escape(key)}</h4>'
                f'<a href="#{pid}">Project total</a>; observed award references '
                f'(bundles are not split): {escape(award_ids) or "none"}; '
                f"inferred non-additive range: {_display(band)}.</article>"
            )
        out.append("</section>")
    out.append("</html>\n")
    return "\n".join(out)


def render_csv(data: dict, results: tuple[Synthesis, ...]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        (
            "project_id",
            "view",
            "identity",
            "derivation",
            "low",
            "high",
            "low_open",
            "high_open",
            "source",
            "allocation_case",
            "target_total",
            "target_endpoint",
            "target_open",
            "limiting",
            "quantity_kind",
        )
    )
    quantum = Decimal(data["quantum"])
    for r in results:
        for name, value in (
            ("total", r.project.total),
            ("eligible", r.eligible),
            ("excluded_compatible", r.excluded),
            ("overlap_compatible", r.overlap),
            ("residual", r.residual),
            ("coverage", r.coverage),
            ("residual_fraction", r.residual_fraction),
        ):
            q = (
                Decimal("0.001")
                if name in {"coverage", "residual_fraction"}
                else quantum
            )
            writer.writerow(
                (
                    r.project.project_id,
                    name,
                    "",
                    "observed",
                    *_bounds(value, q),
                    r.project.source,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "project_metric",
                )
            )
        for row in r.contributions:
            writer.writerow(
                (
                    r.project.project_id,
                    row.disposition,
                    row.award_id,
                    "observed",
                    *_bounds(row.amount, quantum),
                    row.source,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "award",
                )
            )
        for a in r.allocations:
            values = tuple(("requirement", k, v) for k, v in a.amounts) + (
                ("unallocated", "unallocated", a.unallocated),
                (
                    "unreconciled_variance",
                    "unreconciled_variance",
                    a.unreconciled_variance,
                ),
            )
            for kind, key, value in values:
                writer.writerow(
                    (
                        r.project.project_id,
                        a.scenario_id,
                        key,
                        a.derivation,
                        *_bounds(Interval.point(value), quantum),
                        a.source,
                        a.case_id,
                        str(a.total),
                        a.target_endpoint,
                        str(a.target_open).lower(),
                        str(a.limiting).lower(),
                        kind,
                    )
                )
    return stream.getvalue()


def build(path: Path, output: Path, **qualification) -> dict:
    data, results = load_portfolio(path, **qualification)
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "project_cost_map.html": render_html(data, results),
        "project_cost_map.csv": render_csv(data, results),
    }
    for name, content in files.items():
        (output / name).write_text(content, encoding="utf-8", newline="\n")
    modules = sorted(Path(__file__).parent.glob("*.py"))
    manifest = {
        "contract_version": "3.0.0",
        "evidence_status": data["evidence_status"],
        "generated_at_policy": "input revision_date; no wall clock",
        "revision_date": data["revision_date"],
        "decimal_policy": {
            "interval_precision": PRECISION,
            "interval_rounding": "outward",
            "allocation_arithmetic": "exact rational units",
            "output_quantum": data["quantum"],
            "allocation_rounding": "largest_remainder",
        },
        "schema": {
            "version": data["schema_version"],
            "path": "reporting.py",
            "sha256": _hash(Path(__file__)),
        },
        "inputs": [{"path": "portfolio_input", "sha256": _hash(path)}],
        "producer": [{"path": m.name, "sha256": _hash(m)} for m in modules],
        "scenarios": data["scenarios"],
        "upstream_manifest_sha256": qualification.get("manifest_sha256"),
        "outputs": [
            {"path": name, "sha256": _hash(output / name)} for name in sorted(files)
        ],
    }
    (output / "cost_synthesis_manifest.v3.json").write_text(
        # JSON numeric fractions are retained as exact decimal strings.
        json.dumps(manifest, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest
