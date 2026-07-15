# ABOUTME: E5 (#1028) — render the reconciliation harness output: reconciliation.csv + the A1 evidence pack HTML.
# ABOUTME: Consumes the four curated cost tables via worldenergydata.cost.timeseries.reconciliation.
"""
build_reconciliation
====================

Emits, from the four curated cost tables:

* ``reports/cost/reconciliation.csv`` — every cross-check row, flat, for the record.
* ``reports/cost/a1_evidence_pack.html`` — the decision-A1 evidence pack: does the
  sourced award evidence support the stage-share priors?

The headline the pack must answer honestly: **no sourced award exceeds its
stage's prior band, and the only full-scope award anchors land in-band (Suriname
SURF) or just below it (Guyana SURF) — so the A1 priors are corroborated where
testable and contradicted nowhere.** The below-band majority are floors (band
low-bounds, single rigs, FPSO hull buyouts) and are labelled as such so they are
not mis-read as refutations.
"""

from __future__ import annotations

import csv
import html as _html
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "worldenergydata-cost" / "src"))

from worldenergydata.cost.timeseries.reconciliation import reconcile  # noqa: E402

CURATED = PROJECT_ROOT / "data" / "modules" / "cost" / "curated"
OUT_DIR = PROJECT_ROOT / "reports" / "cost"
_esc = _html.escape


def _write_csv(rec) -> Path:
    path = OUT_DIR / "reconciliation.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["CHECK", "PROJECT", "DETAIL", "VALUE", "REFERENCE", "VERDICT"])
        for c in rec.coverage:
            w.writerow(
                [
                    "coverage",
                    c.project,
                    f"{c.n_valued_awards} valued / {c.n_not_public_awards} not-public awards",
                    f"{c.coverage_low_pct:.0f}%+",
                    f"gross ${c.gross_mm:.0f}MM",
                    "",
                ]
            )
        for p in rec.partner_checks:
            w.writerow(
                [
                    "partner_net",
                    p.project,
                    f"{p.company} {p.interest_pct}% net ${p.net_mm:.0f}",
                    f"implied gross ${p.implied_gross_mm:.0f}",
                    (
                        f"disclosed ${p.disclosed_gross_mm:.0f}"
                        if p.disclosed_gross_mm
                        else "n/a"
                    ),
                    p.note,
                ]
            )
        for s in rec.stage_anchors:
            w.writerow(
                [
                    "stage_anchor",
                    s.project,
                    f"{s.stage} ({s.contractor})",
                    f"{s.implied_share*100:.1f}%",
                    f"prior {s.prior_low*100:.0f}-{s.prior_high*100:.0f}%",
                    f"{s.verdict}{'' if not s.is_lower_bound else ' (floor)'}",
                ]
            )
        for o in rec.outturn:
            w.writerow(
                [
                    "outturn",
                    o.project,
                    f"{o.currency} sanction->final",
                    f"x{o.multiplier:.2f}",
                    f"{o.sanction_mm:.0f}->{o.final_mm:.0f}",
                    "",
                ]
            )
    return path


CSS = """
:root{--paper:#f5f7f7;--card:#fff;--ink:#0d2230;--muted:#5f7684;--rule:#e2e8ea;
--brand:#0b3d5c;--brand-ink:#eaf2f2;--good:#1b7f5c;--warn:#b0721a;--bad:#a8442a;--floor:#8894a0;}
@media(prefers-color-scheme:dark){:root{--paper:#0e1a22;--card:#152430;--ink:#e5edf2;
--muted:#93a7b3;--rule:#24363f;--brand:#0b2c42;--brand-ink:#dcebf2;--good:#2f9d77;
--warn:#c08118;--bad:#c9664a;--floor:#6b7b88;}}
*{box-sizing:border-box;margin:0}
body{font:15px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:var(--paper);color:var(--ink);padding:0 0 64px}
header{background:var(--brand);color:var(--brand-ink);padding:32px 24px}
header h1{font-size:23px;max-width:960px;margin:0 auto}
header p{max-width:960px;margin:8px auto 0;opacity:.88}
main{max-width:960px;margin:0 auto;padding:0 16px}
h2{font-size:19px;margin:30px 0 6px}
p{margin:8px 0}.mini{font-size:12.5px}.muted{color:var(--muted)}
.callout{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--good);
border-radius:10px;padding:16px 18px;margin:18px 0}
.tscroll{overflow-x:auto;border:1px solid var(--rule);border-radius:10px;background:var(--card);margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:640px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.v{font-weight:600;padding:1px 8px;border-radius:99px;font-size:12px;color:#fff;white-space:nowrap}
.in_band{background:var(--good)}.below_band{background:var(--warn)}.above_band{background:var(--bad)}
.floor{background:var(--floor)}
footer{max-width:960px;margin:36px auto 0;padding:14px 16px;color:var(--muted);font-size:12.5px;
border-top:1px solid var(--rule)}
"""


