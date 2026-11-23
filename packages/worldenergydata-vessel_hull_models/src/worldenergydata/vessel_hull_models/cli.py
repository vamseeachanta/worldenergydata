# ABOUTME: Command-line interface for vessel hull models module
# ABOUTME: Supports validation, visualization, GDF conversion, and hull management

"""
CLI for Vessel Hull Models Module

Provides commands for:
- Validating OBJ/GDF hull files
- Visualizing vessel hulls
- Converting GDF to OBJ/MSH formats
- Listing available hull models
- Generating parametric hulls
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.vessel_hull_models.config import get_config
from worldenergydata.vessel_hull_models.exceptions import OBJParseError
from worldenergydata.vessel_hull_models.geometry.gdf_parser import (
    convert_gdf_to_obj,
    parse_gdf_file,
    validate_gdf_file,
)
from worldenergydata.vessel_hull_models.geometry.msh_exporter import (
    convert_gdf_to_msh,
    convert_obj_to_msh,
)
from worldenergydata.vessel_hull_models.geometry.obj_parser import (
    parse_obj_file,
    validate_obj_file,
)
from worldenergydata.vessel_hull_models.visualization.plotly_3d import (
    export_hull_html,
    render_vessel_hull,
)

app = typer.Typer(
    name="vessel-hull-models",
    help="Vessel Hull Models - 3D geometry acquisition and visualization",
    no_args_is_help=True,
)
console = Console()


@app.command()
def validate(
    file_path: Path = typer.Argument(..., help="Path to OBJ file to validate"),
    expected_loa: Optional[float] = typer.Option(
        None, "--loa", "-l", help="Expected length overall (meters)"
    ),
    expected_beam: Optional[float] = typer.Option(
        None, "--beam", "-b", help="Expected beam/width (meters)"
    ),
    expected_depth: Optional[float] = typer.Option(
        None, "--depth", "-d", help="Expected depth/height (meters)"
    ),
    tolerance: float = typer.Option(
        0.05, "--tolerance", "-t", help="Dimension tolerance (default 5%)"
    ),
) -> None:
    """
    Validate an OBJ hull file and check dimensions.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli validate hull.obj
        $ python -m worldenergydata.vessel_hull_models.cli validate hull.obj --loa 220 --beam 102
    """
    console.print(f"\n[bold]Validating:[/bold] {file_path}\n")

    result = validate_obj_file(
        file_path,
        expected_loa=expected_loa,
        expected_beam=expected_beam,
        expected_depth=expected_depth,
        tolerance=tolerance,
    )

    if result["valid"]:
        console.print("[green]✓[/green] File is valid\n")
    else:
        console.print("[red]✗[/red] Validation failed\n")
        for error in result["errors"]:
            console.print(f"  [red]Error:[/red] {error}")
        raise typer.Exit(1)

    # Display statistics
    stats = result.get("stats", {})
    if stats:
        table = Table(title="Mesh Statistics")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Vertices", f"{stats.get('vertex_count', 'N/A'):,}")
        table.add_row("Faces", f"{stats.get('face_count', 'N/A'):,}")
        table.add_row("Has Normals", str(stats.get("has_normals", False)))
        table.add_row("Has Texcoords", str(stats.get("has_texcoords", False)))

        dims = stats.get("dimensions", {})
        table.add_row("Length (X)", f"{dims.get('length', 0):.2f} m")
        table.add_row("Width (Y)", f"{dims.get('width', 0):.2f} m")
        table.add_row("Height (Z)", f"{dims.get('height', 0):.2f} m")

        if stats.get("material"):
            table.add_row("Material", stats["material"])
        if stats.get("object_name"):
            table.add_row("Object Name", stats["object_name"])

        console.print(table)

    # Display warnings
    for warning in result.get("warnings", []):
        console.print(f"\n[yellow]⚠ Warning:[/yellow] {warning}")


@app.command()
def visualize(
    file_path: Path = typer.Argument(..., help="Path to OBJ file"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output HTML file path"
    ),
    title: Optional[str] = typer.Option(
        None, "--title", "-t", help="Visualization title"
    ),
    color_by: str = typer.Option(
        "depth", "--color-by", "-c", help="Color scheme: depth, solid, wireframe"
    ),
    show_waterline: bool = typer.Option(
        True, "--waterline/--no-waterline", help="Show waterline plane"
    ),
    show_dimensions: bool = typer.Option(
        True, "--dims/--no-dims", help="Show dimension annotations"
    ),
    open_browser: bool = typer.Option(
        True, "--open/--no-open", help="Open in browser after export"
    ),
) -> None:
    """
    Visualize a vessel hull in 3D.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli visualize hull.obj
        $ python -m worldenergydata.vessel_hull_models.cli visualize hull.obj -o report.html
    """
    console.print(f"\n[bold]Visualizing:[/bold] {file_path}\n")

    try:
        if output:
            # Export to HTML file
            export_hull_html(
                obj_path=file_path,
                output_path=output,
                title=title,
                color_by=color_by,
                show_waterline=show_waterline,
                show_dimensions=show_dimensions,
            )
            console.print(f"[green]✓[/green] Exported to: {output}")

            if open_browser:
                import webbrowser

                webbrowser.open(f"file://{output.resolve()}")
        else:
            # Show interactive plot
            fig = render_vessel_hull(
                obj_path=file_path,
                title=title,
                color_by=color_by,
                show_waterline=show_waterline,
                show_dimensions=show_dimensions,
            )
            fig.show()

    except OBJParseError as e:
        console.print(f"[red]Error parsing file:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_hulls(
    directory: Optional[Path] = typer.Option(
        None, "--dir", "-d", help="Directory to search (default: module data dir)"
    ),
    vessel_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by vessel type"
    ),
) -> None:
    """
    List available hull models.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli list
        $ python -m worldenergydata.vessel_hull_models.cli list --type crane_vessel
    """
    config = get_config()

    if directory is None:
        directory = config.storage.hulls_path

    if not directory.exists():
        console.print(f"[yellow]Directory not found:[/yellow] {directory}")
        raise typer.Exit(1)

    # Find all OBJ files
    obj_files = list(directory.glob("**/*.obj"))

    if not obj_files:
        console.print("[yellow]No hull models found[/yellow]")
        return

    table = Table(title=f"Hull Models in {directory}")
    table.add_column("File", style="cyan")
    table.add_column("Vertices", justify="right")
    table.add_column("Faces", justify="right")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Dimensions (L×W×H)", style="green")

    for obj_file in sorted(obj_files):
        try:
            mesh = parse_obj_file(obj_file)
            dims = mesh.dimensions
            size_mb = obj_file.stat().st_size / (1024 * 1024)

            table.add_row(
                obj_file.name,
                f"{mesh.vertex_count:,}",
                f"{mesh.face_count:,}",
                f"{size_mb:.2f}",
                f"{dims['length']:.1f}×{dims['width']:.1f}×{dims['height']:.1f}",
            )
        except Exception as e:
            table.add_row(obj_file.name, "Error", "-", "-", str(e)[:30])

    console.print(table)
    console.print(f"\n[dim]Total: {len(obj_files)} hull model(s)[/dim]")


@app.command()
def stats(
    file_path: Path = typer.Argument(..., help="Path to OBJ file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """
    Display detailed statistics for a hull model.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli stats hull.obj
        $ python -m worldenergydata.vessel_hull_models.cli stats hull.obj --json
    """
    try:
        mesh = parse_obj_file(file_path)
        stats_data = mesh.get_stats()
        stats_data["file_path"] = str(file_path)
        stats_data["file_size_bytes"] = file_path.stat().st_size

        if json_output:
            import json

            console.print(json.dumps(stats_data, indent=2))
        else:
            panel_content = []
            panel_content.append(f"[bold]File:[/bold] {file_path.name}")
            panel_content.append(
                f"[bold]Size:[/bold] {stats_data['file_size_bytes'] / 1024:.1f} KB"
            )
            panel_content.append("")
            panel_content.append("[bold cyan]Geometry[/bold cyan]")
            panel_content.append(f"  Vertices: {stats_data['vertex_count']:,}")
            panel_content.append(f"  Faces: {stats_data['face_count']:,}")
            panel_content.append(f"  Has Normals: {stats_data['has_normals']}")
            panel_content.append(f"  Has Texcoords: {stats_data['has_texcoords']}")
            panel_content.append("")
            panel_content.append("[bold cyan]Dimensions (meters)[/bold cyan]")
            panel_content.append(f"  Length (X): {stats_data['length']:.2f}")
            panel_content.append(f"  Width (Y): {stats_data['width']:.2f}")
            panel_content.append(f"  Height (Z): {stats_data['height']:.2f}")
            panel_content.append("")
            panel_content.append("[bold cyan]Bounding Box[/bold cyan]")
            panel_content.append(
                f"  Min: ({stats_data['bbox_min'][0]:.2f}, {stats_data['bbox_min'][1]:.2f}, {stats_data['bbox_min'][2]:.2f})"  # noqa: E501
            )
            panel_content.append(
                f"  Max: ({stats_data['bbox_max'][0]:.2f}, {stats_data['bbox_max'][1]:.2f}, {stats_data['bbox_max'][2]:.2f})"  # noqa: E501
            )

            if stats_data.get("object_name"):
                panel_content.append("")
                panel_content.append(
                    f"[bold]Object:[/bold] {stats_data['object_name']}"
                )
            if stats_data.get("material"):
                panel_content.append(f"[bold]Material:[/bold] {stats_data['material']}")

            console.print(Panel("\n".join(panel_content), title="Hull Statistics"))

    except OBJParseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def compare(
    files: list[Path] = typer.Argument(..., help="OBJ files to compare (2 or more)"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output HTML file path"
    ),
) -> None:
    """
    Compare multiple vessel hulls side by side.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli compare hull1.obj hull2.obj
    """
    if len(files) < 2:
        console.print("[red]Error:[/red] Need at least 2 files to compare")
        raise typer.Exit(1)

    from worldenergydata.vessel_hull_models.visualization.plotly_3d import (
        create_fleet_comparison,
    )

    console.print(f"\n[bold]Comparing {len(files)} hull models[/bold]\n")

    try:
        fig = create_fleet_comparison(
            obj_paths=files,
            titles=[f.stem for f in files],
        )

        if output:
            fig.write_html(str(output))
            console.print(f"[green]✓[/green] Exported to: {output}")
        else:
            fig.show()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def info() -> None:
    """
    Display module configuration and paths.
    """
    config = get_config()

    console.print("\n[bold]Vessel Hull Models Module Configuration[/bold]\n")

    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    # Storage settings
    table.add_row("Hull Storage Path", str(config.storage.hulls_path))
    table.add_row("Synthetic Path", str(config.storage.synthetic_path))
    table.add_row("Cache Path", str(config.storage.cache_path))
    table.add_row(
        "Max File Size", f"{config.storage.max_file_size / (1024*1024):.0f} MB"
    )

    # Geometry settings
    table.add_row(
        "Dimension Tolerance", f"{config.geometry.dimension_tolerance * 100:.0f}%"
    )
    table.add_row("Mesh Repair Enabled", str(config.geometry.enable_mesh_repair))

    # Visualization settings
    table.add_row("Default Colorscale", config.visualization.default_colorscale)
    table.add_row("Show Waterline", str(config.visualization.show_waterline))

    console.print(table)

    # Check if data directories exist
    console.print("\n[bold]Data Directories[/bold]\n")

    dirs_to_check = [
        ("Hull Storage", config.storage.hulls_path),
        ("Synthetic", config.storage.synthetic_path),
        ("Cache", config.storage.cache_path),
    ]

    for name, path in dirs_to_check:
        if path.exists():
            obj_count = len(list(path.glob("**/*.obj")))
            console.print(f"  [green]✓[/green] {name}: {path} ({obj_count} .obj files)")
        else:
            console.print(f"  [yellow]○[/yellow] {name}: {path} (not created)")


@app.command("convert-gdf")
def convert_gdf(
    file_path: Path = typer.Argument(..., help="Path to GDF file to convert"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory (default: same as input)"
    ),
    obj: bool = typer.Option(True, "--obj/--no-obj", help="Generate OBJ file"),
    msh: bool = typer.Option(
        True, "--msh/--no-msh", help="Generate MSH file (Gmsh format)"
    ),
) -> None:
    """
    Convert a GDF file to OBJ and/or MSH format.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli convert-gdf barge.gdf
        $ python -m worldenergydata.vessel_hull_models.cli convert-gdf hull.gdf -o ./output/
        $ python -m worldenergydata.vessel_hull_models.cli convert-gdf hull.gdf --no-msh
    """
    console.print(f"\n[bold]Converting GDF:[/bold] {file_path}\n")

    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    if output_dir is None:
        output_dir = file_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Parse GDF to get mesh info
        mesh = parse_gdf_file(file_path)
        console.print(f"  [dim]Description:[/dim] {mesh.object_name}")
        console.print(f"  [dim]Vertices:[/dim] {mesh.vertex_count:,}")
        console.print(f"  [dim]Faces:[/dim] {mesh.face_count:,}")

        dims = mesh.dimensions
        console.print(
            f"  [dim]Dimensions:[/dim] {dims['length']:.1f} × {dims['width']:.1f} × {dims['height']:.1f} m\n"  # noqa: E501
        )

        # Convert to OBJ
        if obj:
            obj_path = output_dir / file_path.with_suffix(".obj").name
            convert_gdf_to_obj(file_path, obj_path)
            console.print(f"[green]✓[/green] Created OBJ: {obj_path}")

            # Convert OBJ to MSH if requested
            if msh:
                msh_path = output_dir / file_path.with_suffix(".msh").name
                convert_obj_to_msh(obj_path, msh_path)
                console.print(f"[green]✓[/green] Created MSH: {msh_path}")
        elif msh:
            # Direct GDF to MSH conversion
            msh_path = output_dir / file_path.with_suffix(".msh").name
            convert_gdf_to_msh(file_path, msh_path)
            console.print(f"[green]✓[/green] Created MSH: {msh_path}")

        console.print("\n[bold green]Conversion complete![/bold green]")

    except OBJParseError as e:
        console.print(f"[red]Error parsing GDF:[/red] {e}")
        raise typer.Exit(1)


@app.command("validate-gdf")
def validate_gdf_cmd(
    file_path: Path = typer.Argument(..., help="Path to GDF file to validate"),
) -> None:
    """
    Validate a GDF file and display information.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli validate-gdf barge.gdf
    """
    console.print(f"\n[bold]Validating GDF:[/bold] {file_path}\n")

    result = validate_gdf_file(file_path)

    if result["valid"]:
        console.print("[green]✓[/green] File is valid\n")

        # Display header info
        header = result["header"]
        stats = result["stats"]

        table = Table(title="GDF File Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Description", header["description"])
        table.add_row("Unit Length", str(header["unit_length"]))
        table.add_row("Gravity", str(header["gravity"]))
        table.add_row("X Symmetry", str(header["symmetry_x"]))
        table.add_row("Y Symmetry", str(header["symmetry_y"]))
        table.add_row("Declared Panels", str(header["declared_panels"]))
        table.add_row("", "")
        table.add_row("Parsed Vertices", f"{stats['vertex_count']:,}")
        table.add_row("Parsed Faces", f"{stats['face_count']:,}")

        dims = stats.get("dimensions", {})
        if dims:
            table.add_row("Length (X)", f"{dims.get('length', 0):.2f} m")
            table.add_row("Width (Y)", f"{dims.get('width', 0):.2f} m")
            table.add_row("Height (Z)", f"{dims.get('height', 0):.2f} m")

        console.print(table)
    else:
        console.print("[red]✗[/red] Validation failed\n")
        for error in result["errors"]:
            console.print(f"  [red]Error:[/red] {error}")
        raise typer.Exit(1)


@app.command("list-gdf")
def list_gdf(
    directory: Path = typer.Argument(..., help="Directory to search for GDF files"),
    recursive: bool = typer.Option(
        True, "--recursive/--no-recursive", "-r", help="Search recursively"
    ),
) -> None:
    """
    List GDF files in a directory.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli list-gdf /path/to/gdf/files
        $ python -m worldenergydata.vessel_hull_models.cli list-gdf . --no-recursive
    """
    if not directory.exists():
        console.print(f"[red]Error:[/red] Directory not found: {directory}")
        raise typer.Exit(1)

    pattern = "**/*.gdf" if recursive else "*.gdf"
    gdf_files = sorted(directory.glob(pattern))

    if not gdf_files:
        console.print(f"[yellow]No GDF files found in {directory}[/yellow]")
        return

    table = Table(title=f"GDF Files in {directory}")
    table.add_column("File", style="cyan")
    table.add_column("Panels", justify="right")
    table.add_column("Faces", justify="right")
    table.add_column("Symmetry", justify="center")
    table.add_column("Description", max_width=40)

    for gdf_file in gdf_files:
        try:
            result = validate_gdf_file(gdf_file)
            if result["valid"]:
                header = result["header"]
                stats = result["stats"]

                symmetry = []
                if header["symmetry_x"]:
                    symmetry.append("X")
                if header["symmetry_y"]:
                    symmetry.append("Y")
                sym_str = ",".join(symmetry) if symmetry else "-"

                table.add_row(
                    str(gdf_file.relative_to(directory)),
                    str(header["declared_panels"]),
                    f"{stats['face_count']:,}",
                    sym_str,
                    header["description"][:40],
                )
            else:
                table.add_row(
                    str(gdf_file.relative_to(directory)),
                    "-",
                    "-",
                    "-",
                    f"[red]Invalid: {result['errors'][0][:30]}[/red]",
                )
        except Exception as e:
            table.add_row(
                str(gdf_file.relative_to(directory)),
                "-",
                "-",
                "-",
                f"[red]Error: {str(e)[:30]}[/red]",
            )

    console.print(table)
    console.print(f"\n[dim]Total: {len(gdf_files)} GDF file(s)[/dim]")


@app.command("batch-convert")
def batch_convert(
    directory: Path = typer.Argument(..., help="Directory containing GDF files"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory (default: same as input)"
    ),
    recursive: bool = typer.Option(
        True, "--recursive/--no-recursive", "-r", help="Search recursively"
    ),
    obj: bool = typer.Option(True, "--obj/--no-obj", help="Generate OBJ files"),
    msh: bool = typer.Option(
        True, "--msh/--no-msh", help="Generate MSH files (Gmsh format)"
    ),
) -> None:
    """
    Batch convert all GDF files in a directory to OBJ and MSH formats.

    Examples:
        $ python -m worldenergydata.vessel_hull_models.cli batch-convert ./gdf_files/
        $ python -m worldenergydata.vessel_hull_models.cli batch-convert ./input/ -o ./output/
    """
    if not directory.exists():
        console.print(f"[red]Error:[/red] Directory not found: {directory}")
        raise typer.Exit(1)

    pattern = "**/*.gdf" if recursive else "*.gdf"
    gdf_files = list(directory.glob(pattern))

    if not gdf_files:
        console.print(f"[yellow]No GDF files found in {directory}[/yellow]")
        return

    console.print(f"\n[bold]Batch Converting {len(gdf_files)} GDF files[/bold]\n")

    if output_dir is None:
        output_dir = directory
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting...", total=len(gdf_files))

        for gdf_file in gdf_files:
            progress.update(task, description=f"Converting {gdf_file.name}...")

            try:
                # Determine output path preserving directory structure
                rel_path = gdf_file.relative_to(directory)
                out_subdir = output_dir / rel_path.parent
                out_subdir.mkdir(parents=True, exist_ok=True)

                if obj:
                    obj_path = out_subdir / gdf_file.with_suffix(".obj").name
                    convert_gdf_to_obj(gdf_file, obj_path)

                    if msh:
                        msh_path = out_subdir / gdf_file.with_suffix(".msh").name
                        convert_obj_to_msh(obj_path, msh_path)
                elif msh:
                    msh_path = out_subdir / gdf_file.with_suffix(".msh").name
                    convert_gdf_to_msh(gdf_file, msh_path)

                success_count += 1

            except Exception as e:
                console.print(f"  [red]Error converting {gdf_file.name}:[/red] {e}")
                error_count += 1

            progress.advance(task)

    console.print("\n[bold]Batch Conversion Complete[/bold]")
    console.print(f"  [green]✓ Successful:[/green] {success_count}")
    if error_count > 0:
        console.print(f"  [red]✗ Failed:[/red] {error_count}")


def main() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
