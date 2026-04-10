"""Data models for wellpath representation.

This module provides data classes and models for representing wells,
wellbore surveys, and wellmap data.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)

# Database file extension
BASE_EXT: str = ".db"


@dataclass
class WellSurface:
    """Surface location information for a well."""

    name: str
    latitude: float
    longitude: float
    altitude: float


@dataclass
class SurveyData:
    """Survey data for a wellbore."""

    depth: float = 0.0
    inc: float = 0.0
    azi: float = 0.0
    tvd: float = 0.0
    north: float = 0.0
    east: float = 0.0
    closure: float = 0.0
    dls: float = 0.0


@dataclass
class StratigraphyMarker:
    """Formation marker in a wellbore."""

    depth: float
    name: str
    color: str
    tvd: float = 0.0
    inc: float = 0.0
    azi: float = 0.0
    north: float = 0.0
    east: float = 0.0
    altitude: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0


class NewWell:
    """Class for creating a new well with database entries.

    This class handles the creation of a new well including:
    - Adding to the master wellnames database
    - Creating individual well database with survey and stratigraphy tables
    - Initializing wellmap data

    Attributes:
        newname: Name of the well.
        latitude: Surface latitude in decimal degrees.
        longitude: Surface longitude in decimal degrees.
        altitude: Surface altitude in meters above sea level.
    """

    def __init__(self, nn: str, lat: float, lon: float, alt: float) -> None:
        self.newname: str = nn
        self.latitude: float = lat
        self.longitude: float = lon
        self.altitude: float = alt

    def create(self, wellnames_given: list[str] | None = None) -> None:
        """Create the well databases and tables.

        Args:
            wellnames_given: Optional list of existing well names to check for duplicates.
        """
        if wellnames_given is None:
            wellnames_given = []

        tryname: str = self.newname.replace("'", "")

        if "." in tryname:
            tryname = tryname.replace(".", "*")

        if tryname in wellnames_given:
            self.newname = self.newname + "2"
        else:
            z: str = "'"
            write_name: str = z + self.newname + z
            con: sqlite3.Connection = sqlite3.connect("wellnames.db")
            cursor: sqlite3.Cursor = con.cursor()
            sql: str = (
                "INSERT INTO wells VALUES("
                + write_name
                + ","
                + str(self.latitude)
                + ","
                + str(self.longitude)
                + ","
                + str(self.altitude)
                + ")"
            )
            cursor.execute(sql)
            con.commit()
            con.close()

        # Create well database
        connex: sqlite3.Connection = sqlite3.connect(tryname + BASE_EXT)
        cursor = connex.cursor()
        sql_0: str = (
            "CREATE TABLE geosurvey("
            "Depth REAL PRIMARY KEY, "
            "Inc REAL, "
            "Azi REAL,"
            "TVD REAL,"
            "North REAL,"
            "East REAL,"
            "Closure,"
            "DLS)"
        )
        cursor.execute(sql_0)
        sql_1: str = "INSERT INTO geosurvey VALUES(0,0,0,0,0,0,0,0)"
        cursor.execute(sql_1)
        connex.commit()
        connex.close()

        # Create Table stratigraphy
        stratcon: sqlite3.Connection = sqlite3.connect(tryname + BASE_EXT)
        cursor = stratcon.cursor()
        sql_2: str = (
            "CREATE TABLE stratigraphy("
            "Depth REAL PRIMARY KEY, "
            "Fm_Name TEXT, "
            "Fm_Color TEXT,"
            "Fm_TVD REAL,"
            "Fm_Inc REAL,"
            "Fm_Azi REAL,"
            "Fm_North REAL,"
            "Fm_East  REAL,"
            "Fm_alt REAL,"
            "Fm_lat REAL,"
            "Fm_lon REAL)"
        )
        cursor.execute(sql_2)

        sql_3: str = (
            "INSERT INTO stratigraphy VALUES(0,'Holocene','#fef2e0',0,0,0,0,0,0,0,0)"
        )
        cursor.execute(sql_3)
        stratcon.commit()

        sql_4: str = "UPDATE stratigraphy SET Fm_alt = " + str(self.altitude) + ""
        sql_5: str = "UPDATE stratigraphy SET Fm_lat = " + str(self.latitude) + ""
        sql_6: str = "UPDATE stratigraphy SET Fm_lon = " + str(self.longitude) + ""
        cursor.execute(sql_4)
        cursor.execute(sql_5)
        cursor.execute(sql_6)
        stratcon.commit()
        stratcon.close()

        # Create Table wellmap
        mapcon: sqlite3.Connection = sqlite3.connect(tryname + BASE_EXT)
        cursor = mapcon.cursor()
        msql: str = (
            "CREATE TABLE wellmap(" "geotvd REAL," "latitude REAL," "longitude REAL)"
        )
        cursor.execute(msql)
        mapcon.commit()
        xsql: str = (
            "INSERT INTO wellmap VALUES("
            + str(self.altitude)
            + ","
            + str(self.latitude)
            + ","
            + str(self.longitude)
            + ")"
        )
        cursor.execute(xsql)
        mapcon.commit()
        mapcon.close()


class Well:
    """Class representing a well with survey data.

    Attributes:
        name: Well name/identifier.
        Depth: Current depth.
        Inc: Current inclination.
        Azi: Current azimuth.
        depthlist: List of depth values from survey.
        inclist: List of inclination values from survey.
        azilist: List of azimuth values from survey.
    """

    def __init__(self, bez: str, teu: float, inc: float, azi: float) -> None:
        self.name: str = bez
        self.Depth: float = teu
        self.Inc: float = inc
        self.Azi: float = azi
        self.depthlist: list[float] = []
        self.inclist: list[float] = []
        self.azilist: list[float] = []

    def __str__(self) -> str:
        return (
            str(self.name)
            + ","
            + str(self.Depth)
            + " m "
            + str(self.Inc)
            + " "
            + str(self.Azi)
            + ""
        )

    def depthtolist(self) -> None:
        """Load depth values from database into depthlist."""
        connection: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = connection.cursor()
        sql: str = "SELECT * FROM geosurvey"
        cursor.execute(sql)
        for dsatz in cursor:
            self.depthlist.append(dsatz[0])
        connection.close()

    def inctolist(self) -> None:
        """Load inclination values from database into inclist."""
        connection: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = connection.cursor()
        sql: str = "SELECT * FROM geosurvey"
        cursor.execute(sql)
        for dsatz in cursor:
            self.inclist.append(dsatz[1])
        connection.close()

    def azitolist(self) -> None:
        """Load azimuth values from database into azilist."""
        connection: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = connection.cursor()
        sql: str = "SELECT * FROM geosurvey"
        cursor.execute(sql)
        for dsatz in cursor:
            self.azilist.append(dsatz[2])


class WellMap:
    """Class for wellmap data with geographic coordinates.

    Used for plotting wells on geographic maps with lat/lon coordinates.

    Attributes:
        name: Well name/identifier.
        Tvd: True vertical depth.
        Lat: Latitude.
        Lon: Longitude.
        tvdlist: List of TVD values.
        latlist: List of latitude values.
        lonlist: List of longitude values.
        strat_altilist: List of formation altitudes.
        strat_latlist: List of formation latitudes.
        strat_lonlist: List of formation longitudes.
        strat_colorlist: List of formation colors.
    """

    def __init__(self, bez: str, tvd: float, lat: float, lon: float) -> None:
        self.name: str = bez
        self.Tvd: float = tvd
        self.Lat: float = lat
        self.Lon: float = lon
        self.tvdlist: list[float] = []
        self.latlist: list[float] = []
        self.lonlist: list[float] = []

        self.strat_altilist: list[float] = []
        self.strat_latlist: list[float] = []
        self.strat_lonlist: list[float] = []
        self.strat_colorlist: list[str] = []

    def __str__(self) -> str:
        return (
            str(self.name)
            + ","
            + str(self.Tvd)
            + " m "
            + str(self.Lat)
            + " "
            + str(self.Lon)
            + ""
        )

    def getName(self) -> str:
        """Return the well name."""
        return str(self.name)

    def add_coordinates(self, wert1: float, wert2: float, wert3: float) -> None:
        """Add surface coordinates to the wellmap.

        Args:
            wert1: Surface altitude.
            wert2: Surface latitude.
            wert3: Surface longitude.
        """
        self.surface_alt: float = wert1
        self.surface_lat: float = wert2
        self.surface_lon: float = wert3

        if not os.path.exists(self.name + BASE_EXT):
            wcon: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
            cursor: sqlite3.Cursor = wcon.cursor()
            sql: str = (
                "CREATE TABLE surface("
                "surfacealt REAL PRIMARY KEY, "
                "surfacelat REAL, "
                "surfacelon REAL)"
            )
            cursor.execute(sql)
            wcon.close()
        else:
            logger.info("database loaded")

        wcon = sqlite3.connect(self.name + BASE_EXT)
        cursor = wcon.cursor()
        sql = (
            "INSERT INTO wellmap VALUES("
            + str(wert1)
            + ","
            + str(wert2)
            + ","
            + str(wert3)
            + ")"
        )
        cursor.execute(sql)
        wcon.commit()
        wcon.close()

    def writedata(self, wert1: float, wert2: float, wert3: float) -> None:
        """Write wellmap data point to database.

        Args:
            wert1: TVD value (will be negated for storage).
            wert2: Latitude.
            wert3: Longitude.
        """
        if not os.path.exists(self.name + BASE_EXT):
            wcon: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
            cursor: sqlite3.Cursor = wcon.cursor()
            sql: str = (
                "CREATE TABLE wellmap("
                "tvd REAL PRIMARY KEY, "
                "lat REAL, "
                "lon REAL)"
            )
            cursor.execute(sql)
            wcon.close()
        else:
            logger.info("database loaded")

        wcon = sqlite3.connect(self.name + BASE_EXT)
        cursor = wcon.cursor()
        sql = (
            "INSERT INTO wellmap VALUES("
            + str(wert1 * (-1))
            + ","
            + str(wert2)
            + ","
            + str(wert3)
            + ")"
        )
        cursor.execute(sql)
        wcon.commit()
        wcon.close()

    def tvdtolist(self) -> None:
        """Load TVD values from database into tvdlist."""
        connection: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = connection.cursor()
        sql: str = "SELECT * FROM wellmap"
        cursor.execute(sql)
        for dsatz in cursor:
            self.tvdlist.append(dsatz[0])

    def lattolist(self) -> None:
        """Load latitude values from database into latlist."""
        connection: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = connection.cursor()
        sql: str = "SELECT * FROM wellmap"
        cursor.execute(sql)
        for dsatz in cursor:
            self.latlist.append(dsatz[1])
        connection.close()

    def lontolist(self) -> None:
        """Load longitude values from database into lonlist."""
        connection: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = connection.cursor()
        sql: str = "SELECT * FROM wellmap"
        cursor.execute(sql)
        for dsatz in cursor:
            self.lonlist.append(dsatz[2])

    def strattolist(self) -> None:
        """Load stratigraphy data from database into strat lists."""
        conni: sqlite3.Connection = sqlite3.connect(self.name + BASE_EXT)
        cursor: sqlite3.Cursor = conni.cursor()

        sql_st: str = "SELECT Fm_alt FROM stratigraphy"
        cursor.execute(sql_st)
        for dsatz in cursor:
            self.strat_altilist.append(dsatz[0])

        sql_slat: str = "SELECT Fm_lat FROM stratigraphy"
        cursor.execute(sql_slat)
        for lats in cursor:
            self.strat_latlist.append(lats[0])

        sql_slon: str = "SELECT Fm_lon FROM stratigraphy"
        cursor.execute(sql_slon)
        for lons in cursor:
            self.strat_lonlist.append(lons[0])

        sql_color: str = "SELECT Fm_Color FROM stratigraphy"
        cursor.execute(sql_color)
        for color in cursor:
            self.strat_colorlist.append(color[0])

        conni.close()