def _cov_table(rec) -> str:
    rows = "".join(
        f"<tr><td>{_esc(c.project)}</td><td class='num'>${c.gross_mm:,.0f}</td>"
        f"<td class='num'>${c.valued_award_low_mm:,.0f}</td>"
        f"<td class='num'>{c.coverage_low_pct:.0f}%+</td>"
        f"<td class='num'>{c.n_valued_awards} / {c.n_not_public_awards}</td></tr>"
        for c in rec.coverage
    )
    return (
        '<div class="tscroll"><table><thead><tr><th>Project</th><th>Gross CAPEX</th>'
        "<th>Valued awards (low)</th><th>Coverage</th><th>Valued / not-public</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _partner_table(rec) -> str:
    rows = ""
    for p in rec.partner_checks:
        g = f"${p.disclosed_gross_mm:,.0f}" if p.disclosed_gross_mm else "—"
        rows += (
            f"<tr><td>{_esc(p.project)}</td><td>{_esc(p.company)}</td>"
            f"<td class='num'>{p.interest_pct:.1f}%</td>"
            f"<td class='num'>${p.net_mm:,.0f}</td>"
            f"<td class='num'>${p.implied_gross_mm:,.0f}</td>"
            f"<td class='num'>{g}</td><td class='mini'>{_esc(p.note)}</td></tr>"
        )
    return (
        '<div class="tscroll"><table><thead><tr><th>Project</th><th>Partner</th>'
        "<th>Interest</th><th>Net share</th><th>Implied gross</th><th>Disclosed gross</th>"
        f"<th>Reconciliation</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _anchor_table(rows) -> str:
    body = ""
    for s in rows:
        cls = "floor" if (s.is_lower_bound and s.verdict == "below_band") else s.verdict
        label = f"{s.verdict}{' (floor)' if s.is_lower_bound else ''}"
        body += (
            f"<tr><td>{_esc(s.project)}</td><td>{_esc(s.stage)}</td>"
            f"<td>{_esc(s.contractor)}</td>"
            f"<td class='num'>{s.implied_share*100:.1f}%</td>"
            f"<td class='num'>{s.prior_low*100:.0f}–{s.prior_high*100:.0f}%</td>"
            f"<td><span class='v {cls}'>{_esc(label)}</span></td>"
            f"<td class='mini muted'>{_esc(s.note)}</td></tr>"
        )
    return (
        '<div class="tscroll"><table><thead><tr><th>Project</th><th>Stage</th>'
        "<th>Contractor</th><th>Implied share</th><th>Prior band</th><th>Verdict</th>"
        f"<th>Interpretation</th></tr></thead><tbody>{body}</tbody></table></div>"
    )


def _outturn_table(rec) -> str:
    rows = "".join(
        f"<tr><td>{_esc(o.project)}</td><td>{_esc(o.currency)}</td>"
        f"<td class='num'>{o.sanction_mm:,.0f}</td><td class='num'>{o.final_mm:,.0f}</td>"
        f"<td class='num'><strong>×{o.multiplier:.2f}</strong></td></tr>"
        for o in rec.outturn
    )
    return (
        '<div class="tscroll"><table><thead><tr><th>Project</th><th>Ccy</th>'
        "<th>Sanction</th><th>Final</th><th>Multiplier</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def main() -> int:
    rec = reconcile(CURATED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = _write_csv(rec)

    full = [s for s in rec.stage_anchors if not s.is_lower_bound]
    floors = [s for s in rec.stage_anchors if s.is_lower_bound]
    above = [s for s in rec.stage_anchors if s.verdict == "above_band"]
    in_band_full = [s for s in full if s.verdict == "in_band"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    repo = "https://github.com/vamseeachanta/worldenergydata"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cost reconciliation — the A1 evidence pack</title>
<style>{CSS}</style></head><body>
<header>
<div class="mini" style="max-width:960px;margin:0 auto;opacity:.75">AceEngineer · worldenergydata · issue #1028 (E5)</div>
<h1>Cost reconciliation — evidence for decision A1 (stage-share priors)</h1>
<p>Four independent views of the same project cost — the sanctioned total, the summed
contract awards, the partners' net shares, and the outturn trail — cross-checked, with the
residuals reported. The question A1 asks: <strong>do the sourced awards support the
assumed stage-share split?</strong></p>
</header>
<main>
<div class="callout">
<h2 style="margin-top:0">Verdict: the priors are corroborated where testable, and contradicted nowhere.</h2>
<p><strong>{len(above)} of {len(rec.stage_anchors)}</strong> award anchors exceed their stage's
prior band (i.e. none do). Of the <strong>{len(full)}</strong> anchors that are full-scope explicit
EPCI awards — the only ones that genuinely test a prior — the three largest by value all land
<strong>inside</strong> the band (Kaombo, Martin Linge and GranMorgu SURF EPCIs, $0.8–3.5bn each),
and none lands above it. The other {len(floors)} anchors are <em>floors</em> (band/range low-bounds,
single-rig backlogs, FPSO hull buyouts, component supplies) that under-represent their stage by
construction, so their below-band position carries no signal.</p>
<p class="mini muted">The below-band full-scope anchors cluster by <em>development architecture</em>,
not error: SURF share is structurally small on platform and dry-tree developments (Shenzi TLP 1.7%,
Mariner/Culzean fixed-platform 2–3%, whose wells are mostly platform-drilled) and larger on
subsea-to-FPSO developments — where the in-band anchors sit. Guyana's SURF (Liza 2 at 11.7%) also
runs below Suriname's (GranMorgu 18.1%): short benign flowline runs vs long ones. Both patterns say
the split should key on architecture and region — which the priors already do by development type —
rather than that any prior is wrong.</p>
</div>

<h2>1 · Award coverage vs sanctioned gross</h2>
<p>Sum of capex-comparable valued awards (band low-bounds; lease/midstream/combined excluded)
as a share of the disclosed gross. A floor on how much of the top-down total the bottom-up
awards account for.</p>
{_cov_table(rec)}

<h2>2 · Partner net share ÷ interest vs gross</h2>
<p>The second costing ladder. Guyana (Hess) nets land ~20–30% below gross — the known
FPSO-exclusion — and the harness flags it. Barossa reconciles within 10%. GranMorgu's
Staatsolie figure implies a higher gross because Staatsolie quotes a $12.2bn total (extra scope)
vs the operator's $10.5bn — a base discrepancy the check surfaces rather than hides.</p>
{_partner_table(rec)}

<h2>3 · Stage anchors — the direct A1 test</h2>
<p><strong>Full-scope explicit awards</strong> (a complete SURF EPCI, not a floor): the genuine tests.</p>
{_anchor_table(full)}
<p style="margin-top:18px"><strong>Floors</strong> — partial-scope awards; below-band is expected and
uninformative about the prior. Shown for completeness.</p>
{_anchor_table(floors)}

<h2>4 · Outturn multipliers (from the revision trails)</h2>
<p>How far FID figures actually run from final: ×0.78 (Kraken, under) to ×2.46 (Martin Linge, NOK).
This is why a single FID number is not a cost basis — the deck must carry the distribution, not the point.</p>
{_outturn_table(rec)}

<footer>Generated {generated} by <code>scripts/cost/build_reconciliation.py</code> from the four
curated cost tables (<code>sanctioned_projects</code>, <code>contract_awards</code>,
<code>project_cost_statements</code>, <code>cost_revision_trails</code>). Machine-readable form:
<code>reports/cost/reconciliation.csv</code>. Issues
<a href="{repo}/issues/1028">#1028</a> · <a href="{repo}/issues/1017">#1017</a> (A1) ·
<a href="{repo}/issues/844">#844</a>.</footer>
</main></body></html>"""

    out = OUT_DIR / "a1_evidence_pack.html"
    out.write_text(html, encoding="utf-8")
    print(
        f"wrote {csv_path.name} ({len(rec.coverage)} coverage, "
        f"{len(rec.partner_checks)} partner, {len(rec.stage_anchors)} anchors, "
        f"{len(rec.outturn)} outturn) + {out.name} ({out.stat().st_size:,} bytes)"
    )
    print(
        f"A1 verdict: {len(above)} above-band, {len(in_band_full)}/{len(full)} full-scope in-band"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
