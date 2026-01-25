# ABOUTME: Unit tests for OBJ file parser
# ABOUTME: Tests parsing, validation, and mesh operations with real vessel data

"""
Unit tests for OBJ Parser module.

Uses real vessel hull data (Sea Cypress) and synthetic test data
to verify parsing correctness and edge case handling.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
from typing import Generator

from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import (
    OBJParser,
    OBJMesh,
    parse_obj_file,
    validate_obj_file,
)
from worldenergydata.modules.vessel_hull_models.exceptions import (
    OBJParseError,
    OBJValidationError,
)


# Path to real vessel hull for integration tests
SEA_CYPRESS_PATH = Path(__file__).parents[3] / "data" / "modules" / "vessel_hull_models" / "hulls" / "sea_cypress.obj"


class TestOBJMesh:
    """Tests for OBJMesh dataclass"""

    def test_vertex_count(self) -> None:
        """Mesh reports correct vertex count"""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = OBJMesh(vertices=vertices, faces=faces)

        assert mesh.vertex_count == 3

    def test_face_count(self) -> None:
        """Mesh reports correct face count"""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2], [1, 2, 3]], dtype=np.int32)
        mesh = OBJMesh(vertices=vertices, faces=faces)

        assert mesh.face_count == 2

    def test_bounding_box(self) -> None:
        """Mesh computes correct bounding box"""
        vertices = np.array([
            [-5, -3, -2],
            [10, 8, 6],
            [0, 0, 0],
        ], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = OBJMesh(vertices=vertices, faces=faces)

        np.testing.assert_array_equal(mesh.bbox_min, [-5, -3, -2])
        np.testing.assert_array_equal(mesh.bbox_max, [10, 8, 6])

    def test_dimensions(self) -> None:
        """Mesh computes correct dimensions"""
        vertices = np.array([
            [0, 0, 0],
            [100, 20, 10],  # length=100, width=20, height=10
        ], dtype=np.float32)
        faces = np.array([[0, 1, 0]], dtype=np.int32)
        mesh = OBJMesh(vertices=vertices, faces=faces)

        dims = mesh.dimensions
        assert dims["length"] == pytest.approx(100.0)
        assert dims["width"] == pytest.approx(20.0)
        assert dims["height"] == pytest.approx(10.0)

    def test_center(self) -> None:
        """Mesh computes correct center point"""
        vertices = np.array([
            [0, 0, 0],
            [10, 20, 30],
        ], dtype=np.float32)
        faces = np.array([[0, 1, 0]], dtype=np.int32)
        mesh = OBJMesh(vertices=vertices, faces=faces)

        np.testing.assert_array_almost_equal(mesh.center, [5, 10, 15])

    def test_get_stats(self) -> None:
        """Mesh returns complete statistics"""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        normals = np.array([[0, 0, 1]], dtype=np.float32)
        mesh = OBJMesh(
            vertices=vertices,
            faces=faces,
            normals=normals,
            material_name="hull_material",
            object_name="test_hull",
        )

        stats = mesh.get_stats()

        assert stats["vertex_count"] == 3
        assert stats["face_count"] == 1
        assert stats["has_normals"] is True
        assert stats["has_texcoords"] is False
        assert stats["material"] == "hull_material"
        assert stats["object_name"] == "test_hull"


class TestOBJParser:
    """Tests for OBJParser class"""

    @pytest.fixture
    def simple_cube_obj(self) -> Generator[Path, None, None]:
        """Create a simple cube OBJ file for testing"""
        obj_content = """# Simple cube
o Cube
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
f 1 2 3 4
f 5 6 7 8
f 1 2 6 5
f 2 3 7 6
f 3 4 8 7
f 4 1 5 8
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        yield temp_path

        temp_path.unlink()

    @pytest.fixture
    def triangle_obj(self) -> Generator[Path, None, None]:
        """Create a simple triangle OBJ file"""
        obj_content = """# Simple triangle
v 0 0 0
v 1 0 0
v 0.5 1 0
f 1 2 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        yield temp_path

        temp_path.unlink()

    @pytest.fixture
    def obj_with_normals(self) -> Generator[Path, None, None]:
        """Create OBJ file with normals"""
        obj_content = """# Triangle with normals
