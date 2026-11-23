"""Merge LNG terminal data from multiple sources into a single enriched CSV.

Sources:
1. Old enriched CSV from git HEAD (75 terminals with coordinates, water_depth,
   storage, capex, detailed sources, high confidence)
2. Seed collector Python module (119 terminals with names, types, capacities,
   operators -- but no coordinates)
3. COORD_LOOKUP (approximate coordinates for ~100 additional terminals from
   public industry sources)

Strategy:
- Start from the seed collector as the broadest base list (119 terminals)
- Enrich with old CSV data (coordinates, water_depth, storage, capex, sources)
- Add coordinate-only terminals from COORD_LOOKUP that aren't in the seed
- Add Lake Charles LNG if not present in any source
- Old CSV's enrichment columns always win when they have data
"""

from __future__ import annotations

import csv
import io
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# CSV column definitions
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "terminal_name",
    "country",
    "latitude",
    "longitude",
    "terminal_type",
    "function",
    "status",
    "capacity_mtpa",
    "year_commissioned",
    "operator",
    "owner",
    "water_depth_m",
    "storage_m3",
    "jetty_count",
    "capex_usd_million",
    "source",
    "source_url",
    "data_confidence",
]

# Columns whose values we prefer from the old (enriched) CSV when available
ENRICH_COLS = [
    "latitude",
    "longitude",
    "water_depth_m",
    "storage_m3",
    "jetty_count",
    "capex_usd_million",
    "source",
    "source_url",
    "data_confidence",
    "owner",
]

# ---------------------------------------------------------------------------
# Approximate coordinates for terminals from public industry sources
# ---------------------------------------------------------------------------

