"""Offline NOAA discovery and independent DAP index calculations.

Synthetic catalog records follow NOAA's CRM catalog (accessed 2026-10-19):
https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml
All index values below are synthetic, not measured coastal elevations.
"""

from urllib.parse import unquote, urlsplit

import pytest
import yaml

from worldenergydata.field_development.coastal_relief import (
    IndexRange,
    discover_crm_volumes,
    plan_crm_subset,
)

CATALOG = """<catalog
 xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
 <dataset name="Coastal Relief Model by Volume">
  <dataset name="crm_vol3.nc" urlPath="crm/crm_vol3.nc"/>
  <dataset name="crm_vol5.nc" urlPath="crm/crm_vol5.nc"/>
  <dataset name="crm_socal_1as_vers2.nc" urlPath="crm/crm_socal_1as_vers2.nc"/>
  <catalogRef name="cudem"/>
 </dataset>
</catalog>"""


def test_discovery_uses_shipped_endpoint_templates():
    volumes = discover_crm_volumes(CATALOG)
    assert [v.name for v in volumes] == ["crm_vol3", "crm_vol5"]
    assert volumes[0].http_url == (
        "https://www.ngdc.noaa.gov/thredds/fileServer/crm/crm_vol3.nc"
    )
    assert volumes[0].opendap_url == (
        "https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol3.nc"
    )


def test_discovery_accepts_saved_xml_bytes():
    assert discover_crm_volumes(CATALOG.encode()) == discover_crm_volumes(CATALOG)


@pytest.mark.parametrize(
    "xml",
    ["<html/>", "<catalog", CATALOG.replace("crm/crm_vol3.nc", "../crm_vol3.nc")],
)
def test_invalid_catalog_rejected(xml):
    with pytest.raises(ValueError):
        discover_crm_volumes(xml)


def test_duplicate_volume_rejected():
    xml = CATALOG.replace("crm_vol5", "crm_vol3")
    with pytest.raises(ValueError, match="duplicate"):
        discover_crm_volumes(xml)


def test_empty_volume_inventory_rejected():
    xml = CATALOG.replace("crm_vol", "other_vol")
    with pytest.raises(ValueError, match="no CRM volumes"):
        discover_crm_volumes(xml)


def test_subset_projection_and_inclusive_count():
    """Hand calculation: rows 1,3,5 and columns 0,3,6,9 give 3*4=12 cells.

    DAP User Guide, section 4.4.2, Constraints (accessed 2026-10-19):
    https://opendap.github.io/documentation/UserGuideComprehensive.html
    The published [0:5:19] example selects 0,5,10,15, confirming inclusive
    stop semantics even when the final stride does not land on the stop.
    """
    volume = discover_crm_volumes(CATALOG)[0]
    rows = IndexRange(start=1, stride=2, stop=6, length=7)
    columns = IndexRange(start=0, stride=3, stop=9, length=10)
    assert rows.count == 3
    assert columns.count == 4
    url = plan_crm_subset(volume, rows, columns, grid_name="z", max_cells=12)
    assert urlsplit(url).path.endswith("crm_vol3.nc.ascii")
    assert unquote(urlsplit(url).query) == "z[1:2:6][0:3:9]"
    with pytest.raises(ValueError, match="max_cells"):
        plan_crm_subset(volume, rows, columns, grid_name="z", max_cells=11)


def test_published_stride_example():
    """DAP Guide section 4.4.2: [0:5:19] selects 0,5,10,15: four cells."""
    assert IndexRange(start=0, stride=5, stop=19, length=20).count == 4


@pytest.mark.parametrize(
    "overrides",
    [
        {"start": -1},
        {"stop": 10},
        {"start": 3, "stop": 2},
        {"stride": 0},
        {"stride": -1},
        {"length": 0},
        {"start": True},
        {"stop": 2.5},
        {"stride": False},
        {"length": 10.0},
    ],
)
def test_invalid_index_ranges(overrides):
    values = {"start": 0, "stop": 9, "stride": 1, "length": 10}
    values.update(overrides)
    with pytest.raises(ValueError):
        IndexRange(**values)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_cell_limits(limit):
    volume = discover_crm_volumes(CATALOG)[0]
    cell = IndexRange(start=0, stop=0, stride=1, length=1)
    with pytest.raises(ValueError, match="max_cells"):
        plan_crm_subset(volume, cell, cell, grid_name="z", max_cells=limit)


@pytest.mark.parametrize("name", ["", "z,x", "z&x", "z[0]", "z?x", "../z"])
def test_projection_injection_rejected(name):
    volume = discover_crm_volumes(CATALOG)[0]
    cell = IndexRange(start=0, stop=0, stride=1, length=1)
    with pytest.raises(ValueError, match="grid_name"):
        plan_crm_subset(volume, cell, cell, grid_name=name, max_cells=1)


def test_endpoint_override_and_unverified_source(tmp_path):
    from worldenergydata.field_development.terrain import TERRAIN_SOURCES_PATH

    catalog = yaml.safe_load(TERRAIN_SOURCES_PATH.read_text())
    entry = catalog["sources"]["noaa_ncei_coastal_relief"]
    entry["endpoints"]["opendap_template"] = "https://example.org/dap/{volume}.nc"
    path = tmp_path / "sources.yml"
    path.write_text(yaml.safe_dump(catalog))
    assert discover_crm_volumes(CATALOG, catalog_path=path)[0].opendap_url == (
        "https://example.org/dap/crm_vol3.nc"
    )
    entry["status"] = "not_verified"
    path.write_text(yaml.safe_dump(catalog))
    with pytest.raises(ValueError, match="not verified"):
        discover_crm_volumes(CATALOG, catalog_path=path)


def test_catalog_cannot_redirect_volume():
    xml = CATALOG.replace("crm/crm_vol3.nc", "https://example.org/crm_vol3.nc")
    with pytest.raises(ValueError, match="urlPath"):
        discover_crm_volumes(xml)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_catalog_rejects_doctype_and_entities(encoding):
    xml = '<!DOCTYPE catalog [<!ENTITY name "crm_vol3.nc">]>' + CATALOG
    with pytest.raises(ValueError, match="DTD"):
        discover_crm_volumes(xml.encode(encoding))
