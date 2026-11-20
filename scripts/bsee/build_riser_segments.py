#!/usr/bin/env python3
"""Build a queryable table of Gulf of America pipeline segments that BSEE
permit text names as risers, and list which ones carry enough public data
for a static riser check.

Inputs are the raw BSEE files fetched by ``fetch_fielddev_public_sources.py``
(Pipeline Masters, Pipeline Permits, Platform Structures and the status code
page). Outputs are small derived tables written into the repository:

- ``riser_segments.csv``: one row per segment with a riser mention;
- ``riser_static_check_candidates.csv``: the subset with outside diameter,
  a wall thickness stated in permit text, and water depth;
- ``riser_segments_summary.json``: counts by riser type, size, water-depth
  band, product, status and readiness tier, plus the term counts that match
  the road map's Table 2.

Public-text rule: the tables carry BSEE codes only (operator code, area and
block, product and status codes). Free text, facility names and company
names are read for matching and never written out.

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

MASTERS_FIELDS = [
    "SEGMENT_NUM",
    "SEG_LENGTH",
    "ORIG_ID_NAME",
    "ORIG_AR_CODE",
    "ORIG_BLK_NUM",
    "ORIG_LSE_NUM",
    "DEST_ID_NAME",
    "DEST_AR_CODE",
    "DEST_BLK_NUM",
    "DEST_LSE_NUM",
    "ABAN_APRV_DT",
    "ABAN_DATE",
    "APPROVED_DATE",
    "AUTH_CODE",
    "BD_PPL_SDV_FL",
    "BUR_DSGN_FL",
    "CAT_LIFE_TM",
    "DEP_FLAG",
    "PPL_CONST_DATE",
    "LK_DETEC_FL",
    "LAST_REV_DATE",
    "INIT_HS_DT",
    "FED_ST_LGTH",
    "STATUS_CODE",
    "PPL_SIZE_CODE",
    "ROW_NUMBER",
    "RECV_MAOP_PRSS",
    "RECV_SEG_NUM",
    "PRPSL_CON_DT",
    "PROD_CODE",
    "SYS_DESIG_CODE",
    "PPL_ROW_PRMTE",
    "FACIL_OPERATOR",
    "MIN_WTR_DPTH",
    "MAX_WTR_DPTH",
    "PROT_NUMBER",
    "MAOP_PRSS",
    "CATHODIC_CODE",
    "BIDIR_FLAG",
    "BD_PPL_FSV_FL",
    "APRV_CODE",
    "ABAN_TYPE",
]

# Same terms as the road map r2 Table 2 (counted 19 Nov 2026).
RISER_TERMS = {
    "riser_any": re.compile(r"riser", re.I),
    "scr": re.compile(r"steel\s+catenary|\bSCRs?\b", re.I),
    "flexible": re.compile(r"flexible\s+riser", re.I),
    "lazy_wave": re.compile(r"lazy[\s-]*wave", re.I),
    "hybrid": re.compile(r"hybrid\s+riser|riser\s+tower|free[\s-]*standing", re.I),
    "ttr": re.compile(r"top[\s-]*tension|\bTTRs?\b", re.I),
}
TYPE_ORDER = ["scr", "lazy_wave", "ttr", "hybrid", "flexible"]

_NUM = r"(\d?\.\d{2,4}|[01]\s*-?\s*\d{1,2}/\d{1,2})"
WT_PATTERNS = [
    re.compile(
        _NUM
        + r"\s*(?:\"|''|-?\s?in(?:ch(?:es)?)?\.?)?\s*-?\s*(?:w\.\s?t\.?|wt\b|wall\b|wall\s+thickness)",
        re.I,
    ),
    re.compile(
        r"(?:w\.\s?t\.?|\bwt\b|wall\s+thickness)\s*(?:of|=|:|is)?\s*" + _NUM, re.I
    ),
]

# API 5L outside diameter for nominal pipe sizes below 14 in.
NPS_OD_IN = {
    1: 1.315,
    2: 2.375,
    3: 3.5,
    4: 4.5,
    5: 5.563,
    6: 6.625,
    8: 8.625,
    10: 10.75,
    12: 12.75,
}
FLOATING_TYPES = {"SEMI", "SPAR", "TLP", "MTLP", "FPSO"}
DEPTH_BANDS_FT = [
    (0, 500),
    (500, 1000),
    (1000, 3000),
    (3000, 5000),
    (5000, 7500),
    (7500, 100000),
]


def _num(text: str) -> float | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_fraction(text: str) -> float | None:
    text = text.strip().replace(" ", "")
    m = re.fullmatch(r"(\d+)?-?(\d+)/(\d+)", text)
    if m:
        whole = int(m.group(1) or 0)
        den = int(m.group(3))
        return whole + int(m.group(2)) / den if den else None
    return _num(text)


def parse_size_code(code: str) -> tuple[float | None, float | None]:
    """Return (nominal inches as coded, outside diameter inches).

    BSEE codes the outside diameter; whole-number codes are read as nominal
    pipe sizes and converted with the API 5L table below 14 in (assumption,
    stated in the README). Fractional codes are read as the diameter itself.
    """
    code = (code or "").strip()
    if not code:
        return None, None
    m = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", code)
    if m:
        value = int(m.group(1)) + int(m.group(2)) / int(m.group(3))
        return value, value
    value = _num(code)
    if value is None:
        return None, None
    if value.is_integer() and int(value) in NPS_OD_IN:
        return value, NPS_OD_IN[int(value)]
    return value, value


def riser_types(text: str) -> list[str]:
    return [k for k, rx in RISER_TERMS.items() if rx.search(text or "")]


def wall_thicknesses(text: str) -> list[float]:
    """Wall thickness values (in) stated in free text, 0.2 to 2.0 in."""
    found = []
    for rx in WT_PATTERNS:
        for m in rx.finditer(text or ""):
            value = parse_fraction(m.group(1))
            if value is not None and 0.2 <= value <= 2.0:
                found.append(round(value, 3))
    return sorted(set(found))


def _date(text: str) -> str:
    text = (text or "").strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _zip_text(path: Path, member_suffix: str) -> io.TextIOWrapper:
    z = zipfile.ZipFile(path)
    name = next(n for n in z.namelist() if n.lower().endswith(member_suffix.lower()))
    return io.TextIOWrapper(
        z.open(name), encoding="cp1252", errors="replace", newline=""
    )


def load_masters(path: Path) -> dict[str, dict]:
    """Latest master record per segment (by LAST_REV_DATE)."""
    out: dict[str, dict] = {}
    for row in csv.reader(_zip_text(path, "pplmastdelimit.txt")):
        if len(row) != len(MASTERS_FIELDS):
            continue
        rec = {k: v.strip() for k, v in zip(MASTERS_FIELDS, row)}
        seg = rec["SEGMENT_NUM"]
        if seg not in out or rec["LAST_REV_DATE"] > out[seg]["LAST_REV_DATE"]:
            out[seg] = rec
    return out


def load_permit_segments(path: Path) -> dict[str, dict]:
    reader = csv.DictReader(_zip_text(path, "mv_pipeperm_segments.txt"))
    return {
        r["SEGMENT_NUM"].strip(): {k: (v or "").strip() for k, v in r.items()}
        for r in reader
    }


def load_submittals(path: Path):
    yield from csv.DictReader(_zip_text(path, "mv_pipeperm_submittals.txt"))


def load_floating_hosts(path: Path) -> dict[tuple[str, str], set[str]]:
    hosts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in csv.DictReader(_zip_text(path, "mv_platstruc_structures.txt")):
        stype = (r.get("STRUC_TYPE_CODE") or "").strip().upper()
        if stype in FLOATING_TYPES:
            hosts[(r["AREA_CODE"].strip(), r["BLOCK_NUMBER"].strip())].add(stype)
    return hosts


def load_status_values(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    values = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        cells = [
            html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        ]
        cells = [c for c in cells if c]
        if len(cells) >= 2 and re.fullmatch(r"[A-Z0-9/]{2,6}", cells[0]):
            values[cells[0]] = cells[1]
    return values


def depth_band(depth: float | None) -> str:
    if depth is None:
        return "unknown"
    for lo, hi in DEPTH_BANDS_FT:
        if lo <= depth < hi:
            return f"{lo}-{hi}" if hi < 100000 else f">={lo}"
    return "unknown"


NON_PIPE_PRODUCT = re.compile(r"^(UMB|UBE|CBL|ELECTRIC)", re.I)
DT_RANGE = (
    8.0,
    60.0,
)  # plausible outside diameter to wall thickness ratio for steel risers
# A submittal counts as a riser submittal when it says "riser", or names a
# steel catenary riser or a top-tensioned riser by acronym. Type words alone
# (for example "free standing" or "top tension") do not qualify a submittal.
RISER_GATE = re.compile(r"riser|steel\s+catenary|\bSCRs?\b|\bTTRs?\b", re.I)
WALL_WORDS = re.compile(r"\bwall\b|thick|\bw\.\s?t\b|\bwt\b", re.I)


def plausible_wts(od_in, wts: list[float]) -> list[float]:
    if od_in in ("", None):
        return []
    return [w for w in wts if DT_RANGE[0] <= float(od_in) / w <= DT_RANGE[1]]


def readiness(row: dict) -> str:
    types = set(row["riser_types"].split(";")) - {"riser_any", ""}
    steel = bool(types & {"scr", "lazy_wave", "ttr", "hybrid"}) or not types
    has_od = row["od_in"] != ""
    has_depth = row["max_water_depth_ft"] not in ("", "0", 0)
    has_wt = row["wt_in_plausible"] != ""
    if NON_PIPE_PRODUCT.match(row["product_code"] or ""):
        return "E_umbilical_or_cable"
    if not (has_od and has_depth):
        return "D_insufficient_od_or_depth"
    if types == {"flexible"}:
        return "C_flexible_needs_vendor_properties"
    if has_wt and steel:
        return "A_ready_od_wt_depth"
    return "B_needs_assumed_wt"


def build(mast: Path, perm: Path, platstruc: Path, status_html: Path | None):
    masters = load_masters(mast)
    pseg = load_permit_segments(perm)
    hosts = load_floating_hosts(platstruc)
    status_values = load_status_values(status_html)

    term_subs = Counter()
    term_segs: dict[str, set] = defaultdict(set)
    seg_info: dict[str, dict] = defaultdict(
        lambda: {
            "types": set(),
            "n": 0,
            "dates": [],
            "permit_types": set(),
            "wts": set(),
            "wt_ids": set(),
        }
    )
    wall_word_subs = 0
    for sub in load_submittals(perm):
        text = sub.get("PPL_DESCRIPTION") or ""
        types = riser_types(text)
        if not types:
            continue
        seg = (sub.get("SEGMENT_NUM") or "").strip()
        for t in types:
            term_subs[t] += 1
            term_segs[t].add(seg)
        if not RISER_GATE.search(text):
            continue
        if WALL_WORDS.search(text):
            wall_word_subs += 1
        info = seg_info[seg]
        info["types"].update(types)
        info["n"] += 1
        d = _date(sub.get("PPL_SUB_RECV_DT") or "")
        if d:
            info["dates"].append(d)
        info["permit_types"].add((sub.get("PPL_PRMT_TYPE_CD") or "").strip())
        wts = wall_thicknesses(text)
        if wts:
            info["wts"].update(wts)
            info["wt_ids"].add((sub.get("SUBMITTAL_ID") or "").strip())

    rows = []
    for seg, info in sorted(
        seg_info.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10**9
    ):
        m = masters.get(seg, {})
        p = pseg.get(seg, {})
        size_code = m.get("PPL_SIZE_CODE") or p.get("PPL_SIZE_CODE", "")
        nominal, od = parse_size_code(size_code)
        max_d = _num(m.get("MAX_WTR_DPTH") or p.get("MAX_WTR_DPTH", ""))
        min_d = _num(m.get("MIN_WTR_DPTH", ""))
        status = m.get("STATUS_CODE") or p.get("STATUS_CODE", "")
        orig = (
            m.get("ORIG_AR_CODE") or p.get("ORIG_AR_CODE", ""),
            m.get("ORIG_BLK_NUM") or p.get("ORIG_BLK_NUM", ""),
        )
        dest = (
            m.get("DEST_AR_CODE") or p.get("DEST_AR_CODE", ""),
            m.get("DEST_BLK_NUM") or p.get("DEST_BLK_NUM", ""),
        )
        host_types = sorted(hosts.get(orig, set()) | hosts.get(dest, set()))
        named = [t for t in TYPE_ORDER if t in info["types"]]
        dates = sorted(info["dates"])
        row = {
            "segment_num": seg,
            "riser_types": ";".join(named) if named else "riser_any",
            "primary_riser_type": named[0] if named else "unspecified",
            "riser_submittals": info["n"],
            "first_riser_submittal": dates[0] if dates else "",
            "last_riser_submittal": dates[-1] if dates else "",
            "riser_permit_types": ";".join(
                sorted(t for t in info["permit_types"] if t)
            ),
            "status_code": status,
            "status_meaning": status_values.get(status, ""),
            "product_code": m.get("PROD_CODE") or p.get("PROD_CODE", ""),
            "size_code": size_code,
            "nominal_in": "" if nominal is None else nominal,
            "od_in": "" if od is None else od,
            "wt_in_stated": ";".join(f"{w:.3f}" for w in sorted(info["wts"])),
            "wt_in_plausible": ";".join(
                f"{w:.3f}"
                for w in plausible_wts("" if od is None else od, sorted(info["wts"]))
            ),
            "wt_values_count": len(info["wts"]),
            "wt_source_submittals": ";".join(sorted(info["wt_ids"])),
            "min_water_depth_ft": "" if min_d is None else int(min_d),
            "max_water_depth_ft": "" if max_d is None else int(max_d),
            "depth_band_ft": depth_band(max_d),
            "segment_length_ft": m.get("SEG_LENGTH") or p.get("SEG_LENGTH", ""),
            "maop_psig": m.get("MAOP_PRSS") or p.get("MAOP_PRSS", ""),
            "approved_date": _date(m.get("APPROVED_DATE", ""))
            or _date(p.get("APPROVED_DATE", "")),
            "construction_date": _date(m.get("PPL_CONST_DATE", "")),
            "abandonment_date": _date(m.get("ABAN_DATE", "")),
            "operator_code": m.get("FACIL_OPERATOR") or p.get("FACIL_OPERATOR", ""),
            "authority_code": m.get("AUTH_CODE") or p.get("AUTHCODE", ""),
            "orig_area_block": " ".join(x for x in orig if x),
            "dest_area_block": " ".join(x for x in dest if x),
            "floating_host_types_in_end_blocks": ";".join(host_types),
            "in_masters": bool(m),
        }
        row["static_check_tier"] = readiness(row)
        rows.append(row)

    summary = {
        "term_counts": {
            t: {"submittals": term_subs[t], "segments": len(term_segs[t] - {""})}
            for t in RISER_TERMS
        },
        "segments": len(rows),
        "by_primary_type": Counter(r["primary_riser_type"] for r in rows),
        "by_static_check_tier": Counter(r["static_check_tier"] for r in rows),
        "by_depth_band_ft": Counter(r["depth_band_ft"] for r in rows),
        "by_status_code": Counter(r["status_code"] for r in rows),
        "by_product_code": Counter(r["product_code"] for r in rows),
        "by_size_code": Counter(r["size_code"] for r in rows),
        "segments_with_floating_host_in_end_block": sum(
            1 for r in rows if r["floating_host_types_in_end_blocks"]
        ),
        "tier_A_by_type": Counter(
            r["primary_riser_type"]
            for r in rows
            if r["static_check_tier"].startswith("A")
        ),
        "tier_A_ge_1000ft": sum(
            1
            for r in rows
            if r["static_check_tier"].startswith("A")
            and (r["max_water_depth_ft"] or 0) >= 1000
        ),
        "tier_B_ge_1000ft_steel_or_unspecified": sum(
            1
            for r in rows
            if r["static_check_tier"].startswith("B")
            and (r["max_water_depth_ft"] or 0) >= 1000
        ),
        "riser_submittals": sum(r["riser_submittals"] for r in rows),
        "riser_submittals_with_wall_words": wall_word_subs,
        "segments_with_any_stated_wt": sum(1 for r in rows if r["wt_in_stated"]),
        "status_values_decoded": len(status_values),
    }
    summary = json.loads(json.dumps(summary, default=dict))
    return rows, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="folder holding the BSEE files of one retrieval",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "data/modules/bsee/pipeline_risers",
    )
    args = ap.parse_args(argv)
    raw = args.raw_dir
    rows, summary = build(
        raw / "pplmastdelimit.zip",
        raw / "PipePermRawData.zip",
        raw / "PlatStrucRawData.zip",
        raw / "FieldValues_domain-STATUS_CODES.html",
    )
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "riser_segments.csv", rows)
    ready = [r for r in rows if r["static_check_tier"].startswith("A")]
    if ready:
        write_csv(args.out / "riser_static_check_candidates.csv", ready)
    summary["retrieval_folder"] = raw.name
    (args.out / "riser_segments_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: summary[k]
                for k in ("segments", "term_counts", "by_static_check_tier")
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
