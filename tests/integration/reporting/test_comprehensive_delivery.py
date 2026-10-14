"""Publication contracts for the comprehensive report."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from worldenergydata.lower_tertiary import comprehensive_report as builder


@pytest.fixture(scope="module")
def report():
    return builder.assemble_comprehensive_report()


def test_revision_history_follows_summary_and_matches_declared_revision(
    report, tmp_path
):
    record = yaml.safe_load(builder.revision_record_path().read_text())
    latest = record["history"][-1]
    assert record["revision"] == latest["revision"]
    assert report.revision_record == record
    for render, suffix in (
        (builder.render_markdown, "md"),
        (builder.render_html, "html"),
    ):
        text = render(report, tmp_path / f"report.{suffix}").read_text()
        assert f"Revision: {latest['revision']}" in text
        if suffix == "md":
            headings = [
                line[3:] for line in text.splitlines() if line.startswith("## ")
            ]
            assert headings[:3] == [
                "Executive Summary",
                "Revision history",
                "Economic basis",
            ]
        else:
            import re

            assert re.findall(r"<h2>(.*?)</h2>", text)[:3] == [
                "Executive Summary",
                "Revision history",
                "Economic basis",
            ]
        assert latest["date"] in text
        assert latest["change"] in text


def test_separate_assemblies_have_identical_text_outputs(tmp_path):
    first = builder.assemble_comprehensive_report()
    second = builder.assemble_comprehensive_report()
    for render, suffix in (
        (builder.render_markdown, "md"),
        (builder.render_html, "html"),
    ):
        a = render(first, tmp_path / f"a.{suffix}")
        b = render(second, tmp_path / f"b.{suffix}")
        assert a.read_bytes() == b.read_bytes()


@pytest.mark.parametrize("render", [builder.render_markdown, builder.render_html])
def test_every_field_states_basis_and_missing_history(report, tmp_path, render):
    text = render(report, tmp_path / "report").read_text()
    assert text.count("Production history: not established") == len(
        report.economics_run.results
    )
    assert text.count("HSE: not established") == len(report.economics_run.results)
    assert text.count("assumed, based on previous experience") >= len(
        report.economics_run.results
    )
    assert "#651" in text
    assert str(report.economics_run.oil_price_usd_per_bbl) in text
    assert "data_through" in text


@pytest.mark.parametrize("render", [builder.render_markdown, builder.render_html])
def test_missing_citation_fails_before_writing(report, tmp_path, render):
    broken = deepcopy(report)
    broken.economics_run.results[0].citations.loc[0, "code_id"] = ""
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="citation"):
        render(broken, output)
    assert not output.exists()


def test_incomplete_roster_is_rejected(report):
    broken = deepcopy(report.economics_run)
    broken.results.pop()
    with pytest.raises(ValueError, match="roster"):
        builder.assemble_comprehensive_report(
            economics_run=broken, analytics_run=report.analytics_run
        )


def test_hse_placeholder_is_unknown_in_report(report):
    frame = builder.report_hse(report)
    assert frame["incident_count"].isna().all()
    assert report.analytics_run.hse["incident_count"].eq(0).all()


def test_missing_browser_does_not_write_a_fake_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(builder.shutil, "which", lambda name: None)
    output = tmp_path / "report.pdf"
    with pytest.raises(FileNotFoundError, match="Chrome"):
        builder.render_pdf(tmp_path / "report.html", output)
    assert not output.exists()


def test_manifest_matches_files_and_inputs(report, tmp_path):
    import hashlib
    import json

    paths = {
        "markdown": builder.render_markdown(report, tmp_path / "comprehensive_2026.md"),
        "html": builder.render_html(report, tmp_path / "comprehensive_2026.html"),
    }
    manifest_path = builder.write_manifest(report, paths, tmp_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["revision"] == report.revision_record["revision"]
    for output in manifest["outputs"]:
        path = tmp_path / Path(output["path"]).name
        assert output["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert output["size_bytes"] == path.stat().st_size
    for item in manifest["inputs"]:
        path = builder.repository_root() / item["path"]
        assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    first_bytes = manifest_path.read_bytes()
    assert builder.write_manifest(report, paths, tmp_path).read_bytes() == first_bytes


def test_revision_record_rejects_mismatched_latest_revision(tmp_path, monkeypatch):
    path = tmp_path / "revision.yml"
    path.write_text(
        "revision: B\nhistory:\n  - revision: A\n    date: '2026-10-14'\n    change: First issue\n"
    )
    monkeypatch.setattr(builder, "revision_record_path", lambda: path)
    with pytest.raises(ValueError, match="revision"):
        builder.load_revision_record()


def test_pdf_dates_and_headers_are_reproducible(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(builder.shutil, "which", lambda name: "chrome")

    def run(command, **kwargs):
        calls.append(command)
        destination = next(
            arg.split("=", 1)[1] for arg in command if arg.startswith("--print-to-pdf=")
        )
        stamp = "20261014010101" if len(calls) == 1 else "20261014020202"
        Path(destination).write_bytes(
            f"%PDF-1.4\n/CreationDate (D:{stamp}+00'00')\n/ModDate (D:{stamp}+00'00')\n%%EOF".encode()
        )

    monkeypatch.setattr(builder.subprocess, "run", run)
    a = builder.render_pdf(tmp_path / "report.html", tmp_path / "a.pdf")
    b = builder.render_pdf(tmp_path / "report.html", tmp_path / "b.pdf")
    assert a.read_bytes() == b.read_bytes()
    assert "--no-pdf-header-footer" in calls[0]
    assert any(arg.startswith("--user-data-dir=") for arg in calls[0])


def test_required_outputs_are_classified(report):
    contract = yaml.safe_load(
        (builder.repository_root() / "config/repo_structure.yml").read_text()
    )
    allowed = contract["temporary_exceptions"]["reports"]["allowed_paths"]
    for suffix in ("md", "html", "pdf", "manifest.json"):
        assert f"reports/lower_tertiary/comprehensive_2026.{suffix}" in allowed


def test_citations_resolve_to_real_fields_and_symbols(report):
    for econ in report.economics_run.results:
        for locator in builder._report_citations(report, econ)["code_id"]:
            assert builder._citation_resolves(locator), locator
    assert not builder._citation_resolves(
        "config/analysis/lower_tertiary/fields/anchor.yml#field.missing"
    )
    assert not builder._citation_resolves(
        "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#missing"
    )


def test_report_comparisons_use_one_decimal_place(report, tmp_path):
    import re

    for render, suffix in (
        (builder.render_markdown, "md"),
        (builder.render_html, "html"),
    ):
        text = render(report, tmp_path / f"report.{suffix}").read_text()
        assert not re.findall(r"(?<![a-zA-Z0-9])\d+\.\d{2,}(?![a-zA-Z0-9])", text)


def test_html_summary_has_no_raw_markdown_emphasis(report, tmp_path):
    text = builder.render_html(report, tmp_path / "report.html").read_text()
    assert "**" not in text
    assert "<strong>" in text


def test_display_units_match_the_model_without_changing_values(report):
    frame = builder._report_technology_frame(report)
    assert "mean_capex_usd_per_bbl_proxy" in frame
    assert frame["mean_capex_usd_per_bbl_proxy"].equals(
        report.analytics_run.technology["mean_capex_per_mmbbl_usd"]
    )
    assert "plateau_thousand_bbl_per_day" in builder._report_summary_frame(report)
    assert "sum_wi_plateau_thousand_bbl_per_day" in builder._report_operator_frame(
        report
    )


def test_annual_mirr_requires_consistent_cashflow_periods(report, tmp_path):
    import re

    original = report.economics_run.to_summary_frame()["mirr_annual"].copy()
    page = builder.render_html(report, tmp_path / "period-basis.html").read_text()
    table = next(
        value
        for value in re.findall(r"<table.*?</table>", page, re.S)
        if "mirr_annual_pct" in value
    )
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
    headers = re.findall(r"<th[^>]*>(.*?)</th>", rows[0], re.S)
    column = headers.index("mirr_annual_pct")
    for row in rows[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        assert cells[column].strip() == "Not established"
    markdown = builder.render_markdown(report, tmp_path / "period-basis.md").read_text()
    for document in (page, markdown):
        assert (
            document.count("Annual MIRR: not established")
            == len(report.economics_run.results) + 1
        )
        assert "monthly-period rate routine" in document
        assert "annual cashflows" in document
    assert original.equals(report.economics_run.to_summary_frame()["mirr_annual"])


@pytest.mark.parametrize("render", [builder.render_markdown, builder.render_html])
def test_public_sources_are_printed_with_retrieval_evidence(report, tmp_path, render):
    text = render(report, tmp_path / "sources").read_text()
    for fid in ("cascade_chinook", "jack_st_malo", "julia"):
        sources = report.field_payloads[fid].get("sources", {})
        assert sources, fid
        for key, references in sources.items():
            citations = builder._report_citations(
                report,
                next(
                    econ
                    for econ in report.economics_run.results
                    if econ.field_id == fid
                ),
            )
            for source in references:
                assert source["url"] in text
                assert source["title"] in text
                rows = citations[citations["url"] == source["url"]]
                assert not rows.empty
                assert (
                    rows["code_id"]
                    == f"config/analysis/lower_tertiary/fields/{fid}.yml#field.{key}"
                ).any()
                if source["retrieved"]:
                    assert source["retrieved"] in text
                    assert source["sha256"] in text
                else:
                    assert "not retrieved in this revision" in rows["retrieved"].values


def test_only_generic_defaults_claim_previous_experience(report):
    generic = (
        "discount_rate:",
        "reinvestment_rate:",
        "annual_decline:",
        "project_years:",
        "plateau_years:",
    )
    for econ in report.economics_run.results:
        citations = builder._report_citations(report, econ)
        for row in citations.to_dict("records"):
            if "assumed, based on previous experience" in row["basis"]:
                assert row["input"].startswith(generic)
            if row["url"] in ("Not applicable", "Not established") and row[
                "input"
            ].startswith(
                ("Capex", "Plateau", "Opex", "Royalty", "Oil price", "Sensitivity")
            ):
                assert row["basis"] == "assumed (unsourced configuration value, #651)"


@pytest.mark.parametrize("render", [builder.render_markdown, builder.render_html])
def test_disputed_interests_are_excluded_and_concentration_recomputed(
    report, tmp_path, render
):
    from worldenergydata.lower_tertiary.portfolio_analytics import (
        analyze_operator_concentration,
    )

    excluded = {"cascade_chinook", "jack_st_malo"}
    for fid in excluded:
        assert report.field_payloads[fid]["working_interest_status"] in (
            "contradicted",
            "unverified",
        )
    eligible = [fid for fid in report.field_payloads if fid not in excluded]
    expected = analyze_operator_concentration(eligible).rename(
        columns={"sum_wi_plateau_mbopd": "sum_wi_plateau_thousand_bbl_per_day"}
    )
    frame = builder._report_operator_frame(report)
    assert frame.equals(expected)
    eligible_capex = sum(
        e.capex_mm_usd for e in report.economics_run.results if e.field_id in eligible
    )
    assert frame["sum_wi_capex_mm_usd"].sum() == eligible_capex
    assert "Suncor" not in frame["company"].values
    top = frame.iloc[0]
    assert top["share_capex_pct"] == 100.0 * top["sum_wi_capex_mm_usd"] / eligible_capex
    bullet = next(
        s for s in report.executive_summary if s.startswith("Operator concentration:")
    )
    assert f"{top['share_capex_pct']:.1f}%" in bullet
    assert f"{int(top['field_count'])} fields" in bullet
    assert frame["hhi_contribution"].equals(frame["share_capex_pct"] ** 2)
    # The full-portfolio capital total is independent of the filtered WI denominator.
    total = sum(e.capex_mm_usd for e in report.economics_run.results)
    assert any(
        f"${total:,.0f} M" in b
        for b in report.executive_summary
        if b.startswith("Portfolio totals:")
    )
    text = render(report, tmp_path / "concentration").read_text()
    assert (
        "Cascade/Chinook and Jack/St. Malo excluded: working interests contradicted or unverified"
        in text
    )


def test_exclusion_is_driven_by_configuration_status(report):
    broken = deepcopy(report)
    for fid in broken.field_payloads:
        broken.field_payloads[fid]["working_interest_status"] = "unverified"
    assert builder._report_operator_frame(broken).empty


def test_revision_b_preserves_revision_a(report):
    assert [row["revision"] for row in report.revision_record["history"]][:2] == [
        "A",
        "B",
    ]
    assert report.revision_record["history"][0]["change"] == (
        "First issue combines ten-field scenario economics, source references and "
        "explicit data gaps to support comparisons on a stated assumption basis."
    )


def test_no_eligible_interests_withholds_summary_share(report, monkeypatch):
    def payload(field_id):
        data = deepcopy(report.field_payloads[field_id])
        data["working_interest_status"] = "unverified"
        return data

    monkeypatch.setattr(builder, "_load_field_payload", payload)
    result = builder.assemble_comprehensive_report(
        economics_run=report.economics_run, analytics_run=report.analytics_run
    )
    bullet = next(
        s for s in result.executive_summary if s.startswith("Operator concentration:")
    )
    assert "Not established" in bullet
    assert "largest" not in bullet