COORD_LOOKUP: dict[str, tuple[float, float]] = {
    # China
    "Tianjin LNG (CNOOC)": (39.10, 117.75),
    "Zhuhai Jinwan LNG": (22.10, 113.35),
    "Ningbo LNG": (29.70, 121.90),
    "Hainan Yangpu LNG": (19.75, 109.10),
    "Shenzhen Diefu LNG": (22.55, 114.55),
    "Yuedong Jieyang LNG": (23.35, 116.55),
    "Binhai LNG": (38.85, 117.60),
    "Fangchenggang LNG": (21.55, 108.35),
    "Zhangzhou LNG": (24.50, 117.85),
    "Dalian LNG": (38.90, 121.65),
    "Tangshan Caofeidian LNG": (39.25, 118.55),
    "Qingdao LNG": (36.05, 120.35),
    "Beihai Guangxi LNG": (21.45, 109.10),
    "Tianjin LNG (Sinopec)": (38.90, 117.70),
    "Wenzhou LNG": (27.95, 120.70),
    "Zhoushan LNG": (30.00, 122.10),
    "Qidong LNG": (31.80, 121.65),
    "Dongguan Hongmei LNG": (23.05, 113.70),
    "Tianjin Nangang LNG": (38.85, 117.55),
    "Chaozhou Huaying LNG": (23.65, 116.65),
    "Longkou Nanshan LNG": (37.65, 120.35),
    "Yantai LNG": (37.55, 121.40),
    "Shenzhen Yingde LNG": (22.55, 114.10),
    "Ningbo LNG Phase III": (29.70, 121.90),
    # Japan
    "Higashi-Ohgishima LNG": (35.47, 139.74),
    "Ohgishima LNG": (35.48, 139.74),
    "Kawagoe LNG": (35.00, 136.70),
    "Chita LNG": (34.95, 136.85),
    "Chita Kyodo LNG": (34.95, 136.85),
    "Chita Midorihama LNG": (34.95, 136.85),
    "Senboku I LNG": (34.50, 135.45),
    "Senboku II LNG": (34.50, 135.45),
    "Himeji Joint LNG": (34.75, 134.65),
    "Tobata LNG": (33.90, 130.80),
    "Hibiki LNG": (33.90, 130.80),
    "Higashi Niigata LNG": (37.95, 139.10),
    "Joetsu LNG": (37.15, 138.25),
    "Naoetsu LNG": (37.15, 138.25),
    "Yokkaichi LNG Center": (34.95, 136.65),
    "Yokkaichi Works LNG": (34.95, 136.65),
    "Hachinohe LNG": (40.50, 141.55),
    "Hatsukaichi LNG": (34.35, 132.30),
    "Ishikari LNG": (43.20, 141.30),
    "Hakodate LNG": (41.80, 140.75),
    "Shin-Sendai LNG": (38.30, 141.00),
    "Yanai LNG": (33.95, 132.10),
    "Oita LNG": (33.25, 131.70),
    "Mizushima LNG": (34.50, 133.75),
    "Sodeshi Shimizu LNG": (35.00, 138.50),
    "Soma LNG": (37.80, 141.00),
    "Fukuoka LNG": (33.60, 130.40),
    "Niihama LNG": (33.95, 133.30),
    "Nakagusuku LNG": (26.30, 127.80),
    # South Korea
    "Gwangyang LNG": (34.90, 127.70),
    "Boryeong LNG": (36.35, 126.55),
    # India
    "Hazira LNG Terminal": (21.10, 72.65),
    "Ennore LNG Terminal": (13.25, 80.33),
    "Mundra LNG Terminal": (22.75, 69.70),
    "Dhamra LNG Terminal": (20.95, 86.95),
    "Chhara LNG Terminal": (20.70, 71.15),
    "Jaigarh FSRU": (17.35, 73.20),
    "Jafrabad FSRU": (20.85, 71.40),
    # Vietnam
    "Thi Vai LNG Terminal": (10.50, 107.00),
    "Cai Mep LNG Terminal": (10.50, 107.05),
    # Philippines
    "FGEN Batangas FSRU": (13.75, 121.05),
    "Filipinas LNG Gateway FSRU": (13.75, 121.05),
    # Indonesia
    "Nusantara Regas Satu FSRU": (-5.90, 106.90),
    "Lampung FSRU": (-5.55, 105.30),
    "Arun LNG Regasification": (5.25, 97.05),
    "Benoa FSRU": (-8.75, 115.20),
    "Jawa Satu FSRU": (-6.00, 106.90),
    # Europe
    "Bilbao LNG": (43.33, -3.05),
    "Mugardos LNG": (43.47, -8.24),
    "Sagunto LNG": (39.65, -0.22),
    "Toscana FSRU (OLT)": (43.37, 10.13),
    "Ravenna FSRU": (44.38, 12.45),
    "Stade FSRU": (53.60, 9.50),
    "Marmara Ereglisi LNG": (40.97, 27.96),
    "Aliaga Etki FSRU": (38.80, 26.94),
    "Dortyol FSRU": (36.86, 36.17),
    "Gulf of Saros FSRU": (40.34, 26.62),
    "Inkoo FSRU": (60.04, 24.01),
    "Krk LNG FSRU": (45.20, 14.55),
    "Gate Terminal Rotterdam": (51.88, 4.03),
    "Alexandroupolis FSRU": (40.84, 25.88),
    # Americas
    "Everett LNG": (42.39, -71.05),
    "Lake Charles LNG": (30.17, -93.27),
    "Quintero LNG": (-32.77, -71.53),
    "Mejillones GNL": (-23.10, -70.41),
    "Cartagena FSRU": (10.36, -75.52),
    "Pecem FSRU": (-3.53, -38.79),
    "Sergipe FSRU": (-10.92, -37.04),
    "Porto do Acu FSRU": (-21.82, -41.00),
    "Sepetiba Bay FSRU": (-22.94, -43.80),
    "New Fortress Barcarena FSRU": (-1.51, -48.64),
    "Terminal Gas Sul FSRU": (-28.65, -49.37),
    "Costa Norte LNG": (9.36, -79.90),
    "Old Harbour FSRU": (17.94, -77.10),
    "AES Andres LNG": (18.44, -69.62),
    "EcoElectrica LNG": (17.97, -66.77),
}

