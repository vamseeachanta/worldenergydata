# ABOUTME: OBJ file parser for vessel hull models
# ABOUTME: Parses Wavefront OBJ format and extracts mesh geometry

"""
OBJ File Parser for Vessel Hull Models

Parses Wavefront OBJ files and extracts mesh geometry data including
vertices, faces, normals, and texture coordinates.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

from worldenergydata.modules.vessel_hull_models.exceptions import (
    OBJParseError,
    OBJValidationError,
)


@dataclass
class OBJMesh:
    """
    Parsed OBJ mesh data structure.

    Stores vertices, faces, normals, and computed bounding box.
    """
    vertices: np.ndarray  # Shape: (N, 3) - XYZ coordinates
    faces: np.ndarray  # Shape: (M, 3 or 4) - Vertex indices (0-based)
    normals: Optional[np.ndarray] = None  # Shape: (K, 3) - Normal vectors
    texcoords: Optional[np.ndarray] = None  # Shape: (L, 2 or 3) - Texture coords

    # Metadata
    material_name: Optional[str] = None
    object_name: Optional[str] = None
    source_file: Optional[str] = None

    # Computed properties (cached)
    _bbox_min: Optional[np.ndarray] = field(default=None, repr=False)
    _bbox_max: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def vertex_count(self) -> int:
        """Number of vertices in the mesh"""
        return len(self.vertices)

    @property
    def face_count(self) -> int:
        """Number of faces in the mesh"""
        return len(self.faces)

    @property
    def bbox_min(self) -> np.ndarray:
        """Minimum bounding box coordinates"""
        if self._bbox_min is None:
            self._bbox_min = np.min(self.vertices, axis=0)
        return self._bbox_min

    @property
    def bbox_max(self) -> np.ndarray:
        """Maximum bounding box coordinates"""
        if self._bbox_max is None:
            self._bbox_max = np.max(self.vertices, axis=0)
        return self._bbox_max

    @property
    def dimensions(self) -> Dict[str, float]:
        """
        Mesh dimensions (length, width, height).

        Assumes X=length, Y=width, Z=height.
        """
        size = self.bbox_max - self.bbox_min
        return {
            "length": float(size[0]),
            "width": float(size[1]),
            "height": float(size[2]),
        }

    @property
    def center(self) -> np.ndarray:
        """Center point of the bounding box"""
        return (self.bbox_min + self.bbox_max) / 2

    def get_stats(self) -> Dict[str, Any]:
        """Get mesh statistics"""
        dims = self.dimensions
        return {
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
            "has_normals": self.normals is not None,
            "has_texcoords": self.texcoords is not None,
            "bbox_min": self.bbox_min.tolist(),
            "bbox_max": self.bbox_max.tolist(),
            "dimensions": dims,
            "length": dims["length"],
            "width": dims["width"],
            "height": dims["height"],
            "material": self.material_name,
            "object_name": self.object_name,
        }


class OBJParser:
    """
    Parser for Wavefront OBJ files.

    Handles standard OBJ format with vertices, faces, normals,
    and texture coordinates.
    """

    def __init__(self):
        self._vertices: List[List[float]] = []
        self._normals: List[List[float]] = []
        self._texcoords: List[List[float]] = []
        self._faces: List[List[int]] = []
        self._material_name: Optional[str] = None
        self._object_name: Optional[str] = None

    def parse(self, file_path: Path) -> OBJMesh:
        """
        Parse an OBJ file and return mesh data.

        Args:
            file_path: Path to OBJ file

        Returns:
            OBJMesh with parsed geometry

        Raises:
            OBJParseError: If file cannot be parsed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise OBJParseError(f"OBJ file not found: {file_path}")

        if not file_path.suffix.lower() == ".obj":
            raise OBJParseError(f"Expected .obj file, got: {file_path.suffix}")

        # Reset state
        self._vertices = []
        self._normals = []
        self._texcoords = []
        self._faces = []
        self._material_name = None
        self._object_name = None

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, start=1):
                    self._parse_line(line.strip(), line_num)
        except Exception as e:
            raise OBJParseError(f"Error parsing {file_path}: {e}")

        if not self._vertices:
            raise OBJParseError(f"No vertices found in {file_path}")

        if not self._faces:
            raise OBJParseError(f"No faces found in {file_path}")

        # Convert to numpy arrays
        vertices = np.array(self._vertices, dtype=np.float32)
        faces = np.array(self._faces, dtype=np.int32)
        normals = np.array(self._normals, dtype=np.float32) if self._normals else None
        texcoords = np.array(self._texcoords, dtype=np.float32) if self._texcoords else None

        return OBJMesh(
            vertices=vertices,
            faces=faces,
            normals=normals,
            texcoords=texcoords,
            material_name=self._material_name,
            object_name=self._object_name,
            source_file=str(file_path),
        )

    def _parse_line(self, line: str, line_num: int) -> None:
        """Parse a single line of OBJ file"""
        if not line or line.startswith("#"):
            return

        parts = line.split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "v":
            # Vertex: v x y z [w]
            self._parse_vertex(parts[1:], line_num)

        elif cmd == "vn":
            # Normal: vn x y z
            self._parse_normal(parts[1:], line_num)

        elif cmd == "vt":
            # Texture coord: vt u [v] [w]
            self._parse_texcoord(parts[1:], line_num)

        elif cmd == "f":
            # Face: f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3 ...
            self._parse_face(parts[1:], line_num)

        elif cmd == "usemtl":
            # Material: usemtl material_name
            self._material_name = " ".join(parts[1:]) if len(parts) > 1 else None

        elif cmd == "o" or cmd == "g":
            # Object/Group: o name or g name
            self._object_name = " ".join(parts[1:]) if len(parts) > 1 else None

    def _parse_vertex(self, coords: List[str], line_num: int) -> None:
        """Parse vertex coordinates"""
        try:
            if len(coords) < 3:
                raise OBJParseError(f"Line {line_num}: Vertex needs at least 3 coordinates")
            x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
            self._vertices.append([x, y, z])
        except ValueError as e:
            raise OBJParseError(f"Line {line_num}: Invalid vertex coordinates: {e}")

    def _parse_normal(self, coords: List[str], line_num: int) -> None:
        """Parse normal vector"""
        try:
            if len(coords) < 3:
                raise OBJParseError(f"Line {line_num}: Normal needs 3 coordinates")
            x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
            self._normals.append([x, y, z])
        except ValueError as e:
            raise OBJParseError(f"Line {line_num}: Invalid normal coordinates: {e}")

    def _parse_texcoord(self, coords: List[str], line_num: int) -> None:
        """Parse texture coordinates"""
        try:
            if len(coords) < 1:
                raise OBJParseError(f"Line {line_num}: Texture coord needs at least 1 value")
            u = float(coords[0])
            v = float(coords[1]) if len(coords) > 1 else 0.0
            self._texcoords.append([u, v])
        except ValueError as e:
            raise OBJParseError(f"Line {line_num}: Invalid texture coordinates: {e}")

    def _parse_face(self, indices: List[str], line_num: int) -> None:
        """
        Parse face definition.

        Handles formats:
        - f v1 v2 v3 (vertices only)
        - f v1/vt1 v2/vt2 v3/vt3 (vertices and texcoords)
        - f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3 (vertices, texcoords, normals)
        - f v1//vn1 v2//vn2 v3//vn3 (vertices and normals)
        """
        if len(indices) < 3:
            raise OBJParseError(f"Line {line_num}: Face needs at least 3 vertices")

        vertex_indices = []

        for idx_str in indices:
            # Split on / to get v/vt/vn components
            parts = idx_str.split("/")

            try:
                # Vertex index (required, 1-based in OBJ, convert to 0-based)
                v_idx = int(parts[0])
                if v_idx < 0:
                    # Negative indices are relative to end
                    v_idx = len(self._vertices) + v_idx + 1
                vertex_indices.append(v_idx - 1)  # Convert to 0-based
            except (ValueError, IndexError) as e:
                raise OBJParseError(f"Line {line_num}: Invalid face index: {e}")

        # Handle quads by triangulating
        if len(vertex_indices) == 4:
            # Split quad into two triangles
            self._faces.append([vertex_indices[0], vertex_indices[1], vertex_indices[2]])
            self._faces.append([vertex_indices[0], vertex_indices[2], vertex_indices[3]])
        elif len(vertex_indices) == 3:
            self._faces.append(vertex_indices)
        else:
            # For polygons with more than 4 vertices, fan triangulation
            for i in range(1, len(vertex_indices) - 1):
                self._faces.append([
                    vertex_indices[0],
                    vertex_indices[i],
                    vertex_indices[i + 1]
                ])


