# ABOUTME: Exports mesh geometry to Gmsh MSH format for FEM analysis
# ABOUTME: Supports MSH version 2.2 ASCII format with triangle elements

"""
Gmsh MSH Format Exporter

Exports OBJMesh objects to Gmsh MSH format (version 2.2) for further
analysis in FEM tools like Gmsh, OpenFOAM, or other mesh-based solvers.
"""

from pathlib import Path
from typing import Optional

from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import OBJMesh


def export_to_msh(
    mesh: OBJMesh,
    output_path: Path,
    physical_group_name: Optional[str] = None,
) -> Path:
    """
    Export an OBJMesh to Gmsh MSH format (version 2.2 ASCII).

    Args:
        mesh: OBJMesh object to export
        output_path: Path for output .msh file
        physical_group_name: Optional name for physical group

    Returns:
        Path to the created .msh file
    """
    output_path = Path(output_path)

    with open(output_path, "w") as f:
        # Write mesh format header (version 2.2, ASCII, size 8)
        f.write("$MeshFormat\n")
        f.write("2.2 0 8\n")
        f.write("$EndMeshFormat\n")

        # Write physical names if provided
        if physical_group_name:
            f.write("$PhysicalNames\n")
            f.write("1\n")  # Number of physical names
            f.write(f'2 1 "{physical_group_name}"\n')  # dim tag "name"
            f.write("$EndPhysicalNames\n")

        # Write nodes
        f.write("$Nodes\n")
        f.write(f"{mesh.vertex_count}\n")
        for i, vertex in enumerate(mesh.vertices, start=1):
            f.write(f"{i} {vertex[0]:.10g} {vertex[1]:.10g} {vertex[2]:.10g}\n")
        f.write("$EndNodes\n")

        # Write elements (triangles are type 2 in Gmsh)
        f.write("$Elements\n")
        f.write(f"{mesh.face_count}\n")

        # Element format: elm-number elm-type number-of-tags <tags> node-numbers
        # Type 2 = 3-node triangle
        # Tags: physical-group elementary-entity-tag (using 1 1 for both)
        physical_tag = 1 if physical_group_name else 0
        entity_tag = 1

        for i, face in enumerate(mesh.faces, start=1):
            # Gmsh uses 1-indexed nodes
            nodes = " ".join(str(v + 1) for v in face[:3])
            if physical_group_name:
                f.write(f"{i} 2 2 {physical_tag} {entity_tag} {nodes}\n")
            else:
                f.write(f"{i} 2 0 {nodes}\n")
        f.write("$EndElements\n")

    return output_path


def convert_obj_to_msh(
    obj_path: Path,
    msh_path: Optional[Path] = None,
    physical_group_name: Optional[str] = None,
) -> Path:
    """
    Convert an OBJ file to Gmsh MSH format.

    Args:
        obj_path: Path to input OBJ file
        msh_path: Path for output MSH file (default: same name with .msh extension)
        physical_group_name: Optional name for physical group

    Returns:
        Path to the created .msh file
    """
    from worldenergydata.modules.vessel_hull_models.geometry.obj_parser import (
        parse_obj_file,
    )

    obj_path = Path(obj_path)

    if msh_path is None:
        msh_path = obj_path.with_suffix(".msh")

    mesh = parse_obj_file(obj_path)

    # Use object name as physical group if not specified
    if physical_group_name is None and mesh.object_name:
        physical_group_name = mesh.object_name.replace(" ", "_")

    return export_to_msh(mesh, msh_path, physical_group_name)


def convert_gdf_to_msh(
    gdf_path: Path,
    msh_path: Optional[Path] = None,
    physical_group_name: Optional[str] = None,
) -> Path:
    """
    Convert a GDF file to Gmsh MSH format.

    Args:
        gdf_path: Path to input GDF file
        msh_path: Path for output MSH file (default: same name with .msh extension)
        physical_group_name: Optional name for physical group

    Returns:
        Path to the created .msh file
    """
    from worldenergydata.modules.vessel_hull_models.geometry.gdf_parser import (
        parse_gdf_file,
    )

    gdf_path = Path(gdf_path)

    if msh_path is None:
        msh_path = gdf_path.with_suffix(".msh")

    mesh = parse_gdf_file(gdf_path)

    # Use object name as physical group if not specified
    if physical_group_name is None and mesh.object_name:
        physical_group_name = mesh.object_name.replace(" ", "_")

    return export_to_msh(mesh, msh_path, physical_group_name)


def validate_msh_file(msh_path: Path) -> dict:
    """
    Validate a Gmsh MSH file and return information about it.

    Args:
        msh_path: Path to the MSH file

    Returns:
        Dictionary with validation results and statistics
    """
    msh_path = Path(msh_path)

    if not msh_path.exists():
        return {
            "valid": False,
            "errors": [f"File not found: {msh_path}"],
            "stats": None,
        }

    try:
        with open(msh_path, "r") as f:
            content = f.read()

        errors = []
        stats = {
            "node_count": 0,
            "element_count": 0,
            "version": None,
            "has_physical_names": False,
        }

        # Check for required sections
        if "$MeshFormat" not in content:
            errors.append("Missing $MeshFormat section")
        else:
            # Parse version
            import re

            match = re.search(r"\$MeshFormat\n([\d.]+)", content)
            if match:
                stats["version"] = match.group(1)

        if "$Nodes" not in content:
            errors.append("Missing $Nodes section")
        else:
            # Count nodes
            match = re.search(r"\$Nodes\n(\d+)", content)
            if match:
                stats["node_count"] = int(match.group(1))

        if "$Elements" not in content:
            errors.append("Missing $Elements section")
        else:
            # Count elements
            match = re.search(r"\$Elements\n(\d+)", content)
            if match:
                stats["element_count"] = int(match.group(1))

        stats["has_physical_names"] = "$PhysicalNames" in content

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "stats": stats,
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "stats": None,
        }
