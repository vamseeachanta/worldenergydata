"""Self-contained, escaped HTML with mandatory evidence limits."""

from html import escape

LIMITS = (
    "Public production supports descriptive comparisons, not an uplift promise. "
    "Reservoir depletion versus mechanical failure: NOT_EVALUATED. "
    "Gas-unit oil signals and gas stripper classification: NOT_EVALUATED. "
    "Pressure context, economics, working interest, rework validation and false-positive "
    "rate: NOT_EVALUATED. Operator of record identifies the filer, not ownership. "
    "Lease totals are never allocated to individual wells. Missing months are unknown, "
    "not zero. Inventory and production may differ after transfers; a dated join is required. "
    "The error budget is unquantified: reporting revisions, downtime, allocation, "
    "completion age and inventory coverage can change the ranking. "
    "Signals are screening inferences; obtain operating records before choosing work. "
    "PDF pagination: NOT_EVALUATED. HTML length varies with evidence coverage."
)


def _show(value):
    if value is None:
        return "NOT_EVALUATED (not captured or not supported)"
    if isinstance(value, float):
        return f"{value:.1f}"
    return escape(str(value), quote=True)


def render_onepager(result: dict, operator_no: str) -> str:
    """Render any registry operator; unknowns and limitations cannot be suppressed."""
    operator = next(
        (o for o in result["operators"] if o["operator_no"] == operator_no), None
    )
    if operator is None:
        raise KeyError("operator is absent from registry")
    candidates = [c for c in result["candidates"] if c["operator_no"] == operator_no]
    selected = candidates[: result["policy"]["top_candidates"]]
    cells = []
    bars = []
    for index, row in enumerate(selected):
        values = [
            row["unit_id"],
            row["granularity"],
            row["rate_bopd"],
            row["peer_median_bopd"],
            row["peer_count"],
            ", ".join(row["signals"]) or "No signal supported",
            (
                f'{row["deficit_fraction"] * 100:.1f} %'
                if row["deficit_fraction"] is not None
                else None
            ),
            (
                f'{row["decline_excess_fraction"] * 100:.1f} %'
                if row["decline_excess_fraction"] is not None
                else None
            ),
            row["rate_cv"],
            row["last_positive_oil_month"],
            row["last_positive_oil_bopd"],
            row["months_since_positive_oil"],
            row["mechanism"],
        ]
        cells.append("<tr>" + "".join(f"<td>{_show(v)}</td>" for v in values) + "</tr>")
        rate, peer = row["rate_bopd"], row["peer_median_bopd"]
        if rate is not None and peer is not None:
            # Chart dimensions are presentation choices; arithmetic values appear in the table.
            scale = max(rate, peer, 1)
            y = 32 + index * 48
            bars.append(
                f'<text x="0" y="{y}">{escape(row["lease_no"])}</text>'
                f'<rect x="90" y="{y - 12}" width="{240 * rate / scale:.1f}" '
                'height="10" fill="#245e80"/>'
                f'<rect x="90" y="{y}" width="{240 * peer / scale:.1f}" '
                'height="10" fill="#b05f23"/>'
            )
    source = result["source"]
    summary = (
        ("Wells in inventory", operator["well_count_total"]),
        (
            "Producing / inactive",
            f'{operator["well_count_producing"]} / {operator["well_count_inactive"]}',
        ),
        ("Oil in selected window (bbl)", operator["oil_bbl_window"]),
        ("Gas in selected window (Mcf)", operator["gas_mcf_window"]),
        (
            "Fields / concentration (fraction HHI)",
            f'{_show(operator["field_count"])} / {_show(operator["field_concentration"])}',
        ),
        ("Water cut estimate", operator["water_cut_est"]),
        ("Stripper share (verified well rates only)", operator["stripper_share"]),
        ("Selection status", operator["selection_status"]),
        (
            "Name variants / other IDs with same normalized name",
            f'{operator["name_variant_count"]} / {operator["name_collision_count"]}',
        ),
    )
    metrics = "".join(
        f"<dt>{escape(label)}</dt><dd>{_show(value)}</dd>" for label, value in summary
    )
    chart = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 {max(70, len(selected) * 48 + 24)}" '
        'role="img" aria-label="Observed oil rate and peer median; each pair has its own scale">'
        + "".join(bars)
        + "</svg>"
        if bars
        else "<p>Peer comparison: NOT_EVALUATED.</p>"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Operator {_show(operator_no)} opportunity screen</title>
<style>body{{font:14px sans-serif;max-width:1100px;margin:2em auto;color:#172c38}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #aaa;padding:.4em;text-align:left}}
dt{{font-weight:bold}}dd{{margin-bottom:.4em}}svg{{max-width:420px}}footer{{font-size:12px}}
@media print{{body{{margin:0;font-size:10px}}tr{{break-inside:avoid}}}}</style></head>
<body><h1>Operator {_show(operator_no)} opportunity screen</h1>
<p>{_show(operator["operator_name"])} · As of {_show(result["as_of"])}</p>
<p>Descriptive evidence count: {_show(operator["signal_count"])}. No predicted uplift.</p>
<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>
<tr><td>1</td><td>{_show(source["snapshot_date"])}</td><td>Generated from the stated snapshot for reproducible screening.</td></tr></table>
<h2>Inventory and coverage</h2><dl>{metrics}</dl>
<p>Window: {_show(result["window"][0])} through {_show(result["window"][-1])}.
Counts describe the inventory date {_show(source["inventory_date"])}. Each value inherits the source below.</p>
<h2>Ranked evidence</h2><p>Showing {len(selected)} of {len(candidates)} units.
Lease evidence describes a group of wells. Rates use calendar days. Fractions are unitless.</p>
<table><tr><th>Unit</th><th>Grain</th><th>Oil bbl/day</th><th>Peer median bbl/day</th>
<th>Peer units</th><th>Signals</th><th>Deficit (%)</th><th>Decline excess (percentage points)</th>
<th>Rate CV</th><th>Last positive oil month</th><th>Prior oil bbl/day</th>
<th>Months since positive oil</th><th>Mechanism</th></tr>{''.join(cells)}</table>
<h2>Peer comparison</h2><p>Blue: observed; brown: peer median. Each pair has its own scale.</p>{chart}
<h2>What this data cannot tell you</h2><p>{escape(LIMITS)}</p>
<footer>Dataset: {_show(source["dataset"])}; snapshot {_show(source["snapshot_date"])}.
Source: <a href="{escape(source["url"], quote=True)}">regulator dataset catalogue</a>.
Method: {_show(result["method_version"])}. Input SHA-256: {_show(result["input_sha256"])}.</footer>
</body></html>
"""
