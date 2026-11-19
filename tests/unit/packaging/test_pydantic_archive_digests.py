"""Verify the locked Pydantic releases against a local archive directory.

Set PYDANTIC_ARCHIVE_DIR to a directory containing the two source archives
and every wheel listed for pydantic and pydantic-core in uv.lock.
"""

import hashlib
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


@pytest.mark.parametrize("name", ["pydantic", "pydantic-core"])
def test_pydantic_archive_digests(name):
    directory = os.environ.get("PYDANTIC_ARCHIVE_DIR")
    if not directory:
        pytest.skip("Set PYDANTIC_ARCHIVE_DIR to the release archive directory")

    with (Path(__file__).resolve().parents[3] / "uv.lock").open("rb") as stream:
        packages = tomllib.load(stream)["package"]
    (package,) = [entry for entry in packages if entry["name"] == name]
    for archive in [package["sdist"], *package["wheels"]]:
        filename = Path(urlsplit(archive["url"]).path).name
        path = Path(directory) / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert f"sha256:{digest}" == archive["hash"], filename