v 0 0 0
v 1 0 0
v 0.5 1 0
vn 0 0 1
f 1//1 2//1 3//1
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        yield temp_path

        temp_path.unlink()

    @pytest.fixture
    def obj_with_texcoords(self) -> Generator[Path, None, None]:
        """Create OBJ file with texture coordinates"""
        obj_content = """# Triangle with texture coords
v 0 0 0
v 1 0 0
v 0.5 1 0
vt 0 0
vt 1 0
vt 0.5 1
f 1/1 2/2 3/3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        yield temp_path

        temp_path.unlink()

    def test_parse_simple_triangle(self, triangle_obj: Path) -> None:
        """Parser handles simple triangle mesh"""
        parser = OBJParser()
        mesh = parser.parse(triangle_obj)

        assert mesh.vertex_count == 3
        assert mesh.face_count == 1
        assert mesh.normals is None
        assert mesh.texcoords is None

    def test_parse_cube_triangulates_quads(self, simple_cube_obj: Path) -> None:
        """Parser triangulates quad faces into triangles"""
        parser = OBJParser()
        mesh = parser.parse(simple_cube_obj)

        assert mesh.vertex_count == 8
        # 6 quad faces become 12 triangles
        assert mesh.face_count == 12
        # All faces should be triangles
        assert mesh.faces.shape[1] == 3

    def test_parse_extracts_normals(self, obj_with_normals: Path) -> None:
        """Parser extracts vertex normals"""
        parser = OBJParser()
        mesh = parser.parse(obj_with_normals)

        assert mesh.normals is not None
        assert len(mesh.normals) == 1
        np.testing.assert_array_almost_equal(mesh.normals[0], [0, 0, 1])

    def test_parse_extracts_texcoords(self, obj_with_texcoords: Path) -> None:
        """Parser extracts texture coordinates"""
        parser = OBJParser()
        mesh = parser.parse(obj_with_texcoords)

        assert mesh.texcoords is not None
        assert len(mesh.texcoords) == 3

    def test_parse_extracts_object_name(self, simple_cube_obj: Path) -> None:
        """Parser extracts object name"""
        parser = OBJParser()
        mesh = parser.parse(simple_cube_obj)

        assert mesh.object_name == "Cube"

    def test_parse_stores_source_file(self, triangle_obj: Path) -> None:
        """Parser stores source file path"""
        parser = OBJParser()
        mesh = parser.parse(triangle_obj)

        assert mesh.source_file == str(triangle_obj)

    def test_parse_file_not_found(self) -> None:
        """Parser raises error for missing file"""
        parser = OBJParser()

        with pytest.raises(OBJParseError, match="not found"):
            parser.parse(Path("/nonexistent/file.obj"))

    def test_parse_wrong_extension(self) -> None:
        """Parser raises error for wrong file extension"""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            temp_path = Path(f.name)

        try:
            parser = OBJParser()
            with pytest.raises(OBJParseError, match="Expected .obj"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_empty_vertices(self) -> None:
        """Parser raises error for file with no vertices"""
        obj_content = """# Empty file
