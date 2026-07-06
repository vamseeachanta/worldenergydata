# ABOUTME: TDD suite for the phase-norm layer (issue #848) — stage metrics vs
# ABOUTME: leave-one-field-out play baselines with honest degradation states.

import json

import openpyxl
import pytest

from worldenergydata.field_development import phase_norms as pn

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

CFG = {
    "min_n": 4,  # small values so fixtures stay tiny; prod values live in YAML
    "field_min_n": 2,
    "low_n_threshold": 4,
    "max_days": 1000,
    "join_coverage_min": 0.9,
    "lease_name_to_field": {
        "Alpha": "alpha",
        "Beta": "beta",
        "Gamma North": "gamma",
        "Gamma South": "gamma",
    },
    "benchmark_field_to_field": {
        "Alpha": "alpha",
        "Beta": "beta",
        "Gamma": "gamma",
    },
    "field_ids": ["alpha", "beta", "gamma"],
    "abandon": {"pa_codes": ["PA", "TA"]},
    "chip_metrics": {
        "drill": "drill_days_median",
        "complete": "completion_days_median",
        "produce": "uptime_median",
        "workover": "interventions_per_well",
        "abandon": "pa_share",
    },
}

XLSX_ROWS = [
    # LEASE_NAME, API_WELL_NUMBER, DRILLING_DAYS, COMPLETION_DAYS, MAX_WELL_BORE_TVD
    ("Alpha", "608100000001.0", 10, 20, 10000),
    ("Alpha", "608100000002.0", 20, 30, 20000),
    ("Beta", "608100000003.0", 30, 40, 15000),
    ("Beta", "608100000004.0", 40, 50, 15000),
    ("Gamma North", "608100000005.0", 50, 60, 15000),
    ("Gamma South", "608100000006.0", 60, 70, 15000),
    # censor targets:
    ("Alpha", "608100000007.0", -5, 10, 15000),  # non-positive drill days
    ("Beta", "608100000008.0", 2000, 10, 15000),  # over max_days
    ("Unknown Lease", "608100000009.0", 10, 10, 15000),  # unmapped lease
    (None, None, 99999, None, None),  # blank/TOTALS trailer analogue
]