def parse_obj_file(file_path: Path) -> OBJMesh:
    """
    Convenience function to parse an OBJ file.

    Args:
        file_path: Path to OBJ file

    Returns:
        OBJMesh with parsed geometry
    """
    parser = OBJParser()
    return parser.parse(file_path)


def validate_obj_file(
    file_path: Path,
    expected_loa: Optional[float] = None,
    expected_beam: Optional[float] = None,
    expected_depth: Optional[float] = None,
    tolerance: float = 0.05,
) -> Dict[str, Any]:
    """
    Validate OBJ file and optionally check dimensions.

    Args:
        file_path: Path to OBJ file
        expected_loa: Expected length overall (optional)
        expected_beam: Expected beam/width (optional)
        expected_depth: Expected depth/height (optional)
        tolerance: Tolerance for dimension validation (default 5%)

    Returns:
        Validation result dict with status and details

    Raises:
        OBJValidationError: If validation fails
    """
    result = {
        "valid": True,
        "file_path": str(file_path),
        "errors": [],
        "warnings": [],
        "stats": {},
    }

    try:
        mesh = parse_obj_file(file_path)
        stats = mesh.get_stats()
        result["stats"] = stats

        # Dimension validation
        if expected_loa is not None:
            actual_loa = stats["length"]
            if abs(actual_loa - expected_loa) / expected_loa > tolerance:
                result["warnings"].append(
                    f"LOA mismatch: expected {expected_loa:.2f}m, got {actual_loa:.2f}m"
                )

        if expected_beam is not None:
            actual_beam = stats["width"]
            if abs(actual_beam - expected_beam) / expected_beam > tolerance:
                result["warnings"].append(
                    f"Beam mismatch: expected {expected_beam:.2f}m, got {actual_beam:.2f}m"
                )

        if expected_depth is not None:
            actual_depth = stats["height"]
            if abs(actual_depth - expected_depth) / expected_depth > tolerance:
                result["warnings"].append(
                    f"Depth mismatch: expected {expected_depth:.2f}m, got {actual_depth:.2f}m"
                )

    except OBJParseError as e:
        result["valid"] = False
        result["errors"].append(str(e))

    return result