# Just comments
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            parser = OBJParser()
            with pytest.raises(OBJParseError, match="No vertices"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_no_faces(self) -> None:
        """Parser raises error for file with no faces"""
        obj_content = """# Vertices only
v 0 0 0
v 1 0 0
v 0 1 0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            parser = OBJParser()
            with pytest.raises(OBJParseError, match="No faces"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_handles_negative_indices(self) -> None:
        """Parser handles negative vertex indices (relative to end)"""
        obj_content = """# Negative indices
v 0 0 0
v 1 0 0
v 0.5 1 0
f -3 -2 -1
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            mesh = parse_obj_file(temp_path)
            assert mesh.face_count == 1
            # Face should reference vertices 0, 1, 2
            np.testing.assert_array_equal(mesh.faces[0], [0, 1, 2])
        finally:
            temp_path.unlink()

    def test_parse_handles_polygon_triangulation(self) -> None:
        """Parser triangulates polygons with more than 4 vertices"""
        obj_content = """# Pentagon
v 0 0 0
v 1 0 0
v 1.5 0.5 0
v 0.75 1 0
v 0 0.5 0
f 1 2 3 4 5
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            mesh = parse_obj_file(temp_path)
            # Pentagon should be triangulated into 3 triangles
            assert mesh.face_count == 3
        finally:
            temp_path.unlink()


class TestParseObjFile:
    """Tests for parse_obj_file convenience function"""

    def test_convenience_function(self) -> None:
        """Convenience function wraps parser correctly"""
        obj_content = """v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            mesh = parse_obj_file(temp_path)
            assert isinstance(mesh, OBJMesh)
            assert mesh.vertex_count == 3
        finally:
            temp_path.unlink()


class TestValidateObjFile:
    """Tests for validate_obj_file function"""

    @pytest.fixture
    def valid_hull_obj(self) -> Generator[Path, None, None]:
        """Create a hull-like OBJ with known dimensions"""
        # Hull: 100m length, 20m beam, 10m depth
        obj_content = """# Test hull
v 0 0 0
v 100 0 0
v 100 20 0
v 0 20 0
v 0 0 10
v 100 0 10
v 100 20 10
v 0 20 10
f 1 2 3 4
f 5 6 7 8
f 1 2 6 5
f 2 3 7 6
f 3 4 8 7
f 4 1 5 8
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        yield temp_path

        temp_path.unlink()

    def test_validate_returns_valid_result(self, valid_hull_obj: Path) -> None:
        """Validation returns valid result for good file"""
        result = validate_obj_file(valid_hull_obj)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "stats" in result

    def test_validate_checks_loa(self, valid_hull_obj: Path) -> None:
        """Validation checks length overall within tolerance"""
        # Exact match should pass
        result = validate_obj_file(valid_hull_obj, expected_loa=100.0, tolerance=0.05)
        assert len(result["warnings"]) == 0

        # Significant mismatch should warn
        result = validate_obj_file(valid_hull_obj, expected_loa=150.0, tolerance=0.05)
        assert any("LOA mismatch" in w for w in result["warnings"])

    def test_validate_checks_beam(self, valid_hull_obj: Path) -> None:
        """Validation checks beam within tolerance"""
        result = validate_obj_file(valid_hull_obj, expected_beam=20.0, tolerance=0.05)
        assert len(result["warnings"]) == 0

        result = validate_obj_file(valid_hull_obj, expected_beam=30.0, tolerance=0.05)
        assert any("Beam mismatch" in w for w in result["warnings"])

    def test_validate_checks_depth(self, valid_hull_obj: Path) -> None:
        """Validation checks depth within tolerance"""
        result = validate_obj_file(valid_hull_obj, expected_depth=10.0, tolerance=0.05)
        assert len(result["warnings"]) == 0

        result = validate_obj_file(valid_hull_obj, expected_depth=15.0, tolerance=0.05)
        assert any("Depth mismatch" in w for w in result["warnings"])

    def test_validate_invalid_file(self) -> None:
        """Validation reports errors for invalid file"""
        result = validate_obj_file(Path("/nonexistent.obj"))

        assert result["valid"] is False
        assert len(result["errors"]) > 0


@pytest.mark.skipif(
    not SEA_CYPRESS_PATH.exists(),
    reason="Sea Cypress hull file not available"
)
class TestSeaCypressIntegration:
    """Integration tests using real Sea Cypress vessel hull"""

    def test_parse_sea_cypress(self) -> None:
        """Parser successfully parses Sea Cypress hull"""
        mesh = parse_obj_file(SEA_CYPRESS_PATH)

        # Known values from digitalmodel export
        assert mesh.vertex_count == 13536
        assert mesh.face_count > 4000  # May vary due to triangulation
        assert mesh.source_file == str(SEA_CYPRESS_PATH)

    def test_sea_cypress_dimensions(self) -> None:
        """Sea Cypress hull has reasonable vessel dimensions"""
        mesh = parse_obj_file(SEA_CYPRESS_PATH)
        dims = mesh.dimensions

        # Sea Cypress is a real vessel - dimensions should be in meters
        assert dims["length"] > 0
        assert dims["width"] > 0
        assert dims["height"] > 0

        # Length should be greater than width (typical vessel proportions)
        assert dims["length"] > dims["width"]

    def test_sea_cypress_bounding_box(self) -> None:
        """Sea Cypress hull has valid bounding box"""
        mesh = parse_obj_file(SEA_CYPRESS_PATH)

        # Bounding box should have finite values
        assert np.all(np.isfinite(mesh.bbox_min))
        assert np.all(np.isfinite(mesh.bbox_max))

        # Max should be greater than min
        assert np.all(mesh.bbox_max > mesh.bbox_min)

    def test_sea_cypress_stats(self) -> None:
        """Sea Cypress hull returns complete statistics"""
        mesh = parse_obj_file(SEA_CYPRESS_PATH)
        stats = mesh.get_stats()

        assert "vertex_count" in stats
        assert "face_count" in stats
        assert "dimensions" in stats
        assert "bbox_min" in stats
        assert "bbox_max" in stats

    def test_validate_sea_cypress(self) -> None:
        """Validation passes for Sea Cypress hull"""
        result = validate_obj_file(SEA_CYPRESS_PATH)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
