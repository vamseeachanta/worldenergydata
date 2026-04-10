"""Wellpath3D - Borehole Path Calculation and Visualization.

Original Author: Michael Kramer
Last Update: 022.01.2020

This module provides a complete solution for:
- Wellbore trajectory calculations using the Minimum Curvature Method
- 3D visualization of well paths
- Geographic coordinate transformations
- Database management for well data

This is the main entry point module that re-exports functionality from:
- wellpath_coordinates: Coordinate transformation functions
- wellpath_trajectory: Trajectory calculation functions
- wellpath_models: Data classes and well models
- wellpath_database: Database operations
- wellpath_visualization: 3D plotting functions

For backward compatibility, all public names are re-exported here.
"""

from __future__ import annotations

import os
import sqlite3
import tkinter as tk
import tkinter.scrolledtext
from tkinter import END, E, N, S, Tk, W, mainloop, ttk
from tkinter.filedialog import askopenfilename
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.interpolate import griddata

# Re-export coordinate transformation functions
from worldenergydata.common.legacy.wellpath_coordinates import (
    calculate_geographic_position,
    east2lon,
    north2lat,
)

# Re-export database functions
from worldenergydata.common.legacy.wellpath_database import (
    delete_stratigraphy_point,
    delete_survey_point,
    delete_well,
    first_start,
    get_formation_color,
    get_well_surface_data,
    import_csv_survey,
    load_all_wells,
    load_formation_list,
    load_stratigraphy_data,
    load_stratigraphy_dataframe,
    load_survey_data,
    load_survey_dataframe,
    load_well_names,
    write_stratigraphy_point,
    write_survey_point,
    write_wellmap_point,
)

# Re-export model classes
from worldenergydata.common.legacy.wellpath_models import (
    NewWell,
    StratigraphyMarker,
    SurveyData,
    Well,
    WellMap,
    WellSurface,
)

# Re-export trajectory calculation functions
from worldenergydata.common.legacy.wellpath_trajectory import (
    SurveyPoint,
    TrajectoryResult,
    calculate_dogleg,
    calculate_dogleg_severity,
    calculate_minimum_curvature,
    calculate_ratio_factor,
    interpolate_survey_point,
)

# Re-export visualization functions
from worldenergydata.common.legacy.wellpath_visualization import (
    COLOR_PALETTE,
    DEFAULT_COLOR,
    create_formation_plane,
    create_wellsite_polygon,
    get_color_from_index,
    plot_multiple_wells,
    plot_single_well,
)


from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


# Legacy function for compatibility
def instantTab(x: Any) -> Any:
    """Legacy compatibility function."""
    return x


# Legacy aliases for backward compatibility
base: str = ".db"
wellnames_given: list[str] = []
wellactual: list[str] = []
wells_plot: list[Any] = []
fmtop: list[Any] = []
wellnamelist: list[tuple[str, ...]] = []
wells_selected: list[Any] = []
well_objects: list[WellMap] = []


def firstStart() -> None:
    """Initialize wellnames database on first start.

    Wrapper for backward compatibility - delegates to wellpath_database.first_start().
    """
    global wellnames_given
    wellnames_given = first_start(wellnames_given)


# Legacy class aliases
class newwell(NewWell):
    """Legacy alias for NewWell class."""

    def create(self) -> None:
        """Create the well databases."""
        super().create(wellnames_given)


class well(Well):
    """Legacy alias for Well class."""

    pass


class wellmap(WellMap):
    """Legacy alias for WellMap class."""

    pass


