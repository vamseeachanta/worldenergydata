"""Annual standalone catalog remains outside the weekly host allowlist."""

from pathlib import Path

import yaml

from worldenergydata.bsee.data.refresh.url_registry import get_specs_for_dir
from worldenergydata.bsee.fieldreserves_fetch import FILES


def test_annual_catalog_matches_fetch_and_supported_registry():
    root = Path(__file__).parents[3]
    config = yaml.safe_load((root / "config/bsee.yml").read_text())
    family = config["fieldreserves_annual"]
    assert family["entry_point"] == "scripts/bsee/fetch_fieldreserves_family.py"
    assert set(family["archives"]) == set(FILES)
    for archive, info in family["archives"].items():
        if info.get("registry_dir"):
            assert get_specs_for_dir(info["registry_dir"])[0].zip_url.endswith(
                archive.replace(" ", "%20")
            )
    assert family["archives"]["2023 FldMoPro.zip"]["status"] == "fetch_only"
    assert (
        family["archives"]["appendbdelimit.zip"]["classification"]
        == "lease_to_field_index"
    )
