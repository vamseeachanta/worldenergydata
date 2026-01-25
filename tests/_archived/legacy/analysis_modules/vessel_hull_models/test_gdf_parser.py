# ABOUTME: Unit tests for GDF parser module
# ABOUTME: Tests parsing of OrcaWave/WAMIT GDF geometry files

"""
Unit tests for GDF Parser.

Tests parsing of GDF (Geometry Definition File) format used by
OrcaWave and WAMIT for hydrodynamic panel mesh definitions.
"""

import pytest
import tempfile
from pathlib import Path
import numpy as np

from worldenergydata.modules.vessel_hull_models.geometry.gdf_parser import (
    GDFHeader,
    parse_gdf_header,
    parse_gdf_file,
    convert_gdf_to_obj,
    validate_gdf_file,
)
from worldenergydata.modules.vessel_hull_models.exceptions import OBJParseError


# Path to real GDF files for integration tests
# Try multiple possible locations for digitalmodel
_test_dir = Path(__file__).parents[4]
_possible_paths = [
    _test_dir / "digitalmodel" / "specs" / "modules" / "orcawave" / "test-configs" / "geometry" / "barge.gdf",
    Path("/mnt/github/workspace-hub/digitalmodel/specs/modules/orcawave/test-configs/geometry/barge.gdf"),
]
BARGE_GDF_PATH = next((p for p in _possible_paths if p.exists()), _possible_paths[0])


class TestGDFHeader:
    """Tests for GDF header parsing"""

    def test_parse_valid_header(self) -> None:
        """Parse a valid GDF header"""
        lines = [
            "Test barge description",
            "1.0 9.80665",
            "0 1",
            "100",
            "0.0 0.0 0.0",
        ]
        header, start_line = parse_gdf_header(lines)

        assert header.description == "Test barge description"
        assert header.unit_length == 1.0
        assert header.gravity == pytest.approx(9.80665)
        assert header.symmetry_x is False
        assert header.symmetry_y is True
        assert header.panel_count == 100
        assert start_line == 4

    def test_parse_header_with_x_symmetry(self) -> None:
        """Parse header with X symmetry enabled"""
        lines = [
            "Symmetric hull",
            "1.0 9.80665",
            "1 0",
            "50",
        ]
        header, _ = parse_gdf_header(lines)

        assert header.symmetry_x is True
        assert header.symmetry_y is False

    def test_parse_header_with_both_symmetries(self) -> None:
        """Parse header with both symmetries enabled"""
        lines = [
            "Quarter hull",
            "1.0 9.80665",
            "1 1",
            "25",
        ]
        header, _ = parse_gdf_header(lines)

        assert header.symmetry_x is True
        assert header.symmetry_y is True

    def test_parse_header_too_short(self) -> None:
        """Raise error for file with insufficient header lines"""
        lines = ["Description", "1.0 9.80665"]

        with pytest.raises(OBJParseError, match="too short"):
            parse_gdf_header(lines)

    def test_parse_header_missing_ulen_grav(self) -> None:
        """Raise error for missing ULEN GRAV values"""
        lines = [
            "Description",
            "1.0",  # Missing gravity
            "0 1",
            "100",
        ]

        with pytest.raises(OBJParseError, match="missing ULEN GRAV"):
            parse_gdf_header(lines)


class TestParseGDFFile:
    """Tests for GDF file parsing"""

    def test_parse_simple_triangle(self) -> None:
        """Parse a GDF file with a single triangle"""
        gdf_content = """Simple triangle test
1.0 9.80665
0 0
1
0.0 0.0 0.0
1.0 0.0 0.0
0.5 1.0 0.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as f:
            f.write(gdf_content)
            temp_path = Path(f.name)

        try:
            mesh = parse_gdf_file(temp_path)

            assert mesh.vertex_count == 3
            assert mesh.face_count == 1
            assert mesh.object_name == "Simple triangle test"
        finally:
            temp_path.unlink()

    def test_parse_box_panels(self) -> None:
        """Parse a GDF file with multiple triangular panels"""
        gdf_content = """Box bottom (2 triangles)