class myApplication:
    """Main application class for Wellpath3D GUI.

    This class provides a Tkinter-based GUI for:
    - Creating and managing wells
    - Viewing and editing survey data
    - 3D visualization of well trajectories
    - Managing stratigraphy data
    - Multi-well map plotting
    """

    def __init__(self, root: Tk) -> None:
        self.root: Tk = root
        self.root.title = "Wellpath 3D Visualization"
        self.init_gui()

    def infobox(self, string: str) -> None:
        """Display information in the info label."""
        self.infoLabel["text"] = string

    def init_gui(self) -> None:
        """Initialize the GUI components."""
        self.createWindow()
        self.createWin()
        self.wellsWin()
        self.surveyWin()
        self.plotWin()
        self.wellmapWin()
        self.stratWin()

    def createWindow(self) -> None:
        """Create the main application window."""
        try:
            logo: tk.PhotoImage = tk.PhotoImage(file="icons/wpLogoSmall.png")
            self.mainLabel: tk.Label = tk.Label(self.root, image=logo)
            self.mainLabel.photo = logo  # type: ignore[attr-defined]
        except Exception:
            self.mainLabel = tk.Label(
                self.root,
                text="Wellpath 3D - Borehole Database and Visualization",
                bg="#ffc600",
                pady=12,
                padx=12,
            )
        self.mainLabel.grid(row=0, column=0, columnspan=2, sticky=E + W)

        style: ttk.Style = ttk.Style()
        style.configure("TNotebook", bg="white")
        self.portal: ttk.Notebook = ttk.Notebook(self.root)
        self.portal.grid(row=2, column=0, columnspan=2)

        self.tab0: ttk.Frame = ttk.Frame(self.portal, padding=20)
        self.tab1: ttk.Frame = ttk.Frame(self.portal, padding=20)
        self.tab2: ttk.Frame = ttk.Frame(self.portal, padding=20)
        self.tab3: ttk.Frame = ttk.Frame(self.portal, padding=20)
        self.tab4: ttk.Frame = ttk.Frame(self.portal, padding=20)
        self.tab5: ttk.Frame = ttk.Frame(self.portal, padding=20)

        self.portal.add(self.tab0, text="     Create     ")
        self.portal.add(self.tab1, text="     Wells      ")
        self.portal.add(self.tab2, text="    Survey      ")
        self.portal.add(self.tab3, text="    3D Plot     ")
        self.portal.add(self.tab4, text="    Wellmap     ")
        self.portal.add(self.tab5, text=" Stratigraphy   ")

        self.infoLabel: tk.Label = tk.Label(
            self.root, text="user information", bg="white", fg="#4d2e00"
        )
        self.infoLabel.grid(row=3, column=0, columnspan=2, sticky=E + W)
        self.tab0Separator: ttk.Separator = ttk.Separator(
            self.root, orient="horizontal"
        )
        self.tab0Separator.grid(row=7, column=0, columnspan=2, sticky=W + E)
        self.statusLabel: tk.Label = tk.Label(
            self.root, text="Active borehole: ", fg="red"
        )
        self.statusLabel.grid(row=8, column=0, sticky=E)
        self.statusActive: tk.Label = tk.Label(
            self.root, text="Load from database or create new well"
        )
        self.statusActive.grid(row=8, column=1, sticky=W)

    def createWin(self) -> None:
        """Create the 'Create Well' tab interface."""

        def createWell() -> None:
            wellName: str = str(tab0nameEntry.get())
            lat: float = float(tab0latEntry.get())
            lon: float = float(tab0lonEntry.get())
            alt: float = float(tab0altEntry.get())

            well_instance: newwell = newwell(wellName, lat, lon, alt)
            well_instance.create()
            infoString: str = "New borehole created"
            self.infoLabel["text"] = infoString

        boreholeFrame: tk.Frame = tk.Frame(self.tab0)
        boreholeFrame.pack()
        tab0Label1: tk.Label = tk.Label(
            boreholeFrame, text="Create a new borehole", bg="#ffffff", pady=4, padx=12
        )
        tab0Label1.grid(row=0, column=0, columnspan=2, sticky=E + W)
        tab0Separator: ttk.Separator = ttk.Separator(boreholeFrame, orient="horizontal")
        tab0Separator.grid(row=1, column=0, columnspan=2, sticky=W + E, pady=8)
        tab0BottomSeparator: ttk.Separator = ttk.Separator(
            boreholeFrame, orient="horizontal"
        )
        tab0BottomSeparator.grid(row=6, column=0, columnspan=2, sticky=W + E, pady=8)
        tab0nameLabel: tk.Label = tk.Label(boreholeFrame, text="Name:", pady=4)
        tab0nameLabel.grid(row=2, column=0)
        tab0nameEntry: tk.Entry = tk.Entry(boreholeFrame, width=32)
        tab0nameEntry.grid(row=2, column=1)
        tab0latLabel: tk.Label = tk.Label(boreholeFrame, text="Latitude:", pady=4)
        tab0latLabel.grid(row=3, column=0)
        tab0latEntry: tk.Entry = tk.Entry(boreholeFrame, width=32)
        tab0latEntry.grid(row=3, column=1)
        tab0lonLabel: tk.Label = tk.Label(boreholeFrame, text="Longitude:", pady=4)
        tab0lonLabel.grid(row=4, column=0)
        tab0lonEntry: tk.Entry = tk.Entry(boreholeFrame, width=32)
        tab0lonEntry.grid(row=4, column=1)
        tab0altLabel: tk.Label = tk.Label(boreholeFrame, text="Altitude:", pady=4)
        tab0altLabel.grid(row=5, column=0)
        tab0altEntry: tk.Entry = tk.Entry(boreholeFrame, width=32)
        tab0altEntry.grid(row=5, column=1)

        try:
            iconOk: tk.PhotoImage = tk.PhotoImage(file="icons/iconOkSmall.png")
            tab0Button: tk.Button = tk.Button(
                boreholeFrame,
                text="Submit",
                padx=4,
                image=iconOk,
                compound="left",
                command=createWell,
            )
            tab0Button.image = iconOk  # type: ignore[attr-defined]
        except Exception:
            tab0Button = tk.Button(boreholeFrame, text="Submit", command=createWell)
        tab0Button.grid(row=7, column=0, columnspan=2)

    def wellsWin(self) -> None:
        """Create the 'Wells' tab interface."""

        def fileload() -> None:
            connection: sqlite3.Connection = sqlite3.connect("wellnames.db")
            cursor: sqlite3.Cursor = connection.cursor()
            sql: str = "SELECT * FROM wells"
            cursor.execute(sql)
            dsatz: list[Any] = cursor.fetchall()
            tab1Tree.delete(*tab1Tree.get_children())
            for row in dsatz:
                tab1Tree.insert("", tk.END, values=row)
            connection.close()

        def selectItem(a: Any) -> None:
            curItem: str = tab1Tree.focus()
            try:
                self.infoLabel["text"] = tab1Tree.item(curItem)["values"][0]
            except Exception:
                self.infoLabel["text"] = (
                    "choose a well with mouse button and press load"
                )

        def openwell() -> None:
            curItem: str = tab1Tree.focus()
            try:
                ow: str = tab1Tree.item(curItem)["values"][0]
                openWell: well = well(ow, 0, 0, 0)
                currentwell: str = ow
                wellactual.append(currentwell)
                self.infoLabel["text"] = "Well loaded from database"
                self.statusActive["text"] = ow
            except Exception:
                self.infoLabel["text"] = "choose well from list"

        def delwell() -> None:
            currentItem: str = tab1Tree.focus()
            deletewell_name: str = tab1Tree.item(currentItem)["values"][0]
            delete_well(deletewell_name)
            self.infoLabel["text"] = "Well removed from database"

        wellsWinFrame: tk.Frame = tk.Frame(self.tab1)
        wellsWinFrame.pack()
        tab1Label1: tk.Label = tk.Label(
            wellsWinFrame, text="Well Database", bg="#ffffff", pady=4, padx=12
        )
        tab1Label1.grid(row=0, column=0, columnspan=40, sticky=W + E)
        tab1Separator: ttk.Separator = ttk.Separator(wellsWinFrame, orient="horizontal")
        tab1Separator.grid(row=1, column=0, columnspan=40, sticky=W + E, pady=9)

        bottomSeparator: ttk.Separator = ttk.Separator(
            wellsWinFrame, orient="horizontal"
        )
        bottomSeparator.grid(row=3, column=0, columnspan=40, sticky=W + E, pady=9)

        tab1RefreshButton: tk.Button = tk.Button(
            wellsWinFrame, text="Show All", command=fileload
        )
        tab1RefreshButton.grid(row=4, column=0, sticky=W + E)

        tab1LoadButton: tk.Button = tk.Button(
            wellsWinFrame, text="Load Well", command=openwell
        )
        tab1LoadButton.grid(row=4, column=1, sticky=W + E)

        tab1DeleteButton: tk.Button = tk.Button(
            wellsWinFrame, text="Delete Well", command=delwell, bg="#ff4646"
        )
        tab1DeleteButton.grid(row=4, column=2, sticky=W + E, padx=12)

        tab1Tree: ttk.Treeview = ttk.Treeview(
            wellsWinFrame,
            selectmode="browse",
            column=("one", "two", "three", "four"),
            show="headings",
        )
        tab1Tree.heading("one", text="Well")
        tab1Tree.heading("two", text="Latitude")
        tab1Tree.heading("three", text="Longitude")
        tab1Tree.heading("four", text="Altitude")
        tab1Tree.bind("<ButtonRelease-1>", selectItem)
        tab1Tree.bind("<Double-Button 1>", selectItem)
        tab1Tree.grid(row=2, column=0, columnspan=38)

        wScroll: ttk.Scrollbar = ttk.Scrollbar(wellsWinFrame, command=tab1Tree.yview)
        wScroll.grid(row=2, column=39, sticky=N + S + W)
        tab1Tree.configure(yscrollcommand=wScroll.set, height=22)
        fileload()

    def surveyWin(self) -> None:
        """Create the 'Survey' tab interface."""

        def importCsv() -> None:
            try:
                currentwell: str = wellactual[-1]
                Tk().withdraw()
                csvFile: str = askopenfilename()
                csvName: str = str(csvFile)

                csv_pdf = import_csv_survey(currentwell, csvName)
                self.infoLabel["text"] = "Loading File..."

                z_surface, lat_surface, lon_surface = get_well_surface_data(currentwell)

                csv_north_list: list[float] = csv_pdf.North.tolist()
                csv_east_list: list[float] = csv_pdf.East.tolist()
                csv_tvd_list: list[float] = csv_pdf.TVD.tolist()
                csv_Lat: list[float] = []
                csv_Lon: list[float] = []
                csv_Alt: list[float] = []

                for i in range(0, len(csv_north_list)):
                    increment_lat: float = north2lat(csv_north_list[i], lat_surface)
                    csv_Lat.append(increment_lat)

                for i in range(0, len(csv_east_list)):
                    increment_Lon: float = east2lon(
                        csv_east_list[i], lat_surface, lon_surface
                    )
                    csv_Lon.append(increment_Lon)

                for i in range(0, len(csv_tvd_list)):
                    increment_Tvd: float = z_surface - csv_tvd_list[i]
                    csv_Alt.append(increment_Tvd)

                se_lat: pd.Series = pd.Series(csv_Lat)
                se_lon: pd.Series = pd.Series(csv_Lon)
                se_alt: pd.Series = pd.Series(csv_Alt)

                new_dataframe: pd.DataFrame = pd.DataFrame()
                new_dataframe["geotvd"] = se_alt.values
                new_dataframe["latitude"] = se_lat.values
                new_dataframe["longitude"] = se_lon.values

                dfcon: sqlite3.Connection = sqlite3.connect(currentwell + base)
                new_dataframe.to_sql(
                    "wellmap", con=dfcon, if_exists="append", index=False
                )
                dfcon.close()
                self.infoLabel["text"] = "data import from csv-file"
            except Exception:
                self.infoLabel["text"] = "some strange error occured during operation"

        def loadsurvey() -> None:
            if len(wellactual) == 0:
                self.infoLabel["text"] = "load a well from the Wells tab first"
            else:
                currentwell: str = wellactual[-1]
                data = load_survey_data(currentwell)
                surveyTree.delete(*surveyTree.get_children())
                for row in data:
                    surveyTree.insert(
                        "",
                        tk.END,
                        values=(
                            row[0],
                            row[1],
                            row[2],
                            round(row[3], 2),
                            round(row[4], 2),
                            round(row[5], 2),
                            round(row[6], 2),
                            round(row[7], 3),
                        ),
                    )

        def writesurvey() -> None:
            depthlist: list[float] = []
            inclist: list[float] = []
            azilist: list[float] = []
            tvdlist: list[float] = []
            northlist: list[float] = []
            eastlist: list[float] = []

            try:
                depth_str: str = e1.get()
                inc_str: str = e2.get()
                azi_str: str = e3.get()
                d: float = float(depth_str)
                i: float = float(inc_str)
                a: float = float(azi_str)

                if len(wellactual) == 0:
                    self.infoLabel["text"] = "por favor selecciona un taladro"
                    return
                currentwell: str = wellactual[-1]

                data = load_survey_data(currentwell)
                for dsatz in data:
                    depthlist.append(dsatz[0])
                    inclist.append(dsatz[1])
                    azilist.append(dsatz[2])
                    tvdlist.append(dsatz[3])
                    northlist.append(dsatz[4])
                    eastlist.append(dsatz[5])

                ldepth: float = depthlist[-1]
                linc: float = inclist[-1]
                lazi: float = azilist[-1]
                ltvd: float = tvdlist[-1]
                lnorth: float = northlist[-1]
                least: float = eastlist[-1]

                result = calculate_minimum_curvature(
                    ldepth, linc, lazi, ltvd, lnorth, least, d, i, a
                )

                z_surface, lat_surface, lon_surface = get_well_surface_data(currentwell)
                geotvd: float = z_surface - result.tvd
                latit: float = north2lat(result.north, lat_surface)
                longit: float = east2lon(result.east, lat_surface, lon_surface)

            except Exception:
                self.infoLabel["text"] = "Please try again, check your input"
                return

            try:
                write_survey_point(
                    currentwell,
                    d,
                    i,
                    a,
                    result.tvd,
                    result.north,
                    result.east,
                    result.closure,
                    result.dls,
                )
                self.infoLabel["text"] = "writing in progress"

                write_wellmap_point(currentwell, geotvd, latit, longit)
                self.infoLabel["text"] = "wellmap data written"
            except Exception:
                self.infoLabel["text"] = "survey not written"

            loadsurvey()

        def delData() -> None:
            if len(wellactual) == 0:
                self.infoLabel["text"] = "create or choose a well"
            else:
                currentwell: str = wellactual[-1]
                try:
                    de: str = deleteSurvey.get()
                    delsurvey: str = str(de)
                    result = delete_survey_point(currentwell, delsurvey)
                    if result is not None:
                        self.infoLabel["text"] = "survey deleted"
                    else:
                        self.infoLabel["text"] = (
                            "specify the depth from which survey shall be removed"
                        )
                    deleteSurvey.delete(0, END)
                except Exception:
                    self.infoLabel["text"] = "survey not removed, database error likely"

        surveyWinFrame: tk.Frame = tk.Frame(self.tab2)
        surveyWinFrame.pack()
        tab2Label1: tk.Label = tk.Label(
            surveyWinFrame, text="Surveys", bg="#ffffff", pady=4, padx=12
        )
        tab2Label1.grid(row=0, column=0, columnspan=40, sticky=E + W)
        tab2Separator: ttk.Separator = ttk.Separator(
            surveyWinFrame, orient="horizontal"
        )
        tab2Separator.grid(row=1, column=0, columnspan=40, sticky=W + E, pady=8)
        tab2BottomSeparator: ttk.Separator = ttk.Separator(
            surveyWinFrame, orient="horizontal"
        )
        tab2BottomSeparator.grid(row=3, column=0, columnspan=40, sticky=W + E, pady=8)
        tab2refreshButton: tk.Button = tk.Button(
            surveyWinFrame, text="Show", command=loadsurvey
        )
        tab2refreshButton.grid(row=4, column=0, sticky=E + W)
        tab3writeButton: tk.Button = tk.Button(
            surveyWinFrame, text="Write", command=writesurvey
        )
        tab3writeButton.grid(row=4, column=1, sticky=E + W)
        tab3importButton: tk.Button = tk.Button(
            surveyWinFrame, text="Import", command=importCsv
        )
        tab3importButton.grid(row=4, column=2, sticky=E + W)

        surveyTree: ttk.Treeview = ttk.Treeview(
            surveyWinFrame, selectmode="browse", show="headings"
        )
        surveyTree["columns"] = [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
        ]
        surveyTree.column("one", width=100)
        surveyTree.column("two", width=100)
        surveyTree.column("three", width=100)
        surveyTree.column("four", width=100)
        surveyTree.column("five", width=100)
        surveyTree.column("six", width=100)
        surveyTree.column("seven", width=100)
        surveyTree.column("eight", width=100)
        surveyTree.heading("one", text="Depth")
        surveyTree.heading("two", text="Inc")
        surveyTree.heading("three", text="Azi")
        surveyTree.heading("four", text="TVD")
        surveyTree.heading("five", text="North")
        surveyTree.heading("six", text="East")
        surveyTree.heading("seven", text="Closure")
        surveyTree.heading("eight", text="DLS")
        surveyTree.grid(row=2, column=0, columnspan=38, sticky=E + W)
        wScroll2: ttk.Scrollbar = ttk.Scrollbar(
            surveyWinFrame, command=surveyTree.yview
        )
        wScroll2.grid(row=2, column=39, sticky=N + S + W)
        surveyTree.configure(yscrollcommand=wScroll2.set, height=12)

        pw1: ttk.PanedWindow = ttk.PanedWindow(surveyWinFrame, orient="horizontal")
        f1: ttk.Labelframe = ttk.Labelframe(
            pw1, text="Add Survey", width=200, height=200
        )
        f2: ttk.Labelframe = ttk.Labelframe(
            pw1, text="Delete Survey", width=200, height=200
        )
        pw1.add(f1)
        pw1.add(f2)
        pw1.grid(row=5, column=0, columnspan=40, sticky=E + W, pady=20)

        label1: tk.Label = tk.Label(f1, text="Depth:")
        label1.pack(padx=24, pady=4)
        e1: tk.Entry = tk.Entry(f1, justify="center")
        e1.pack(padx=24)
        label2: tk.Label = tk.Label(f1, text="Inclination:")
        label2.pack(padx=24, pady=4)
        e2: tk.Entry = tk.Entry(f1, justify="center")
        e2.pack(padx=24, pady=4)
        label3: tk.Label = tk.Label(f1, text="Azimuth:")
        label3.pack(padx=24, pady=4)
        e3: tk.Entry = tk.Entry(f1, justify="center")
        e3.pack(padx=24, pady=4)

        dele_lb: tk.Label = tk.Label(f2, text="Survey from Depth:")
        dele_lb.pack(pady=4)
        deleteSurvey: tk.Entry = tk.Entry(f2, justify="center")
        deleteSurvey.pack(padx=24, pady=4)
        surveyDeleteButton: tk.Button = tk.Button(
            f2, text="Delete", bg="#ff4646", command=delData, width=8
        )
        surveyDeleteButton.pack(pady=8)

    def plotWin(self) -> None:
        """Create the '3D Plot' tab interface."""
        showstrat: tk.IntVar = tk.IntVar()
        showsite: tk.IntVar = tk.IntVar()
        showsite.set(1)
        schwert: tk.IntVar = tk.IntVar()
        schwert.set(10)
        autoscale: tk.IntVar = tk.IntVar()
        autoscale.set(1)
        equalxy: tk.IntVar = tk.IntVar()
        idls: tk.IntVar = tk.IntVar()
        stratplane: tk.IntVar = tk.IntVar()
        scvp: tk.IntVar = tk.IntVar()
        scvp.set(10)
        scv_alpha: tk.StringVar = tk.StringVar()
        scv_alpha.set("0.4")
        scv_color: tk.IntVar = tk.IntVar()
        scv_color.set(8)

        def colorpick(event: Any) -> None:
            farblabel["bg"] = get_color_from_index(scv_color.get())

        def plot_well_gui() -> None:
            if len(wellactual) == 0:
                self.infoLabel["text"] = "choose and load a well from database first"
                return

            currentwell: str = wellactual[-1]

            try:
                panda = load_survey_dataframe(currentwell)
                strat_data = None
                if showstrat.get() == 1 or stratplane.get() == 1:
                    strat_data = load_stratigraphy_dataframe(currentwell)

                plot_single_well(
                    panda=panda,
                    well_name=currentwell,
                    show_site=showsite.get() == 1,
                    show_strat=showstrat.get() == 1 and stratplane.get() == 0,
                    show_strat_planes=stratplane.get() == 1,
                    autoscale=autoscale.get() == 1,
                    equal_xy=equalxy.get() == 1,
                    show_dls=idls.get() == 1,
                    axis_limit=int(schwert.get()),
                    plane_size=int(scvp.get()),
                    alpha_level=float(scv_alpha.get()),
                    color_index=scv_color.get(),
                    strat_data=strat_data,
                )
            except Exception:
                self.infoLabel["text"] = "please select a well from database"

        plotWinFrame: tk.Frame = tk.Frame(self.tab3)
        plotWinFrame.pack()
        plotLabel1: tk.Label = tk.Label(
            plotWinFrame, text="3D Plot of Single Well", bg="#ffffff", pady=4, padx=12
        )
        plotLabel1.grid(row=0, column=0, columnspan=6, sticky=E + W)
        plotSeparator: ttk.Separator = ttk.Separator(plotWinFrame, orient="horizontal")
        plotSeparator.grid(row=1, column=0, columnspan=6, sticky=W + E, pady=8)
        plotLabel2: tk.Label = tk.Label(plotWinFrame, text="Show Elements")
        plotLabel2.grid(row=3, column=0)

        cb1: tk.Checkbutton = tk.Checkbutton(
            plotWinFrame, text="Wellsite", variable=showsite, padx=4, pady=4
        )
        cb1.grid(row=5, column=0, sticky=W)
        cb2: tk.Checkbutton = tk.Checkbutton(
            plotWinFrame, text="Formations", variable=showstrat, padx=4, pady=4
        )
        cb2.grid(row=6, column=0, sticky=W)

        cd3: tk.Checkbutton = tk.Checkbutton(
            plotWinFrame,
            text="Formations as Planes",
            variable=stratplane,
            padx=4,
            pady=4,
        )
        cd3.grid(row=7, column=0, sticky=W)

        cb4: tk.Checkbutton = tk.Checkbutton(
            plotWinFrame, text="Autoscale", variable=autoscale, padx=4, pady=4
        )
        cb4.grid(row=8, column=0, sticky=W)
        cb6: tk.Checkbutton = tk.Checkbutton(
            plotWinFrame, text="Equal xy-Scale", variable=equalxy, padx=4, pady=4
        )
        cb6.grid(row=9, column=0, sticky=W)

        cb7: tk.Checkbutton = tk.Checkbutton(
            plotWinFrame, text="Indicate Dogleg Severity", variable=idls, padx=4, pady=4
        )
        cb7.grid(row=10, column=0, sticky=W)

        scv: tk.Scale = tk.Scale(
            plotWinFrame,
            width=20,
            length=320,
            orient="horizontal",
            from_=0,
            to=2000,
            resolution=10,
            tickinterval=400,
            label="Axis Scaling",
            variable=schwert,
            showvalue=False,
        )
        scv.grid(row=3, column=5, rowspan=3, padx=24, sticky=E)

        scv2: tk.Scale = tk.Scale(
            plotWinFrame,
            width=20,
            length=320,
            orient="horizontal",
            from_=20,
            to=120,
            resolution=10,
            tickinterval=20,
            label="Plane Size",
            variable=scvp,
            showvalue=False,
        )
        scv2.grid(row=6, column=5, rowspan=3, padx=24, sticky=E)

        scv3: tk.Scale = tk.Scale(
            plotWinFrame,
            width=20,
            length=320,
            orient="horizontal",
            from_=0,
            to=1,
            resolution=0.1,
            tickinterval=0.2,
            label="Alpha Level",
            variable=scv_alpha,
            showvalue=False,
        )
        scv3.grid(row=9, column=5, rowspan=3, padx=24, sticky=E)

        scv4: tk.Scale = tk.Scale(
            plotWinFrame,
            width=20,
            length=320,
            orient="horizontal",
            from_=0,
            to=10,
            resolution=2,
            tickinterval=2,
            label="Color Slider",
            variable=scv_color,
            command=colorpick,
            showvalue=False,
        )
        scv4.grid(row=12, column=5, rowspan=3, padx=24, sticky=E)

        vertsep: ttk.Separator = ttk.Separator(plotWinFrame, orient="vertical")
        vertsep.grid(row=3, column=3, rowspan=14, sticky=N + S, padx=24)

        plotSeparator3: ttk.Separator = ttk.Separator(plotWinFrame, orient="horizontal")
        plotSeparator3.grid(row=18, column=0, columnspan=6, sticky=W + E, pady=8)

        plotButton: tk.Button = tk.Button(
            plotWinFrame, text="3D Plot", padx=50, command=plot_well_gui
        )
        plotButton.grid(row=19, column=0, columnspan=6)

        farblabel: tk.Label = tk.Label(plotWinFrame, bg="#00AFFE")
        farblabel.grid(row=17, column=5, columnspan=2, sticky=W + E, pady=0)

    def wellmapWin(self) -> None:
        """Create the 'Wellmap' tab interface for multi-well plotting."""
        mapstrat: tk.IntVar = tk.IntVar()
        showDEM: tk.IntVar = tk.IntVar()
        showPolygon: tk.IntVar = tk.IntVar()
        showLegend: tk.IntVar = tk.IntVar()

        # File paths for surface data
        xyzFile: str = ""
        nodesFile: str = ""
        attributesFile: str = ""

        def load_choice() -> None:
            del well_objects[: len(well_objects)]
            for x in wellsToChoose.curselection():
                k: str = wellsToChoose.get(x)[0]
                k_wellmap: wellmap = wellmap(k, 0, 0, 0)
                well_objects.append(k_wellmap)

        def show_objects() -> None:
            plot_multiple_wells(
                well_objects=well_objects,
                show_stratigraphy=mapstrat.get() == 1,
                show_legend=showLegend.get() == 1,
                show_dem=showDEM.get() == 1,
                show_polygon=showPolygon.get() == 1,
                xyz_file=xyzFile if xyzFile else None,
                nodes_file=nodesFile if nodesFile else None,
                attributes_file=attributesFile if attributesFile else None,
            )

        def fileDialogXYZ() -> None:
            nonlocal xyzFile
            Tk().withdraw()
            xyzFile = askopenfilename()

        def fileDialogNodes() -> None:
            nonlocal nodesFile
            Tk().withdraw()
            nodesFile = askopenfilename()

        def fileDialogAttributes() -> None:
            nonlocal attributesFile
            Tk().withdraw()
            attributesFile = askopenfilename()

        wellnames = load_well_names()

        wellmapFrame: tk.Frame = tk.Frame(self.tab4)
        wellmapFrame.pack()
        tab4Label1: tk.Label = tk.Label(
            wellmapFrame, text="Plot Multiple Wells on a Map", bg="#ffffff"
        )
        tab4Label1.grid(row=0, column=0, columnspan=8, sticky=E + W)
        tab4Separator: ttk.Separator = ttk.Separator(wellmapFrame, orient="horizontal")
        tab4Separator.grid(row=1, column=0, columnspan=8, sticky=W + E, pady=8)
        tab4BottomSeparator: ttk.Separator = ttk.Separator(
            wellmapFrame, orient="horizontal"
        )
        tab4BottomSeparator.grid(row=12, column=0, columnspan=8, sticky=W + E, pady=8)
        wellmapBt1: tk.Button = tk.Button(
            wellmapFrame, text="Load Wells", command=load_choice, relief="groove"
        )
        wellmapBt1.grid(row=13, column=0, columnspan=2, sticky=W + E)
        wellmapBt2: tk.Button = tk.Button(
            wellmapFrame, text="Plot Map", command=show_objects, relief="groove"
        )
        wellmapBt2.grid(row=13, column=2, sticky=W + E)
        wellmapChk1: tk.Checkbutton = tk.Checkbutton(
            wellmapFrame, text="Include stratigraphy", variable=mapstrat
        )
        wellmapChk1.grid(row=3, column=5, columnspan=3, sticky=W)
        DEMcheckbox: tk.Checkbutton = tk.Checkbutton(
            wellmapFrame, text="Plot xyz-data", variable=showDEM
        )
        DEMcheckbox.grid(row=4, column=5, columnspan=3, sticky=W)

        polygonCheckbox: tk.Checkbutton = tk.Checkbutton(
            wellmapFrame, text="Plot Polygon-data", variable=showPolygon
        )
        polygonCheckbox.grid(row=5, column=5, columnspan=3, sticky=W)

        legendCheckbox: tk.Checkbutton = tk.Checkbutton(
            wellmapFrame, text="Show Legend", variable=showLegend
        )
        legendCheckbox.grid(row=6, column=5, columnspan=3, sticky=W)

        addGeometryLabel: tk.Label = tk.Label(
            wellmapFrame, text="xyz-Point Geometry Data", pady=8, padx=32, bg="#fff5e6"
        )
        addGeometryLabel.grid(row=14, column=0, columnspan=8, sticky=E + W, pady=4)

        searchXyzLabel: tk.Label = tk.Label(
            wellmapFrame, text="Add xyz-Data", bg="#fefefe"
        )
        searchXyzLabel.grid(row=15, column=0, columnspan=4, sticky=E + W)

        xyzButton: tk.Button = tk.Button(
            wellmapFrame, text="Open File", command=fileDialogXYZ
        )
        xyzButton.grid(row=15, column=5)

        searchPolygonLabel: tk.Label = tk.Label(
            wellmapFrame, text="Polygon Data", bg="#fff5e6", pady=8
        )
        searchPolygonLabel.grid(row=16, column=0, columnspan=8, sticky=E + W, pady=4)

        nodeLabel: tk.Label = tk.Label(wellmapFrame, text="Add nodes", bg="#fefefe")
        nodeLabel.grid(row=17, column=0, columnspan=4, sticky=W + E, pady=4)
        nodeButton: tk.Button = tk.Button(
            wellmapFrame, text="Open File", command=fileDialogNodes
        )
        nodeButton.grid(row=17, column=5)
        attributeLabel: tk.Label = tk.Label(
            wellmapFrame, text="Add Attributes", bg="#fefefe"
        )
        attributeLabel.grid(row=18, column=0, columnspan=4, sticky=W + E, pady=4)
        attributeButton: tk.Button = tk.Button(
            wellmapFrame, text="Open File", command=fileDialogAttributes
        )
        attributeButton.grid(row=18, column=5)

        selectLabel: tk.Label = tk.Label(wellmapFrame, text="Select Wells")
        selectLabel.grid(row=2, column=0)
        scbChoose: tk.Scrollbar = tk.Scrollbar(wellmapFrame, orient="vertical")
        wellsToChoose: tk.Listbox = tk.Listbox(
            wellmapFrame,
            height=16,
            width=32,
            yscrollcommand=scbChoose.set,
            selectmode="multiple",
        )
        scbChoose["command"] = wellsToChoose.yview

        for wellmap_well in wellnames:
            wellsToChoose.insert("end", wellmap_well)
        wellsToChoose.grid(
            row=3, column=0, columnspan=4, rowspan=8, sticky=W + E + N + S
        )
        scbChoose.grid(row=3, column=4, rowspan=9, sticky=W + N + S)

    def stratWin(self) -> None:
        """Create the 'Stratigraphy' tab interface."""

        def interpolate() -> None:
            try:
                fm_dep: str = stratentry2.get()
                fm_depth: str = str(float(fm_dep))

                currentwell: str = wellactual[-1]
                panda_fm_min = pd.read_sql_query(
                    "SELECT * FROM geosurvey WHERE DEPTH <= " + fm_depth + "",
                    sqlite3.connect(currentwell + base),
                )
                panda_fm_max = pd.read_sql_query(
                    "SELECT * FROM geosurvey WHERE DEPTH >= " + fm_depth + "",
                    sqlite3.connect(currentwell + base),
                )

                self.infoLabel["text"] = "interpolate formation top"
                panda_fm_min.sort_values(by=["Depth"])
                panda_fm_max.sort_values(by=["Depth"])

                up_survey = panda_fm_min.tail(1)
                down_survey = panda_fm_max.head(1)

                us_depth: list[float] = up_survey.Depth.tolist()
                ls_depth: list[float] = down_survey.Depth.tolist()
                us_inc: list[float] = up_survey.Inc.tolist()
                ls_inc: list[float] = down_survey.Inc.tolist()
                us_azi: list[float] = up_survey.Azi.tolist()
                ls_azi: list[float] = down_survey.Azi.tolist()
                us_tvd: list[float] = up_survey.TVD.tolist()
                us_north: list[float] = up_survey.North.tolist()
                us_east: list[float] = up_survey.East.tolist()

                inc_fm, azi_fm, tvd_fm, north_fm, east_fm, _ = interpolate_survey_point(
                    us_depth[0],
                    us_inc[0],
                    us_azi[0],
                    us_tvd[0],
                    us_north[0],
                    us_east[0],
                    ls_depth[0],
                    ls_inc[0],
                    ls_azi[0],
                    float(fm_dep),
                )

                self.infoLabel["text"] = str((tvd_fm, north_fm, east_fm))
            except Exception:
                self.infoLabel["text"] = "please check the input"

        def deleteStratigraphy() -> None:
            if len(wellactual) == 0:
                self.infoLabel["text"] = "choose a well from database first"
            else:
                currentwell: str = wellactual[-1]
                try:
                    xd: str = stratentry2.get()
                    xdepth: str = str(xd)
                    delete_stratigraphy_point(currentwell, xdepth)
                    stratentry2.delete(0, END)
                    self.infoLabel["text"] = "formation top deleted from list"
                except Exception:
                    self.infoLabel["text"] = "to be deleted from which depth?"

        def addstrat() -> None:
            if len(wellactual) == 0:
                self.infoLabel["text"] = "choose a well first"
                return
            currentwell: str = wellactual[-1]

            try:
                for formation in li.curselection():
                    F: str = li.get(formation)

                fm_nam: str = str(F)
                fm_nam = fm_nam.replace('"', "")

                HexColor = get_formation_color(fm_nam)
                if HexColor is None:
                    self.infoLabel["text"] = "Color not found for formation"
                    return

                fm_dep: str = stratentry2.get()
                fm_depth: str = str(float(fm_dep))

                panda_fm_min = pd.read_sql_query(
                    "SELECT * FROM geosurvey WHERE DEPTH <= " + fm_depth + "",
                    sqlite3.connect(currentwell + base),
                )
                panda_fm_max = pd.read_sql_query(
                    "SELECT * FROM geosurvey WHERE DEPTH >= " + fm_depth + "",
                    sqlite3.connect(currentwell + base),
                )

                panda_fm_min.sort_values(by=["Depth"])
                panda_fm_max.sort_values(by=["Depth"])
                up_survey = panda_fm_min.tail(1)
                down_survey = panda_fm_max.head(1)

                z_surface, lat_surface, lon_surface = get_well_surface_data(currentwell)

                us_depth: list[float] = up_survey.Depth.tolist()
                ls_depth: list[float] = down_survey.Depth.tolist()
                us_inc: list[float] = up_survey.Inc.tolist()
                ls_inc: list[float] = down_survey.Inc.tolist()
                us_azi: list[float] = up_survey.Azi.tolist()
                ls_azi: list[float] = down_survey.Azi.tolist()
                us_tvd: list[float] = up_survey.TVD.tolist()
                us_north: list[float] = up_survey.North.tolist()
                us_east: list[float] = up_survey.East.tolist()

                inc_fm, azi_fm, tvd_fm, north_fm, east_fm, _ = interpolate_survey_point(
                    us_depth[0],
                    us_inc[0],
                    us_azi[0],
                    us_tvd[0],
                    us_north[0],
                    us_east[0],
                    ls_depth[0],
                    ls_inc[0],
                    ls_azi[0],
                    float(fm_dep),
                )

                lat_fm = north2lat(north_fm, lat_surface)
                lon_fm = east2lon(east_fm, lat_surface, lon_surface)
                alt_fm = z_surface - tvd_fm

                write_stratigraphy_point(
                    currentwell,
                    float(fm_dep),
                    fm_nam,
                    HexColor,
                    tvd_fm,
                    inc_fm,
                    azi_fm,
                    north_fm,
                    east_fm,
                    alt_fm,
                    lat_fm,
                    lon_fm,
                )
                self.infoLabel["text"] = str(tvd_fm)
            except Exception:
                self.infoLabel["text"] = (
                    "load well, check your input or pick a stratigraphic unit from the list"
                )

        def update() -> None:
            if len(wellactual) == 0:
                self.infoLabel["text"] = "Create or Select Well from Database"
            else:
                currentwell: str = wellactual[-1]
                data = load_stratigraphy_data(currentwell)
                tab5Tree.delete(*tab5Tree.get_children())
                for row in data:
                    tab5Tree.insert("", tk.END, values=row)

        stratWinFrame: tk.Frame = tk.Frame(self.tab5)
        stratWinFrame.pack()
        tab5Label1: tk.Label = tk.Label(
            stratWinFrame, text="Formations", bg="#ffffff", pady=4, padx=12
        )
        tab5Label1.grid(row=0, column=0, columnspan=20, sticky=E + W)
        tab5Separator: ttk.Separator = ttk.Separator(stratWinFrame, orient="horizontal")
        tab5Separator.grid(row=1, column=0, columnspan=20, sticky=W + E, pady=8)

        tab5BottomSeparator: ttk.Separator = ttk.Separator(
            stratWinFrame, orient="horizontal"
        )
        tab5BottomSeparator.grid(row=3, column=0, columnspan=20, sticky=W + E, pady=8)

        formbutton: tk.Button = tk.Button(
            stratWinFrame, text="Interpolate", command=interpolate
        )
        formbutton.grid(row=4, column=3, sticky=W + E)

        write_fm: tk.Button = tk.Button(stratWinFrame, text="Write", command=addstrat)
        write_fm.grid(row=4, column=1, sticky=W + E)

        deleteStratigraphyButton: tk.Button = tk.Button(
            stratWinFrame, text="Delete", command=deleteStratigraphy
        )
        deleteStratigraphyButton.grid(row=4, column=2, sticky=W + E)

        view_fm: tk.Button = tk.Button(stratWinFrame, text="Show", command=update)
        view_fm.grid(row=4, column=0, sticky=W + E)

        tab5Tree: ttk.Treeview = ttk.Treeview(
            stratWinFrame,
            selectmode="browse",
            column=("one", "two", "three", "four"),
            show="headings",
        )
        tab5Tree.heading("one", text="Depth [m]")
        tab5Tree.heading("two", text="Unit")
        tab5Tree.heading("three", text="Colorcode")
        tab5Tree.heading("four", text="TVD [m]")
        tab5Tree.grid(row=2, column=0, columnspan=20, sticky=W + E)

        wScroll: ttk.Scrollbar = ttk.Scrollbar(stratWinFrame, command=tab5Tree.yview)
        wScroll.grid(row=2, column=19, sticky=N + S + E)
        tab5Tree.configure(yscrollcommand=wScroll.set, height=10)

        lb2: tk.Label = tk.Label(stratWinFrame, text="New Formation-Top [m]:")
        lb2.grid(row=5, column=4, columnspan=19, sticky=W, pady=6)
        stratentry2: tk.Entry = tk.Entry(stratWinFrame, justify="center")
        stratentry2.grid(row=6, column=4, columnspan=19, sticky=W + E + N, pady=6)

        lb: tk.Label = tk.Label(stratWinFrame, text="Chronostratigraphy:")
        lb.grid(row=5, column=0, columnspan=4, sticky=W, pady=8)

        scb: tk.Scrollbar = tk.Scrollbar(stratWinFrame, orient="vertical")
        li: tk.Listbox = tk.Listbox(stratWinFrame, height=12, yscrollcommand=scb.set)
        scb["command"] = li.yview

        formations = load_formation_list()

        for formation in formations:
            li.insert("end", formation)

        li.grid(row=6, column=0, columnspan=3, sticky=W + E, pady=6)
        scb.grid(row=6, column=3, sticky=N + S + W, pady=6)


