#!/usr/bin/env python3
"""Expand LNG terminal seed CSV with researched terminals."""
import csv
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from worldenergydata.lng_terminals.collectors.seed_collector import _SEED_TERMINALS
from worldenergydata.lng_terminals.constants import (
    TerminalType, TerminalFunction, TerminalStatus, Region
)

CSV_PATH = Path(__file__).parent.parent / "data/modules/lng_terminals/curated/terminals_seed.csv"

COLUMNS = [
    "terminal_name", "country", "latitude", "longitude", "terminal_type",
    "function", "status", "capacity_mtpa", "year_commissioned", "operator",
    "owner", "water_depth_m", "storage_m3", "jetty_count", "capex_usd_million",
    "source", "source_url", "data_confidence"
]

def enum_val(v):
    """Convert enum to its value string, or return as-is."""
    return v.value if hasattr(v, 'value') else v

def seed_to_row(d):
    """Convert a seed dict to a CSV row dict."""
    return {
        "terminal_name": d.get("terminal_name", ""),
        "country": d.get("country", ""),
        "latitude": d.get("latitude", ""),
        "longitude": d.get("longitude", ""),
        "terminal_type": enum_val(d.get("terminal_type", "")),
        "function": enum_val(d.get("function", "")),
        "status": enum_val(d.get("status", "")),
        "capacity_mtpa": d.get("capacity_mtpa", ""),
        "year_commissioned": d.get("year_commissioned", ""),
        "operator": d.get("operator", ""),
        "owner": d.get("owner", ""),
        "water_depth_m": d.get("water_depth_m", ""),
        "storage_m3": d.get("storage_m3", ""),
        "jetty_count": d.get("jetty_count", ""),
        "capex_usd_million": d.get("capex_usd_million", ""),
        "source": d.get("source", "IGU/GIIGNL/Operator disclosures"),
        "source_url": d.get("source_url", ""),
        "data_confidence": d.get("data_confidence", "medium"),
    }

# Start with existing seed terminals
all_terminals = [seed_to_row(d) for d in _SEED_TERMINALS]

# Track names to avoid duplicates
seen = {r["terminal_name"].lower().strip() for r in all_terminals}

def add(name, country, ttype, func, status, capacity, operator, year=None,
        region=None, owner=None, lat=None, lon=None, storage=None,
        source="Global Energy Monitor/GIIGNL/Operator disclosures", confidence="medium"):
    """Add a terminal if not already present."""
    key = name.lower().strip()
    if key in seen:
        return
    seen.add(key)
    all_terminals.append({
        "terminal_name": name,
        "country": country,
        "latitude": lat or "",
        "longitude": lon or "",
        "terminal_type": ttype,
        "function": func,
        "status": status,
        "capacity_mtpa": capacity or "",
        "year_commissioned": year or "",
        "operator": operator or "",
        "owner": owner or "",
        "water_depth_m": "",
        "storage_m3": storage or "",
        "jetty_count": "",
        "capex_usd_million": "",
        "source": source,
        "source_url": "",
        "data_confidence": confidence,
    })

