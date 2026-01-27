# ABOUTME: PNG export for vessel hull models using matplotlib
# ABOUTME: Creates static preview images for quality checking

"""
PNG Exporter for Vessel Hull Models

Creates static PNG preview images using matplotlib's 3D projection.
More reliable than kaleido for static image generation.
"""

from pathlib import Path
from typing import Optional, Tuple

try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from worldenergydata.modules.vessel_hull_models.exceptions import VisualizationError
from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import (
    OBJMesh,
    parse_obj_file,
)


def _check_matplotlib():
    """Check if matplotlib is available"""
    if not MATPLOTLIB_AVAILABLE:
        raise VisualizationError(
            "Matplotlib is required for PNG export. Install with: pip install matplotlib"
        )


def export_hull_png(
    mesh: OBJMesh,
    output_path: Path,
    title: Optional[str] = None,
    figsize: Tuple[int, int] = (12, 9),
    dpi: int = 150,
    elevation: float = 25,
    azimuth: float = -60,
    color: str = "steelblue",
    edge_color: str = "darkblue",
    alpha: float = 0.8,
    show_stats: bool = True,
) -> Path:
    """
    Export an OBJMesh to PNG image.

    Args:
        mesh: OBJMesh object with parsed geometry
        output_path: Path for output PNG file
        title: Figure title (defaults to object name)
        figsize: Figure size in inches (width, height)
        dpi: Image resolution (dots per inch)
        elevation: Camera elevation angle in degrees
        azimuth: Camera azimuth angle in degrees
        color: Face color
        edge_color: Edge line color
        alpha: Face transparency (0-1)
        show_stats: Show mesh statistics on image

    Returns:
        Path to created PNG file
    """
    _check_matplotlib()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create figure
    fig = plt.figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111, projection="3d")

    # Get vertices and faces
    vertices = mesh.vertices
    faces = mesh.faces

    # Create polygon collection for faces
    verts_list = []
    for face in faces:
        face_verts = vertices[face]
        verts_list.append(face_verts)

    # Create 3D polygon collection
    poly = Poly3DCollection(
        verts_list,
        alpha=alpha,
        facecolor=color,
        edgecolor=edge_color,
        linewidth=0.1,
    )
    ax.add_collection3d(poly)

    # Set axis limits based on mesh dimensions
    dims = mesh.dimensions
    center = mesh.center

    # Calculate bounds with padding
    pad = 0.1
    x_range = dims["length"] * (1 + pad)
    y_range = dims["width"] * (1 + pad)
    z_range = dims["height"] * (1 + pad)

    # Make axes equal scale
    max_range = max(x_range, y_range, z_range) / 2

    ax.set_xlim(center[0] - max_range, center[0] + max_range)
    ax.set_ylim(center[1] - max_range, center[1] + max_range)
    ax.set_zlim(center[2] - max_range, center[2] + max_range)

    # Set viewing angle
    ax.view_init(elev=elevation, azim=azimuth)

    # Labels
    ax.set_xlabel("X (m)", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)
    ax.set_zlabel("Z (m)", fontsize=10)

    # Title
    if title is None:
        title = mesh.object_name or "Vessel Hull"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

    # Add statistics text box
    if show_stats:
        stats = mesh.get_stats()
        stats_text = (
            f"Dimensions:\n"
            f"  L: {stats['length']:.1f}m\n"
            f"  B: {stats['width']:.1f}m\n"
            f"  D: {stats['height']:.1f}m\n"
            f"Mesh:\n"
            f"  Vertices: {stats['vertex_count']:,}\n"
            f"  Faces: {stats['face_count']:,}"
        )
        ax.text2D(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="gray"),
        )

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path


def render_obj_to_png(
    obj_path: Path,
    output_path: Optional[Path] = None,
    **kwargs,
) -> Path:
    """
    Render an OBJ file to PNG image.

    Args:
        obj_path: Path to OBJ file
        output_path: Output PNG path (defaults to same name with .png extension)
        **kwargs: Additional arguments passed to export_hull_png

    Returns:
        Path to created PNG file
    """
    _check_matplotlib()

    obj_path = Path(obj_path)
    mesh = parse_obj_file(obj_path)

    if output_path is None:
        output_path = obj_path.with_suffix(".png")

    if "title" not in kwargs:
        kwargs["title"] = obj_path.stem.replace("_", " ").title()

    return export_hull_png(mesh, output_path, **kwargs)


def generate_preview_gallery(
    obj_files: list[Path],
    output_dir: Path,
    thumbnail_size: Tuple[int, int] = (8, 6),
    dpi: int = 100,
) -> list[Path]:
    """
    Generate PNG previews for multiple OBJ files.

    Args:
        obj_files: List of OBJ file paths
        output_dir: Output directory for PNG files
        thumbnail_size: Figure size for thumbnails
        dpi: Image resolution

    Returns:
        List of created PNG file paths
    """
    _check_matplotlib()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    for obj_path in obj_files:
        obj_path = Path(obj_path)
        png_name = obj_path.stem + ".png"
        png_path = output_dir / png_name

        try:
            render_obj_to_png(
                obj_path,
                png_path,
                figsize=thumbnail_size,
                dpi=dpi,
            )
            created_files.append(png_path)
            print(f"  ✓ {obj_path.stem}")
        except Exception as e:
            print(f"  ✗ {obj_path.stem}: {e}")

    return created_files


def create_comparison_grid(
    obj_files: list[Path],
    output_path: Path,
    cols: int = 3,
    cell_size: Tuple[float, float] = (4, 3),
    dpi: int = 150,
) -> Path:
    """
    Create a grid comparison image of multiple hulls.

    Args:
        obj_files: List of OBJ file paths
        output_path: Output PNG path
        cols: Number of columns in grid
        cell_size: Size of each cell (width, height) in inches
        dpi: Image resolution

    Returns:
        Path to created PNG file
    """
    _check_matplotlib()

    n_files = len(obj_files)
    if n_files == 0:
        raise VisualizationError("No OBJ files provided")

    rows = (n_files + cols - 1) // cols

    fig = plt.figure(
        figsize=(cols * cell_size[0], rows * cell_size[1]), facecolor="white"
    )

    for idx, obj_path in enumerate(obj_files):
        obj_path = Path(obj_path)
        ax = fig.add_subplot(rows, cols, idx + 1, projection="3d")

        try:
            mesh = parse_obj_file(obj_path)
            vertices = mesh.vertices
            faces = mesh.faces

            # Create polygon collection
            verts_list = [vertices[face] for face in faces]
            poly = Poly3DCollection(
                verts_list,
                alpha=0.7,
                facecolor="steelblue",
                edgecolor="darkblue",
                linewidth=0.05,
            )
            ax.add_collection3d(poly)

            # Set limits
            dims = mesh.dimensions
            center = mesh.center
            max_range = max(dims["length"], dims["width"], dims["height"]) / 2 * 1.1

            ax.set_xlim(center[0] - max_range, center[0] + max_range)
            ax.set_ylim(center[1] - max_range, center[1] + max_range)
            ax.set_zlim(center[2] - max_range, center[2] + max_range)

            ax.view_init(elev=20, azim=-60)
            ax.set_title(obj_path.stem[:25], fontsize=9, pad=2)

            # Hide axis labels for cleaner look
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])

        except Exception as e:
            ax.text(
                0.5,
                0.5,
                0.5,
                f"Error:\n{str(e)[:30]}",
                ha="center",
                va="center",
                fontsize=8,
            )
            ax.set_title(obj_path.stem[:25], fontsize=9, color="red")

    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path
