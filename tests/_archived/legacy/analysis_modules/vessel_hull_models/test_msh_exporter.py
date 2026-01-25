# ABOUTME: Unit tests for MSH exporter module
# ABOUTME: Tests export of mesh geometry to Gmsh MSH format

"""
Unit tests for MSH Exporter.

Tests export of OBJMesh objects to Gmsh MSH format (version 2.2).
"""

import pytest
import tempfile
from pathlib import Path
import numpy as np

from worldenergydata.modules.vessel_hull_models.geometry.msh_exporter import (
    export_to_msh,
    convert_obj_to_msh,
    convert_gdf_to_msh,
    validate_msh_file,
)
from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import OBJMesh


class TestExportToMsh:
    """Tests for direct MSH export from OBJMesh"""

    def test_export_simple_triangle(self) -> None:
        """Export a single triangle mesh to MSH"""
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, 1.0, 0.0],
        ])
        faces = np.array([[0, 1, 2]])

        mesh = OBJMesh(
            vertices=vertices,
            faces=faces,
            normals=None,
            texcoords=None,
            object_name="TestTriangle",
            material_name=None,
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as f:
            msh_path = Path(f.name)

        try:
            result_path = export_to_msh(mesh, msh_path)

            assert result_path.exists()
            content = msh_path.read_text()

            # Check format header
            assert "$MeshFormat" in content
            assert "2.2 0 8" in content

            # Check nodes section
            assert "$Nodes" in content
            assert "3" in content  # 3 nodes

            # Check elements section
            assert "$Elements" in content
            assert "1" in content  # 1 element

            # Verify coordinates
            assert "0 0 0" in content or "0.0 0.0 0.0" in content
        finally:
            msh_path.unlink()

    def test_export_with_physical_group(self) -> None:
        """Export mesh with physical group name"""
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, 1.0, 0.0],
        ])
        faces = np.array([[0, 1, 2]])

        mesh = OBJMesh(
            vertices=vertices,
            faces=faces,
            normals=None,
            texcoords=None,
            object_name=None,
            material_name=None,
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as f:
            msh_path = Path(f.name)

        try:
            export_to_msh(mesh, msh_path, physical_group_name="HullSurface")

            content = msh_path.read_text()
            assert "$PhysicalNames" in content
            assert "HullSurface" in content
        finally:
            msh_path.unlink()

    def test_export_multiple_faces(self) -> None:
        """Export mesh with multiple triangular faces"""
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [10.0, 5.0, 0.0],
            [0.0, 5.0, 0.0],
        ])
        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ])

        mesh = OBJMesh(
            vertices=vertices,
            faces=faces,
            normals=None,
            texcoords=None,
            object_name="TestQuad",
            material_name=None,
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as f:
            msh_path = Path(f.name)

        try:
            export_to_msh(mesh, msh_path)

            # Validate the file
            result = validate_msh_file(msh_path)
            assert result["valid"] is True
            assert result["stats"]["node_count"] == 4
            assert result["stats"]["element_count"] == 2
        finally:
            msh_path.unlink()


class TestConvertObjToMsh:
    """Tests for OBJ to MSH conversion"""

    def test_convert_simple_obj(self) -> None:
        """Convert a simple OBJ file to MSH"""
        obj_content = """# Test object
o TestHull
v 0 0 0
v 10 0 0
v 10 5 0
v 0 5 0
f 1 2 3
f 1 3 4
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as obj_file:
            obj_file.write(obj_content)
            obj_path = Path(obj_file.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as msh_file:
            msh_path = Path(msh_file.name)

        try:
            result_path = convert_obj_to_msh(obj_path, msh_path)

            assert result_path.exists()

            result = validate_msh_file(msh_path)
            assert result["valid"] is True
            assert result["stats"]["node_count"] == 4
            assert result["stats"]["element_count"] == 2
        finally:
            obj_path.unlink()
            msh_path.unlink()

    def test_convert_uses_object_name_as_physical_group(self) -> None:
        """Object name becomes physical group in MSH"""
        obj_content = """# Test object
o BargeDeck
v 0 0 0
v 10 0 0
v 5 5 0
f 1 2 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as obj_file:
            obj_file.write(obj_content)
            obj_path = Path(obj_file.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as msh_file:
            msh_path = Path(msh_file.name)

        try:
            convert_obj_to_msh(obj_path, msh_path)

            content = msh_path.read_text()
            assert "BargeDeck" in content
        finally:
            obj_path.unlink()
            msh_path.unlink()

    def test_convert_default_output_path(self) -> None:
        """Uses same path with .msh extension if not specified"""
        obj_content = """v 0 0 0
v 1 0 0
v 0.5 1 0
f 1 2 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as obj_file:
            obj_file.write(obj_content)
            obj_path = Path(obj_file.name)

        expected_msh_path = obj_path.with_suffix(".msh")

        try:
            result_path = convert_obj_to_msh(obj_path)

            assert result_path == expected_msh_path
            assert result_path.exists()
        finally:
            obj_path.unlink()
            expected_msh_path.unlink()


class TestConvertGdfToMsh:
    """Tests for GDF to MSH conversion"""

    def test_convert_simple_gdf(self) -> None:
        """Convert a simple GDF file to MSH"""
        gdf_content = """Test hull conversion
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
            mode="w", suffix=".msh", delete=False
        ) as msh_file:
            msh_path = Path(msh_file.name)

        try:
            result_path = convert_gdf_to_msh(gdf_path, msh_path)

            assert result_path.exists()

            result = validate_msh_file(msh_path)
            assert result["valid"] is True
            # 2 triangles with 4 unique vertices
            assert result["stats"]["node_count"] == 4
            assert result["stats"]["element_count"] == 2
        finally:
            gdf_path.unlink()
            msh_path.unlink()


class TestValidateMshFile:
    """Tests for MSH file validation"""

    def test_validate_valid_file(self) -> None:
        """Validate a correctly formatted MSH file"""
        msh_content = """$MeshFormat
2.2 0 8
$EndMeshFormat
$Nodes
3
1 0.0 0.0 0.0
2 1.0 0.0 0.0
3 0.5 1.0 0.0
$EndNodes
$Elements
1
1 2 0 1 2 3
$EndElements
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as f:
            f.write(msh_content)
            msh_path = Path(f.name)

        try:
            result = validate_msh_file(msh_path)

            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert result["stats"]["version"] == "2.2"
            assert result["stats"]["node_count"] == 3
            assert result["stats"]["element_count"] == 1
        finally:
            msh_path.unlink()

    def test_validate_nonexistent_file(self) -> None:
        """Return error for nonexistent file"""
        result = validate_msh_file(Path("/nonexistent/file.msh"))

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower()

    def test_validate_missing_sections(self) -> None:
        """Detect missing required sections"""
        msh_content = """$MeshFormat
2.2 0 8
$EndMeshFormat
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as f:
            f.write(msh_content)
            msh_path = Path(f.name)

        try:
            result = validate_msh_file(msh_path)

            assert result["valid"] is False
            # Should detect missing Nodes and Elements sections
            assert any("Nodes" in e for e in result["errors"])
            assert any("Elements" in e for e in result["errors"])
        finally:
            msh_path.unlink()

    def test_validate_detects_physical_names(self) -> None:
        """Detect presence of physical names section"""
        msh_content = """$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
1
2 1 "Hull"
$EndPhysicalNames
$Nodes
3
1 0.0 0.0 0.0
2 1.0 0.0 0.0
3 0.5 1.0 0.0
$EndNodes
$Elements
1
1 2 2 1 1 1 2 3
$EndElements
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as f:
            f.write(msh_content)
            msh_path = Path(f.name)

        try:
            result = validate_msh_file(msh_path)

            assert result["valid"] is True
            assert result["stats"]["has_physical_names"] is True
        finally:
            msh_path.unlink()


# Integration test with real GDF file
_test_dir = Path(__file__).parents[4]
_possible_paths = [
    _test_dir / "digitalmodel" / "specs" / "modules" / "orcawave" / "test-configs" / "geometry" / "barge.gdf",
    Path("/mnt/github/workspace-hub/digitalmodel/specs/modules/orcawave/test-configs/geometry/barge.gdf"),
]
BARGE_GDF_PATH = next((p for p in _possible_paths if p.exists()), _possible_paths[0])


@pytest.mark.skipif(
    not BARGE_GDF_PATH.exists(),
    reason="Barge GDF file not available"
)
class TestBargeGdfToMshIntegration:
    """Integration tests converting real barge GDF to MSH"""

    def test_convert_barge_to_msh(self) -> None:
        """Convert barge GDF file to MSH format"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".msh", delete=False
        ) as msh_file:
            msh_path = Path(msh_file.name)

        try:
            result_path = convert_gdf_to_msh(BARGE_GDF_PATH, msh_path)

            assert result_path.exists()
            assert result_path.stat().st_size > 0

            # Validate the MSH file
            result = validate_msh_file(msh_path)
            assert result["valid"] is True
            # Barge has 608 faces
            assert result["stats"]["element_count"] == 608
        finally:
            msh_path.unlink()