1.0 9.80665
0 0
2
0.0 0.0 0.0
10.0 0.0 0.0
10.0 5.0 0.0
0.0 0.0 0.0
10.0 5.0 0.0
0.0 5.0 0.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as f:
            f.write(gdf_content)
            temp_path = Path(f.name)

        try:
            mesh = parse_gdf_file(temp_path)

            assert mesh.vertex_count == 4  # Deduplicated vertices
            assert mesh.face_count == 2
            dims = mesh.dimensions
            assert dims["length"] == pytest.approx(10.0)
            assert dims["width"] == pytest.approx(5.0)
        finally:
            temp_path.unlink()

    def test_parse_with_y_symmetry(self) -> None:
        """Parse GDF with Y symmetry - should mirror geometry"""
        gdf_content = """Half hull with Y symmetry
1.0 9.80665
0 1
1
0.0 1.0 0.0
10.0 1.0 0.0
10.0 2.0 0.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as f:
            f.write(gdf_content)
            temp_path = Path(f.name)

        try:
            mesh = parse_gdf_file(temp_path)

            # With Y symmetry, should have 2 faces (original + mirrored)
            assert mesh.face_count == 2
            # Y dimension should span from -2 to +2
            dims = mesh.dimensions
            assert dims["width"] == pytest.approx(4.0)  # -2 to +2
        finally:
            temp_path.unlink()

    def test_parse_nonexistent_file(self) -> None:
        """Raise error for nonexistent file"""
        with pytest.raises(OBJParseError, match="not found"):
            parse_gdf_file(Path("/nonexistent/file.gdf"))


class TestConvertGDFToOBJ:
    """Tests for GDF to OBJ conversion"""

    def test_convert_simple_gdf(self) -> None:
        """Convert a simple GDF to OBJ format"""
        gdf_content = """Test conversion
1.0 9.80665
0 0
1
0.0 0.0 0.0
1.0 0.0 0.0
0.5 1.0 0.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as gdf_file:
            gdf_file.write(gdf_content)
            gdf_path = Path(gdf_file.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as obj_file:
            obj_path = Path(obj_file.name)

        try:
            mesh = convert_gdf_to_obj(gdf_path, obj_path)

            assert mesh.vertex_count == 3
            assert obj_path.exists()

            # Read and verify OBJ content
            obj_content = obj_path.read_text()
            assert "# Converted from GDF:" in obj_content
            assert "v 0.000000 0.000000 0.000000" in obj_content
            assert "f 1 2 3" in obj_content
        finally:
            gdf_path.unlink()
            obj_path.unlink()

    def test_converted_obj_is_valid(self) -> None:
        """Verify converted OBJ can be parsed back"""
        from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import (
            parse_obj_file,
        )

        gdf_content = """Roundtrip test
1.0 9.80665
0 0
2
0.0 0.0 0.0
10.0 0.0 0.0
10.0 5.0 0.0
0.0 0.0 0.0
10.0 5.0 0.0
0.0 5.0 0.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as gdf_file:
            gdf_file.write(gdf_content)
            gdf_path = Path(gdf_file.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as obj_file:
            obj_path = Path(obj_file.name)

        try:
            original_mesh = convert_gdf_to_obj(gdf_path, obj_path)
            parsed_mesh = parse_obj_file(obj_path)

            assert parsed_mesh.vertex_count == original_mesh.vertex_count
            assert parsed_mesh.face_count == original_mesh.face_count
        finally:
            gdf_path.unlink()
            obj_path.unlink()


class TestValidateGDFFile:
    """Tests for GDF file validation"""

    def test_validate_valid_file(self) -> None:
        """Validate a valid GDF file"""
        gdf_content = """Valid test file
1.0 9.80665
0 0
1
0.0 0.0 0.0
10.0 0.0 0.0
5.0 5.0 0.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as f:
            f.write(gdf_content)
            temp_path = Path(f.name)

        try:
            result = validate_gdf_file(temp_path)

            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert result["header"]["description"] == "Valid test file"
            assert result["header"]["declared_panels"] == 1
            assert result["stats"]["vertex_count"] == 3
            assert result["stats"]["face_count"] == 1
        finally:
            temp_path.unlink()

    def test_validate_invalid_file(self) -> None:
        """Validate an invalid GDF file"""
        gdf_content = """Invalid file
1.0
"""  # Missing header lines
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gdf", delete=False
        ) as f:
            f.write(gdf_content)
            temp_path = Path(f.name)

        try:
            result = validate_gdf_file(temp_path)

            assert result["valid"] is False
            assert len(result["errors"]) > 0
        finally:
            temp_path.unlink()


