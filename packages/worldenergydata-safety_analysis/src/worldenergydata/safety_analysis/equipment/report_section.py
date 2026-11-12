# ABOUTME: Fill the HSE and safety report appendix for one equipment class from the table.
# ABOUTME: Every number carries its source and retrieval date; causes are those the sources state.

"""HSE and safety report section.

``build_section`` assembles, for the equipment class of the report in hand:

1. the data used (source, records, period, retrieval date);
2. the incident history and the counts by failure mode and by stated cause;
3. two or three illustrative public cases, each cited to its investigation;
4. the lessons those investigations state, each tied to the part of the report
   that answers it.

``render_markdown`` prints it under the fixed subsection headings. The section
states only what the sources state. Where a data set gives no cause, the text
says so; it never supplies one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from worldenergydata.safety_analysis.equipment.cases import PublicCase, cases_for
from worldenergydata.safety_analysis.equipment.classify import EquipmentFailureRow
from worldenergydata.safety_analysis.equipment.table import (
    SourceStats,
    query,
    summarise,
)
from worldenergydata.safety_analysis.equipment.taxonomy import (
    EQUIPMENT_CLASSES,
    FAILURE_MECHANISMS,
    FAILURE_MODES,
    NOT_STATED,
)

MAX_CASES = 3
UNASSIGNED = "not yet assigned"


@dataclass
class HseSection:
    equipment_class: str
    equipment_label: str
    letter: str
    summary: dict
    sources: list[SourceStats]
    records: list[EquipmentFailureRow]
    cases: list[PublicCase]
    lessons: list[dict]
    references: list[str]
    open_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "equipment_class": self.equipment_class,
            "equipment_label": self.equipment_label,
            "summary": self.summary,
            "sources": [s.as_record() for s in self.sources],
            "records": [r.as_record() for r in self.records],
            "cases": [c.id for c in self.cases],
            "lessons": self.lessons,
            "references": self.references,
            "open_items": self.open_items,
        }


def build_section(
    equipment_class: str,
    rows: Sequence[EquipmentFailureRow],
    stats: Sequence[SourceStats],
    cases: Sequence[PublicCase],
    *,
    design_links: Optional[Mapping[str, str]] = None,
    case_ids: Optional[Sequence[str]] = None,
    letter: str = "F",
) -> HseSection:
    """Assemble the section for ``equipment_class``.

    ``design_links`` maps ``"<case id>#<lesson number>"`` to the report section
    that answers that lesson. A lesson without a link is listed in
    ``open_items``; the section is not ready to issue until that list is empty.
    """
    term = EQUIPMENT_CLASSES[equipment_class]
    picked = query(rows, equipment_class)
    used_sources = {r.source_id for r in picked}
    class_cases = cases_for(list(cases), equipment_class)
    if case_ids is not None:
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("case ids must be distinct")
        by_id = {c.id: c for c in class_cases}
        unknown = [i for i in case_ids if i not in by_id]
        if unknown:
            raise ValueError(f"no case {unknown} for {equipment_class}")
        class_cases = [by_id[i] for i in case_ids]
    class_cases = class_cases[:MAX_CASES]
    links = dict(design_links or {})
    lessons, open_items = [], []
    for case in class_cases:
        for n, lesson in enumerate(case.lessons, start=1):
            key = f"{case.id}#{n}"
            answered = links.get(key)
            if not isinstance(answered, str) or not answered.strip():
                answered = UNASSIGNED
            answered = answered.strip()
            if answered == UNASSIGNED:
                open_items.append(f"lesson {key} has no design response")
            lessons.append(
                {
                    "key": key,
                    "case_id": case.id,
                    "lesson": lesson.statement,
                    "page": lesson.page,
                    "addressed_in": answered,
                }
            )
    if not picked:
        open_items.append("no records for this equipment class in the table")
    if len({c.id for c in class_cases}) < 2:
        open_items.append("fewer than two illustrative public cases on file")
    references = [
        f"{s.title or s.source_id}. {s.url} (read {s.retrieved})."
        for s in stats
        if s.source_id in used_sources
    ] + [c.reference() for c in class_cases]
    return HseSection(
        equipment_class=equipment_class,
        equipment_label=term.label,
        letter=letter,
        summary=summarise(picked),
        sources=[s for s in stats if s.source_id in used_sources],
        records=picked,
        cases=class_cases,
        lessons=lessons,
        references=references,
        open_items=open_items,
    )


def _table(header: Sequence[str], body: Sequence[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in body]
    return lines


def _block(text: str) -> str:
    """Area block reduced to letters and digits, upper case."""
    return "".join(ch for ch in text.upper() if ch.isalnum())


def _modes(joined: str) -> str:
    return "; ".join(FAILURE_MODES[m].label for m in joined.split(";"))


def render_markdown(section: HseSection, *, max_records: int = 12) -> str:
    """Render the appendix. Reference numbers [H1], [H2] ... are local to it."""
    s, L = section.summary, section.letter
    refs = {text: f"[H{i}]" for i, text in enumerate(section.references, start=1)}
    src_ref = {
        st.source_id: refs[
            f"{st.title or st.source_id}. {st.url} (read {st.retrieved})."
        ]
        for st in section.sources
    }
    out: list[str] = [f"## Appendix {L} HSE and safety", ""]
    out.append(
        "This appendix gives the public incident history for "
        f"{section.equipment_label.lower()}, the recorded failure modes and "
        "causes, and the lessons that apply to this design."
    )
    out += ["", f"### {L}.1 Data used", ""]
    out += _table(
        (
            "Source",
            "Records read",
            "Records for this equipment",
            "Period",
            "Read on",
            "Ref.",
        ),
        [
            (
                st.title or st.source_id,
                st.records_read,
                s["by_source"].get(st.source_id, 0),
                f"{st.first_date} to {st.last_date}",
                st.retrieved,
                src_ref[st.source_id],
            )
            for st in section.sources
        ],
    )
    out += [
        "",
        "The records are matched to the equipment by rules on the source's own "
        "fields. A cause is listed only where the source states it.",
        "",
        f"### {L}.2 Incident history",
        "",
    ]
    if s["records"]:
        all_refs = ", ".join(sorted(src_ref.values()))
        out.append(
            f"The data holds {s['records']} records whose event type names this "
            f"equipment, dated {s['first_date']} to {s['last_date']} {all_refs}. "
            f"Records with a fatality: {s['with_fatality']}; with an injury: "
            f"{s['with_injury']}; with pollution: {s['with_pollution']}."
        )
        keys = {(r.date, _block(r.location)) for r in section.records}
        located = [c for c in section.cases if c.area_block]
        outside = [c for c in located if (c.date, _block(c.area_block)) not in keys]
        unverified = len(section.cases) - len(located)
        if outside:
            out.append(
                f"The count is a lower bound: {len(outside)} of the "
                f"{len(section.cases)} cases in Section {L}.4 are not among these "
                "records by date and area block, because the event type recorded "
                "for them does not name this equipment or the data set does not "
                "hold them."
            )
        if unverified:
            out.append(
                f"For {unverified} of the {len(section.cases)} cases the area "
                "block is not on file, so whether the case is among these records "
                "is not verified."
            )
        if EQUIPMENT_CLASSES[section.equipment_class].note:
            out.append(EQUIPMENT_CLASSES[section.equipment_class].note)
        out += [""] + _table(("Decade", "Records"), list(s["by_decade"].items()))
        shown = sorted(section.records, key=lambda r: r.date, reverse=True)[
            :max_records
        ]
        out += ["", f"The {len(shown)} most recent records are listed below.", ""]
        out += _table(
            ("Date", "Location", "Event type as recorded", "Ref."),
            [
                (r.date, r.location or "not given", r.event_text, src_ref[r.source_id])
                for r in shown
            ],
        )
    else:
        out.append("The data sets read hold no record for this equipment.")
    out += ["", f"### {L}.3 Failure modes and stated causes", ""]
    out.append(
        "A record with two event types counts under both, so the counts can "
        "add up to more than the number of records."
    )
    out += [""] + _table(
        ("Failure mode", "Records"),
        [(m["label"], m["records"]) for m in s["by_failure_mode"]],
    )
    out.append("")
    if s["cause_coded"]:
        out += _table(
            ("Cause as coded by the source", "Records"),
            [(m["label"], m["records"]) for m in s["by_coded_cause"]],
        )
        out.append("")
        out.append(
            f"The source codes a cause for {s['cause_coded']} of the "
            f"{s['records']} records; it codes {s['cause_coded_unknown']} of "
            "those as unknown."
        )
        if s["cause_not_coded"]:
            out.append(
                f"The other {s['cause_not_coded']} records come from a data set "
                "that gives the event type only and state no cause."
            )
    else:
        out.append(
            f"None of the {s['records']} records states a cause: the data set "
            "gives the event type only. The causes on record are those in the "
            f"investigation reports of Section {L}.4."
        )
    out += ["", f"### {L}.4 Illustrative public cases", ""]
    if not section.cases:
        out.append("No investigated public case is on file for this equipment.")
    for n, case in enumerate(section.cases, start=1):
        ref = refs[case.reference()]
        out.append(
            f"**Case {n}: {case.facility_type}, {case.location}, {case.date}** {ref}"
        )
        out.append("")
        out.append(f"- What failed: {case.what_failed.cite()};")
        out.append(
            "- Failure mode: "
            + "; ".join(FAILURE_MODES[m].label for m in case.failure_modes)
            + ";"
        )
        if case.cause_statements:
            for c in case.cause_statements:
                out.append(f"- Cause stated by the investigation: {c.cite()};")
        else:
            out.append("- Cause: the investigation does not state one;")
        for c in case.ruled_out:
            out.append(
                f"- Ruled out or found unlikely by the investigation: {c.cite()};"
            )
        if case.mechanism != NOT_STATED:
            out.append(
                f"- Mechanism as stated: {FAILURE_MECHANISMS[case.mechanism].label};"
            )
        for c in case.consequences:
            out.append(f"- Consequence: {c.cite()};")
        out.append("")
    out += [f"### {L}.5 Lessons for this design", ""]
    if section.lessons:
        case_no = {c.id: i for i, c in enumerate(section.cases, start=1)}
        out += _table(
            (
                "Finding or recommendation stated by the investigation",
                "Case",
                "Addressed in",
            ),
            [
                (
                    f"{x['lesson']} (p. {x['page']})",
                    case_no[x["case_id"]],
                    x["addressed_in"],
                )
                for x in section.lessons
            ],
        )
    else:
        out.append("The cited investigations state no recommendation.")
    out += ["", f"### {L}.6 References for this appendix", ""]
    out += [f"- {tag} {text}" for text, tag in refs.items()]
    return "\n".join(out) + "\n"
