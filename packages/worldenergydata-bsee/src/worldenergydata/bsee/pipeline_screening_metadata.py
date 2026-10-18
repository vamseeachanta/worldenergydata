"""Publisher metadata and semantic status-table qualification."""

import hashlib
import json

USGS_TITLE = (
    "usSEABED: Gulf of Mexico and Caribbean (Puerto Rico and U.S. Virgin Islands) "
    "Offshore Surficial Sediment Data Release, version 1.0"
)
PUBLISHERS = {
    "bsee-data-center": (
        "Bureau of Safety and Environmental Enforcement",
        "Generally, materials produced by federal agencies belong to the public domain and may be reproduced without permission.",
        "https://www.bsee.gov/bsee/privacy-policy#copyright",
        "Third-party materials may carry restrictions; no blanket rights warranty is supplied.",
    ),
    "noaa-ndbc": (
        "NOAA National Data Buoy Center",
        "The information on National Weather Service (NWS) Web pages are in the public domain, unless specifically noted otherwise",
        "https://www.weather.gov/disclaimer#use",
        "Credit the source; no implied endorsement; derivatives are not official products. Third-party exceptions apply.",
    ),
    "usgs-layer-register": (
        "U.S. Geological Survey",
        "Public domain data from the U.S. Government are freely redistributable with proper metadata and source attribution.",
        "https://pubs.usgs.gov/ds/2006/146/data/gmx_ext.zip#gmx_extmeta.txt",
        "Credit the source; third-party materials may have separate rights. DS 146 extracted-table Use_Constraints requires metadata and source attribution.",
    ),
}


def publisher_metadata(entry):
    """Attach verified publisher statements; input-specific evidence stays intact."""
    value = dict(entry)
    publisher, statement, url, limits = PUBLISHERS[
        (
            "bsee-data-center"
            if value["source_id"] == "bsee-status-dictionary"
            else value["source_id"]
        )
    ]
    locator = value.get("url", "")
    title = (
        USGS_TITLE
        if value["source_id"] == "usgs-layer-register"
        else (
            "Pipeline permits raw data"
            if "PipePermRawData" in locator
            else (
                "Pipeline locations raw data"
                if "PipeLocRawData" in locator
                else (
                    "Pipeline status field values"
                    if "FieldValues" in locator
                    else (
                        "Active stations list"
                        if "activestations" in locator
                        else "Historical standard meteorological data: "
                        + locator.split("filename=")[-1].split("&")[0]
                    )
                )
            )
        )
    )
    value.update(
        title=title,
        publisher=publisher,
        terms_of_use={"statement": statement, "url": url, "limitations": limits},
    )
    if "http_status" in value:
        value["http_status"] = int(value["http_status"])
    if isinstance(value.get("source_vintage"), str):
        value["source_vintage"] = {
            "state": "observed",
            "latest_observation": value["source_vintage"],
        }
    return value


def status_table(path):
    """Extract only the code-to-meaning data, excluding ASP.NET hidden state."""
    from bs4 import BeautifulSoup

    result = {}
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for row in soup.select("tr.dxgvDataRow"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all("td", recursive=False)
        ]
        if len(cells) == 4 and cells[1] and cells[3]:
            if cells[1] in result:
                raise ValueError("Duplicate status dictionary code")
            result[cells[1]] = cells[3]
    if not result:
        raise ValueError("Missing status dictionary table")
    return result


def status_table_digest(table):
    raw = json.dumps(
        table, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()
