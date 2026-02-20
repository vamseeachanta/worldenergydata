"""Tests for OBJ file parser."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from worldenergydata.vessel_hull_models.exceptions import OBJParseError
from worldenergydata.vessel_hull_models.geometry.obj_parser import (
    OBJMesh,
    OBJParser,
    parse_obj_file,
    validate_obj_file,
)


def _write_obj(content: str, suffix=".obj") -> Path:
    """Write OBJ content to a temp file and return its Path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


_TRIANGLE_OBJ = """\
# simple triangle
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
f 1 2 3
"""

_QUAD_OBJ = """\
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 0.0 1.0 0.0
f 1 2 3 4
"""

_FULL_OBJ = """\
# full featured
o TestObject
usemtl TestMaterial
v 0.0 0.0 0.0
v 10.0 0.0 0.0
v 10.0 5.0 0.0
v 0.0 5.0 0.0
v 0.0 0.0 3.0
v 10.0 0.0 3.0
v 10.0 5.0 3.0
v 0.0 5.0 3.0
vn 0.0 0.0 -1.0
vt 0.0 0.0
f 1/1/1 2/1/1 3/1/1
f 1 3 4
f 5 6 7
f 5 7 8
"""


class TestOBJMesh:
    def test_vertex_count(self):
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        assert mesh.vertex_count == 3

    def test_face_count(self):
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        assert mesh.face_count == 1

    def test_bbox(self):
        verts = np.array(
            [[0, 0, 0], [10, 5, 3], [5, 2, 1]], dtype=np.float32
        )
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        np.testing.assert_array_equal(mesh.bbox_min, [0, 0, 0])
        np.testing.assert_array_equal(mesh.bbox_max, [10, 5, 3])

    def test_dimensions(self):
        verts = np.array(
            [[0, 0, 0], [10, 5, 3]], dtype=np.float32
        )
        faces = np.array([[0, 1, 0]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        dims = mesh.dimensions
        assert dims["length"] == pytest.approx(10.0)
        assert dims["width"] == pytest.approx(5.0)
        assert dims["height"] == pytest.approx(3.0)

    def test_center(self):
        verts = np.array(
            [[0, 0, 0], [10, 10, 10]], dtype=np.float32
        )
        faces = np.array([[0, 1, 0]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        np.testing.assert_array_almost_equal(mesh.center, [5, 5, 5])

    def test_get_stats(self):
        verts = np.array(
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32
        )
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = OBJMesh(
            vertices=verts, faces=faces,
            material_name="mat1", object_name="obj1",
        )
        stats = mesh.get_stats()
        assert stats["vertex_count"] == 3
        assert stats["face_count"] == 1
        assert stats["has_normals"] is False
        assert stats["has_texcoords"] is False
        assert stats["material"] == "mat1"
        assert stats["object_name"] == "obj1"
        assert "length" in stats
        assert "width" in stats
        assert "height" in stats

    def test_metadata_defaults(self):
        verts = np.array([[0, 0, 0]], dtype=np.float32)
        faces = np.array([[0, 0, 0]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        assert mesh.material_name is None
        assert mesh.object_name is None
        assert mesh.source_file is None
        assert mesh.normals is None
        assert mesh.texcoords is None

    def test_bbox_cached(self):
        verts = np.array(
            [[0, 0, 0], [1, 1, 1]], dtype=np.float32
        )
        faces = np.array([[0, 1, 0]], dtype=np.int32)
        mesh = OBJMesh(vertices=verts, faces=faces)
        _ = mesh.bbox_min
        _ = mesh.bbox_max
        # Second access uses cached values
        assert mesh._bbox_min is not None
        assert mesh._bbox_max is not None


class TestOBJParserParse:
    def test_triangle(self):
        path = _write_obj(_TRIANGLE_OBJ)
        mesh = OBJParser().parse(path)
        assert mesh.vertex_count == 3
        assert mesh.face_count == 1
        path.unlink()

    def test_quad_triangulated(self):
        path = _write_obj(_QUAD_OBJ)
        mesh = OBJParser().parse(path)
        assert mesh.vertex_count == 4
        assert mesh.face_count == 2  # quad split into 2 triangles
        path.unlink()

    def test_full_featured(self):
        path = _write_obj(_FULL_OBJ)
        mesh = OBJParser().parse(path)
        assert mesh.vertex_count == 8
        assert mesh.normals is not None
        assert len(mesh.normals) == 1
        assert mesh.texcoords is not None
        assert len(mesh.texcoords) == 1
        assert mesh.material_name == "TestMaterial"
        assert mesh.object_name == "TestObject"
        assert mesh.source_file == str(path)
        path.unlink()

    def test_file_not_found(self):
        with pytest.raises(OBJParseError, match="not found"):
            OBJParser().parse(Path("/nonexistent/file.obj"))

    def test_wrong_extension(self):
        path = _write_obj("v 0 0 0\nf 1 1 1", suffix=".txt")
        with pytest.raises(OBJParseError, match="Expected .obj"):
            OBJParser().parse(path)
        path.unlink()

    def test_no_vertices(self):
        path = _write_obj("# empty\n")
        with pytest.raises(OBJParseError, match="No vertices"):
            OBJParser().parse(path)
        path.unlink()

    def test_no_faces(self):
        path = _write_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\n")
        with pytest.raises(OBJParseError, match="No faces"):
            OBJParser().parse(path)
        path.unlink()

    def test_invalid_vertex(self):
        path = _write_obj("v abc def ghi\nf 1 1 1\n")
        with pytest.raises(OBJParseError):
            OBJParser().parse(path)
        path.unlink()

    def test_too_few_vertex_coords(self):
        path = _write_obj("v 1.0 2.0\nf 1 1 1\n")
        with pytest.raises(OBJParseError, match="at least 3"):
            OBJParser().parse(path)
        path.unlink()

    def test_face_too_few_indices(self):
        path = _write_obj("v 0 0 0\nv 1 0 0\nf 1 2\n")
        with pytest.raises(OBJParseError, match="at least 3"):
            OBJParser().parse(path)
        path.unlink()

    def test_face_with_slashes(self):
        content = """\
v 0 0 0
v 1 0 0
v 0 1 0
vt 0 0
vn 0 0 1
f 1/1/1 2/1/1 3/1/1
"""
        path = _write_obj(content)
        mesh = OBJParser().parse(path)
        assert mesh.face_count == 1
        path.unlink()

    def test_face_vertex_normal_only(self):
        content = """\
v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 1
f 1//1 2//1 3//1
"""
        path = _write_obj(content)
        mesh = OBJParser().parse(path)
        assert mesh.face_count == 1
        path.unlink()

    def test_negative_index(self):
        content = """\
v 0 0 0
v 1 0 0
v 0 1 0
f -3 -2 -1
"""
        path = _write_obj(content)
        mesh = OBJParser().parse(path)
        assert mesh.face_count == 1
        # Negative indices resolve to 0-based: -3 -> 0, -2 -> 1, -1 -> 2
        assert mesh.faces[0][0] == 0
        assert mesh.faces[0][1] == 1
        assert mesh.faces[0][2] == 2
        path.unlink()

    def test_polygon_fan_triangulation(self):
        content = """\
v 0 0 0
v 1 0 0
v 1 1 0
v 0.5 1.5 0
v 0 1 0
f 1 2 3 4 5
"""
        path = _write_obj(content)
        mesh = OBJParser().parse(path)
        # 5-vertex polygon -> 3 triangles via fan triangulation
        assert mesh.face_count == 3
        path.unlink()

    def test_group_name(self):
        content = """\
g GroupName
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
"""
        path = _write_obj(content)
        mesh = OBJParser().parse(path)
        assert mesh.object_name == "GroupName"
        path.unlink()

    def test_parser_resets_state(self):
        parser = OBJParser()
        path1 = _write_obj(_TRIANGLE_OBJ)
        mesh1 = parser.parse(path1)
        path2 = _write_obj(_QUAD_OBJ)
        mesh2 = parser.parse(path2)
        assert mesh1.vertex_count == 3
        assert mesh2.vertex_count == 4
        path1.unlink()
        path2.unlink()


class TestParseObjFile:
    def test_convenience_function(self):
        path = _write_obj(_TRIANGLE_OBJ)
        mesh = parse_obj_file(path)
        assert mesh.vertex_count == 3
        path.unlink()


class TestValidateObjFile:
    def test_valid_file(self):
        path = _write_obj(_FULL_OBJ)
        result = validate_obj_file(path)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "stats" in result
        path.unlink()

    def test_invalid_file(self):
        path = _write_obj("# empty\n")
        result = validate_obj_file(path)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        path.unlink()

    def test_dimension_check_within_tolerance(self):
        path = _write_obj(_FULL_OBJ)
        result = validate_obj_file(path, expected_loa=10.0)
        assert len(result["warnings"]) == 0
        path.unlink()

    def test_dimension_check_outside_tolerance(self):
        path = _write_obj(_FULL_OBJ)
        result = validate_obj_file(path, expected_loa=20.0)
        assert len(result["warnings"]) > 0
        assert "LOA mismatch" in result["warnings"][0]
        path.unlink()

    def test_beam_check(self):
        path = _write_obj(_FULL_OBJ)
        result = validate_obj_file(path, expected_beam=20.0)
        assert any("Beam mismatch" in w for w in result["warnings"])
        path.unlink()

    def test_depth_check(self):
        path = _write_obj(_FULL_OBJ)
        result = validate_obj_file(path, expected_depth=20.0)
        assert any("Depth mismatch" in w for w in result["warnings"])
        path.unlink()
