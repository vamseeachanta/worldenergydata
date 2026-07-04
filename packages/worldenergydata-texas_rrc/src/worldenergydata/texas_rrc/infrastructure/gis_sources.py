"""Load official Texas RRC well and pipeline GIS shapefile ZIPs."""

from __future__ import annotations

import math
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from zipfile import BadZipFile, ZipFile

import shapefile


class GisSourceError(ValueError):
    """Raised when a GIS source ZIP cannot be read as a shapefile."""


@dataclass(frozen=True)
class WellGisRecord:
    """One Texas RRC well point from official GIS layers."""

    api_number: str | None
    county_fips: str | None
    latitude: float
    longitude: float
    source_file: str


@dataclass(frozen=True)
class PipelineGisRecord:
    """One Texas RRC pipeline polyline from official GIS layers."""

    pipeline_identifier: str | None
    county_fips: str | None
    coordinates: tuple[tuple[float, float], ...]
    source_file: str


@dataclass(frozen=True)
class GisLoadResult:
    """GIS load result with structured gaps for CLI and quality reports."""

    well_gis: tuple[WellGisRecord, ...]
    pipeline_gis: tuple[PipelineGisRecord, ...]
    source_gaps: tuple[str, ...]
    malformed_source_files: tuple[str, ...]
    input_paths: tuple[str, ...]


API_ALIASES = (
    "API",
    "API_NO",
    "API_NUM",
    "API_NUMBER",
    "APINUM",
    "API_UWI",
    "API14",
    "API10",
)
COUNTY_ALIASES = ("CNTY_FIPS", "COUNTY_FIP", "COUNTYFIPS", "FIPS", "COUNTY")
PIPELINE_ID_ALIASES = (
    "T4PERMIT",
    "PERMIT",
    "P5NUM",
    "PIPE_ID",
    "PIPELINEID",
    "SEGMENT",
    "OBJECTID",
)


def load_well_gis_records(raw_root: Path | str) -> tuple[WellGisRecord, ...]:
    """Load well point records from zipped official RRC shapefiles."""
    return tuple(_load_zip_records(_local_root(raw_root), _well_records_from_reader))


def load_pipeline_gis_records(raw_root: Path | str) -> tuple[PipelineGisRecord, ...]:
    """Load pipeline polyline records from zipped official RRC shapefiles."""
    return tuple(
        _load_zip_records(_local_root(raw_root), _pipeline_records_from_reader)
    )


def load_gis_inputs(root: Path | str) -> GisLoadResult:
    """Load GIS records under a Texas RRC root without aborting on one bad ZIP."""
    local_root = _local_root(root)
    source_gaps: list[str] = []
    malformed: list[str] = []
    input_paths: list[str] = []
    well_root = local_root / "raw" / "gis" / "wells"
    pipeline_root = local_root / "raw" / "gis" / "pipelines"
    wells = _safe_load_source(
        well_root,
        "well_gis_layers",
        _well_records_from_reader,
        source_gaps,
        malformed,
        input_paths,
    )
    pipelines = _safe_load_source(
        pipeline_root,
        "pipeline_gis_layers",
        _pipeline_records_from_reader,
        source_gaps,
        malformed,
        input_paths,
    )
    return GisLoadResult(
        well_gis=wells,
        pipeline_gis=pipelines,
        source_gaps=tuple(source_gaps),
        malformed_source_files=tuple(malformed),
        input_paths=tuple(input_paths),
    )


