"""3D visualization functions for wellpath plotting.

This module provides functions for creating 3D visualizations of
wellbore trajectories using matplotlib.
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.interpolate import griddata

# Color palette for well visualization
COLOR_PALETTE: dict[int, str] = {
    0: "#0AA0AF",
    2: "#AA00AF",
    4: "#FFDD33",
    6: "#ff0000",
    8: "#00AFFE",
}

DEFAULT_COLOR: str = "#090909"


def get_color_from_index(color_index: int) -> str:
    """Get a color from the palette by index.

    Args:
        color_index: Index into the color palette (0, 2, 4, 6, 8).

    Returns:
        Hex color string.
    """
    return COLOR_PALETTE.get(color_index, DEFAULT_COLOR)


def create_wellsite_polygon(size: int = 30) -> list[list[int]]:
    """Create a square polygon representing the wellsite.

    Args:
        size: Half-width of the square in meters.

    Returns:
        List of [x, y, z] coordinates forming a closed polygon.
    """
    return [
        [-size, size, 0],
        [-size, -size, 0],
        [size, -size, 0],
        [size, size, 0],
        [-size, size, 0],
    ]


def create_formation_plane(
    east: float, north: float, tvd: float, size: int = 10
) -> list[list[float]]:
    """Create a square plane representing a formation marker.

    Args:
        east: Easting coordinate of center.
        north: Northing coordinate of center.
        tvd: TVD (negative) of the plane.
        size: Half-width of the square in meters.

    Returns:
        List of [x, y, z] coordinates forming a closed polygon.
    """
    return [
        [east - size, north + size, tvd],
        [east - size, north - size, tvd],
        [east + size, north - size, tvd],
        [east + size, north + size, tvd],
        [east - size, north + size, tvd],
    ]


def plot_single_well(
    panda: pd.DataFrame,
    well_name: str,
    show_site: bool = True,
    show_strat: bool = False,
    show_strat_planes: bool = False,
    autoscale: bool = True,
    equal_xy: bool = False,
    show_dls: bool = False,
    axis_limit: int = 10,
    plane_size: int = 10,
    alpha_level: float = 0.4,
    color_index: int = 8,
    strat_data: pd.DataFrame | None = None,
) -> None:
    """Plot a single well in 3D.

    Args:
        panda: DataFrame with survey data (North, East, TVD, DLS columns).
        well_name: Name of the well for labeling.
        show_site: Whether to show the wellsite polygon.
        show_strat: Whether to show formation markers as points.
        show_strat_planes: Whether to show formation markers as planes.
        autoscale: Whether to autoscale axes to data.
        equal_xy: Whether to use equal scaling for X and Y axes.
        show_dls: Whether to color the trajectory by dogleg severity.
        axis_limit: Manual axis limit when not autoscaling.
        plane_size: Size of formation planes.
        alpha_level: Transparency level for planes (0-1).
        color_index: Index for well color from palette.
        strat_data: Optional DataFrame with stratigraphy data.
    """
    panda = panda.sort_values(by=["Depth"])

    north: list[float] = panda.North.tolist()
    east: list[float] = panda.East.tolist()
    tvd_positiv: list[float] = panda.TVD.tolist()
    dls: list[float] = panda.DLS.tolist()

    # Calculate negative TVD for display
    tvd: list[float] = [-v for v in tvd_positiv]

    # Calculate axis limits
    northmax: float = max(north)
    northmin: float = min(north)
    eastmax: float = max(east)
    eastmin: float = min(east)

    # Create figure
    plt.figure()
    plt.style.use("seaborn-v0_8")
    ax = plt.axes(projection="3d")

    # Get line color
    line_color = get_color_from_index(color_index)

    # Plot well trajectory
    if show_dls:
        ax.scatter(east, north, tvd, c=dls, s=42, cmap="plasma", label=well_name)
        ax.plot(east, north, tvd, color="#010101", linewidth=1.2, label=well_name)
    else:
        ax.plot(east, north, tvd, color=line_color, linewidth=1.6, label=well_name)

    ax.tick_params(labelsize=6)

    # Handle equal XY scaling
    if equal_xy:
        min_val = min(eastmin, northmin)
        max_val = max(eastmax, northmax)
        eastmin = northmin = min_val
        eastmax = northmax = max_val

    # Set axis limits
    if autoscale:
        ax.set_xlim(eastmin - 100, eastmax + 100)
        ax.set_ylim(northmin - 100, northmax + 100)
    else:
        ax.set_xlim(-axis_limit, axis_limit)
        ax.set_ylim(-axis_limit, axis_limit)

    # Axis labels
    ax.set_xlabel("Easting", fontsize=7)
    ax.set_ylabel("Northing", fontsize=7)
    ax.set_zlabel("Depth TVD[m]", fontsize=7)

    # Add wellsite polygon
    if show_site:
        bohrplatz = create_wellsite_polygon(30)
        layer4: Poly3DCollection = Poly3DCollection([bohrplatz], alpha=0.4)
        face_color: list[float] = [0.2, 0.1, 0.2]
        layer4.set_facecolor(face_color)
        ax.add_collection3d(layer4)

    # Add stratigraphy markers
    if strat_data is not None and (show_strat or show_strat_planes):
        strat_data = strat_data.sort_values(by=["Depth"])

        col_fm: list[str] = strat_data.Fm_Color.tolist()
        north_fm: list[float] = strat_data.Fm_North.tolist()
        east_fm: list[float] = strat_data.Fm_East.tolist()
        tvd_fm_pos: list[float] = strat_data.Fm_TVD.tolist()
        tvd_fm: list[float] = [-v for v in tvd_fm_pos]

        if show_strat and not show_strat_planes:
            for idx in range(len(tvd_fm)):
                ax.scatter3D(
                    east_fm[idx],
                    north_fm[idx],
                    tvd_fm[idx],
                    c=col_fm[idx],
                    marker="o",
                    s=24,
                )

        if show_strat_planes:
            for idx in range(len(tvd_fm)):
                plane_coords = create_formation_plane(
                    east_fm[idx], north_fm[idx], tvd_fm[idx], plane_size
                )
                plane: Poly3DCollection = Poly3DCollection(
                    [plane_coords], alpha=alpha_level
                )
                plane.set_facecolor([col_fm[idx]])
                ax.add_collection3d(plane)

    plt.legend(fontsize=7)
    plt.show()


def plot_multiple_wells(
    well_objects: list[Any],
    show_stratigraphy: bool = False,
    show_legend: bool = False,
    show_dem: bool = False,
    show_polygon: bool = False,
    xyz_file: str | None = None,
    nodes_file: str | None = None,
    attributes_file: str | None = None,
) -> None:
    """Plot multiple wells on a geographic map.

    Args:
        well_objects: List of WellMap objects with loaded data.
        show_stratigraphy: Whether to show formation markers.
        show_legend: Whether to show the legend.
        show_dem: Whether to show DEM surface from xyz file.
        show_polygon: Whether to show surface from polygon data.
        xyz_file: Path to xyz data file for DEM.
        nodes_file: Path to nodes file for polygon data.
        attributes_file: Path to attributes file for polygon data.
    """
    plt.figure()
    plt.style.use("fivethirtyeight")
    ax = plt.axes(projection="3d")

    for y in well_objects:
        y.tvdtolist()
        y.lattolist()
        y.lontolist()
        labels: str = y.getName()
        ax.plot(
            y.lonlist,
            y.latlist,
            y.tvdlist,
            color="#ff0000",
            linewidth=1.4,
            label=labels,
        )

        # Add wellsite marker
        bohrplatz: list[list[float]] = [
            [y.lonlist[0] - 0.0005, y.latlist[0] + 0.0005, y.tvdlist[0]],
            [y.lonlist[0] - 0.0005, y.latlist[0] - 0.0005, y.tvdlist[0]],
            [y.lonlist[0] + 0.0005, y.latlist[0] - 0.0005, y.tvdlist[0]],
            [y.lonlist[0] + 0.0005, y.latlist[0] + 0.0005, y.tvdlist[0]],
            [y.lonlist[0] - 0.0005, y.latlist[0] + 0.0005, y.tvdlist[0]],
        ]
        layer_y: Poly3DCollection = Poly3DCollection([bohrplatz], alpha=0.2)
        face_color: list[float] = [0.2, 0.1, 0.4]
        layer_y.set_facecolor(face_color)
        ax.add_collection3d(layer_y)

        if show_legend:
            ax.legend(fontsize=7)

    # Add stratigraphy if enabled
    if show_stratigraphy:
        for y in well_objects:
            y.strattolist()
            for idx in range(len(y.strat_altilist)):
                ax.scatter3D(
                    y.strat_lonlist[idx],
                    y.strat_latlist[idx],
                    y.strat_altilist[idx],
                    c=y.strat_colorlist[idx],
                    marker="o",
                    s=28,
                )

    ax.tick_params(labelsize=6)
    ax.set_xlabel("Longitude", fontsize=7)
    ax.set_ylabel("Latitude", fontsize=7)
    ax.set_zlabel("Depth [m]", fontsize=7)

    # Add polygon surface data
    if show_polygon and nodes_file and attributes_file:
        try:
            attribute_names: list[str] = ["shapeid", "ID", "HOEHE"]
            node_names: list[str] = ["shapeid", "x", "y"]

            panda_att: pd.DataFrame = pd.read_csv(
                attributes_file, header=0, names=attribute_names
            )
            panda_nod: pd.DataFrame = pd.read_csv(
                nodes_file, header=0, names=node_names
            )

            z_att: list[float] = panda_att.HOEHE.tolist()
            id_att: list[int] = panda_att.shapeid.tolist()
            x: list[float] = panda_nod.x.tolist()
            y: list[float] = panda_nod.y.tolist()
            id_nod: list[int] = panda_nod.shapeid.tolist()

            dict_att: dict[int, float] = dict(zip(id_att, z_att))
            new_z: list[float] = []

            for item in id_nod:
                if item in dict_att:
                    new_z.append(dict_att[item])

            # Set up 2D grid
            xi: Any = np.linspace(min(x), max(x))
            yi: Any = np.linspace(min(y), max(y))
            X: Any
            Y: Any
            X, Y = np.meshgrid(xi, yi)

            Z: Any = griddata(
                (x, y), new_z, (xi[None, :], yi[:, None]), method="linear"
            )

            ax.plot_surface(
                X, Y, Z, rstride=1, cstride=1, alpha=0.6, linewidth=1, antialiased=True
            )
        except Exception:
            pass

    # Add DEM surface from xyz file
    if show_dem and xyz_file:
        try:
            xyz_header: list[str] = ["Field_1", "Field_2", "Field_3"]
            xyz_dataframe: pd.DataFrame = pd.read_csv(xyz_file, names=xyz_header)

            x = xyz_dataframe["Field_1"].tolist()
            y = xyz_dataframe["Field_2"].tolist()
            z: list[float] = xyz_dataframe["Field_3"].tolist()

            xi = np.linspace(min(x), max(x))
            yi = np.linspace(min(y), max(y))
            X, Y = np.meshgrid(xi, yi)

            Z = griddata((x, y), z, (xi[None, :], yi[:, None]), method="linear")

            ax.scatter(x, y, z, c="#aaaaaa", s=9)
            cs = plt.tricontourf(x, y, z, 100, cmap="terrain", alpha=0.3)
            plt.colorbar(cs, aspect=5, shrink=0.5)
        except Exception:
            pass

    plt.show()
