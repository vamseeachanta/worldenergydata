# ABOUTME: Flag state and country code normalization utilities for IMO data.
# ABOUTME: Converts various flag state formats to ISO 2-letter country codes.

"""
IMO Data Normalizers

Provides normalization functions for IMO GISIS data fields, particularly
flag state normalization to ISO 2-letter country codes.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Comprehensive flag state mappings (name/code -> ISO 2-letter)
FLAG_STATE_MAPPINGS = {
    # Major flag states
    "panama": "PA",
    "pan": "PA",
    "liberia": "LR",
    "lbr": "LR",
    "marshall islands": "MH",
    "mhl": "MH",
    "hong kong": "HK",
    "hkg": "HK",
    "hong kong, china": "HK",
    "singapore": "SG",
    "sgp": "SG",
    "malta": "MT",
    "mlt": "MT",
    "bahamas": "BS",
    "bhs": "BS",
    "china": "CN",
    "chn": "CN",
    "greece": "GR",
    "grc": "GR",
    "japan": "JP",
    "jpn": "JP",
    "norway": "NO",
    "nor": "NO",
    "cyprus": "CY",
    "cyp": "CY",
    "united kingdom": "GB",
    "uk": "GB",
    "gbr": "GB",
    "great britain": "GB",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "united states of america": "US",
    "denmark": "DK",
    "dnk": "DK",
    "italy": "IT",
    "ita": "IT",
    "netherlands": "NL",
    "nld": "NL",
    "germany": "DE",
    "deu": "DE",
    "france": "FR",
    "fra": "FR",
    "south korea": "KR",
    "korea": "KR",
    "kor": "KR",
    "republic of korea": "KR",
    "india": "IN",
    "ind": "IN",
    "indonesia": "ID",
    "idn": "ID",
    "turkey": "TR",
    "tur": "TR",
    "russia": "RU",
    "rus": "RU",
    "russian federation": "RU",
    "brazil": "BR",
    "bra": "BR",
    "antigua and barbuda": "AG",
    "atg": "AG",
    "bermuda": "BM",
    "bmu": "BM",
    "cayman islands": "KY",
    "cym": "KY",
    "isle of man": "IM",
    "imn": "IM",
    "gibraltar": "GI",
    "gib": "GI",
    "portugal": "PT",
    "prt": "PT",
    "madeira": "PT",
    "spain": "ES",
    "esp": "ES",
    "belgium": "BE",
    "bel": "BE",
    "canada": "CA",
    "can": "CA",
    "australia": "AU",
    "aus": "AU",
    "new zealand": "NZ",
    "nzl": "NZ",
    "philippines": "PH",
    "phl": "PH",
    "vietnam": "VN",
    "vnm": "VN",
    "thailand": "TH",
    "tha": "TH",
    "malaysia": "MY",
    "mys": "MY",
    "saudi arabia": "SA",
    "sau": "SA",
    "united arab emirates": "AE",
    "uae": "AE",
    "are": "AE",
    "egypt": "EG",
    "egy": "EG",
    "south africa": "ZA",
    "zaf": "ZA",
    "nigeria": "NG",
    "nga": "NG",
    "mexico": "MX",
    "mex": "MX",
    "argentina": "AR",
    "arg": "AR",
    "chile": "CL",
    "chl": "CL",
    "peru": "PE",
    "per": "PE",
    "venezuela": "VE",
    "ven": "VE",
    "colombia": "CO",
    "col": "CO",
    "ecuador": "EC",
    "ecu": "EC",
    # Flags of convenience - additional
    "vanuatu": "VU",
    "vut": "VU",
    "tuvalu": "TV",
    "tuv": "TV",
    "st vincent": "VC",
    "st vincent and the grenadines": "VC",
    "vct": "VC",
    "belize": "BZ",
    "blz": "BZ",
    "cambodia": "KH",
    "khm": "KH",
    "mongolia": "MN",
    "mng": "MN",
    "palau": "PW",
    "plw": "PW",
    "comoros": "KM",
    "com": "KM",
    "togo": "TG",
    "tgo": "TG",
    "tanzania": "TZ",
    "tza": "TZ",
    "sierra leone": "SL",
    "sle": "SL",
    "moldova": "MD",
    "mda": "MD",
    "georgia": "GE",
    "geo": "GE",
}


def normalize_flag_state(flag_state: Optional[str]) -> Optional[str]:
    """
    Normalize flag state to ISO 2-letter country code.

    Handles various IMO GISIS flag state formats including:
    - Full country names
    - ISO 2-letter codes
    - ISO 3-letter codes
    - Common variations and misspellings

    Args:
        flag_state: Raw flag state string from GISIS

    Returns:
        ISO 2-letter country code or original string if not found
    """
    if not flag_state:
        return None

    flag_lower = flag_state.lower().strip()

    if flag_lower in FLAG_STATE_MAPPINGS:
        return FLAG_STATE_MAPPINGS[flag_lower]

    # If already 2-letter code, return uppercase
    if len(flag_state) == 2:
        return flag_state.upper()

    # If 3-letter code in mappings, return
    if flag_lower in FLAG_STATE_MAPPINGS:
        return FLAG_STATE_MAPPINGS[flag_lower]

    logger.debug(f"Unknown flag state: {flag_state}")
    return flag_state.upper()[:2] if len(flag_state) >= 2 else flag_state


def get_flag_state_name(iso_code: str) -> Optional[str]:
    """
    Get the full name of a flag state from its ISO code.

    Args:
        iso_code: ISO 2-letter country code

    Returns:
        Full country name or None if not found
    """
    # Reverse lookup - find first full name that maps to this code
    code_upper = iso_code.upper() if iso_code else None
    if not code_upper:
        return None

    for name, code in FLAG_STATE_MAPPINGS.items():
        if code == code_upper and len(name) > 3:  # Skip abbreviations
            return name.title()

    return None


def is_flag_of_convenience(iso_code: str) -> bool:
    """
    Check if a flag state is commonly considered a flag of convenience.

    Args:
        iso_code: ISO 2-letter country code

    Returns:
        True if the flag is commonly considered a flag of convenience
    """
    # Common flags of convenience
    foc_codes = {
        "PA",  # Panama
        "LR",  # Liberia
        "MH",  # Marshall Islands
        "BS",  # Bahamas
        "MT",  # Malta
        "CY",  # Cyprus
        "AG",  # Antigua and Barbuda
        "VU",  # Vanuatu
        "BZ",  # Belize
        "KH",  # Cambodia
        "MN",  # Mongolia
        "KM",  # Comoros
        "TG",  # Togo
        "SL",  # Sierra Leone
        "MD",  # Moldova
        "VC",  # St Vincent and the Grenadines
    }

    return iso_code.upper() in foc_codes if iso_code else False
