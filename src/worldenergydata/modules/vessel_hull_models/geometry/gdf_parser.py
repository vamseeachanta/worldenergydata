# ABOUTME: Parser for OrcaWave/WAMIT GDF (Geometry Definition File) format
# ABOUTME: Converts panel mesh files to OBJ format for visualization

"""
GDF Parser for OrcaWave/WAMIT geometry files.

GDF files contain panel mesh definitions for hydrodynamic analysis.
This module parses GDF files and converts them to OBJ format.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from worldenergydata.modules.vessel_hull_models.exceptions import OBJParseError
from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import OBJMesh


@dataclass
class GDFHeader:
    """Header information from a GDF file."""

    description: str
    unit_length: float
    gravity: float
    symmetry_x: bool
    symmetry_y: bool
    panel_count: int


def parse_gdf_header(lines: list[str]) -> tuple[GDFHeader, int]:
    """
    Parse the header of a GDF file.

    Args:
        lines: All lines from the GDF file

    Returns:
        Tuple of (GDFHeader, start_line_index for vertex data)
    """
    if len(lines) < 4:
        raise OBJParseError("GDF file too short - missing header")

    # Line 1: Description
    description = lines[0].strip()

    # Line 2: ULEN GRAV
    parts = lines[1].split()
    if len(parts) < 2:
        raise OBJParseError("Invalid GDF header - missing ULEN GRAV")
    unit_length = float(parts[0])
    gravity = float(parts[1])

    # Line 3: ISX ISY (symmetry flags)
    parts = lines[2].split()
    if len(parts) < 2:
        raise OBJParseError("Invalid GDF header - missing ISX ISY")
    symmetry_x = int(parts[0]) == 1
    symmetry_y = int(parts[1]) == 1

    # Line 4: Panel count (may include label like "NPAN" or "NEQN")
    panel_parts = lines[3].split()
    panel_count = int(panel_parts[0])

    header = GDFHeader(
        description=description,
        unit_length=unit_length,
        gravity=gravity,
        symmetry_x=symmetry_x,
        symmetry_y=symmetry_y,
        panel_count=panel_count,
    )

    return header, 4  # Vertex data starts at line 4 (0-indexed)


def _detect_vertices_per_panel(data_line_count: int, panel_count: int) -> int:
    """
    Detect whether GDF uses quads (4 vertices) or triangles (3 vertices) per panel.

    Args:
        data_line_count: Number of non-empty data lines
        panel_count: Declared panel count from header

    Returns:
        4 for quads, 3 for triangles
    """
    if panel_count <= 0:
        return 3
    ratio = data_line_count / panel_count
    return 4 if ratio >= 3.5 else 3


def _parse_vertex_line(line: str) -> tuple[float, float, float] | None:
    """
    Parse a single vertex line.

    Args:
        line: Line containing x, y, z coordinates

    Returns:
        Tuple of (x, y, z) or None if parsing fails
    """
    parts = line.split()
    if len(parts) < 3:
        return None
    try:
        return float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        return None


def _add_vertex_to_map(
    coords: tuple[float, float, float],
    vertices: list[tuple[float, float, float]],
    vertex_map: dict[tuple[float, float, float], int],
) -> int:
    """
    Add vertex to map if unique, return its index.

    Args:
        coords: Vertex coordinates (x, y, z)
        vertices: List of unique vertices
        vertex_map: Map from rounded coords to 1-indexed vertex index

    Returns:
        1-indexed vertex index
    """
    vertex_key = (round(coords[0], 6), round(coords[1], 6), round(coords[2], 6))

    if vertex_key not in vertex_map:
        vertex_map[vertex_key] = len(vertices) + 1  # 1-indexed for OBJ
        vertices.append(coords)

    return vertex_map[vertex_key]


def _read_panel_vertices(
    lines: list[str],
    start_line: int,
    vertices_per_panel: int,
    vertices: list[tuple[float, float, float]],
    vertex_map: dict[tuple[float, float, float], int],
) -> tuple[list[int], int]:
    """
    Read vertices for a single panel from file lines.

    Args:
        lines: All file lines
        start_line: Line index to start reading from
        vertices_per_panel: Expected number of vertices (3 or 4)
        vertices: Accumulated unique vertices list
        vertex_map: Map for deduplication

    Returns:
        Tuple of (panel_vertex_indices, next_line_index)
    """
    panel_vertices: list[int] = []
    current_line = start_line

    while len(panel_vertices) < vertices_per_panel and current_line < len(lines):
        line = lines[current_line].strip()
        current_line += 1

        if not line:
            continue

        coords = _parse_vertex_line(line)
        if coords is not None:
            vertex_idx = _add_vertex_to_map(coords, vertices, vertex_map)
            panel_vertices.append(vertex_idx)

    return panel_vertices, current_line


def _create_faces_from_panel(
    panel_vertices: list[int],
    vertices_per_panel: int,
) -> list[tuple[int, ...]]:
    """
    Create face(s) from panel vertices.

    Quads are split into 2 triangles for OBJ compatibility.

    Args:
        panel_vertices: List of vertex indices for this panel
        vertices_per_panel: Expected count (3 or 4)

    Returns:
        List of face tuples (1 for triangles, 2 for quads)
    """
    if vertices_per_panel == 4 and len(panel_vertices) == 4:
        # Split quad into 2 triangles: (v1,v2,v3) and (v1,v3,v4)
        return [
            (panel_vertices[0], panel_vertices[1], panel_vertices[2]),
            (panel_vertices[0], panel_vertices[2], panel_vertices[3]),
        ]
    if vertices_per_panel == 3 and len(panel_vertices) == 3:
        return [tuple(panel_vertices)]
    return []


def _parse_panels(
    lines: list[str],
    data_start: int,
    vertices_per_panel: int,
    max_panels: int,
) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    """
    Parse all panels from GDF data lines.

    Args:
        lines: All file lines
        data_start: Index of first data line
        vertices_per_panel: 3 for triangles, 4 for quads
        max_panels: Maximum number of panels to parse

    Returns:
        Tuple of (vertices, faces)
    """
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    vertex_map: dict[tuple[float, float, float], int] = {}

    current_line = data_start
    panel_count = 0

    while current_line < len(lines) and panel_count < max_panels:
        panel_vertices, current_line = _read_panel_vertices(
            lines, current_line, vertices_per_panel, vertices, vertex_map
        )

        new_faces = _create_faces_from_panel(panel_vertices, vertices_per_panel)
        if new_faces:
            faces.extend(new_faces)
            panel_count += 1

    return vertices, faces


def _to_obj_mesh(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    object_name: str,
) -> OBJMesh:
    """
    Convert parsed vertices and faces to OBJMesh.

    Args:
        vertices: List of vertex coordinates
        faces: List of face tuples (1-indexed)
        object_name: Name for the mesh object

    Returns:
        OBJMesh with numpy arrays (0-indexed faces)
    """
    vertices_array = np.array(vertices, dtype=np.float64)
    faces_array = np.array([[v - 1 for v in f] for f in faces], dtype=np.int32)

    return OBJMesh(
        vertices=vertices_array,
        faces=faces_array,
        normals=None,
        texcoords=None,
        object_name=object_name,
        material_name=None,
    )


def parse_gdf_file(file_path: Path) -> OBJMesh:
    """
    Parse a GDF file and return a OBJMesh.

    Standard WAMIT GDF format uses 4 vertices per panel (quadrilaterals),
    but some files use 3 vertices per panel (triangles). This parser
    auto-detects the format based on data line count vs declared panel count.

    Args:
        file_path: Path to the GDF file

    Returns:
        OBJMesh object with parsed geometry
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise OBJParseError(f"GDF file not found: {file_path}")

    with open(file_path, "r") as f:
        lines = f.readlines()

    header, data_start = parse_gdf_header(lines)

    data_lines = [line for line in lines[data_start:] if line.strip()]
    data_line_count = len(data_lines)

    vertices_per_panel = _detect_vertices_per_panel(data_line_count, header.panel_count)
    max_panels = header.panel_count if vertices_per_panel == 4 else data_line_count // 3

    vertices, faces = _parse_panels(lines, data_start, vertices_per_panel, max_panels)

    if header.symmetry_x or header.symmetry_y:
        vertices, faces = _apply_symmetry(
            vertices, faces, header.symmetry_x, header.symmetry_y
        )

    return _to_obj_mesh(vertices, faces, header.description)