# Public API exports
__all__ = [
    # Coordinate functions
    "north2lat",
    "east2lon",
    "calculate_geographic_position",
    # Trajectory functions
    "calculate_dogleg",
    "calculate_dogleg_severity",
    "calculate_ratio_factor",
    "calculate_minimum_curvature",
    "interpolate_survey_point",
    "SurveyPoint",
    "TrajectoryResult",
    # Model classes
    "NewWell",
    "Well",
    "WellMap",
    "WellSurface",
    "SurveyData",
    "StratigraphyMarker",
    # Legacy aliases
    "newwell",
    "well",
    "wellmap",
    # Database functions
    "first_start",
    "firstStart",
    "load_all_wells",
    "load_well_names",
    "delete_well",
    "get_well_surface_data",
    "load_survey_data",
    "load_survey_dataframe",
    "load_stratigraphy_dataframe",
    "write_survey_point",
    "write_wellmap_point",
    "delete_survey_point",
    "import_csv_survey",
    "write_stratigraphy_point",
    "delete_stratigraphy_point",
    "load_stratigraphy_data",
    "get_formation_color",
    "load_formation_list",
    # Visualization functions
    "plot_single_well",
    "plot_multiple_wells",
    "get_color_from_index",
    "create_wellsite_polygon",
    "create_formation_plane",
    "COLOR_PALETTE",
    "DEFAULT_COLOR",
    # Application class
    "myApplication",
    # Legacy globals
    "base",
    "wellnames_given",
    "wellactual",
    "wells_plot",
    "fmtop",
    "wellnamelist",
    "wells_selected",
    "well_objects",
    "instantTab",
]


if __name__ == "__main__":
    firstStart()
    root = Tk()
    root.resizable(width=False, height=False)
    myApplication(root)
    mainloop()

logger.info("hasta proxima vez")