# =====================================================================
# CHINA -- additional terminals (24 new)
# =====================================================================
add("Tianjin LNG (CNOOC)", "CHN", "onshore_import", "import", "operational", 14.2, "CNOOC", 2013)
add("Zhuhai Jinwan LNG", "CHN", "onshore_import", "import", "operational", 7.0, "CNOOC", 2013)
add("Ningbo LNG", "CHN", "onshore_import", "import", "operational", 6.0, "CNOOC", 2012)
add("Hainan Yangpu LNG", "CHN", "onshore_import", "import", "operational", 3.0, "CNOOC", 2014)
add("Shenzhen Diefu LNG", "CHN", "onshore_import", "import", "operational", 4.0, "CNOOC", 2018)
add("Yuedong Jieyang LNG", "CHN", "onshore_import", "import", "operational", 2.0, "CNOOC", 2017)
add("Binhai LNG", "CHN", "onshore_import", "import", "operational", 5.4, "CNOOC", 2023)
add("Fangchenggang LNG", "CHN", "onshore_import", "import", "operational", 0.6, "CNOOC", 2019)
add("Zhangzhou LNG", "CHN", "onshore_import", "import", "operational", 3.0, "PipeChina", 2024)
add("Dalian LNG", "CHN", "onshore_import", "import", "operational", 10.0, "PetroChina", 2011)
add("Tangshan Caofeidian LNG", "CHN", "onshore_import", "import", "operational", 10.0, "PetroChina", 2013)
add("Qingdao LNG", "CHN", "onshore_import", "import", "operational", 11.0, "Sinopec", 2014)
add("Beihai Guangxi LNG", "CHN", "onshore_import", "import", "operational", 6.0, "Sinopec", 2016)
add("Tianjin LNG (Sinopec)", "CHN", "onshore_import", "import", "operational", 11.65, "Sinopec", 2018)
add("Wenzhou LNG", "CHN", "onshore_import", "import", "operational", 3.0, "Zhejiang Energy", 2023)
add("Zhoushan LNG", "CHN", "onshore_import", "import", "operational", 5.0, "ENN", 2018)
add("Qidong LNG", "CHN", "onshore_import", "import", "operational", 3.0, "Guanghui Energy", 2017)
add("Dongguan Hongmei LNG", "CHN", "onshore_import", "import", "operational", 1.5, "JOVO Group", 2012)
add("Tianjin Nangang LNG", "CHN", "onshore_import", "import", "operational", 5.0, "Beijing Gas Group", 2023)
add("Chaozhou Huaying LNG", "CHN", "onshore_import", "import", "operational", 6.0, "Huaying Gas / Sinopec", 2024)
add("Longkou Nanshan LNG", "CHN", "onshore_import", "import", "under_construction", 5.0, "PipeChina")
add("Yantai LNG", "CHN", "onshore_import", "import", "under_construction", 5.9, "GCL-Poly Energy")
add("Shenzhen Yingde LNG", "CHN", "onshore_import", "import", "under_construction", 3.0, "PipeChina")
add("Ningbo LNG Phase III", "CHN", "onshore_import", "import", "under_construction", 6.0, "CNOOC")

# =====================================================================
# JAPAN -- additional terminals (33 new)
# =====================================================================
add("Higashi-Ohgishima LNG", "JPN", "onshore_import", "import", "operational", 13.2, "JERA", 1984)
add("Ohgishima LNG", "JPN", "onshore_import", "import", "operational", 10.2, "Tokyo Gas", 1998)
add("Kawagoe LNG", "JPN", "onshore_import", "import", "operational", 8.7, "JERA", 1997)
add("Chita LNG", "JPN", "onshore_import", "import", "operational", 10.9, "JERA / Toho Gas", 1977)
add("Chita Kyodo LNG", "JPN", "onshore_import", "import", "operational", 7.5, "JERA / Toho Gas", 1977)
add("Chita Midorihama LNG", "JPN", "onshore_import", "import", "operational", 7.7, "Toho Gas", 2001)
add("Senboku I LNG", "JPN", "onshore_import", "import", "operational", 1.9, "Osaka Gas", 1972)
add("Senboku II LNG", "JPN", "onshore_import", "import", "operational", 9.9, "Osaka Gas", 1977)
add("Himeji Joint LNG", "JPN", "onshore_import", "import", "operational", 8.1, "Kansai Electric", 1979)
add("Tobata LNG", "JPN", "onshore_import", "import", "operational", 7.6, "Nippon Steel / Kyushu Electric", 1977)
add("Hibiki LNG", "JPN", "onshore_import", "import", "operational", 2.4, "Saibu Gas / Kyushu Electric", 2014)
add("Higashi Niigata LNG", "JPN", "onshore_import", "import", "operational", 8.9, "Nihonkai LNG / Tohoku Electric", 1984)
add("Joetsu LNG", "JPN", "onshore_import", "import", "operational", 3.2, "JERA", 2013)
add("Naoetsu LNG", "JPN", "onshore_import", "import", "operational", 2.1, "INPEX", 2013)
add("Yokkaichi LNG Center", "JPN", "onshore_import", "import", "operational", 6.4, "JERA", 1987)
add("Yokkaichi Works LNG", "JPN", "onshore_import", "import", "operational", 2.2, "Toho Gas", 1991)
add("Hachinohe LNG", "JPN", "onshore_import", "import", "operational", 1.5, "ENEOS", 2015)
add("Hatsukaichi LNG", "JPN", "onshore_import", "import", "operational", 0.9, "Hiroshima Gas", 1996)
add("Ishikari LNG", "JPN", "onshore_import", "import", "operational", 4.6, "Hokkaido Gas", 2012)
add("Hakodate LNG", "JPN", "onshore_import", "import", "operational", 0.2, "Hokkaido Gas", 2006)
add("Shin-Sendai LNG", "JPN", "onshore_import", "import", "operational", 1.7, "Tohoku Electric", 2015)
add("Yanai LNG", "JPN", "onshore_import", "import", "operational", 2.3, "Chugoku Electric", 1990)
add("Oita LNG", "JPN", "onshore_import", "import", "operational", 5.4, "Oita LNG", 1990)
add("Mizushima LNG", "JPN", "onshore_import", "import", "operational", 4.3, "ENEOS", 2006)
add("Sodeshi Shimizu LNG", "JPN", "onshore_import", "import", "operational", 2.9, "Shizuoka Gas / ENEOS", 1996)
add("Soma LNG", "JPN", "onshore_import", "import", "operational", 1.5, "JAPEX", 2018)
add("Fukuoka LNG", "JPN", "onshore_import", "import", "operational", 0.65, "Saibu Gas", 1993)
add("Niihama LNG", "JPN", "onshore_import", "import", "operational", 1.0, "Niihama LNG", 2022)
add("Nakagusuku LNG", "JPN", "onshore_import", "import", "operational", 9.0, "Okinawa Electric", 2013)

