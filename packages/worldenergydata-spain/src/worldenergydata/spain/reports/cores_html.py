"""Self-contained Spain CORES field-development HTML renderer (#810)."""

from __future__ import annotations

import html
import json
from typing import Any


def render_spain_cores_html(summary: dict[str, Any]) -> str:
    payload = _json_payload(summary)
    fields = summary["fields"]
    source = summary["source"]
    economics = summary["economics"]
    manifest = summary["scheduler_manifest"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spain CORES Field Development</title>
<style>{_STYLE}</style>
</head>
<body>
<header>
  <a class="home" href="../index.html">worldenergydata</a>
  <div>
    <h1>Spain CORES Field Development</h1>
    <p>Normalized CORES production, scheduler provenance, and reference-chain field-development screening.</p>
  </div>
</header>
<main>
  <section class="metrics">
    <div><strong>{fields["field_count"]}</strong><span>fields</span></div>
    <div><strong>{source["record_count"]:,}</strong><span>normalized rows</span></div>
    <div><strong>{len(economics["evaluated_fields"])}</strong><span>economics runs</span></div>
    <div><strong>{html.escape(source["format"])}</strong><span>format</span></div>
  </section>
  <section class="panel provenance">
    <h2>Source Provenance</h2>
    <p><strong>Source URL:</strong> {html.escape(source["source_url"])}</p>
    <p><strong>Refresh timestamp:</strong> {html.escape(source["last_refresh"])}</p>
    <p><strong>Scheduler status:</strong> {html.escape(str(manifest["status"]))}</p>
    <p><strong>Scheduler job:</strong> {html.escape(str(manifest["job_name"]))}</p>
    <p><strong>Scheduler records:</strong> {html.escape(str(manifest["records_updated"]))}</p>
    {_workbook_table(summary)}
  </section>
  <section class="panel warning">
    <h2>Caveats</h2>
    {_limitations_html(summary)}
  </section>
  <section class="layout">
    <aside class="panel">
      <h2>Fields</h2>
      <label for="field-select">Field</label>
      <select id="field-select"></select>
      <dl id="field-detail"></dl>
    </aside>
    <section class="panel">
      <h2>Monthly Production</h2>
      <svg id="chart" viewBox="0 0 760 320" role="img" aria-label="Monthly oil and gas production chart"></svg>
      <div class="legend">
        <span><i class="oil"></i> oil bbl</span>
        <span><i class="gas"></i> gas mcf</span>
      </div>
    </section>
  </section>
  <section class="panel">
    <h2>Economics And Limits</h2>
    <div id="economics"></div>
  </section>
</main>
<script type="application/json" id="cores-data">{payload}</script>
<script>{_SCRIPT}</script>
</body>
</html>
"""


def _json_payload(summary: dict[str, Any]) -> str:
    return json.dumps(summary, allow_nan=False, sort_keys=True).replace("</", "<\\/")


def _limitations_html(summary: dict[str, Any]) -> str:
    items = [f"<li>{html.escape(str(item))}</li>" for item in summary["limitations"]]
    return "<ul>" + "".join(items) + "</ul>"


def _workbook_table(summary: dict[str, Any]) -> str:
    rows = []
    for product, data in sorted(summary["workbook_metadata"]["workbooks"].items()):
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(product))}</td>"
            f"<td>{html.escape(str(data['status_code']))}</td>"
            f"<td>{html.escape(str(data['byte_count']))}</td>"
            f"<td>{html.escape(str(data['last_modified']))}</td>"
            f"<td>{html.escape(str(data['sha256']))}</td>"
            f"<td>{html.escape(str(data['source_url']))}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>product</th><th>status_code</th><th>byte_count</th>"
        "<th>last_modified</th><th>sha256</th><th>source_url</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


_STYLE = """
:root{--bg:#f6f7f9;--fg:#1c2633;--muted:#607080;--line:#dce2ea;--panel:#fff;--oil:#1168b3;--gas:#b35b11;--accent:#0a7a52}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 Arial,Helvetica,sans-serif}
header{display:flex;gap:24px;align-items:flex-start;padding:22px 28px;background:#fff;border-bottom:1px solid var(--line)}
.home{color:var(--accent);font-weight:700;text-decoration:none}
h1{margin:0;font-size:30px}
h2{margin:0 0 14px;font-size:18px}
p{margin:6px 0;color:var(--muted)}
main{max-width:1180px;margin:0 auto;padding:24px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:18px}
.metrics div,.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px}
.metrics strong{display:block;font-size:26px}
.metrics span{display:block;color:var(--muted);font-size:13px}
.layout{display:grid;grid-template-columns:300px 1fr;gap:18px;margin:18px 0}
label{display:block;color:var(--muted);font-size:13px;margin-bottom:6px}
select{width:100%;height:38px;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--fg);padding:0 10px}
dl{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;margin:16px 0 0}
dt{color:var(--muted);font-size:12px}
dd{margin:0;font-weight:700;word-break:break-word}
svg{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fbfcfd}
.legend{display:flex;gap:18px;color:var(--muted);font-size:13px;margin-top:10px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.oil{background:var(--oil)}.gas{background:var(--gas)}
.warning{border-left:4px solid #b35b11;background:#fff8ef;padding:10px 12px;margin:8px 0}
.ok{border-left:4px solid var(--accent);background:#edf8f3;padding:10px 12px;margin:8px 0}
.table-wrap{overflow-x:auto;margin-top:12px}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f0f3f7}
@media(max-width:800px){header{display:block}.metrics,.layout{grid-template-columns:1fr}}
""".strip()


_SCRIPT = r"""
const data = JSON.parse(document.getElementById('cores-data').textContent);
const fields = data.fields.items;
const select = document.getElementById('field-select');
const detail = document.getElementById('field-detail');
const chart = document.getElementById('chart');
const economics = document.getElementById('economics');

function fmt(value) {
  return Number(value || 0).toLocaleString(undefined, {maximumFractionDigits: 0});
}

function init() {
  fields.forEach((field, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = field.field_name;
    select.appendChild(option);
  });
  select.addEventListener('change', () => render(Number(select.value)));
  const defaultIndex = Math.max(0, fields.findIndex(field =>
    data.economics.evaluated_fields.includes(field.field_name)));
  select.value = String(defaultIndex);
  render(defaultIndex);
}

function render(index) {
  const field = fields[index] || fields[0];
  detail.innerHTML = [
    ['Rows', fmt(field.row_count)],
    ['First period', field.first_period],
    ['Last period', field.last_period],
    ['Oil bbl', fmt(field.oil_bbl)],
    ['Gas mcf', fmt(field.gas_mcf)],
    ['Limits', (field.limitations || []).join(', ') || 'None flagged']
  ].map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(String(v))}</dd>`).join('');
  drawChart(field);
  renderEconomics(field.field_name);
}

function drawChart(selected) {
  const monthly = (selected.monthly || []).slice(-60);
  const max = Math.max(...monthly.map(item => Math.max(item.oil_bbl, item.gas_mcf)), 1);
  const slot = Math.max(8, Math.floor(650 / Math.max(monthly.length, 1)));
  const bars = monthly.map((item, i) => {
    const x = 58 + i * slot;
    const oilH = Math.max(1, item.oil_bbl / max * 230);
    const gasH = Math.max(1, item.gas_mcf / max * 230);
    const width = Math.max(2, Math.floor(slot / 3));
    return `<g><rect x="${x}" y="${280 - oilH}" width="${width}" height="${oilH}" fill="#1168b3"><title>${escapeHtml(selected.field_name)} ${escapeHtml(item.period)} oil ${fmt(item.oil_bbl)}</title></rect><rect x="${x + width + 1}" y="${280 - gasH}" width="${width}" height="${gasH}" fill="#b35b11"><title>${escapeHtml(selected.field_name)} ${escapeHtml(item.period)} gas ${fmt(item.gas_mcf)}</title></rect></g>`;
  });
  chart.innerHTML = `<line x1="44" y1="280" x2="730" y2="280" stroke="#8b98a8"/><text x="44" y="34" font-size="12" fill="#607080">${escapeHtml(selected.field_name)} monthly production, latest ${monthly.length} rows</text>${bars.join('')}`;
}

function renderEconomics(fieldName) {
  const result = data.economics.results[fieldName];
  if (!result) {
    economics.innerHTML = '<div class="warning">Economics deferred: field metadata or oil-backed valuation path is not curated for this field.</div>';
    return;
  }
  const metrics = result.pre_tax_metrics;
  economics.innerHTML = `<div class="ok"><strong>${escapeHtml(fieldName)}</strong> uses ${escapeHtml(result.dev_system)} reference-chain plumbing. onshore_model_mismatch=${metrics.onshore_model_mismatch}</div><dl><dt>Months</dt><dd>${fmt(metrics.months)}</dd><dt>Gross revenue USD</dt><dd>${fmt(metrics.gross_revenue_usd)}</dd><dt>Net cashflow USD</dt><dd>${fmt(metrics.net_cashflow_usd)}</dd><dt>Label</dt><dd>${escapeHtml(result.economics_label)}</dd></dl>`;
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

init();
""".strip()