def normalize_api_number(value: object) -> str | None:
    """Normalize Texas API-like values to a 14-digit comparison key."""
    if value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        value = int(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return None
    digits = _digits(value)
    if not digits:
        return None
    if len(digits) == 8:
        return f"42{digits}0000"
    if len(digits) == 10:
        return f"{digits}0000"
    if len(digits) >= 14:
        return digits[:14]
    return None


def normalize_county_fips(value: object) -> str | None:
    """Normalize county/FIPS values to the Texas three-digit county key."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return None
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return digits[-3:].zfill(3)


def _safe_load_source(
    raw_root: Path,
    source_id: str,
    loader: Callable,
    source_gaps: list[str],
    malformed: list[str],
    input_paths: list[str],
) -> tuple:
    zip_paths = _zip_paths(raw_root)
    if not zip_paths:
        source_gaps.append(source_id)
        return ()
    input_paths.extend(str(path.relative_to(raw_root.parents[2])) for path in zip_paths)
    records = []
    for zip_path in zip_paths:
        try:
            records.extend(_records_from_zip(zip_path, loader))
        except GisSourceError as exc:
            malformed.append(str(exc))
    if not records:
        source_gaps.append(source_id)
    return tuple(records)


def _local_root(root: Path | str) -> Path:
    value = str(root)
    if "://" in value:
        raise ValueError("GIS source inputs must be local filesystem paths")
    return Path(root)


def _load_zip_records(raw_root: Path, loader: Callable) -> Iterable:
    for zip_path in _zip_paths(raw_root):
        yield from _records_from_zip(zip_path, loader)


def _zip_paths(raw_root: Path) -> tuple[Path, ...]:
    if not raw_root.exists():
        return ()
    return tuple(sorted(path for path in raw_root.rglob("*.zip") if path.is_file()))


def _records_from_zip(zip_path: Path, loader: Callable) -> Iterable:
    try:
        with ZipFile(zip_path) as archive:
            _validate_members(zip_path, archive)
            with tempfile.TemporaryDirectory() as tmp:
                _extract_members_safely(zip_path, archive, Path(tmp))
                shapefiles = sorted(Path(tmp).rglob("*.shp"))
                if not shapefiles:
                    raise GisSourceError(f"{zip_path.name}: missing .shp member")
                for shp_path in shapefiles:
                    reader = shapefile.Reader(str(shp_path))
                    yield from loader(reader, zip_path.name)
    except BadZipFile as exc:
        raise GisSourceError(f"{zip_path.name}: invalid ZIP archive") from exc
    except GisSourceError:
        raise
    except Exception as exc:  # pyshp raises mixed exception types
        raise GisSourceError(f"{zip_path.name}: {exc}") from exc


def _validate_members(zip_path: Path, archive: ZipFile) -> None:
    suffixes = {Path(name).suffix.lower() for name in archive.namelist()}
    missing = {".shp", ".shx", ".dbf"} - suffixes
    if missing:
        raise GisSourceError(
            f"{zip_path.name}: missing required shapefile members "
            f"{', '.join(sorted(missing))}"
        )


def _extract_members_safely(zip_path: Path, archive: ZipFile, target_dir: Path) -> None:
    root = target_dir.resolve()
    for member in archive.namelist():
        member_path = Path(member)
        target = (target_dir / member_path).resolve()
        if member_path.is_absolute() or not target.is_relative_to(root):
            raise GisSourceError(f"{zip_path.name}: unsafe ZIP member path {member!r}")
    archive.extractall(target_dir)


def _well_records_from_reader(
    reader: shapefile.Reader,
    source_file: str,
) -> Iterable[WellGisRecord]:
    for item in reader.iterShapeRecords():
        if not item.shape.points:
            continue
        longitude, latitude = item.shape.points[0]
        attrs = _attributes(reader, item.record)
        raw_api = _first_attr(attrs, API_ALIASES)
        yield WellGisRecord(
            api_number=normalize_api_number(raw_api),
            county_fips=_well_county_fips(attrs, raw_api, source_file),
            latitude=float(latitude),
            longitude=float(longitude),
            source_file=source_file,
        )


def _pipeline_records_from_reader(
    reader: shapefile.Reader,
    source_file: str,
) -> Iterable[PipelineGisRecord]:
    for item in reader.iterShapeRecords():
        coordinates = tuple((float(x), float(y)) for x, y in item.shape.points)
        if len(coordinates) < 2:
            continue
        attrs = _attributes(reader, item.record)
        yield PipelineGisRecord(
            pipeline_identifier=_string_or_none(
                _first_attr(attrs, PIPELINE_ID_ALIASES)
            ),
            county_fips=normalize_county_fips(_first_attr(attrs, COUNTY_ALIASES)),
            coordinates=coordinates,
            source_file=source_file,
        )


def _attributes(reader: shapefile.Reader, record) -> dict[str, object]:
    fields = [field[0].upper().strip() for field in reader.fields[1:]]
    return dict(zip(fields, list(record)))


def _first_attr(attrs: dict[str, object], aliases: tuple[str, ...]) -> object | None:
    for alias in aliases:
        if alias in attrs:
            return attrs[alias]
    return None


def _well_county_fips(
    attrs: dict[str, object],
    raw_api: object | None,
    source_file: str,
) -> str | None:
    county = normalize_county_fips(_first_attr(attrs, COUNTY_ALIASES))
    if county:
        return county
    api_digits = _digits(raw_api)
    if len(api_digits) == 8:
        return api_digits[:3]
    match = re.match(r"well(\d{3})", source_file.lower())
    return match.group(1) if match else None


def _digits(value: object | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\D", "", str(value).strip())


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "GisLoadResult",
    "GisSourceError",
    "PipelineGisRecord",
    "WellGisRecord",
    "load_gis_inputs",
    "load_pipeline_gis_records",
    "load_well_gis_records",
    "normalize_api_number",
    "normalize_county_fips",
]
