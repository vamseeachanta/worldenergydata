"""Equipment failure taxonomy, table, case register and report section.

All inputs are synthetic. The rules under test never infer a cause: a
mechanism appears only from a source-coded field or a page-referenced case.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from worldenergydata.safety_analysis.equipment import (
    EQUIPMENT_CLASSES,
    FAILURE_MECHANISMS,
    FAILURE_MODES,
    SourceFile,
    build_section,
    build_table,
    classify_records,
    coverage,
    load_cases,
    query,
    render_markdown,
    summarise,
)
from worldenergydata.safety_analysis.equipment.__main__ import main
from worldenergydata.safety_analysis.equipment.cases import parse_case
from worldenergydata.safety_analysis.equipment.classify import (
    classify_bsee,
    classify_phmsa,
    phmsa_mechanism,
)
from worldenergydata.safety_analysis.equipment.table import read_csv, write_csv
from worldenergydata.safety_analysis.equipment.taxonomy import (
    BASIS_NONE,
    BASIS_SOURCE_CODED,
    NOT_STATED,
)

BSEE_ROWS = [
    (
        "1/2/2001",
        "10:00",
        "G00001",
        "XX 100",
        "- Pollution - Capsized - Mooring Failure ",
    ),
    (
        "3/4/2005",
        "11:00",
        "G00002",
        "XX 200",
        "- Pollution - Accidental Riser Disconnect",
    ),
    ("5/6/2010", "12:00", "G00003", "XX 300", "- Fatality - Crane - Dropped Object"),
    ("7/8/2015", "13:00", "G00004", "XX 400", "- Fire - Explosion "),
    ("9/10/2020", "14:00", "G00005", "XX 500", "- LTA (>3 days) "),
    ("11/12/2021", "15:00", "G00006", "XX 600", "- Blowout - wellhead failure"),
    ("1/3/2022", "16:00", "", "Not Applicable", "- lift boat damages pipeline"),
    ("2/3/2023", "17:00", "G00008", "XX 800", "- marine riser fatigue crack"),
]
BSEE_HEADER = (
    "DATE_OCCURRED",
    "MILITARY_TIME",
    "LEASE_NUMBER",
    "AREA_BLOCK",
    "ACCIDENT_TYPE",
)


def bsee(text: str, date: str = "1/2/2001") -> dict:
    return dict(zip(BSEE_HEADER, (date, "10:00", "G1", "XX 1", text)))


def phmsa(**over) -> dict:
    rec = {
        "Report Number": "20100001",
        "Accident Date/Time": "1/5/2010 7:30 AM",
        "Pipeline Location": "OFFSHORE",
        "Accident State": "",
        "Cause Category": "CORROSION",
        "Cause Subcategory": "EXTERNAL",
        "Liquid Ignition": "NO",
        "Liquid Explosion": "NO",
        "All Fatalities": "",
        "All Injuries": "",
    }
    rec.update(over)
    return rec


@pytest.fixture
def source_files(tmp_path):
    b = tmp_path / "mv_acc_investigations.txt"
    with open(b, "w", encoding="cp1252", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(BSEE_HEADER + ("PANEL_DISTRICT", "STATUS"))
        for row in BSEE_ROWS:
            w.writerow(row + ("DISTRICT", "Complete"))
    p = tmp_path / "phmsa.csv"
    records = [
        phmsa(),
        phmsa(
            **{
                "Report Number": "20100002",
                "Pipeline Location": "ONSHORE",
                "Accident State": "TX",
                "Cause Category": "INCORRECT OPERATION",
                "Cause Subcategory": "INCORRECT VALVE POSITION",
                "Liquid Ignition": "YES",
                "All Injuries": "2",
            }
        ),
    ]
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    return [
        SourceFile(
            "bsee_incident_investigations",
            b,
            "https://example.org/b.zip",
            "2026-01-31",
            title="Synthetic investigations",
        ),
        SourceFile(
            "phmsa_hazardous_liquid",
            p,
            "https://example.org/p.zip",
            "2026-01-31",
            title="Synthetic pipeline reports",
        ),
    ]


# --- classification ----------------------------------------------------------
def test_bsee_event_type_gives_class_and_modes_but_never_a_cause():
    (row,) = classify_bsee(bsee("- Pollution - Capsized - Mooring Failure "))
    assert row.equipment_class == "mooring_line"
    assert row.failure_modes == "loss_of_containment;loss_of_station;structural_damage"
    assert row.mechanism == NOT_STATED and row.mechanism_basis == BASIS_NONE
    assert row.pollution and not row.fatality
    assert row.source_record_id == "2001-01-02|10:00|G1|XX 1"


def test_bsee_does_not_infer_fatigue_from_event_text():
    (row,) = classify_bsee(bsee("- marine riser fatigue crack"))
    assert row.equipment_class == "riser"
    assert row.equipment_subclass == "drilling_riser"
    assert row.mechanism == NOT_STATED


@pytest.mark.parametrize(
    "text,expected",
    [
        ("- Fatality - Crane - Dropped Object", {"lifting_rigging"}),
        ("- Fire - Explosion ", {"fpso_topsides"}),
        ("- Blowout - wellhead failure", {"wellhead_conductor"}),
        ("- lift boat damages pipeline", {"jack_up", "pipeline"}),
        ("- Casing Jack", {"wellhead_conductor"}),
        ("- LTA (>3 days) ", set()),
        ("", set()),
    ],
)
def test_bsee_equipment_classes(text, expected):
    assert {r.equipment_class for r in classify_bsee(bsee(text))} == expected


def test_bsee_riser_subclass_only_when_named():
    assert classify_bsee(bsee("- Riser Disconnect"))[0].equipment_subclass == NOT_STATED
    assert classify_bsee(bsee("- SCR leak"))[0].equipment_subclass == "scr"
    assert (
        classify_bsee(bsee("- flexible riser leak"))[0].equipment_subclass == "flexible"
    )
    assert (
        classify_bsee(bsee("- Prod. Riser Disconnect"))[0].equipment_subclass
        == "production_riser"
    )


@pytest.mark.parametrize(
    "cause,detail,expected",
    [
        ("CORROSION", "EXTERNAL", "corrosion_external"),
        ("CORROSION", "INTERNAL", "corrosion_internal"),
        ("CORROSION FAILURE", "", "corrosion"),
        (
            "MATERIAL/WELD/EQUIP FAILURE",
            "ENVIRONMENTAL CRACKING-RELATED",
            "environmental_cracking",
        ),
        (
            "MATERIAL/WELD/EQUIP FAILURE",
            "CONSTRUCTION, INSTALLATION OR FABRICATION-RELATED",
            "installation_or_fabrication_error",
        ),
        (
            "MATERIAL/WELD/EQUIP FAILURE",
            "MANUFACTURING-RELATED",
            "manufacturing_defect",
        ),
        (
            "MATERIAL/WELD/EQUIP FAILURE",
            "PUMP OR PUMP-RELATED EQUIPMENT",
            "material_weld_or_equipment_failure",
        ),
        ("INCORRECT OPERATION", "OTHER", "incorrect_operation"),
        ("NATURAL FORCE DAMAGE", "EARTH MOVEMENT", "natural_force"),
        ("EXCAVATION DAMAGE", "", "outside_force"),
        ("OTHER OUTSIDE FORCE DAMAGE", "", "outside_force"),
        ("ALL OTHER CAUSES", "UNKNOWN", "unknown"),
        ("ALL OTHER CAUSES", "MISCELLANEOUS", "other"),
        ("", "", NOT_STATED),
    ],
)
def test_phmsa_mechanism_comes_from_the_coded_cause(cause, detail, expected):
    assert phmsa_mechanism(cause, detail) == expected
    assert expected in FAILURE_MECHANISMS


def test_phmsa_row_keeps_source_text_and_basis():
    (row,) = classify_phmsa(phmsa())
    assert (row.equipment_class, row.equipment_subclass) == ("pipeline", "offshore")
    assert row.mechanism == "corrosion_external"
    assert row.mechanism_basis == BASIS_SOURCE_CODED
    assert row.mechanism_source_text == "CORROSION / EXTERNAL"
    assert row.date == "2010-01-05" and row.failure_modes == "loss_of_containment"


def test_phmsa_agency_column_names_and_blank_cause():
    (row,) = classify_phmsa(
        {
            "REPORT_NUMBER": "1",
            "LOCAL_DATETIME": "2/3/2015 10:00",
            "ON_OFF_SHORE": "ONSHORE",
            "ONSHORE_STATE_ABBREVIATION": "LA",
            "IGNITE_IND": "YES",
            "FATAL": "1",
        }
    )
    assert row.mechanism == NOT_STATED and row.mechanism_basis == BASIS_NONE
    assert row.failure_modes == "fire;loss_of_containment"
    assert row.fatality and row.location == "LA"
    assert classify_phmsa({"REPORT_NUMBER": ""}) == []


def test_unknown_source_is_an_error():
    with pytest.raises(KeyError, match="unsupported source"):
        classify_records("made_up", [])


# --- table --------------------------------------------------------------------
def test_build_table_counts_and_provenance(source_files):
    rows, stats = build_table(source_files)
    by_class = {line["equipment_class"]: line for line in coverage(rows)}
    assert set(by_class) == set(EQUIPMENT_CLASSES)
    assert by_class["mooring_line"]["records"] == 1
    assert by_class["riser"]["records"] == 2
    assert by_class["pipeline"]["records"] == 3  # 2 PHMSA + 1 BSEE
    assert by_class["pipeline"]["mechanism_stated"] == 2
    assert by_class["lifting_rigging"]["records"] == 1
    b = stats[0]
    assert (b.records_read, b.records_classified) == (8, 7)  # the LTA row has no class
    assert (b.first_date, b.last_date) == ("2001-01-02", "2023-02-03")
    assert all(
        r.source_url.startswith("https://") and r.retrieved == "2026-01-31"
        for r in rows
    )


def test_summary_counts_a_record_under_each_mode(source_files):
    rows, _ = build_table(source_files)
    s = summarise(query(rows, "mooring_line"))
    assert s["records"] == 1 and s["mechanism_stated"] == 0
    assert {m["key"] for m in s["by_failure_mode"]} == {
        "loss_of_containment",
        "loss_of_station",
        "structural_damage",
    }
    assert all(m["key"] in FAILURE_MODES for m in s["by_failure_mode"])
    assert s["by_decade"] == {"2000s": 1}
    with pytest.raises(KeyError):
        query(rows, "umbilical")


def test_csv_round_trip(source_files, tmp_path):
    rows, _ = build_table(source_files)
    path = tmp_path / "t.csv"
    write_csv(rows, path)
    assert read_csv(path) == rows


def test_source_file_needs_https_and_iso_date(tmp_path):
    with pytest.raises(ValueError, match="https"):
        SourceFile("x", tmp_path, "http://example.org", "2026-01-31")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        SourceFile("x", tmp_path, "https://example.org", "31 Jan 2026")


# --- case register --------------------------------------------------------------
CASE = {
    "id": "mooring-synthetic-1",
    "equipment_class": "mooring_line",
    "date": "2001-01-02",
    "location": "Block XX 100",
    "area_block": "XX 100",
    "facility_type": "Spar",
    "authority": "Synthetic regulator",
    "title": "Investigation report",
    "report_ref": "report 1",
    "url": "https://example.org/report.pdf",
    "retrieved": "2026-01-31",
    "what_failed": {"statement": "A chain link parted", "page": 2},
    "failure_modes": ["loss_of_station"],
    "mechanism": "fatigue",
    "cause_statements": [
        {"statement": "The link most likely failed by fatigue", "page": 3}
    ],
    "lessons": [{"statement": "Inspect the top chain", "page": 4}],
}


def test_packaged_register_is_valid_and_names_no_mechanism_without_a_cause():
    cases = load_cases()
    assert len(cases) >= 3
    for case in cases:
        assert case.url.startswith("https://")
        assert case.mechanism == NOT_STATED or case.cause_statements


@pytest.mark.parametrize(
    "change,match",
    [
        ({"mechanism": "fatigue", "cause_statements": []}, "page-referenced cause"),
        ({"mechanism": "wear"}, "unknown mechanism"),
        ({"equipment_class": "umbilical"}, "unknown equipment class"),
        ({"failure_modes": []}, "failure_modes"),
        ({"url": "http://example.org/r.pdf"}, "https"),
        ({"date": "2 Jan 2001"}, "YYYY-MM-DD"),
        ({"operator": "named"}, "unknown keys"),
        (
            {"what_failed": {"statement": 'It said "parted"', "page": 2}},
            "paraphrase only",
        ),
        ({"what_failed": {"statement": "x " * 61, "page": 2}}, "over 60 words"),
        (
            {"what_failed": {"statement": "A link parted", "page": 0}},
            "positive integer",
        ),
    ],
)
def test_case_validation(change, match):
    with pytest.raises(ValueError, match=match):
        parse_case({**CASE, **change})


def test_case_without_a_stated_cause_is_allowed():
    case = parse_case({**CASE, "mechanism": NOT_STATED, "cause_statements": []})
    assert case.mechanism == NOT_STATED


# --- report section ---------------------------------------------------------------
def test_section_cites_every_number_and_flags_open_lessons(source_files):
    rows, stats = build_table(source_files)
    cases = [
        parse_case(CASE),
        parse_case(
            {
                **CASE,
                "id": "mooring-synthetic-2",
                "date": "2019-05-05",
                "area_block": "XX 900",
            }
        ),
    ]
    section = build_section("mooring_line", rows, stats, cases)
    assert section.open_items == [
        "lesson mooring-synthetic-1#1 has no design response",
        "lesson mooring-synthetic-2#1 has no design response",
    ]
    text = render_markdown(section)
    for heading in (
        "F.1 Data used",
        "F.2 Incident history",
        "F.3 Failure modes and stated causes",
        "F.4 Illustrative public cases",
        "F.5 Lessons for this design",
        "F.6 References for this appendix",
    ):
        assert f"### {heading}" in text
    assert "https://example.org/b.zip (read 2026-01-31)" in text
    assert "https://example.org/report.pdf (read 2026-01-31)" in text
    assert "None of the 1 records states a cause" in text
    assert "The count is a lower bound: 1 of the 2 cases" in text
    assert "(p. 3)" in text and "not yet assigned" in text
    assert "Synthetic pipeline reports" not in text  # unused source is not cited


def test_section_with_design_links_has_no_open_items(source_files):
    rows, stats = build_table(source_files)
    cases = [parse_case(CASE), parse_case({**CASE, "id": "mooring-synthetic-2"})]
    links = {
        "mooring-synthetic-1#1": "Section 6.3",
        "mooring-synthetic-2#1": "Section 3.3",
    }
    section = build_section("mooring_line", rows, stats, cases, design_links=links)
    assert section.open_items == []
    assert "Section 6.3" in render_markdown(section)


def test_section_for_coded_causes_prints_the_cause_table(source_files):
    rows, stats = build_table(source_files)
    section = build_section("pipeline", rows, stats, [])
    text = render_markdown(section)
    assert "Cause as coded by the source" in text and "External corrosion" in text
    assert "fewer than two illustrative public cases on file" in section.open_items


def test_cli_build_and_section(source_files, tmp_path, capsys):
    listing = tmp_path / "sources.json"
    listing.write_text(
        json.dumps(
            [
                {
                    "source_id": s.source_id,
                    "path": s.path.name,
                    "url": s.url,
                    "retrieved": s.retrieved,
                    "title": s.title,
                }
                for s in source_files
            ]
        )
    )
    assert (
        main(["build", "--sources", str(listing), "--out-dir", str(tmp_path / "out")])
        == 0
    )
    summary = json.loads(
        (tmp_path / "out" / "equipment-failure-summary.json").read_text()
    )
    assert summary["by_class"]["riser"]["records"] == 2
    out = tmp_path / "out" / "section.md"
    rc = main(
        [
            "section",
            "--sources",
            str(listing),
            "--equipment-class",
            "mooring_line",
            "--out",
            str(out),
        ]
    )
    assert rc == 1 and out.exists()  # packaged cases have lessons without design links
    assert (
        main(
            [
                "section",
                "--sources",
                str(listing),
                "--equipment-class",
                "mooring_line",
                "--out",
                str(out),
                "--allow-open",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "build",
                "--sources",
                str(tmp_path / "missing.json"),
                "--out-dir",
                str(tmp_path),
            ]
        )
        == 2
    )


# --- review findings (regressions) -------------------------------------------------
REPO = Path(__file__).resolve().parents[4]
PHMSA_EXPORT = (
    REPO / "data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv"
)


def test_unknown_coded_cause_is_kept_but_not_counted_as_stated():
    (row,) = classify_phmsa(
        phmsa(**{"Cause Category": "ALL OTHER CAUSES", "Cause Subcategory": "UNKNOWN"})
    )
    assert row.mechanism == "unknown"
    assert row.mechanism_source_text == "ALL OTHER CAUSES / UNKNOWN"
    s = summarise([row])
    assert s["mechanism_stated"] == 0
    assert s["by_mechanism"] == [
        {
            "key": "unknown",
            "label": "Cause coded as unknown by the source",
            "records": 1,
        }
    ]


def test_committed_pipeline_export_has_exact_stated_cause_count():
    source = SourceFile(
        "phmsa_hazardous_liquid", PHMSA_EXPORT, "https://example.org/p", "2026-05-05"
    )
    rows, stats = build_table([source])
    s = summarise(query(rows, "pipeline"))
    unknown = sum(1 for r in rows if r.mechanism == "unknown")
    assert (stats[0].records_read, unknown, s["mechanism_stated"]) == (2795, 42, 2753)


@pytest.mark.parametrize("response", ["", "   ", None, 7, "not yet assigned"])
def test_blank_design_response_keeps_the_lesson_open(source_files, response):
    rows, stats = build_table(source_files)
    cases = [parse_case(CASE), parse_case({**CASE, "id": "mooring-synthetic-2"})]
    links = {
        "mooring-synthetic-1#1": response,
        "mooring-synthetic-2#1": " Section 3.3 ",
    }
    section = build_section("mooring_line", rows, stats, cases, design_links=links)
    assert section.open_items == ["lesson mooring-synthetic-1#1 has no design response"]
    assert section.lessons[0]["addressed_in"] == "not yet assigned"
    assert section.lessons[1]["addressed_in"] == "Section 3.3"


def test_repeated_or_unknown_case_ids_are_refused(source_files):
    rows, stats = build_table(source_files)
    cases = [parse_case(CASE), parse_case({**CASE, "id": "mooring-synthetic-2"})]
    with pytest.raises(ValueError, match="distinct"):
        build_section(
            "mooring_line",
            rows,
            stats,
            cases,
            case_ids=["mooring-synthetic-1", "mooring-synthetic-1"],
        )
    with pytest.raises(ValueError, match="no case"):
        build_section("mooring_line", rows, stats, cases, case_ids=["missing"])
    one = build_section(
        "mooring_line", rows, stats, cases, case_ids=["mooring-synthetic-1"]
    )
    assert "fewer than two illustrative public cases on file" in one.open_items


def test_case_membership_uses_date_and_area_block(source_files):
    rows, stats = build_table(source_files)
    same_day_elsewhere = parse_case({**CASE, "id": "c2", "area_block": "YY 9"})
    no_block = parse_case(
        {k: v for k, v in {**CASE, "id": "c3"}.items() if k != "area_block"}
    )
    text = render_markdown(
        build_section(
            "mooring_line",
            rows,
            stats,
            [parse_case(CASE), same_day_elsewhere, no_block],
        )
    )
    assert "The count is a lower bound: 1 of the 3 cases" in text
    assert "For 1 of the 3 cases the area block is not on file" in text
    matched = render_markdown(
        build_section(
            "mooring_line",
            rows,
            stats,
            [
                parse_case(CASE),
                parse_case({**CASE, "id": "c4", "area_block": "xx-100"}),
            ],
        )
    )
    assert "lower bound" not in matched and "not verified" not in matched


@pytest.mark.parametrize(
    "value", ["XXXXXXXXXX", "2026-02-30", "2026-1-31 ", "20260131", ""]
)
def test_retrieval_date_must_be_a_real_calendar_date(tmp_path, value):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        SourceFile("x", tmp_path, "https://example.org", value)


def test_ruled_out_factor_is_never_printed_as_a_cause(source_files):
    rows, stats = build_table(source_files)
    case = parse_case(
        {
            **CASE,
            "ruled_out": [
                {
                    "statement": "Direct collision, for which there was no evidence",
                    "page": 4,
                }
            ],
        }
    )
    other = parse_case({**CASE, "id": "mooring-synthetic-2"})
    text = render_markdown(build_section("mooring_line", rows, stats, [case, other]))
    assert (
        "- Ruled out or found unlikely by the investigation: "
        "Direct collision, for which there was no evidence (p. 4);" in text
    )
    assert "Cause stated by the investigation: Direct collision" not in text


def test_packaged_cases_keep_ruled_out_factors_apart():
    by_id = {c.id: c for c in load_cases()}
    tlp = by_id["mooring-2005-gc237-tendon-connector"]
    assert len(tlp.ruled_out) == 1 and "1000-year" in tlp.ruled_out[0].statement
    assert all("1000-year" not in c.statement for c in tlp.cause_statements)


# --- second review round -----------------------------------------------------------
AGENCY_HEADER = (
    "REPORT_NUMBER",
    "SUPPLEMENTAL_NUMBER",
    "LOCAL_DATETIME",
    "ON_OFF_SHORE",
    "ONSHORE_STATE_ABBREVIATION",
    "IGNITE_IND",
    "EXPLODE_IND",
    "FATAL",
    "INJURE",
    "CAUSE",
    "CAUSE_DETAILS",
)


def _agency_file(path, rows, delimiter="\t"):
    lines = [delimiter.join(AGENCY_HEADER)] + [delimiter.join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return SourceFile(
        "phmsa_hazardous_liquid", path, "https://example.org/hl.zip", "2026-01-31"
    )


def test_tab_separated_agency_layout_is_read_and_classified(tmp_path):
    source = _agency_file(
        tmp_path / "hl.txt",
        [
            (
                "20200001",
                "0",
                "3/4/2020 10:15",
                "OFFSHORE",
                "",
                "NO",
                "NO",
                "0",
                "0",
                "CORROSION FAILURE",
                "INTERNAL CORROSION",
            ),
            (
                "20200002",
                "0",
                "5/6/2021 08:00",
                "ONSHORE",
                "TX",
                "YES",
                "NO",
                "0",
                "1",
                "INCORRECT OPERATION",
                "VALVE LEFT OR PLACED IN WRONG POSITION",
            ),
        ],
    )
    rows, stats = build_table([source])
    assert (stats[0].records_read, stats[0].records_classified) == (2, 2)
    assert [r.mechanism for r in rows] == ["corrosion_internal", "incorrect_operation"]
    assert rows[0].equipment_subclass == "offshore" and rows[1].injury
    assert (stats[0].first_date, stats[0].last_date) == ("2020-03-04", "2021-05-06")


def test_file_without_the_required_columns_is_an_error_not_zero_records(tmp_path):
    bad = tmp_path / "hl.txt"
    bad.write_text("ID;WHEN\n1;2020\n", encoding="utf-8")
    source = SourceFile(
        "phmsa_hazardous_liquid", bad, "https://example.org/hl.zip", "2026-01-31"
    )
    with pytest.raises(ValueError, match="lacks required column"):
        build_table([source])
    b = tmp_path / "inv.txt"
    b.write_text("DATE_OCCURRED,AREA_BLOCK\n1/2/2001,XX 1\n", encoding="cp1252")
    with pytest.raises(ValueError, match="ACCIDENT_TYPE"):
        build_table(
            [
                SourceFile(
                    "bsee_incident_investigations",
                    b,
                    "https://example.org/b",
                    "2026-01-31",
                )
            ]
        )


def test_two_files_of_one_source_are_refused(tmp_path):
    one = _agency_file(tmp_path / "a.txt", [])
    two = _agency_file(tmp_path / "b.txt", [])
    with pytest.raises(ValueError, match="one file per source"):
        build_table([one, two])


def test_unknown_coded_cause_is_printed_as_unknown_not_as_event_type_only(tmp_path):
    source = _agency_file(
        tmp_path / "hl.txt",
        [
            (
                "20200003",
                "0",
                "7/8/2022 09:00",
                "ONSHORE",
                "LA",
                "NO",
                "NO",
                "0",
                "0",
                "OTHER INCIDENT CAUSE",
                "UNKNOWN",
            )
        ],
    )
    rows, stats = build_table([source])
    text = render_markdown(build_section("pipeline", rows, stats, []))
    assert "| Cause coded as unknown by the source | 1 |" in text
    assert (
        "The source codes a cause for 1 of the 1 records; it codes 1 of those as unknown."
        in text
    )
    assert "event type only" not in text


def test_coded_and_uncoded_records_are_explained_separately(source_files):
    rows, stats = build_table(source_files)
    s = summarise(query(rows, "pipeline"))
    assert (s["cause_coded"], s["cause_coded_unknown"], s["cause_not_coded"]) == (
        2,
        0,
        1,
    )
    text = render_markdown(build_section("pipeline", rows, stats, []))
    assert (
        "The source codes a cause for 2 of the 3 records; it codes 0 of those as unknown."
        in text
    )
    assert "Records from a data set that gives the event type only: 1." in text
    assert "blank cause field" not in text


def test_reference_names_no_company_and_carries_the_digest():
    for case in load_cases():
        ref = case.reference().lower()
        for word in ("exxon", "equinor", "shell"):
            assert word not in ref, case.id
        assert case.sha256 and case.sha256 in case.reference()
        assert "Available from https://www.bsee.gov/" in case.reference()


def test_bad_digest_is_refused():
    with pytest.raises(ValueError, match="sha256"):
        parse_case({**CASE, "sha256": "abc123"})


def test_no_data_appendix_states_what_is_not_established(source_files):
    rows, stats = build_table(source_files[:1])
    rows = [r for r in rows if r.equipment_class != "jack_up"]
    section = build_section(
        "jack_up",
        rows,
        stats,
        [],
        missing_data="investigation reports for\n jack-up legs (issue 1932).",
    )
    assert section.open_items == [
        "no records for this equipment class in the table",
        "fewer than two illustrative public cases on file",
    ]
    text = render_markdown(section)
    assert (
        "| Synthetic investigations | 8 | 0 | 2001-01-02 to 2023-02-03 | 2026-01-31 | [H1] |"
        in text
    )
    assert "The data sets read hold no record for this equipment." in text
    assert "Missing data: investigation reports for jack-up legs (issue 1932)." in text
    assert (
        "Not established: the data sets read hold no record for this equipment." in text
    )
    assert (
        "Not established: fewer than two investigated public cases are on file" in text
    )
    assert "### F.5 Lessons for this design\n\nNot established.\n" in text
    assert (
        "- [H1] Synthetic investigations. https://example.org/b.zip (read 2026-01-31)."
        in text
    )
    assert "None of the 0 records" not in text and "Failure mode | Records" not in text


def test_one_case_on_file_is_shown_and_marked_not_established(source_files):
    rows, stats = build_table(source_files)
    section = build_section(
        "mooring_line",
        rows,
        stats,
        [parse_case(CASE)],
        design_links={"mooring-synthetic-1#1": "Section 6.3"},
    )
    assert section.open_items == ["fewer than two illustrative public cases on file"]
    text = render_markdown(section)
    assert "**Case 1: Spar" in text
    assert (
        "Not established: fewer than two investigated public cases are on file" in text
    )


@pytest.mark.parametrize("prefix", ["\ufeff", "  ", "\ufeff "])
def test_header_with_byte_order_mark_or_spaces_is_still_classified(tmp_path, prefix):
    path = tmp_path / "phmsa.csv"
    record = phmsa()
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(prefix)
        w = csv.DictWriter(fh, fieldnames=list(record))
        w.writeheader()
        w.writerow(record)
    source = SourceFile(
        "phmsa_hazardous_liquid", path, "https://example.org/p.zip", "2026-01-31"
    )
    rows, stats = build_table([source])
    assert (stats[0].records_read, len(rows)) == (1, 1)
    assert rows[0].source_record_id == "20100001"
    assert rows[0].mechanism == "corrosion_external"


def _pipeline_file(tmp_path, records):
    path = tmp_path / "phmsa_blank.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    return SourceFile(
        "phmsa_hazardous_liquid", path, "https://example.org/p.zip", "2026-01-31"
    )


BLANK_CAUSE = {"Cause Category": "", "Cause Subcategory": ""}


def test_all_blank_cause_fields_are_not_explained_as_event_type_only(tmp_path):
    source = _pipeline_file(tmp_path, [phmsa(**BLANK_CAUSE)])
    rows, stats = build_table([source])
    s = summarise(query(rows, "pipeline"))
    assert (s["cause_coded"], s["cause_not_coded"], s["cause_field_blank"]) == (0, 1, 1)
    text = render_markdown(build_section("pipeline", rows, stats, []))
    assert "None of the 1 records states a cause." in text
    assert "Records with a blank cause field: 1." in text
    assert "event type only" not in text


def test_blank_coded_and_event_only_records_are_counted_apart(source_files, tmp_path):
    blank = phmsa(**{"Report Number": "20100009"}, **BLANK_CAUSE)
    mixed = _pipeline_file(tmp_path, [phmsa(), blank])
    rows, stats = build_table([source_files[0], mixed])
    s = summarise(query(rows, "pipeline"))
    assert (s["cause_coded"], s["cause_not_coded"], s["cause_field_blank"]) == (1, 2, 1)
    text = render_markdown(build_section("pipeline", rows, stats, []))
    assert "The source codes a cause for 1 of the 3 records" in text
    assert "Records with a blank cause field: 1." in text
    assert "Records from a data set that gives the event type only: 1." in text


@pytest.mark.parametrize("delimiter", [",", "\t"])
def test_quoted_header_after_a_byte_order_mark_is_read(tmp_path, delimiter):
    path = tmp_path / "phmsa_quoted.csv"
    record = phmsa()
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\ufeff")
        w = csv.DictWriter(
            fh, fieldnames=list(record), quoting=csv.QUOTE_ALL, delimiter=delimiter
        )
        w.writeheader()
        w.writerow(record)
    assert path.read_bytes().startswith(b'\xef\xbb\xbf"Report Number"')
    source = SourceFile(
        "phmsa_hazardous_liquid", path, "https://example.org/p.zip", "2026-01-31"
    )
    rows, stats = build_table([source])
    assert (stats[0].records_read, len(rows)) == (1, 1)
    assert rows[0].source_record_id == "20100001"
    assert rows[0].mechanism == "corrosion_external"