def _apply_symmetry(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    symmetry_x: bool,
    symmetry_y: bool,
) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    """
    Apply symmetry to create full hull from partial definition.

    Args:
        vertices: Original vertices
        faces: Original faces
        symmetry_x: If True, mirror across X=0 plane
        symmetry_y: If True, mirror across Y=0 plane

    Returns:
        Tuple of (expanded_vertices, expanded_faces)
    """
    all_vertices = list(vertices)
    all_faces = list(faces)

    vertex_offset = len(vertices)

    if symmetry_y:
        # Mirror across Y=0 plane (Y -> -Y)
        vertex_map = {}
        for i, (x, y, z) in enumerate(vertices):
            mirrored = (x, -y, z)
            if (
                mirrored not in vertex_map and y != 0
            ):  # Don't duplicate centerline vertices
                vertex_map[i + 1] = len(all_vertices) + 1
                all_vertices.append(mirrored)
            elif y == 0:
                vertex_map[i + 1] = i + 1  # Reuse centerline vertex

        # Add mirrored faces (reverse winding for correct normals)
        for face in faces:
            mirrored_face = tuple(vertex_map.get(v, v) for v in reversed(face))
            all_faces.append(mirrored_face)

    if symmetry_x:
        # Mirror across X=0 plane (X -> -X)
        current_vertex_count = len(all_vertices)
        current_faces = list(all_faces)
        vertex_map = {}

        for i, (x, y, z) in enumerate(all_vertices[:current_vertex_count]):
            mirrored = (-x, y, z)
            if mirrored not in vertex_map and x != 0:
                vertex_map[i + 1] = len(all_vertices) + 1
                all_vertices.append(mirrored)
            elif x == 0:
                vertex_map[i + 1] = i + 1

        for face in current_faces:
            mirrored_face = tuple(vertex_map.get(v, v) for v in reversed(face))
            all_faces.append(mirrored_face)

    return all_vertices, all_faces


