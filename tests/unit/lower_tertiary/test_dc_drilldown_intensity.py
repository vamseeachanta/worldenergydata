"""Synthetic integration cases; expected ratios are hand-calculated below."""

import csv
import importlib.util
import json
import re
import socket
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def builder(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network access is forbidden in synthetic tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    spec = importlib.util.spec_from_file_location(
        "drilldown_intensity", REPO / "scripts/lower_tertiary/build_dc_drilldown.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "SLUG", {"synthetic-field": "synthetic-field"})
    monkeypatch.setattr(mod, "STATUS", {"synthetic-field": ("synthetic", "ok")})
    for name in ("SOURCE_CSV", "BENCHMARK_CSV", "VINTAGE_CSV"):
        path = tmp_path / f"{name}.csv"
        path.write_text("api12\n", encoding="utf-8")
        monkeypatch.setattr(mod, name, path)
    return mod


def write_bores(builder, *changes, labelled=True):
    """Synthetic units: days and feet; no measured well data."""
    base = {
        "API_WELL_NUMBER": "synthetic-00",
        "WELL_NAME": "synthetic",
        "LEASE_NAME": "synthetic-field",
        "SURF_LEASE_NUM": "synthetic-block",
        "WATER_DEPTH": "",
        "WELL_SPUD_DATE": "",
        "TOTAL_DEPTH_DATE": "",
        "DRILLING_DAYS": "40",
        "COMPLETION_DAYS": "900",
        "MAX_BH_TOTAL_MD": "20000",
        "MAX_WELL_BORE_TVD": "10000",
        "MAX_DRILL_FLUID_WGT": "",
    }
    if labelled:
        base.update(BASIS="synthetic-rule", PND_DAYS="", DAYS_STATUS="war_covered")
    rows = [
        dict(base, **({"API_WELL_NUMBER": f"synthetic-{i}"} | row))
        for i, row in enumerate(changes)
    ] or [base]
    with builder.SOURCE_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("denominator,expected", [("md", 20), ("tvd", 40)])
def test_opt_in_bore_ratio_and_declared_denominator(builder, denominator, expected):
    """40 / 20000 * 10000 = 20 MD; 40 / 10000 * 10000 = 40 TVD."""
    write_bores(builder)
    legacy = builder.load_payload()
    payload = builder.load_payload(intensity_denominator=denominator)
    bore = payload["bores"][0]
    assert bore["days_per_10k_ft"] == expected
    assert bore["days_per_10k_md"] == 20
    assert bore["days_per_10k_tvd"] == 40
    assert bore["days_per_10k_ft_denominator"] == denominator
    assert bore["basis"] == "synthetic-rule"
    for key, value in legacy["bores"][0].items():
        assert bore[key] == value
    assert "days_per_10k_ft" not in legacy["bores"][0]
    json.dumps(payload, allow_nan=False)


@pytest.mark.parametrize("raw", ["", "-1"])
def test_missing_or_invalid_drilling_is_not_zero(builder, raw):
    """An absent/invalid numerator has no defined ratio, for either depth."""
    write_bores(builder, {"DRILLING_DAYS": raw})
    payload = builder.load_payload(intensity_denominator="md")
    for surface in ("bores", "fields", "blocks"):
        row = payload[surface][0]
        assert row["days_per_10k_ft"] is None
        assert row["days_per_10k_tvd"] is None
        assert row["included_bores_md"] == 0
        assert row["excluded_bores_md"] == 1


def test_zero_and_fractional_days_are_preserved(builder):
    """0 / 20000 * 10000 = 0; 0.5 / 20000 * 10000 = 0.25."""
    write_bores(builder, {"DRILLING_DAYS": "0"}, {"DRILLING_DAYS": "0.5"})
    bores = builder.load_payload(intensity_denominator="md")["bores"]
    assert [b["days_per_10k_ft"] for b in bores] == [0, 0.25]


@pytest.mark.parametrize("depth", ["", "0", "-1"])
def test_depth_coverage_is_independent(builder, depth):
    """MD undefined; 40 / 10000 * 10000 = 40 TVD still defined."""
    write_bores(builder, {"MAX_BH_TOTAL_MD": depth})
    payload = builder.load_payload(intensity_denominator="md")
    for surface in ("bores", "fields", "blocks"):
        row = payload[surface][0]
        assert row["days_per_10k_ft"] is None
        assert row["days_per_10k_tvd"] == 40
        assert row["excluded_bores_md"] == 1
        assert row["excluded_bores_tvd"] == 0


def test_rollups_use_matched_pairs_and_depth_weighting(builder):
    """MD: (10+90)/(10000+30000)*10000=25, not (10+30)/2=20.

    TVD: (10+90+40)/(10000+10000+10000)*10000=140/3.
    The third bore lacks MD; its days must also be excluded from MD totals.
    """
    write_bores(
        builder,
        {
            "API_WELL_NUMBER": "synthetic-00",
            "DRILLING_DAYS": "10",
            "MAX_BH_TOTAL_MD": "10000",
        },
        {
            "API_WELL_NUMBER": "synthetic-01",
            "DRILLING_DAYS": "90",
            "MAX_BH_TOTAL_MD": "30000",
        },
        {"API_WELL_NUMBER": "synthetic-02", "MAX_BH_TOTAL_MD": ""},
    )
    payload = builder.load_payload(intensity_denominator="md")
    for surface in ("fields", "blocks"):
        row = payload[surface][0]
        assert row["days_per_10k_ft"] == 25
        assert row["total_drilling_days_md"] == 100
        assert row["total_depth_ft_md"] == 40000
        assert row["excluded_bores_md"] == 1
        assert row["excluded_bores_tvd"] == 0
        assert row["days_per_10k_tvd"] == pytest.approx(140 / 3)
        assert row["intensity_status"] == "computed_partial"


def test_unlabelled_source_refuses_ratios(builder):
    """Days/depth alone cannot establish a measurement basis."""
    write_bores(builder, labelled=False)
    payload = builder.load_payload(intensity_denominator="md")
    for surface in ("bores", "fields", "blocks"):
        row = payload[surface][0]
        assert row["days_per_10k_ft"] is None
        assert row["intensity_status"] == "missing_basis"


def test_conflicting_basis_refuses_group_even_on_excluded_bore(builder):
    """An invalid depth must not hide conflicting provenance."""
    write_bores(builder, {}, {"BASIS": "another-rule", "MAX_BH_TOTAL_MD": ""})
    payload = builder.load_payload(intensity_denominator="md")
    for surface in ("fields", "blocks"):
        assert payload[surface][0]["days_per_10k_ft"] is None
        assert payload[surface][0]["intensity_status"] == "mixed_basis"


def test_completion_does_not_affect_intensity(builder):
    """40 / 20000 * 10000 = 20 regardless of completion duration."""
    write_bores(builder, {"COMPLETION_DAYS": "0"})
    before = builder.load_payload(intensity_denominator="md")
    write_bores(builder, {"COMPLETION_DAYS": "900"})
    after = builder.load_payload(intensity_denominator="md")
    for surface in ("bores", "fields", "blocks"):
        for key, value in before[surface][0].items():
            if "10k" in key or key.startswith("total_"):
                assert after[surface][0][key] == value


def test_invalid_denominator_is_rejected(builder):
    with pytest.raises(ValueError, match="denominator"):
        builder.load_payload(intensity_denominator="unknown")


def test_duplicate_bore_ids_are_refused(builder):
    """Bore sums require distinct members; duplicated identifiers cannot be counted."""
    write_bores(
        builder,
        {"API_WELL_NUMBER": "duplicate"},
        {"API_WELL_NUMBER": "duplicate"},
    )
    with pytest.raises(ValueError, match="unique bore"):
        builder.load_payload(intensity_denominator="md")


def test_rollup_groups_and_sorted_bores_keep_their_own_ratios(builder):
    """First input: 90/30000*10000=30; second: 10/10000*10000=10.

    Sorting the fields reverses the source order; neither bore may inherit
    its neighbour's ratio. Each field/block has only its own bore's ratio.
    """
    builder.SLUG["another-field"] = "another-field"
    builder.STATUS["another-field"] = ("synthetic", "ok")
    write_bores(
        builder,
        {"DRILLING_DAYS": "90", "MAX_BH_TOTAL_MD": "30000"},
        {
            "LEASE_NAME": "another-field",
            "SURF_LEASE_NUM": "another-block",
            "DRILLING_DAYS": "10",
            "MAX_BH_TOTAL_MD": "10000",
        },
    )
    payload = builder.load_payload(intensity_denominator="md")
    assert [b["days_per_10k_ft"] for b in payload["bores"]] == [10, 30]
    for surface in ("fields", "blocks"):
        assert [g["days_per_10k_ft"] for g in payload[surface]] == [10, 30]


def test_optional_html_contains_null_safe_ratios_and_metadata(builder):
    """40 / 20000 * 10000 = 20; absent days render a gap, not zero."""
    write_bores(builder, {}, {"DRILLING_DAYS": ""})
    payload = builder.load_payload(intensity_denominator="md")
    html = builder.build_html(payload)
    assert "Days/10K (MD)" in html
    assert "Days/10K (TVD)" in html
    assert "synthetic-rule" in html
    assert "computed_partial" in html
    assert "no_valid_pairs" in html
    assert "Included / excluded (MD)" in html
    assert "20.0" in html
    assert "—" in html
    raw = re.search(r"<script>const DATA=(\{.*\});\nconst \$=", html, re.DOTALL).group(
        1
    )
    assert json.loads(raw.replace("<\\/", "</"))["bores"][1]["days_per_10k_ft"] is None
    assert "Normalized drilling intensity" not in builder.build_html(
        builder.load_payload()
    )


def test_cli_opt_in_writes_only_selected_output(builder, monkeypatch, tmp_path):
    """CLI requires an explicit MD/TVD choice and an output destination."""
    write_bores(builder)
    output = tmp_path / "intensity.html"
    monkeypatch.setattr(builder, "OUT_HTML", tmp_path / "default.html")
    builder.main(["--intensity-denominator", "tvd", "--output", str(output)])
    assert "Days/10K (TVD)" in output.read_text(encoding="utf-8")
    assert not builder.OUT_HTML.exists()


def test_cli_intensity_requires_separate_output(builder):
    with pytest.raises(SystemExit) as exc:
        builder.main(["--intensity-denominator", "md"])
    assert exc.value.code != 0


def test_cli_preview_cannot_overwrite_default_page(builder, monkeypatch, tmp_path):
    output = tmp_path / "published.html"
    monkeypatch.setattr(builder, "OUT_HTML", output)
    with pytest.raises(SystemExit) as exc:
        builder.main(["--intensity-denominator", "md", "--output", str(output)])
    assert exc.value.code != 0
    assert not output.exists()


def test_html_escapes_supplied_basis(builder):
    """User-supplied basis is text, including a closing script-tag sequence."""
    write_bores(builder, {"BASIS": "synthetic</script><b>"})
    payload = builder.load_payload(intensity_denominator="md")
    table = builder.intensity_html(payload)
    assert "synthetic&lt;/script&gt;&lt;b&gt;" in table
    html = builder.build_html(payload)
    assert html.count("</script>") == 1