# =====================================================================
# SOUTH KOREA -- additional terminals (2 new)
# =====================================================================
add("Gwangyang LNG", "KOR", "onshore_import", "import", "operational", 7.1, "POSCO International", 2005)
add("Boryeong LNG", "KOR", "onshore_import", "import", "operational", 10.8, "SK E&S / GS Energy", 2017)

# =====================================================================
# INDIA -- additional terminals (7 new)
# =====================================================================
add("Hazira LNG Terminal", "IND", "onshore_import", "import", "operational", 5.0, "Shell Energy India", 2005)
add("Ennore LNG Terminal", "IND", "onshore_import", "import", "operational", 5.0, "Indian Oil Corporation", 2019)
add("Mundra LNG Terminal", "IND", "onshore_import", "import", "operational", 5.0, "GSPC LNG", 2020)
add("Dhamra LNG Terminal", "IND", "onshore_import", "import", "operational", 5.0, "Dhamra LNG Terminal Pvt Ltd", 2023)
add("Chhara LNG Terminal", "IND", "onshore_import", "import", "operational", 5.0, "HPCL LNG Limited", 2025)
add("Jaigarh FSRU", "IND", "fsru", "import", "under_construction", 4.0, "H-Energy")
add("Jafrabad FSRU", "IND", "fsru", "import", "under_construction", 5.0, "Swan LNG")

# =====================================================================
# SOUTHEAST ASIA -- additional terminals (12 new)
# =====================================================================
add("Thi Vai LNG Terminal", "VNM", "onshore_import", "import", "operational", 1.0, "PV Gas", 2023)
add("Cai Mep LNG Terminal", "VNM", "onshore_import", "import", "operational", 3.0, "Hai Linh / AG&P LNG", 2025)
add("FGEN Batangas FSRU", "PHL", "fsru", "import", "operational", 5.26, "FGEN LNG Corp", 2024)
add("Filipinas LNG Gateway FSRU", "PHL", "fsru", "import", "under_construction", 4.4, "Excelerate Energy")
add("Nusantara Regas Satu FSRU", "IDN", "fsru", "import", "operational", 3.0, "PT Nusantara Regas", 2012)
add("Lampung FSRU", "IDN", "fsru", "import", "operational", 1.8, "PGN LNG Indonesia", 2014)
add("Arun LNG Regasification", "IDN", "onshore_import", "import", "operational", 3.0, "PT Perta Arun Gas", 2015)
add("Benoa FSRU", "IDN", "fsru", "import", "operational", 0.3, "Pelindo Energi Logistik", 2016)
add("Jawa Satu FSRU", "IDN", "fsru", "import", "operational", 2.4, "PT Jawa Satu Regas", 2024)

