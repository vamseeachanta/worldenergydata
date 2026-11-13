"""Crude oil and natural gas production, from PPAC tables.

PPAC (Petroleum Planning & Analysis Cell, MoPNG) publishes production tables
at https://ppac.gov.in as XLS. Three layouts are read:

* crude oil by company group, one column per Indian fiscal year (April-March),
  English or Hindi labels ("PT_Crude oil production_H", "HN_PT_...");
* crude oil by company group, one column per month of the fiscal year in the
  sheet title ("PT_Crude oil production_Current");
* natural gas gross production by state, onshore and offshore, one column per
  month ("NG-H-Production" month-wise sheets, "NG-C-Production").

Sub-totals and totals are used only to check the components; they are not
stored, except national net gas production, which has no components. Units are
read from the sheet (million metric tonnes for crude, MMSCM for gas) and must
match; values are not converted. Months a sheet has not reached print blank
components and are dropped as not yet published, never stored as zero.
Provisional periods ("(P)" or "*" in the title) are flagged.

In the gas sheets the CBM row (West Bengal, MP, Jharkhand) is outside "Onshore
Total (A)" but inside "Total (A+B)"; it is stored with location ``onshore_cbm``.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

from .sources import data_path

MONTHS = [
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "january",
    "february",
    "march",
]
UNITS = {
    "million metric tonnes": "million_tonnes",
    "मिलियन मीट्रिक टन": "million_tonnes",
    "mmscm": "million_scm",
}
# Crude row label (lower-case, all whitespace removed) -> (company group, role).
CRUDE_ROWS = {
    "ongc": ("ONGC", "component"),
    "ओ.एन.जी.सी.": ("ONGC", "component"),
    "oil": ("OIL", "component"),
    "ओ.आई.एल.": ("OIL", "component"),
    "jvc/private": ("JVC/Private", "component"),
    "जे.वी.सी./प्राईवेट": ("JVC/Private", "component"),
    "psutotal": ("PSU", "subtotal"),
    "psutotal(crudeoil)": ("PSU", "subtotal"),
    "पी.एस.यू._कुल": ("PSU", "subtotal"),
    "totalcrudeoil": ("TOTAL", "total"),
    "कुलकच्चातेल": ("TOTAL", "total"),
    "condensate": ("all", "condensate"),
    "condensate*": ("all", "condensate"),
    "संघनन(condensate)*": ("all", "condensate"),
}
COLUMNS = [
    "period",
    "period_type",
    "fiscal_year",
    "product",
    "measure",
    "company_group",
    "location",
    "state",
    "value",
    "unit",
    "provisional",
    "source_id",
]


def _label(value) -> str:
    return (
        re.sub(r"\s+", "", str(value)).replace("‌", "").lower()
        if isinstance(value, str)
        else ""
    )


def _fiscal_year(text: str) -> str | None:
    # Exclude full-year ranges and ISO dates before checking consecutive years.
    for match in re.finditer(r"(?<![\d-])(\d{4})\s*-\s*(\d{2})(?![\d-])", text):
        start, end = match.groups()
        if int(end) == (int(start) + 1) % 100:
            return f"{start}-{end}"
    return None


def _period_month(fiscal_year: str, month_index: int) -> str:
    start = int(fiscal_year[:4])
    year = start if month_index < 9 else start + 1  # April-December, then January-March
    calendar_month = (month_index + 3) % 12 + 1
    return f"{year}-{calendar_month:02d}"


def _number(value) -> float:
    if value is None or value == "" or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"production value must be numeric or blank, got {value!r}")
    if not math.isfinite(value) or value < 0:
        raise ValueError("production value must be finite and non-negative")
    return float(value)


def _cells(frame: pd.DataFrame) -> list[list]:
    return frame.astype(object).where(frame.notna(), None).values.tolist()


def _unit(cells: list[list]) -> str:
    text = " ".join(str(c) for row in cells for c in row if isinstance(c, str)).lower()
    for key, unit in UNITS.items():
        if key in text:
            return unit
    raise ValueError("unit not stated in sheet")


def _periods(cells: list[list]):
    """Return (header row index, [(column, period, period_type, fiscal_year, provisional)])."""
    for index, row in enumerate(cells):
        labels = [_label(c) for c in row]
        if "april" in labels and "march" in labels:
            title = " ".join(
                str(c) for r in cells[:index] for c in r if isinstance(c, str)
            )
            fiscal = _fiscal_year(title)
            if fiscal is None:
                raise ValueError("monthly sheet has no fiscal year in its title")
            provisional = "(p)" in title.lower() or "*" in title
            return index, [
                (
                    i,
                    _period_month(fiscal, MONTHS.index(l)),
                    "month",
                    fiscal,
                    provisional,
                )
                for i, l in enumerate(labels)
                if l in MONTHS
            ]
        years = [
            (i, _fiscal_year(c))
            for i, c in enumerate(row)
            if isinstance(c, str) and _fiscal_year(c)
        ]
        if len(years) >= 3:
            return index, [
                (i, fy, "fiscal_year", fy, "(p)" in str(row[i]).lower())
                for i, fy in years
            ]
    raise ValueError("no period header row")


def _close(parts: list[float], total: float) -> bool:
    """Compare stored XLS numbers, allowing only binary rounding error.

    The pinned PPAC workbooks retain unrounded numeric cells even where their
    display formats show fewer decimals. No display rounding or unit-relative
    tolerance is applied. Allow one representable step (ulp) per stored operand
    and total, plus one for the correctly rounded sum computed by math.fsum.
    """
    computed = math.fsum(parts)
    bound = math.fsum(math.ulp(v) for v in [*parts, total, computed])
    return abs(computed - total) <= bound


def parse_ppac_sheet(frame: pd.DataFrame, product: str, source_id: str) -> pd.DataFrame:
    """Parse one PPAC crude-by-company sheet (read with header=None)."""
    if product != "crude_oil":
        raise ValueError(
            "company-group sheets are crude oil; use parse_ppac_gas_sheet for gas"
        )
    cells = _cells(frame)
    unit = _unit(cells)
    if unit != "million_tonnes":
        raise ValueError(f"unit changed: {unit} for {product}")
    header_index, periods = _periods(cells)
    records, checks = [], {}
    for row in cells[header_index + 1 :]:
        key = _label(row[0])
        if key not in CRUDE_ROWS:
            continue
        group, role = CRUDE_ROWS[key]
        for column, period, period_type, fiscal, provisional in periods:
            value = _number(row[column] if column < len(row) else None)
            checks.setdefault(period, {})[
                group if role == "component" else role
            ] = value
            if role in ("component", "condensate") and not math.isnan(value):
                records.append(
                    {
                        "period": period,
                        "period_type": period_type,
                        "fiscal_year": fiscal,
                        "product": "condensate" if role == "condensate" else product,
                        "measure": "production",
                        "company_group": group,
                        "location": "all",
                        "state": "all",
                        "value": value,
                        "unit": unit,
                        "provisional": provisional,
                        "source_id": source_id,
                    }
                )
    if not records:
        raise ValueError("no production rows recognised")
    published = set()
    for period, values in checks.items():
        required = [
            values.get(k, math.nan)
            for k in ("ONGC", "OIL", "JVC/Private", "subtotal", "total")
        ]
        if _unpublished(
            required[:3], required[3:] + [values.get("condensate", math.nan)]
        ):
            continue
        if any(map(math.isnan, required)):
            raise ValueError(f"{period}: incomplete crude production period")
        published.add(period)
        ongc, oil = values.get("ONGC", math.nan), values.get("OIL", math.nan)
        private, subtotal, total = (
            values.get(k, math.nan) for k in ("JVC/Private", "subtotal", "total")
        )
        if not _close([ongc, oil], subtotal):
            raise ValueError(f"{period}: ONGC + OIL does not equal PSU total")
        if not _close([ongc, oil, private], total):
            raise ValueError(f"{period}: company groups do not equal total")
    return pd.DataFrame(
        [r for r in records if r["period"] in published], columns=COLUMNS
    )


def _unpublished(components: list[float], totals: list[float]) -> bool:
    """Future columns have blank components and blank or formula-zero totals."""
    return all(math.isnan(v) for v in components) and all(
        math.isnan(v) or v == 0 for v in totals
    )


def _gas_row(label: str):
    text = label.lower()
    if text.startswith("onshoretotal"):
        return "onshore_total", None
    if text.startswith("b)offshore"):
        return "offshore", None
    if text.startswith("total(a+b)"):
        return "total", None
    if text.startswith("netproduction"):
        return "net", None
    if re.match(r"\((?:i|ii|iii|iv|v|vi|vii|viii)\)", text):
        return ("cbm" if "(cbm)" in text else "state"), None
    return None, None


def parse_ppac_gas_sheet(frame: pd.DataFrame, source_id: str) -> pd.DataFrame:
    """Parse one PPAC month-wise state gas sheet (read with header=None)."""
    cells = _cells(frame)
    unit = _unit(cells)
    if unit != "million_scm":
        raise ValueError(f"unit changed: {unit} for natural gas")
    header_index, periods = _periods(cells)
    if any(p[2] != "month" for p in periods):
        raise ValueError("gas sheet must be month-wise")
    records, checks = [], {}
    for row in cells[header_index + 1 :]:
        kind, _ = _gas_row(_label(row[0]))
        if kind is None:
            continue
        name = re.sub(r"^\s*\([ivx]+\)\s*", "", str(row[0])).strip()
        for column, period, _, fiscal, provisional in periods:
            value = _number(row[column] if column < len(row) else None)
            bucket = checks.setdefault(period, {"state": []})
            if kind == "state":
                bucket["state"].append(value)
            else:
                bucket[kind] = value
            if math.isnan(value):
                continue
            base = {
                "period": period,
                "period_type": "month",
                "fiscal_year": fiscal,
                "product": "natural_gas",
                "company_group": "all",
                "unit": unit,
                "provisional": provisional,
                "source_id": source_id,
            }
            if kind == "state":
                records.append(
                    {
                        **base,
                        "measure": "gross_production",
                        "location": "onshore",
                        "state": name,
                        "value": value,
                    }
                )
            elif kind == "cbm":
                records.append(
                    {
                        **base,
                        "measure": "gross_production",
                        "location": "onshore_cbm",
                        "state": name,
                        "value": value,
                    }
                )
            elif kind == "offshore":
                records.append(
                    {
                        **base,
                        "measure": "gross_production",
                        "location": "offshore",
                        "state": "all",
                        "value": value,
                    }
                )
            elif kind == "net":
                records.append(
                    {
                        **base,
                        "measure": "net_production",
                        "location": "all",
                        "state": "all",
                        "value": value,
                    }
                )
    if not records:
        raise ValueError("no gas rows recognised")
    published = set()
    for period, values in checks.items():
        states = values["state"]
        components = states + [values.get("offshore", math.nan)]
        if "cbm" in values:
            components.append(values["cbm"])
        totals = [values.get(k, math.nan) for k in ("onshore_total", "total")]
        if _unpublished(components, totals + [values.get("net", math.nan)]):
            continue
        if not states or any(map(math.isnan, components + totals)):
            raise ValueError(f"{period}: incomplete gas production period")
        published.add(period)
        onshore = values["onshore_total"]
        if not _close(states, onshore):
            raise ValueError(f"{period}: onshore states do not equal Onshore Total (A)")
        parts = [onshore, values["offshore"]]
        if "cbm" in values:
            parts.append(values["cbm"])
        if not _close(parts, values["total"]):
            raise ValueError(
                f"{period}: onshore + offshore + CBM does not equal Total (A+B)"
            )
    return pd.DataFrame(
        [r for r in records if r["period"] in published], columns=COLUMNS
    )


def read_sheets(path: Path, month_wise_only: bool = False) -> list[pd.DataFrame]:
    book = pd.read_excel(path, header=None, sheet_name=None)
    return [
        frame
        for name, frame in book.items()
        if not month_wise_only or "month" in name.lower() or "current" in name.lower()
    ]


def combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Later sources replace whole (period, product) groups.

    Crude sheets also cover condensate: a later published crude period without
    condensate removes the older condensate value rather than mixing vintages.
    Gas coverage remains independent of crude and condensate coverage.
    """
    owners = {}
    for index, frame in enumerate(frames):
        for period, product in zip(frame.period, frame["product"]):
            owners[period, product] = index
            if product == "crude_oil":
                owners[period, "condensate"] = index
    frame = pd.concat(
        [
            part.loc[
                [
                    owners[period, product] == index
                    for period, product in zip(part.period, part["product"])
                ]
            ]
            for index, part in enumerate(frames)
        ],
        ignore_index=True,
    )
    key = ["period", "product", "measure", "company_group", "location", "state"]
    return (
        frame.drop_duplicates(key, keep="last").sort_values(key).reset_index(drop=True)
    )


def load_production() -> pd.DataFrame:
    """Production records shipped with the package; see README for coverage."""
    return pd.read_csv(data_path("production.csv"))