# Path to standard (quad format) GDF files
QUAD_GDF_PATH = Path("/mnt/github/workspace-hub/digitalmodel/docs/modules/orcaflex/aqwa/to_orcawave/multibody_test1/output/Body_1.gdf")


@pytest.mark.skipif(
    not QUAD_GDF_PATH.exists(),
    reason="Standard quad GDF file not available"
)
class TestQuadGDFIntegration:
    """Integration tests using standard quad-format GDF files"""

    def test_parse_quad_gdf(self) -> None:
        """Parse a standard quad-format GDF file"""
        mesh = parse_gdf_file(QUAD_GDF_PATH)

        # Body_1.gdf has 128 panels in quad format (ratio 4.0)
        # Each quad becomes 2 triangles: 128 × 2 = 256 faces
        # No symmetry flags
        assert mesh.face_count == 256
        assert mesh.vertex_count > 0

    def test_validate_quad_gdf(self) -> None:
        """Validate a standard quad-format GDF file"""
        result = validate_gdf_file(QUAD_GDF_PATH)

        assert result["valid"] is True
        assert result["header"]["declared_panels"] == 128


@pytest.mark.skipif(
    not BARGE_GDF_PATH.exists(),
    reason="Barge GDF file not available"
)
class TestBargeGDFIntegration:
    """Integration tests using real barge.gdf from digitalmodel"""

    def test_parse_barge_gdf(self) -> None:
        """Parse the barge GDF file"""
        mesh = parse_gdf_file(BARGE_GDF_PATH)

        # Barge.gdf declares 912 panels but has 912 data lines (ratio 1.0)
        # This is detected as triangle format: 912/3 = 304 triangles
        # With Y symmetry: 304 × 2 = 608 faces
        assert mesh.face_count == 608
        assert mesh.vertex_count > 0

        dims = mesh.dimensions
        # Barge dimensions approximately 100m x 20m x 8m
        assert 95 <= dims["length"] <= 105
        assert 18 <= dims["width"] <= 22
        assert 7 <= dims["height"] <= 9

    def test_convert_barge_to_obj(self) -> None:
        """Convert barge GDF to OBJ format"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as obj_file:
            obj_path = Path(obj_file.name)

        try:
            mesh = convert_gdf_to_obj(BARGE_GDF_PATH, obj_path)

            assert obj_path.exists()
            assert obj_path.stat().st_size > 0

            # Verify OBJ can be parsed
            from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import (
                parse_obj_file,
            )
            parsed = parse_obj_file(obj_path)
            assert parsed.vertex_count == mesh.vertex_count
        finally:
            obj_path.unlink()

    def test_validate_barge_gdf(self) -> None:
        """Validate the barge GDF file"""
        result = validate_gdf_file(BARGE_GDF_PATH)

        assert result["valid"] is True
        assert result["header"]["declared_panels"] == 912
        assert result["header"]["symmetry_y"] is True
        assert result["header"]["symmetry_x"] is False