# =====================================================================
# EUROPE -- additional terminals (17 new)
# =====================================================================
add("Bilbao LNG", "ESP", "onshore_import", "import", "operational", 7.0, "BBG (Enagas / Basque Govt)", 2003)
add("Mugardos LNG", "ESP", "onshore_import", "import", "operational", 2.6, "Reganosa", 2007)
add("Sagunto LNG", "ESP", "onshore_import", "import", "operational", 8.8, "Saggas (Enagas / Union Fenosa)", 2006)
add("Toscana FSRU (OLT)", "ITA", "fsru", "import", "operational", 3.7, "OLT Offshore LNG Toscana", 2013)
add("Ravenna FSRU", "ITA", "fsru", "import", "operational", 5.0, "Snam", 2025)
add("Stade FSRU", "DEU", "fsru", "import", "under_construction", 5.0, "Deutsche Energy Terminal")
add("Marmara Ereglisi LNG", "TUR", "onshore_import", "import", "operational", 9.9, "BOTAS", 1994)
add("Aliaga Etki FSRU", "TUR", "fsru", "import", "operational", 5.7, "Etki / Pardus Energy", 2016)
add("Dortyol FSRU", "TUR", "fsru", "import", "operational", 7.5, "BOTAS", 2018)
add("Gulf of Saros FSRU", "TUR", "fsru", "import", "operational", 5.0, "BOTAS", 2023)
add("Inkoo FSRU", "FIN", "fsru", "import", "operational", 3.7, "Gasgrid Finland", 2023)
add("Krk LNG FSRU", "HRV", "fsru", "import", "operational", 4.5, "LNG Croatia", 2021)
add("Gate Terminal Rotterdam", "NLD", "onshore_import", "import", "operational", 8.8, "Gasunie / Vopak", 2011)
add("Alexandroupolis FSRU", "GRC", "fsru", "import", "operational", 4.1, "Gastrade", 2024)
add("Everett LNG", "USA", "onshore_import", "import", "operational", 5.4, "Constellation Energy", 1971)

# =====================================================================
# AMERICAS -- additional terminals (13 new)
# =====================================================================
add("Quintero LNG", "CHL", "onshore_import", "import", "operational", 4.0, "GNL Quintero (EIG / Fluxys)", 2009)
add("Mejillones GNL", "CHL", "onshore_import", "import", "operational", 1.5, "GNL Mejillones (Engie / Codelco)", 2010)
add("Cartagena FSRU", "COL", "fsru", "import", "operational", 3.0, "SPEC LNG (Promigas / Vopak)", 2016)
add("Pecem FSRU", "BRA", "fsru", "import", "operational", 1.9, "Petrobras", 2008)
add("Sergipe FSRU", "BRA", "fsru", "import", "operational", 5.6, "CELSE", 2020)
add("Porto do Acu FSRU", "BRA", "fsru", "import", "operational", 5.6, "GNA (Prumo / Siemens / BP)", 2021)
add("Sepetiba Bay FSRU", "BRA", "fsru", "import", "operational", 2.7, "New Fortress Energy", 2022)
add("New Fortress Barcarena FSRU", "BRA", "fsru", "import", "operational", 4.4, "New Fortress Energy", 2024)
add("Terminal Gas Sul FSRU", "BRA", "fsru", "import", "operational", 4.4, "New Fortress Energy", 2024)
add("Costa Norte LNG", "PAN", "onshore_import", "import", "operational", 1.5, "AES", 2018)
add("Old Harbour FSRU", "JAM", "fsru", "import", "operational", 3.6, "Excelerate Energy", 2018)
add("AES Andres LNG", "DOM", "onshore_import", "import", "operational", 1.7, "AES Dominicana", 2003)
add("EcoElectrica LNG", "PRI", "onshore_import", "import", "operational", 2.1, "EcoElectrica (New Fortress Energy)", 2000)


# Write CSV
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(all_terminals)

print(f"Wrote {len(all_terminals)} terminals to {CSV_PATH}")

# Print summary stats
countries = set(r["country"] for r in all_terminals)
types = {}
statuses = {}
for r in all_terminals:
    t = r.get("terminal_type", "unknown")
    types[t] = types.get(t, 0) + 1
    s = r.get("status", "unknown")
    statuses[s] = statuses.get(s, 0) + 1
print(f"Countries: {len(countries)}")
print(f"Types: {types}")
print(f"Statuses: {statuses}")