@pytest.fixture()
def xlsx_path(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(
        [
            "LEASE_NAME",
            "API_WELL_NUMBER",
            "DRILLING_DAYS",
            "COMPLETION_DAYS",
            "MAX_WELL_BORE_TVD",
        ]
    )
    for row in XLSX_ROWS:
        ws.append(row)
    p = tmp_path / "dc.xlsx"
    wb.save(p)
    return p


BENCH_ROWS = [
    {
        "api12": "608100000001",
        "field": "Alpha",
        "uptime_pct": "90.0",
        "decline_annual_pct": "10.0",
        "cum_oil_mmbbl": "10.0",
        "interventions": "1",
    },
    {
        "api12": "608100000002",
        "field": "Alpha",
        "uptime_pct": "92.0",
        "decline_annual_pct": "12.0",
        "cum_oil_mmbbl": "20.0",
        "interventions": "0",
    },
    {
        "api12": "608100000003",
        "field": "Beta",
        "uptime_pct": "94.0",
        "decline_annual_pct": "14.0",
        "cum_oil_mmbbl": "30.0",
        "interventions": "2",
    },
    {
        "api12": "608100000004",
        "field": "Beta",
        "uptime_pct": "96.0",
        "decline_annual_pct": "16.0",
        "cum_oil_mmbbl": "40.0",
        "interventions": "1",
    },
    {
        "api12": "608100000005",
        "field": "Gamma",
        "uptime_pct": "98.0",
        "decline_annual_pct": "18.0",
        "cum_oil_mmbbl": "50.0",
        "interventions": "3",
    },
    {
        "api12": "608100000006",
        "field": "Gamma",
        "uptime_pct": "88.0",
        "decline_annual_pct": "20.0",
        "cum_oil_mmbbl": "60.0",
        "interventions": "0",
    },
]


@pytest.fixture()
def bench_csv(tmp_path):
    p = tmp_path / "bench.csv"
    cols = list(BENCH_ROWS[0].keys())
    lines = [",".join(cols)]
    lines += [",".join(r[c] for c in cols) for r in BENCH_ROWS]
    p.write_text("\n".join(lines) + "\n")
    return p


# ---------------------------------------------------------------------------
# 1 — loader drops blank/TOTALS rows and censors durations, with counts
# ---------------------------------------------------------------------------


def test_lt_loader_drops_blank_and_totals_rows_and_censors(xlsx_path):
    rows, exclusions = pn.load_lt_population(xlsx_path, CFG)
    apis = {r["api"] for r in rows}
    assert "608100000009" not in apis  # unmapped lease excluded
    # 6 clean wells + 2 rows whose drill value was censored to None but whose
    # completion value stays usable (censoring is per-metric, not per-row)
    assert len(rows) == 8
    censored = {r["api"]: r for r in rows}
    assert censored["608100000007"]["drill_days"] is None
    assert censored["608100000007"]["compl_days"] == 10
    assert censored["608100000008"]["drill_days"] is None
    assert exclusions["blank_or_totals"] == 1
    assert exclusions["unmapped_lease"] == 1
    assert exclusions["drill_nonpositive"] == 1
    assert exclusions["drill_over_max"] == 1


# 2 — api normalization (float-string suffix + zero padding)


def test_normalize_api_float_suffix_and_padding():
    assert pn.normalize_api("608100000001.0") == "608100000001"
    assert pn.normalize_api("608100000001") == "608100000001"
    assert pn.normalize_api("8100000001") == "008100000001"
    assert pn.normalize_api(None) is None


# 3 — benchmark↔xlsx consistency gate


def test_join_coverage_gate_fails_below_threshold(xlsx_path, bench_csv):
    lt_rows, _ = pn.load_lt_population(xlsx_path, CFG)
    bench = pn.load_benchmark(bench_csv, CFG)
    cov = pn.benchmark_consistency(bench, lt_rows)
    assert cov == 1.0
    bad_cfg = dict(CFG, join_coverage_min=1.01)
    with pytest.raises(pn.JoinCoverageError):
        pn.assert_join_coverage(cov, bad_cfg)


# 4 — leave-one-field-out baseline excludes the field itself


def test_leave_one_field_out_baseline_excludes_self(xlsx_path):
    rows, _ = pn.load_lt_population(xlsx_path, CFG)
    # drill_days pool: alpha[10,20] beta[30,40] gamma[50,60]
    base = pn.loo_baseline(rows, "alpha", "drill_days", CFG)
    assert base.status == "ok"
    assert base.metric.value == 45  # median of [30,40,50,60]
    assert base.metric.n == 4
    assert base.method == "leave_one_field_out"


# 5 — field-side low-n flag and insufficient states


def test_field_side_low_n_flag_and_insufficient(xlsx_path):
    rows, _ = pn.load_lt_population(xlsx_path, CFG)
    entries = pn.compute_norms(rows, [], CFG)
    drill = {e.field_id: e for e in entries if e.metric_id == "drill_days_median"}
    assert drill["alpha"].field_status == "low_n"  # n=2 < low_n_threshold=4
    assert drill["alpha"].field.n == 2
    solo_cfg = dict(CFG, field_min_n=3)
    entries2 = pn.compute_norms(rows, [], solo_cfg)
    drill2 = {e.field_id: e for e in entries2 if e.metric_id == "drill_days_median"}
    assert drill2["alpha"].field_status == "insufficient"
    assert drill2["alpha"].field is None


# 6 — roadmap/unavailable comparators never carry numbers


def test_unavailable_and_roadmap_never_carry_numbers(xlsx_path):
    rows, _ = pn.load_lt_population(xlsx_path, CFG)
    entries = pn.compute_norms(rows, [], CFG)
    for e in entries:
        if e.country.status in ("roadmap", "unavailable"):
            assert e.country.metric is None
            assert e.delta_country_pct is None
            assert e.country.reason
        if e.stage == "abandon":
            assert e.field is None and e.field_status == "unavailable"
            assert e.play.status == "unavailable"


# 7 — deltas only within same basis AND population


def test_delta_requires_same_basis_and_population():
    a = pn.MetricValue(50, 10, "calendar_days", "xlsx_wellbores", "median")
    b = pn.MetricValue(40, 10, "calendar_days", "xlsx_wellbores", "median")
    assert pn.delta_pct(a, b) == 25.0
    c = pn.MetricValue(40, 10, "rig_days", "xlsx_wellbores", "median")
    with pytest.raises(pn.BasisMismatchError):
        pn.delta_pct(a, c)
    d = pn.MetricValue(40, 10, "calendar_days", "benchmark_wells", "median")
    with pytest.raises(pn.BasisMismatchError):
        pn.delta_pct(a, d)


# 8 — schema completeness + deterministic serialization


def test_norms_json_schema_complete_and_deterministic(xlsx_path, bench_csv, tmp_path):
    rows, exclusions = pn.load_lt_population(xlsx_path, CFG)
    bench = pn.load_benchmark(bench_csv, CFG)
    entries = pn.compute_norms(rows, bench, CFG)
    prov = pn.build_provenance(
        sources=[{"path": str(xlsx_path), "rows_total": 10, "rows_used": 6}],
        exclusions=exclusions,
        join_coverage=1.0,
    )
    out1 = tmp_path / "a.json"
    out2 = tmp_path / "b.json"
    pn.write_norms_json(entries, prov, out1)
    pn.write_norms_json(entries, prov, out2)
    assert out1.read_text() == out2.read_text()  # deterministic
    doc = json.loads(out1.read_text())
    assert doc["schema_version"] == pn.SCHEMA_VERSION
    assert doc["provenance"]["join_coverage"] == 1.0
    got = {(e["field_id"], e["stage"], e["metric_id"]) for e in doc["entries"]}
    for fid in CFG["field_ids"]:
        for stage in ("drill", "complete", "produce", "workover", "abandon"):
            assert any(k[0] == fid and k[1] == stage for k in got)
    for e in doc["entries"]:
        assert {"field_id", "stage", "metric_id", "unit", "field_status"} <= set(e)


# 9 — golden reconciliation contract (against the published drilling-insights
#     figure; uses the REAL repo workbook)


def test_golden_reconciliation_against_drilling_insights():
    cfg = pn.load_config(pn.DEFAULT_CONFIG_PATH)
    rows, _ = pn.load_lt_population(pn.repo_root() / cfg["sources"]["lt_dc_xlsx"], cfg)
    drill = [r["drill_days"] for r in rows if r["drill_days"] is not None]
    med = pn.median(drill)
    assert len(drill) == cfg["golden"]["drill_population_n"]
    assert med == pytest.approx(cfg["golden"]["drill_play_median_days"], abs=0.05)


# 10 — lease-name split mapping (Cascade/Chinook, Jack/St Malo analogue)


def test_lease_name_field_split_mapping(xlsx_path):
    rows, _ = pn.load_lt_population(xlsx_path, CFG)
    gamma = [r for r in rows if r["field_id"] == "gamma"]
    assert len(gamma) == 2  # Gamma North + Gamma South merged


# 11 — chips payload for the poster generator (incl. degraded states)


def test_chips_payload_states(xlsx_path, bench_csv):
    rows, _ = pn.load_lt_population(xlsx_path, CFG)
    bench = pn.load_benchmark(bench_csv, CFG)
    # gamma has no benchmark rows in this variant → produce/workover no-data
    bench_no_gamma = [b for b in bench if b["field_id"] != "gamma"]
    entries = pn.compute_norms(rows, bench_no_gamma, CFG)
    chips = pn.chips_for_field(entries, "gamma", CFG)
    assert [c["stage"] for c in chips] == [
        "drill",
        "complete",
        "produce",
        "workover",
        "abandon",
    ]
    produce = next(c for c in chips if c["stage"] == "produce")
    assert produce["state"] == "no_data"
    drill = next(c for c in chips if c["stage"] == "drill")
    assert drill["state"] in ("ok", "low_n")
    assert drill["href"] == "norms/drill.html#gamma"


# 12 — abandon context share from status codes


def test_abandon_context_share_from_status_codes(tmp_path):
    p = tmp_path / "well_data.csv"
    p.write_text(
        "API_WELL_NUMBER,BOREHOLE_STAT_CD\n" "1,PA\n2,TA\n3,COM\n4,ST\n5,PA\n6,\n"
    )
    ctx = pn.compute_abandon_context(p, CFG)
    assert ctx["n"] == 5  # blank status excluded
    assert ctx["share_pct"] == pytest.approx(60.0)  # 3 of 5
    assert "vintage" in ctx["caveat"].lower()