# Country code to short name mapping for terminals from COORD_LOOKUP
# (used when creating new rows for terminals only in COORD_LOOKUP)
COORD_TERMINAL_META: dict[str, dict[str, str]] = {
    # China
    "Tianjin LNG (CNOOC)": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Zhuhai Jinwan LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Ningbo LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Hainan Yangpu LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Shenzhen Diefu LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Yuedong Jieyang LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Binhai LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Sinopec"},
    "Fangchenggang LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Sinopec"},
    "Zhangzhou LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "CNOOC"},
    "Dalian LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "PetroChina"},
    "Tangshan Caofeidian LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "PetroChina"},
    "Qingdao LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Sinopec"},
    "Beihai Guangxi LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "Sinopec"},
    "Tianjin LNG (Sinopec)": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Sinopec"},
    "Wenzhou LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "ENN Energy"},
    "Zhoushan LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "ENN Energy"},
    "Qidong LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Guanghui Energy"},
    "Dongguan Hongmei LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Jiuhe Energy"},
    "Tianjin Nangang LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "CNOOC"},
    "Chaozhou Huaying LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "China Gas"},
    "Longkou Nanshan LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "Nanshan Group"},
    "Yantai LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "CNOOC"},
    "Shenzhen Yingde LNG": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "Yingde Gases"},
    "Ningbo LNG Phase III": {"country": "China", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "CNOOC"},
    # Japan
    "Higashi-Ohgishima LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "TEPCO"},
    "Ohgishima LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Tokyo Gas"},
    "Kawagoe LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Chubu Electric"},
    "Chita LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Chubu Electric"},
    "Chita Kyodo LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Toho Gas"},
    "Chita Midorihama LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Chubu Electric"},
    "Senboku I LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Osaka Gas"},
    "Senboku II LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Osaka Gas"},
    "Himeji Joint LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Kansai Electric"},
    "Tobata LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Kyushu Electric"},
    "Hibiki LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Saibu Gas"},
    "Higashi Niigata LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Nihonkai LNG"},
    "Joetsu LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "INPEX"},
    "Naoetsu LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Nihonkai LNG"},
    "Yokkaichi LNG Center": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Cosmo Energy"},
    "Yokkaichi Works LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Chubu Electric"},
    "Hachinohe LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "JFE Engineering"},
    "Hatsukaichi LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Hiroshima Gas"},
    "Ishikari LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Hokkaido Gas"},
    "Hakodate LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Hokkaido Gas"},
    "Shin-Sendai LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Tohoku Electric"},
    "Yanai LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Chugoku Electric"},
    "Oita LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Kyushu Electric"},
    "Mizushima LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Mizushima LNG"},
    "Sodeshi Shimizu LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Shizuoka Gas"},
    "Soma LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Soma LNG"},
    "Fukuoka LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Saibu Gas"},
    "Niihama LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Shikoku Electric"},
    "Nakagusuku LNG": {"country": "Japan", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Okinawa Electric"},
    # South Korea
    "Gwangyang LNG": {"country": "South Korea", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "KOGAS"},
    "Boryeong LNG": {"country": "South Korea", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "KOGAS"},
    # India
    "Hazira LNG Terminal": {"country": "India", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Shell"},
    "Ennore LNG Terminal": {"country": "India", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Indian Oil"},
    "Mundra LNG Terminal": {"country": "India", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "GSPC"},
    "Dhamra LNG Terminal": {"country": "India", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Adani"},
    "Chhara LNG Terminal": {"country": "India", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "H-Energy"},
    "Jaigarh FSRU": {"country": "India", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "H-Energy"},
    "Jafrabad FSRU": {"country": "India", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Swan Energy"},
    # Vietnam
    "Thi Vai LNG Terminal": {"country": "Vietnam", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "PV Gas"},
    "Cai Mep LNG Terminal": {"country": "Vietnam", "terminal_type": "onshore_import", "function": "import", "status": "under_construction", "operator": "T&T Group"},
    # Philippines
    "FGEN Batangas FSRU": {"country": "Philippines", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "First Gen"},
    "Filipinas LNG Gateway FSRU": {"country": "Philippines", "terminal_type": "fsru", "function": "import", "status": "planned", "operator": "AG&P"},
    # Indonesia
    "Nusantara Regas Satu FSRU": {"country": "Indonesia", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Nusantara Regas"},
    "Lampung FSRU": {"country": "Indonesia", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "PGN"},
    "Arun LNG Regasification": {"country": "Indonesia", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Pertamina"},
    "Benoa FSRU": {"country": "Indonesia", "terminal_type": "fsru", "function": "import", "status": "planned", "operator": "Pertamina"},
    "Jawa Satu FSRU": {"country": "Indonesia", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Pertamina"},
    # Europe
    "Bilbao LNG": {"country": "Spain", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Enagas"},
    "Mugardos LNG": {"country": "Spain", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Reganosa"},
    "Sagunto LNG": {"country": "Spain", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Enagas"},
    "Toscana FSRU (OLT)": {"country": "Italy", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "OLT Offshore"},
    "Ravenna FSRU": {"country": "Italy", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Snam"},
    "Stade FSRU": {"country": "Germany", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Hanseatic Energy Hub"},
    "Marmara Ereglisi LNG": {"country": "Turkey", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "BOTAS"},
    "Aliaga Etki FSRU": {"country": "Turkey", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Etki Liman"},
    "Dortyol FSRU": {"country": "Turkey", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "BOTAS"},
    "Gulf of Saros FSRU": {"country": "Turkey", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "BOTAS"},
    "Inkoo FSRU": {"country": "Finland", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Gasgrid Finland"},
    "Krk LNG FSRU": {"country": "Croatia", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "LNG Croatia"},
    "Gate Terminal Rotterdam": {"country": "Netherlands", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Gate terminal"},
    "Alexandroupolis FSRU": {"country": "Greece", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Gastrade"},
    # Americas
    "Everett LNG": {"country": "USA", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "Constellation Energy"},
    "Lake Charles LNG": {"country": "USA", "terminal_type": "onshore_import", "function": "bidirectional", "status": "mothballed", "operator": "Energy Transfer", "capacity_mtpa": "22.1", "year_commissioned": "1982"},
    "Quintero LNG": {"country": "Chile", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "GNL Quintero"},
    "Mejillones GNL": {"country": "Chile", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "GNL Mejillones"},
    "Cartagena FSRU": {"country": "Colombia", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "SPEC"},
    "Pecem FSRU": {"country": "Brazil", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Petrobras"},
    "Sergipe FSRU": {"country": "Brazil", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "CELSE"},
    "Porto do Acu FSRU": {"country": "Brazil", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "Prumo Logistica"},
    "Sepetiba Bay FSRU": {"country": "Brazil", "terminal_type": "fsru", "function": "import", "status": "planned", "operator": "Petrobras"},
    "New Fortress Barcarena FSRU": {"country": "Brazil", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "New Fortress Energy"},
    "Terminal Gas Sul FSRU": {"country": "Brazil", "terminal_type": "fsru", "function": "import", "status": "planned", "operator": "Petrobras"},
    "Costa Norte LNG": {"country": "Panama", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "AES"},
    "Old Harbour FSRU": {"country": "Jamaica", "terminal_type": "fsru", "function": "import", "status": "operational", "operator": "New Fortress Energy"},
    "AES Andres LNG": {"country": "Dominican Republic", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "AES"},
    "EcoElectrica LNG": {"country": "Puerto Rico", "terminal_type": "onshore_import", "function": "import", "status": "operational", "operator": "EcoElectrica"},
}


# ---------------------------------------------------------------------------
# Enum-to-CSV value mapping for seed collector records
# ---------------------------------------------------------------------------

def _enum_val(v: Any) -> str:
    """Convert enum or raw value to string for CSV."""
    if hasattr(v, "value"):
        return str(v.value)
    return str(v) if v is not None else ""


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_old_csv() -> list[dict[str, str]]:
    """Load the enriched CSV from git HEAD."""
    result = subprocess.run(
        ["git", "show", "HEAD:data/modules/lng_terminals/curated/terminals_seed.csv"],
        capture_output=True,
        text=True,
        check=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    return list(reader)


def load_seed_terminals() -> list[dict[str, str]]:
    """Load terminals from the seed_collector Python module and convert to CSV-format dicts."""
    # Import here to avoid module-level dependency on the project's src
    from worldenergydata.lng_terminals.collectors.seed_collector import _SEED_TERMINALS

    rows: list[dict[str, str]] = []
    for rec in _SEED_TERMINALS:
        row: dict[str, str] = {}
        row["terminal_name"] = rec.get("terminal_name", "")
        row["country"] = rec.get("country", "")
        row["latitude"] = ""
        row["longitude"] = ""
        row["terminal_type"] = _enum_val(rec.get("terminal_type", ""))
        row["function"] = _enum_val(rec.get("function", ""))
        row["status"] = _enum_val(rec.get("status", ""))
        row["capacity_mtpa"] = str(rec["capacity_mtpa"]) if rec.get("capacity_mtpa") else ""
        row["year_commissioned"] = str(rec["year_commissioned"]) if rec.get("year_commissioned") else ""
        row["operator"] = rec.get("operator", "")
        row["owner"] = ""
        row["water_depth_m"] = ""
        row["storage_m3"] = ""
        row["jetty_count"] = ""
        row["capex_usd_million"] = ""
        row["source"] = "IGU/GIIGNL/Operator disclosures"
        row["source_url"] = ""
        row["data_confidence"] = "medium"
        rows.append(row)
    return rows


def build_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Build case-insensitive lookup by terminal_name."""
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row["terminal_name"].strip().lower()
        lookup[key] = row
    return lookup


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def merge(
    old_rows: list[dict[str, str]],
    seed_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Merge all sources into a single deduplicated terminal list.

    Priority: old CSV enrichment > seed collector data > COORD_LOOKUP metadata.
    """
    old_lookup = build_lookup(old_rows)
    all_keys: set[str] = set()
    merged: list[dict[str, str]] = []

    # --- Pass 1: Start with seed collector terminals, enrich from old CSV ---
    for row in seed_rows:
        key = row["terminal_name"].strip().lower()
        all_keys.add(key)
        old_row = old_lookup.get(key)

        if old_row:
            # Overlay enrichment columns from old CSV -- old CSV wins
            for col in ENRICH_COLS:
                old_val = old_row.get(col, "").strip()
                if old_val:
                    row[col] = old_val

        # If still no coords, try COORD_LOOKUP
        name = row["terminal_name"].strip()
        if not row.get("latitude", "").strip() and name in COORD_LOOKUP:
            lat, lon = COORD_LOOKUP[name]
            row["latitude"] = str(lat)
            row["longitude"] = str(lon)

        merged.append(row)

    # --- Pass 2: Carry forward old-only terminals not in seed ---
    for row in old_rows:
        key = row["terminal_name"].strip().lower()
        if key not in all_keys:
            all_keys.add(key)
            merged.append(row)

    # --- Pass 3: Add COORD_LOOKUP-only terminals not in seed or old ---
    for name, (lat, lon) in COORD_LOOKUP.items():
        key = name.strip().lower()
        if key not in all_keys:
            all_keys.add(key)
            meta = COORD_TERMINAL_META.get(name, {})
            row = {
                "terminal_name": name,
                "country": meta.get("country", ""),
                "latitude": str(lat),
                "longitude": str(lon),
                "terminal_type": meta.get("terminal_type", ""),
                "function": meta.get("function", ""),
                "status": meta.get("status", ""),
                "capacity_mtpa": meta.get("capacity_mtpa", ""),
                "year_commissioned": meta.get("year_commissioned", ""),
                "operator": meta.get("operator", ""),
                "owner": "",
                "water_depth_m": "",
                "storage_m3": "",
                "jetty_count": "",
                "capex_usd_million": "",
                "source": "IGU/GIIGNL/Operator disclosures",
                "source_url": "",
                "data_confidence": "low",
            }
            merged.append(row)

    return merged


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    """Write merged rows to CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def report(rows: list[dict[str, str]]) -> None:
    """Print summary statistics."""
    total = len(rows)
    with_coords = sum(
        1 for r in rows
        if r.get("latitude", "").strip() and r.get("longitude", "").strip()
    )
    without_coords = total - with_coords
    us_terminals = [r for r in rows if r.get("country", "").strip() == "USA"]
    high_conf = sum(1 for r in rows if r.get("data_confidence", "").strip() == "high")
    medium_conf = sum(1 for r in rows if r.get("data_confidence", "").strip() == "medium")
    low_conf = sum(1 for r in rows if r.get("data_confidence", "").strip() == "low")

    print(f"\n{'='*60}")
    print("  Merge Summary")
    print(f"{'='*60}")
    print(f"  Total terminals:          {total}")
    print(f"  With coordinates:         {with_coords}")
    print(f"  Without coordinates:      {without_coords}")
    print(f"  US terminals:             {len(us_terminals)}")
    print(f"  Confidence: high={high_conf}  medium={medium_conf}  low={low_conf}")
    print(f"{'='*60}")

    print("\n  US Terminals:")
    for r in sorted(us_terminals, key=lambda x: x["terminal_name"]):
        lat = r.get("latitude", "") or "?"
        lon = r.get("longitude", "") or "?"
        print(f"    {r['terminal_name']:<45} ({lat}, {lon})")

    # Country distribution
    countries: dict[str, int] = {}
    for r in rows:
        c = r.get("country", "Unknown").strip() or "Unknown"
        countries[c] = countries.get(c, 0) + 1
    print("\n  Country distribution (top 15):")
    for c, n in sorted(countries.items(), key=lambda x: -x[1])[:15]:
        print(f"    {c:<30} {n:>4}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    csv_path = Path("data/modules/lng_terminals/curated/terminals_seed.csv")

    print("Loading old enriched CSV from git HEAD...")
    old_rows = load_old_csv()
    print(f"  Old CSV: {len(old_rows)} terminals (with enrichment data)")

    print("Loading seed collector terminals...")
    seed_rows = load_seed_terminals()
    print(f"  Seed collector: {len(seed_rows)} terminals")

    print(f"  COORD_LOOKUP: {len(COORD_LOOKUP)} terminals with coordinates")

    print("Merging all sources...")
    merged = merge(old_rows, seed_rows)

    print(f"Writing {len(merged)} terminals to {csv_path}...")
    write_csv(merged, csv_path)

    report(merged)

    # --- Validation ---
    total = len(merged)
    assert total >= 219, f"Expected >= 219 terminals, got {total}"

    lake = [r for r in merged if "lake charles" in r["terminal_name"].lower()]
    assert len(lake) == 1, f"Expected exactly 1 Lake Charles LNG, got {len(lake)}"
    assert lake[0]["latitude"], "Lake Charles LNG must have latitude"
    assert lake[0]["longitude"], "Lake Charles LNG must have longitude"

    with_coords = sum(
        1 for r in merged
        if r.get("latitude", "").strip() and r.get("longitude", "").strip()
    )
    print(f"  Terminals with coordinates: {with_coords} / {total}")

    us_count = sum(1 for r in merged if r.get("country", "").strip() == "USA")
    assert us_count >= 15, f"Expected >= 15 US terminals, got {us_count}"
    print(f"  US terminal count: {us_count}")

    print("\nAll validations passed.")


if __name__ == "__main__":
    main()
