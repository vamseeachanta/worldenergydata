# ABOUTME: Geometry processing for vessel hull models
# ABOUTME: OBJ parsing, GDF parsing, MSH export, mesh operations, and format conversion

"""
Geometry Processing for Vessel Hull Models Module

Provides OBJ file parsing, GDF file parsing, MSH export, mesh manipulation, and format conversion.
"""

from worldenergydata.vessel_hull_models.geometry.gdf_parser import (
    GDFHeader,
    convert_gdf_to_obj,
    parse_gdf_file,
    parse_gdf_header,
    validate_gdf_file,
)
from worldenergydata.vessel_hull_models.geometry.msh_exporter import (
    convert_gdf_to_msh,
    convert_obj_to_msh,
    export_to_msh,
    validate_msh_file,
)
from worldenergydata.vessel_hull_models.geometry.obj_parser import (
    OBJMesh,
    OBJParser,
    parse_obj_file,
    validate_obj_file,
)

__all__ = [
    # OBJ parser exports
    "OBJParser",
    "OBJMesh",
    "parse_obj_file",
    "validate_obj_file",
    # GDF parser exports
    "GDFHeader",
    "parse_gdf_header",
    "parse_gdf_file",
    "convert_gdf_to_obj",
    "validate_gdf_file",
    # MSH exporter exports
    "export_to_msh",
    "convert_obj_to_msh",
    "convert_gdf_to_msh",
    "validate_msh_file",
]
