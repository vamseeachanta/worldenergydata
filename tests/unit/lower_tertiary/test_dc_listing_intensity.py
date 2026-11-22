"""Synthetic publication previews, with independent hand calculations."""

import socket

import pandas as pd
import pytest

from tests.unit.lower_tertiary.test_dc_drilldown_intensity import write_bores
from tests.unit.lower_tertiary.test_dc_provenance import REPO, load_script, patch_inputs


@pytest.fixture
def surfaces(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network disabled in synthetic tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    listing = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
    drilldown = load_script(REPO / "scripts/lower_tertiary/build_dc_drilldown.py")
    exporter = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    inputs = [tmp_path / f"input-{i}.csv" for i in range(3)]
    inputs[1].write_text("api12\n", encoding="utf-8", newline="\n")
    inputs[2].write_text(
        "api12,dev,category,drill_v30,compl_v30,drill_wed,compl_wed,d_drill,d_compl,spud_wed\n"
        "synthetic-00,synthetic-field,unchanged,0,0,0,0,0,0,\n",
        encoding="utf-8",
        newline="\n",
    )
    for mod in (listing, drilldown):
        patch_inputs(monkeypatch, mod, inputs)
        monkeypatch.setattr(mod, "STATUS", {"synthetic-field": ("synthetic", "ok")})
    monkeypatch.setattr(drilldown, "SLUG", {"synthetic-field": "synthetic-field"})
    monkeypatch.setattr(exporter, "_load_listing_module", lambda: listing)
    monkeypatch.setattr(exporter, "_drilldown_extras", dict)
    return listing, drilldown, exporter


@pytest.mark.parametrize("denominator,expected", [("md", 20), ("tvd", 40)])
def test_all_surfaces_agree(surfaces, denominator, expected):
    """40 / 20000 * 10000 = 20 MD; 40 / 10000 * 10000 = 40 TVD."""
    listing, drilldown, exporter = surfaces
    write_bores(listing)
    bores = listing.load_bores(intensity_denominator=denominator)
    bore = bores["synthetic-field"][0]
    payload = drilldown.load_payload(intensity_denominator=denominator)
    tables = exporter.build_tables(intensity_denominator=denominator)
    for row in (bore, payload["bores"][0], tables["dc_bores"].iloc[0]):
        assert row["days_per_10k_ft"] == expected
        assert row["days_per_10k_ft_denominator"] == denominator
        assert row["days_per_10k_md"] == 20
        assert row["days_per_10k_tvd"] == 40
    text = listing.build_markdown(bores, {})
    assert f"Days/10K ({denominator.upper()})" in text
    assert "SPE-87117-MS" in text
    assert "Included / excluded (MD)" in text
    assert "days_per_10k_ft" not in listing.load_bores()["synthetic-field"][0]
    assert "days_per_10k_ft" not in exporter.build_tables()["dc_bores"]


def test_rollup_weighting_and_independent_coverage(surfaces):
    """MD: (10+90)/(10000+30000)*10000=25, not mean(10,30)=20.

    TVD: (10+90+40)/(10000+10000+10000)*10000=140/3.
    The third bore lacks MD and must be excluded from both MD totals.
    """
    listing, _, exporter = surfaces
    write_bores(
        listing,
        {"DRILLING_DAYS": "10", "MAX_BH_TOTAL_MD": "10000"},
        {"DRILLING_DAYS": "90", "MAX_BH_TOTAL_MD": "30000"},
        {"MAX_BH_TOTAL_MD": ""},
    )
    tables = exporter.build_tables(intensity_denominator="md")
    row = tables["dc_development_summary"].iloc[0]
    assert row["days_per_10k_ft"] == 25
    assert row["days_per_10k_tvd"] == pytest.approx(140 / 3)
    assert row["total_drilling_days_md"] == 100
    assert row["total_depth_ft_md"] == 40000
    assert row["included_bores_md"] == 2
    assert row["excluded_bores_md"] == 1
    assert row["excluded_bores_tvd"] == 0
    assert row["intensity_status"] == "computed_partial"
    text = listing.build_markdown(listing.load_bores(intensity_denominator="md"), {})
    assert "25.0" in text
    assert "46.7" in text


@pytest.mark.parametrize("raw", ["", "-1", "0", "0.5", "nan", "inf", "-inf"])
def test_nullable_raw_days_not_legacy_display_values(surfaces, raw):
    """Absent/negative: undefined; 0/20000*10000=0; 0.5/20000*10000=0.25."""
    listing, _, exporter = surfaces
    write_bores(listing, {"DRILLING_DAYS": raw})
    tables = exporter.build_tables(intensity_denominator="md")
    for name in ("dc_bores", "dc_development_summary"):
        value = tables[name].iloc[0]["days_per_10k_ft"]
        if raw in ("", "-1", "nan", "inf", "-inf"):
            assert pd.isna(value)
        else:
            assert value == float(raw) / 2


def assert_excluded_drilling(row):
    for suffix in ("md", "tvd"):
        assert pd.isna(row[f"days_per_10k_{suffix}"])
        assert row[f"included_bores_{suffix}"] == 0
        assert row[f"excluded_bores_{suffix}"] == 1
        assert row[f"intensity_status_{suffix}"] == "no_valid_pairs"


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf"])
@pytest.mark.parametrize("denominator,expected", [("md", 20), ("tvd", 40)])
@pytest.mark.parametrize("surface", ["listing", "dataset"])
@pytest.mark.parametrize("valid_neighbor", [True, False])
def test_nonfinite_days_excluded_without_losing_rows(
    surfaces, raw, denominator, expected, surface, valid_neighbor
):
    """Valid neighbor: 40/20000*10000=20 MD; 40/10000*10000=40 TVD."""
    listing, _, exporter = surfaces
    write_bores(
        listing,
        {"DRILLING_DAYS": raw},
        {"DRILLING_DAYS": "40" if valid_neighbor else raw},
    )
    listing.WO_ARTICLE["synthetic-field"] = (2, 0, 1840)
    if surface == "listing":
        from lower_tertiary.dc_intensity import rollup

        devs = listing.load_bores(intensity_denominator=denominator)
        bores = devs["synthetic-field"]
        summary = rollup(bores, denominator=denominator)
        text = listing.build_markdown(devs, {})
        assert "| — | 900 | — |" in text
        ratio_text = str(float(expected)) if valid_neighbor else "—"
        assert f"| synthetic-field | {ratio_text} |" in text
    else:
        tables = exporter.build_tables(intensity_denominator=denominator)
        bores = tables["dc_bores"].to_dict("records")
        summary = tables["dc_development_summary"].iloc[0]
    assert len(bores) == 2
    assert pd.isna(bores[0]["days_per_10k_ft"])
    assert_excluded_drilling(bores[0])
    for suffix in ("md", "tvd"):
        assert summary[f"included_bores_{suffix}"] == int(valid_neighbor)
        assert summary[f"excluded_bores_{suffix}"] == 2 - int(valid_neighbor)
    if valid_neighbor:
        assert bores[1]["days_per_10k_ft"] == expected
        assert summary["days_per_10k_ft"] == expected
        assert summary["total_drilling_days_md"] == 40
        assert summary["total_depth_ft_md"] == 20000
        assert summary["intensity_status"] == "computed_partial"
    else:
        assert pd.isna(summary["days_per_10k_ft"])
        assert pd.isna(summary["total_drilling_days_md"])
        assert summary["intensity_status"] == "no_valid_pairs"
    if surface == "dataset":
        assert pd.isna(bores[0]["drilling_days"])
        assert pd.isna(bores[0]["dc_days"])
        assert pd.isna(summary["drilling_days"])
        assert pd.isna(summary["delta_days"])


def test_unlabelled_source_refuses_ratios(surfaces):
    """A supplied day count does not establish a basis."""
    listing, _, exporter = surfaces
    write_bores(listing, labelled=False)
    for name in ("dc_bores", "dc_development_summary"):
        row = exporter.build_tables(intensity_denominator="md")[name].iloc[0]
        assert pd.isna(row["days_per_10k_ft"])
        assert row["intensity_status"] == "missing_basis"


def test_conflicting_basis_on_excluded_bore_refuses_rollup(surfaces):
    listing, _, exporter = surfaces
    write_bores(listing, {}, {"BASIS": "other-rule", "MAX_BH_TOTAL_MD": ""})
    row = exporter.build_tables(intensity_denominator="md")[
        "dc_development_summary"
    ].iloc[0]
    assert pd.isna(row["days_per_10k_ft"])
    assert row["intensity_status"] == "mixed_basis"


def test_completion_excluded_and_parquet_round_trip(surfaces, tmp_path):
    """40/20000*10000=20 regardless of completion days; nulls survive export."""
    listing, _, exporter = surfaces
    write_bores(listing, {"COMPLETION_DAYS": "0"}, {"DRILLING_DAYS": ""})
    before = exporter.build_tables(intensity_denominator="md")["dc_bores"]
    write_bores(listing, {"COMPLETION_DAYS": "900"}, {"DRILLING_DAYS": ""})
    after = exporter.build_tables(intensity_denominator="md")["dc_bores"]
    columns = [c for c in before if "10k" in c or c.startswith("total_")]
    pd.testing.assert_frame_equal(before[columns], after[columns])
    target = tmp_path / "preview.parquet"
    after.to_parquet(target, index=False)
    pd.testing.assert_frame_equal(pd.read_parquet(target), after)


def test_duplicate_bore_refused(surfaces):
    listing, _, _ = surfaces
    write_bores(
        listing, {"API_WELL_NUMBER": "duplicate"}, {"API_WELL_NUMBER": "duplicate"}
    )
    with pytest.raises(ValueError, match="unique bore"):
        listing.load_bores(intensity_denominator="md")


def test_listing_cli_requires_separate_preview(surfaces, monkeypatch, tmp_path):
    listing, _, _ = surfaces
    write_bores(listing)
    monkeypatch.setattr(listing, "OUT_MD", tmp_path / "published.md")
    for args in (
        ["--intensity-denominator", "md"],
        ["--intensity-denominator", "md", "--output", str(listing.OUT_MD)],
    ):
        with pytest.raises(SystemExit):
            listing.main(args)
    output = tmp_path / "preview.md"
    listing.main(["--intensity-denominator", "md", "--output", str(output)])
    assert "Days/10K (MD)" in output.read_text(encoding="utf-8")
    assert not listing.OUT_MD.exists()


def test_export_preview_cannot_publish(surfaces):
    _, _, exporter = surfaces
    with pytest.raises(SystemExit):
        exporter.main(["--intensity-denominator", "md"])


def test_basis_text_is_escaped_in_preview(surfaces):
    listing, _, _ = surfaces
    write_bores(listing, {"BASIS": "synthetic | rule\n<tag>"})
    text = listing.build_markdown(listing.load_bores(intensity_denominator="md"), {})
    assert "synthetic \\| rule<br>&lt;tag&gt;" in text


def test_invalid_denominator_rejected(surfaces):
    listing, _, exporter = surfaces
    for loader in (listing.load_bores, exporter.build_tables):
        with pytest.raises(ValueError, match="denominator"):
            loader(intensity_denominator="unknown")


def test_all_null_parquet_has_numeric_schema_and_reference(surfaces, tmp_path):
    """Missing basis means undefined ratios, with a stable nullable numeric type."""
    listing, _, exporter = surfaces
    write_bores(listing, labelled=False)
    tables = exporter.build_tables(intensity_denominator="md")
    for name in ("dc_bores", "dc_development_summary"):
        target = tmp_path / f"{name}.parquet"
        tables[name].to_parquet(target, index=False)
        restored = pd.read_parquet(target)
        assert str(restored["days_per_10k_ft"].dtype) == "Float64"
        assert restored["days_per_10k_ft"].isna().all()
        # SPE-87117-MS (2004), public abstract paragraph 4, bounds and units.
        assert restored.iloc[0]["days_per_10k_reference_lower"] == 20
        assert restored.iloc[0]["days_per_10k_reference_upper"] == 23
        assert "denominator" in restored.iloc[0]["days_per_10k_reference_qualification"]


@pytest.mark.parametrize("depth", ["", "0", "-1"])
def test_invalid_depth_only_excludes_its_own_denominator(surfaces, depth):
    """MD undefined; TVD 40 / 10000 * 10000 = 40 remains defined."""
    listing, _, exporter = surfaces
    write_bores(listing, {"MAX_BH_TOTAL_MD": depth})
    for name in ("dc_bores", "dc_development_summary"):
        row = exporter.build_tables(intensity_denominator="md")[name].iloc[0]
        assert pd.isna(row["days_per_10k_md"])
        assert row["days_per_10k_tvd"] == 40
        assert row["excluded_bores_md"] == 1
        assert row["excluded_bores_tvd"] == 0


def test_separate_field_summaries_keep_their_own_members(surfaces):
    """First: 90/30000*10000=30; other field: 10/10000*10000=10."""
    listing, _, exporter = surfaces
    listing.STATUS["other-field"] = "synthetic"
    write_bores(
        listing,
        {"DRILLING_DAYS": "90", "MAX_BH_TOTAL_MD": "30000"},
        {
            "LEASE_NAME": "other-field",
            "SURF_LEASE_NUM": "other-block",
            "DRILLING_DAYS": "10",
            "MAX_BH_TOTAL_MD": "10000",
        },
    )
    table = exporter.build_tables(intensity_denominator="md")["dc_development_summary"]
    assert dict(zip(table["development"], table["days_per_10k_ft"])) == {
        "other-field": 10,
        "synthetic-field": 30,
    }
