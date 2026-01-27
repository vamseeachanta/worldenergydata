"""Database operations for wellpath data.

This module provides functions for initializing and managing SQLite
databases used for storing well, survey, and stratigraphy data.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

import pandas as pd

# Database file extension
BASE_EXT: str = ".db"


def first_start(wellnames_given: list[str] | None = None) -> list[str]:
    """Initialize wellnames database on first start.

    Creates the wellnames.db file if it doesn't exist, or loads
    existing well names from the database.

    Args:
        wellnames_given: Optional list to populate with existing well names.

    Returns:
        List of existing well names from the database.
    """
    if wellnames_given is None:
        wellnames_given = []

    print("first start")
    if not os.path.exists("wellnames.db"):
        con: sqlite3.Connection = sqlite3.connect("wellnames.db")
        cursor: sqlite3.Cursor = con.cursor()
        sql: str = (
            "CREATE TABLE wells("
            "name TEXT, "
            "latitude REAL, "
            "longitude REAL,"
            "altitude REAL)"
        )
        cursor.execute(sql)
        con.close()
    else:
        print("file wellnames.db already exists", " load wells from database...")
        con = sqlite3.connect("wellnames.db")
        cursor = con.cursor()
        sql = "SELECT * FROM wells"
        cursor.execute(sql)
        for dsatz in cursor:
            wellnames_given.append(dsatz[0])
        con.close()

    return wellnames_given


def load_all_wells() -> list[tuple[Any, ...]]:
    """Load all wells from the wellnames database.

    Returns:
        List of tuples containing (name, latitude, longitude, altitude).
    """
    connection: sqlite3.Connection = sqlite3.connect("wellnames.db")
    cursor: sqlite3.Cursor = connection.cursor()
    sql: str = "SELECT * FROM wells"
    cursor.execute(sql)
    wells = cursor.fetchall()
    connection.close()
    return wells


def load_well_names() -> list[tuple[str, ...]]:
    """Load just the well names from the database.

    Returns:
        List of tuples containing well names.
    """
    wellnamelist: list[tuple[str, ...]] = []
    mapcon: sqlite3.Connection = sqlite3.connect("wellnames.db")
    cursor: sqlite3.Cursor = mapcon.cursor()
    msql: str = "SELECT Name FROM wells"
    cursor.execute(msql)
    for wn in cursor:
        wellnamelist.append(wn)
    mapcon.close()
    return wellnamelist


def delete_well(well_name: str) -> None:
    """Delete a well from the database.

    Args:
        well_name: Name of the well to delete.
    """
    z: str = "'"
    abc: str = z + well_name + z

    delcon: sqlite3.Connection = sqlite3.connect("wellnames.db")
    cursor: sqlite3.Cursor = delcon.cursor()
    sqldel: str = "DELETE FROM wells WHERE Name = " + abc + ""
    cursor.execute(sqldel)
    delcon.commit()
    delcon.close()

    # Remove the well database file
    if os.path.exists(well_name + BASE_EXT):
        os.remove(well_name + BASE_EXT)


def get_well_surface_data(well_name: str) -> tuple[float, float, float]:
    """Get surface location data for a well.

    Args:
        well_name: Name of the well.

    Returns:
        Tuple of (altitude, latitude, longitude).
    """
    z: str = "'"
    cwell: str = z + str(well_name) + z

    gcon: sqlite3.Connection = sqlite3.connect("wellnames.db")
    cursor: sqlite3.Cursor = gcon.cursor()

    sqla: str = "SELECT altitude FROM wells WHERE name = " + cwell + ""
    cursor.execute(sqla)
    z_surface: float = 0.0
    for c in cursor:
        z_surface = c[0]

    sqllat: str = "SELECT latitude FROM wells WHERE name = " + cwell + ""
    cursor.execute(sqllat)
    lat_surface: float = 0.0
    for lat in cursor:
        lat_surface = lat[0]

    sqllon: str = "SELECT longitude FROM wells WHERE name = " + cwell + ""
    cursor.execute(sqllon)
    lon_surface: float = 0.0
    for lon in cursor:
        lon_surface = lon[0]

    gcon.close()
    return z_surface, lat_surface, lon_surface


def load_survey_data(well_name: str) -> list[tuple[Any, ...]]:
    """Load survey data for a well.

    Args:
        well_name: Name of the well.

    Returns:
        List of survey data tuples.
    """
    connection: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = connection.cursor()
    sql: str = "SELECT * FROM geosurvey"
    cursor.execute(sql)
    data = cursor.fetchall()
    connection.close()
    return data


def load_survey_dataframe(well_name: str) -> pd.DataFrame:
    """Load survey data as a pandas DataFrame.

    Args:
        well_name: Name of the well.

    Returns:
        DataFrame with survey data.
    """
    con: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    panda = pd.read_sql_query("SELECT * FROM geosurvey", con)
    con.close()
    return panda


def load_stratigraphy_dataframe(well_name: str) -> pd.DataFrame:
    """Load stratigraphy data as a pandas DataFrame.

    Args:
        well_name: Name of the well.

    Returns:
        DataFrame with stratigraphy data.
    """
    constr: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    panstrat = pd.read_sql_query("SELECT * FROM stratigraphy", constr)
    constr.close()
    return panstrat


def write_survey_point(
    well_name: str,
    depth: float,
    inc: float,
    azi: float,
    tvd: float,
    north: float,
    east: float,
    closure: float,
    dls: float,
) -> None:
    """Write a survey point to the database.

    Args:
        well_name: Name of the well.
        depth: Measured depth.
        inc: Inclination.
        azi: Azimuth.
        tvd: True vertical depth.
        north: Northing.
        east: Easting.
        closure: Closure distance.
        dls: Dogleg severity.
    """
    con: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = con.cursor()
    sql_insert: str = (
        "INSERT INTO geosurvey VALUES("
        + str(depth)
        + ","
        + str(inc)
        + ","
        + str(azi)
        + ","
        + str(tvd)
        + ","
        + str(north)
        + ","
        + str(east)
        + ","
        + str(closure)
        + ","
        + str(dls)
        + ")"
    )
    cursor.execute(sql_insert)
    con.commit()
    con.close()


def write_wellmap_point(
    well_name: str, geotvd: float, latitude: float, longitude: float
) -> None:
    """Write a wellmap point to the database.

    Args:
        well_name: Name of the well.
        geotvd: Geographic TVD (altitude).
        latitude: Latitude.
        longitude: Longitude.
    """
    bcon: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = bcon.cursor()
    bsql: str = (
        "INSERT INTO wellmap VALUES("
        + str(geotvd)
        + ","
        + str(latitude)
        + ","
        + str(longitude)
        + ")"
    )
    cursor.execute(bsql)
    bcon.commit()
    bcon.close()


def delete_survey_point(well_name: str, depth: str) -> int | None:
    """Delete a survey point at a given depth.

    Args:
        well_name: Name of the well.
        depth: Depth of survey point to delete.

    Returns:
        Row ID of deleted point, or None if not found.
    """
    con: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = con.cursor()

    # Get the row ID
    sql_1: str = "SELECT ROWID FROM geosurvey WHERE Depth = " + depth + ""
    cursor.execute(sql_1)
    con.commit()
    rowid: int | None = None
    for row in cursor:
        rowid = row[0]
    con.close()

    if rowid is None:
        return None

    # Delete from geosurvey
    con = sqlite3.connect(well_name + BASE_EXT)
    cursor = con.cursor()
    sql_2: str = "DELETE FROM geosurvey WHERE Depth = " + depth + ""
    cursor.execute(sql_2)
    con.commit()
    con.close()

    # Delete from wellmap
    con = sqlite3.connect(well_name + BASE_EXT)
    cursor = con.cursor()
    sql_3: str = "DELETE FROM wellmap WHERE ROWID = " + str(rowid) + ""
    cursor.execute(sql_3)
    con.commit()
    con.close()

    return rowid


def import_csv_survey(well_name: str, csv_file: str) -> pd.DataFrame:
    """Import survey data from a CSV file.

    Args:
        well_name: Name of the well.
        csv_file: Path to CSV file.

    Returns:
        DataFrame with imported data.
    """
    csv_names: list[str] = [
        "Depth",
        "Inc",
        "Azi",
        "TVD",
        "North",
        "East",
        "Closure",
        "DLS",
    ]
    csv_pdf: pd.DataFrame = pd.read_csv(csv_file, names=csv_names)

    # Write to database
    csv_con: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    csv_pdf.to_sql("geosurvey", con=csv_con, if_exists="append", index=False)
    csv_con.close()

    return csv_pdf


def write_stratigraphy_point(
    well_name: str,
    depth: float,
    fm_name: str,
    fm_color: str,
    tvd: float,
    inc: float,
    azi: float,
    north: float,
    east: float,
    altitude: float,
    latitude: float,
    longitude: float,
) -> None:
    """Write a stratigraphy marker to the database.

    Args:
        well_name: Name of the well.
        depth: Measured depth of formation top.
        fm_name: Formation name.
        fm_color: Hex color code for formation.
        tvd: True vertical depth.
        inc: Inclination at formation top.
        azi: Azimuth at formation top.
        north: Northing at formation top.
        east: Easting at formation top.
        altitude: Altitude (elevation) of formation top.
        latitude: Latitude of formation top.
        longitude: Longitude of formation top.
    """
    z: str = "'"
    Fm_Name: str = z + str(fm_name) + z
    Fm_Color: str = z + str(fm_color) + z

    connex: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = connex.cursor()
    sql_insert: str = (
        "INSERT INTO stratigraphy VALUES("
        + str(depth)
        + ","
        + Fm_Name
        + ","
        + Fm_Color
        + ","
        + str(tvd)
        + ","
        + str(inc)
        + ","
        + str(azi)
        + ","
        + str(north)
        + ","
        + str(east)
        + ","
        + str(altitude)
        + ","
        + str(latitude)
        + ","
        + str(longitude)
        + ")"
    )
    cursor.execute(sql_insert)
    connex.commit()
    connex.close()


def delete_stratigraphy_point(well_name: str, depth: str) -> None:
    """Delete a stratigraphy marker at a given depth.

    Args:
        well_name: Name of the well.
        depth: Depth of stratigraphy point to delete.
    """
    delcon: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = delcon.cursor()
    delFm_sql: str = "DELETE FROM stratigraphy WHERE Depth = " + depth + ""
    cursor.execute(delFm_sql)
    delcon.commit()
    delcon.close()


def load_stratigraphy_data(well_name: str) -> list[tuple[Any, ...]]:
    """Load stratigraphy data for a well.

    Args:
        well_name: Name of the well.

    Returns:
        List of stratigraphy data tuples.
    """
    connection: sqlite3.Connection = sqlite3.connect(well_name + BASE_EXT)
    cursor: sqlite3.Cursor = connection.cursor()
    sql: str = "SELECT * FROM stratigraphy"
    cursor.execute(sql)
    data = cursor.fetchall()
    connection.close()
    return data


def get_formation_color(formation_name: str) -> str | None:
    """Get the hex color code for a formation from geocolors database.

    Args:
        formation_name: Name of the formation.

    Returns:
        Hex color code or None if not found.
    """
    z: str = "'"
    hcol: str = z + str(formation_name) + z

    try:
        con: sqlite3.Connection = sqlite3.connect("geocolors.db")
        cursor: sqlite3.Cursor = con.cursor()
        sql_color: str = "SELECT hexcolor FROM stratcolor WHERE unit = " + hcol + ""
        cursor.execute(sql_color)
        for color in cursor:
            con.close()
            return color[0]
        con.close()
    except Exception:
        pass
    return None


def load_formation_list() -> list[str]:
    """Load list of available formation names from geocolors database.

    Returns:
        List of formation names.
    """
    formations: list[str] = []
    try:
        listbox_connect: sqlite3.Connection = sqlite3.connect("geocolors.db")
        listbox_cursor: sqlite3.Cursor = listbox_connect.cursor()
        listbox_sql: str = "SELECT unit FROM stratcolor"
        listbox_cursor.execute(listbox_sql)
        for unit in listbox_cursor:
            formations.append(unit[0])
        listbox_connect.close()
    except Exception:
        pass
    return formations