def convert_gdf_to_obj(gdf_path: Path, obj_path: Path) -> OBJMesh:
    """
    Convert a GDF file to OBJ format.

    Args:
        gdf_path: Path to input GDF file
        obj_path: Path for output OBJ file

    Returns:
        OBJMesh object representing the converted geometry
    """
    mesh = parse_gdf_file(gdf_path)

    # Write OBJ file
    with open(obj_path, "w") as f:
        f.write(f"# Converted from GDF: {gdf_path.name}\n")
        f.write(f"# {mesh.object_name}\n")
        f.write(f"# Vertices: {mesh.vertex_count}\n")
        f.write(f"# Faces: {mesh.face_count}\n\n")

        if mesh.object_name:
            f.write(f"o {mesh.object_name.replace(' ', '_')}\n\n")

        # Write vertices
        for v in mesh.vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        f.write("\n")

        # Write faces (OBJ uses 1-indexed vertices)
        for face in mesh.faces:
            face_str = " ".join(str(v + 1) for v in face)
            f.write(f"f {face_str}\n")

    return mesh


def validate_gdf_file(file_path: Path) -> dict:
    """
    Validate a GDF file and return information about it.

    Args:
        file_path: Path to the GDF file

    Returns:
        Dictionary with validation results and statistics
    """
    try:
        mesh = parse_gdf_file(file_path)

        # Read header separately for more info
        with open(file_path, "r") as f:
            lines = f.readlines()
        header, _ = parse_gdf_header(lines)

        dims = mesh.dimensions
        stats = mesh.get_stats()

        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "header": {
                "description": header.description,
                "unit_length": header.unit_length,
                "gravity": header.gravity,
                "symmetry_x": header.symmetry_x,
                "symmetry_y": header.symmetry_y,
                "declared_panels": header.panel_count,
            },
            "stats": {
                "vertex_count": stats["vertex_count"],
                "face_count": stats["face_count"],
                "dimensions": dims,
            },
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "header": None,
            "stats": None,
        }
