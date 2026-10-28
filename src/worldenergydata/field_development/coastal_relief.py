"""NOAA CRM volume discovery and bounded OPeNDAP request planning.

No network access or raster download occurs here. Catalog XML and dimension
lengths must be supplied from inspected source metadata; no spatial resolution,
vertical datum, depth sign, or engineering suitability is inferred.

Sources (accessed 2026-10-19):
* NOAA NCEI, U.S. Coastal Relief Model catalog (citation: September 2010):
  https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml
* OPeNDAP User Guide, section 4.4.2, Constraints (undated online edition):
  https://opendap.github.io/documentation/UserGuideComprehensive.html
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from xml.parsers import expat

from .terrain import load_terrain_sources

# Namespace, volume naming and urlPath pattern: NOAA catalog cited above.
_NAMESPACE = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
_VOLUME_NAME = re.compile(r"crm_vol[1-9][0-9]*\.nc")


@dataclass(frozen=True)
class CrmVolume:
    """An advertised numbered volume, with catalog-configured access URLs."""

    name: str
    http_url: str
    opendap_url: str


def _catalog_datasets(catalog_xml: str | bytes) -> list[dict[str, str]]:
    """Collect dataset attributes without accepting DTDs or entity expansion."""
    parser = expat.ParserCreate(namespace_separator="}")
    root_name = None
    datasets = []

    def reject_dtd(*_args: object) -> None:
        raise ValueError("CRM catalog DTD and entity declarations are forbidden")

    def start_element(name: str, attributes: dict[str, str]) -> None:
        nonlocal root_name
        if root_name is None:
            root_name = name
        if name == f"{_NAMESPACE}}}dataset":
            datasets.append(attributes)

    # Reject at declaration time, before any internal/external entity can be
    # expanded. Expat handles encodings, so UTF-16 cannot evade a text filter.
    parser.StartDoctypeDeclHandler = reject_dtd
    parser.EntityDeclHandler = reject_dtd
    parser.StartElementHandler = start_element
    try:
        parser.Parse(catalog_xml, True)
    except expat.ExpatError as exc:
        raise ValueError("invalid CRM catalog XML") from exc
    if root_name != f"{_NAMESPACE}}}catalog":
        raise ValueError("expected a THREDDS catalog")
    return datasets


def discover_crm_volumes(
    catalog_xml: str | bytes, *, catalog_path: Path | None = None
) -> tuple[CrmVolume, ...]:
    """Read numbered CRM volumes from saved NOAA THREDDS XML.

    Endpoints come from the existing terrain source catalog. Only the numbered
    ``crm_vol*.nc`` family is supported; other products and catalog references
    are ignored. No remote service URL from the XML is followed. Inventory order
    is preserved, and malformed paths or duplicates are rejected.
    """
    datasets = _catalog_datasets(catalog_xml)
    source = load_terrain_sources(catalog_path)["noaa_ncei_coastal_relief"]
    if source["status"] != "verified":
        raise ValueError("CRM terrain source is not verified")
    endpoints = source["endpoints"]
    volumes = []
    seen = set()
    for dataset in datasets:
        name = dataset.get("name", "")
        if not _VOLUME_NAME.fullmatch(name):
            continue
        if dataset.get("urlPath") != f"crm/{name}":
            raise ValueError("unexpected CRM volume urlPath")
        volume = name.removesuffix(".nc")
        if volume in seen:
            raise ValueError("duplicate CRM volume")
        seen.add(volume)
        volumes.append(
            CrmVolume(
                volume,
                endpoints["http_file_template"].format(volume=volume),
                endpoints["opendap_template"].format(volume=volume),
            )
        )
    if not volumes:
        raise ValueError("catalog advertises no CRM volumes")
    return tuple(volumes)


@dataclass(frozen=True)
class IndexRange:
    """Zero-based inclusive DAP indices, bounded by an inspected axis length.

    DAP Guide section 4.4.2 uses [start:stride:stop], including stop if reached.
    Thus count = floor((stop - start) / stride) + 1. Zero and one below are
    index/count identities, not physical constants or acceptance limits.
    """

    start: int
    stop: int
    stride: int
    length: int

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (self.start, self.stop, self.stride, self.length)
        ):
            raise ValueError("indices, stride and length must be integers")
        if not (0 <= self.start <= self.stop < self.length) or self.stride <= 0:
            raise ValueError("index range outside axis or nonpositive stride")

    @property
    def count(self) -> int:
        """Number of selected cells, using DAP's inclusive stop semantics."""
        return (self.stop - self.start) // self.stride + 1

    def projection(self) -> str:
        """Return the DAP hyperslab expression for this axis."""
        return f"[{self.start}:{self.stride}:{self.stop}]"


def plan_crm_subset(
    volume: CrmVolume,
    rows: IndexRange,
    columns: IndexRange,
    *,
    grid_name: str,
    max_cells: int,
) -> str:
    """Plan an ASCII DAP request for an inspected two-dimensional grid.

    Inspect the volume's .dds and .das first. Supply the exact grid name,
    dimension order and lengths from those documents. For example, NOAA's
    crm_vol3.nc.dds (accessed 2026-10-19) declares z[y][x]:
    https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol3.nc.dds

    The caller must set max_cells; this is an operational budget, not a source
    accuracy criterion. It bounds selected data cells, not response bytes or
    server memory. The returned URL is a plan, not a validated dataset or a
    downloaded netCDF file. ASCII DAP responses include coordinate maps.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", grid_name):
        raise ValueError("grid_name must be a simple DAP identifier")
    if isinstance(max_cells, bool) or not isinstance(max_cells, int) or max_cells <= 0:
        raise ValueError("max_cells must be a positive integer")
    if rows.count * columns.count > max_cells:
        raise ValueError("subset exceeds max_cells")
    projection = grid_name + rows.projection() + columns.projection()
    return volume.opendap_url + ".ascii?" + quote(projection, safe=":")
