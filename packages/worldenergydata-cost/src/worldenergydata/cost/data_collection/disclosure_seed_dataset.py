"""Manually transcribed operator CAPEX, not pipeline-ingested disclosures.

Amounts are nominal USD million, with the fiscal definitions stated per row.
No FX, inflation, comparability or restatement qualification is inferred.
Shell's 2021 amount uses the 2023 filing (19,697), rather than the 2022
filing (19,698); the source vintage is preserved, without inferring why it
changed. Original public filings remain at the cited open archive URLs.
"""

from copy import deepcopy

from worldenergydata.cost.disclosure_analytics import SCOPE_OPERATOR, DisclosureRecord

# Annual report editions, PDF page numbers and SHA-256 of the retrieved PDFs.
# Retrieval: 2026-10-20; archive responses HTTP 200. Values below are transcribed
# from these tables, not estimated from charts or recalled from other work.
_FILINGS = {
    ("Chevron", 2023): (
        "c/NYSE_CVX_2023",
        "Financial Highlights, PDF p.22 (printed XX)",
        "65eb16767aed1023026cf2ffec33426e2ead0fcfdd60e78333f88c326943b1aa",
    ),
    ("Chevron", 2022): (
        "c/NYSE_CVX_2022",
        "Financial Highlights, PDF p.24 (printed XXII)",
        "6efad64410a44f7a09e72d0e3269646cb5cefce47af790569dc56153bd711d2a",
    ),
    ("Shell", 2023): (
        "s/NYSE_SHEL_2023",
        "Group results, Key metrics, PDF p.34",
        "d944ec8c973f4988fbb07174ec922d5ae21a3818662d08a6de41cfe70150a78d",
    ),
    ("Shell", 2022): (
        "s/NYSE_SHEL_2022",
        "Group results, Key metrics, PDF p.32",
        "f69e2ea59c85551bb81a2ed686d30377cc87db86120750d6bb2a4eafbf0df6a2",
    ),
    ("BP", 2023): (
        "b/LSE_BP_2023",
        "Financial statements summary, PDF p.39 (printed 37)",
        "9cd79ab7653dda7750431f549284039fdf85d4d1a13c8a775e3ef17a7d422252",
    ),
    ("BP", 2022): (
        "b/LSE_BP_2022",
        "Financial statements summary, PDF p.36 (printed 34)",
        "68b4b79a687ecf083b79ce99f3ed4044f46a553f105b378751806cd72ffcf11e",
    ),
}

# Each tuple: operator, filing edition, fiscal year, as-reported USD million.
# Chevron: Capital expenditures (Capex), excluding affiliate capex.
# Shell: Cash capital expenditure (company-defined alternative measure).
# BP: Capital expenditure, magnitude of cash outflow in the summary table.
_VALUES = (
    ("Chevron", 2022, 2020, 8922),
    ("Chevron", 2023, 2021, 8056),
    ("Chevron", 2023, 2022, 11974),
    ("Chevron", 2023, 2023, 15829),
    ("Shell", 2022, 2020, 17827),
    ("Shell", 2023, 2021, 19697),
    ("Shell", 2023, 2022, 24833),
    ("Shell", 2023, 2023, 24392),
    ("BP", 2022, 2020, 14055),
    ("BP", 2023, 2021, 12848),
    ("BP", 2023, 2022, 16330),
    ("BP", 2023, 2023, 16253),
)
_BASIS = {
    "Chevron": "Consolidated capital expenditures; excludes affiliate capex",
    "Shell": "Cash capital expenditure; company-defined alternative measure",
    "BP": "Capital expenditure; positive magnitude of reported cash outflow",
}


def _record(operator, edition, year, amount):
    locator, page, digest = _FILINGS[operator, edition]
    return DisclosureRecord(
        operator=operator,
        fiscal_year=year,
        reported_capex_usd_mm=amount,
        scope=SCOPE_OPERATOR,
        currency="USD",
        provenance={
            "source": f"{operator} Annual Report {edition}",
            "source_url": (
                "https://www.annualreports.com/HostedData/AnnualReportArchive/"
                f"{locator}.pdf"
            ),
            "publisher": operator,
            "archive": "AnnualReports open archive",
            "page_ref": page,
            "revision": str(edition),
            "source_sha256": digest,
            "retrieval_date": "2026-10-20",
            "retrieval_note": "Manual table transcription; source vintage retained",
            "fiscal_basis": _BASIS[operator],
            "data_tier": "seed",
            "units": "USD million, nominal, as reported",
        },
    )


SEED_DISCLOSURE_RECORDS = [_record(*row) for row in _VALUES]


def load_seed_disclosure_records() -> list[DisclosureRecord]:
    """Return independent records and provenance dictionaries on each call."""
    return deepcopy(SEED_DISCLOSURE_RECORDS)
