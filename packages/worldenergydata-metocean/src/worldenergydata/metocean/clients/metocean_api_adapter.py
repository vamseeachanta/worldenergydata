"""Optional metocean-api adapter limited to NORA3 and NorKyst800.

The LGPL backend is imported only for a cache miss. See the optional-backends
guide for dependency installation and the inspected release API.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

_PRODUCTS = {"NORA3": "NORA3_wave_sub", "NorKyst800": "NORKYST800"}

# The upstream implementation writes relative cache files. A child interpreter
# confines those files to the caller's cache directory without changing cwd in
# the application process. Constructor and method names were checked against
# metocean-api 1.1.14 (ts/ts_mod.py); no shell interpolates request values.
_DOWNLOAD = """
import json
import sys
from metocean_api.ts import TimeSeries
payload = json.load(sys.stdin)
series = TimeSeries(**payload['request'], datafile=payload['destination'])
series.import_data(save_csv=False, save_nc=False, use_cache=True)
if series.data is None or series.data.empty:
    raise ValueError('No sample returned')
series.data.to_csv(payload['destination'])
"""


class MetoceanAPIAdapter:
    """Fetch explicit variables and time windows, with digest-checked CSV caching.

    No product passthrough is provided. The dataset names are adapter inputs;
    upstream product identifiers remain private. Existing cache entries can be
    read without the optional backend. A timeout may be supplied by the caller.
    """

    def __init__(self, cache_dir: Path, *, timeout_seconds: float | None = None):
        self.cache_dir = Path(cache_dir).resolve()
        self.timeout_seconds = timeout_seconds

    def fetch(
        self,
        *,
        dataset: str,
        lon: float,
        lat: float,
        start_time: str,
        end_time: str,
        variables: list[str],
        depth: list[float] | None = None,
    ) -> pd.DataFrame:
        if dataset not in _PRODUCTS:
            raise ValueError("dataset must be NORA3 or NorKyst800")
        if not variables or not all(isinstance(v, str) and v for v in variables):
            raise ValueError("Explicit variable names are required")
        start, end = pd.Timestamp(start_time), pd.Timestamp(end_time)
        if pd.isna(start) or pd.isna(end) or start > end:
            raise ValueError("Expected an ordered time window")
        request = {
            "product": _PRODUCTS[dataset],
            "lon": lon,
            "lat": lat,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "variable": list(variables),
            "depth": depth,
        }
        encoded = json.dumps(request, sort_keys=True, allow_nan=False)
        key = hashlib.sha256(encoded.encode()).hexdigest()
        directory = self.cache_dir / key
        destination = directory / "sample.csv"
        manifest = directory / "manifest.json"
        if manifest.exists():
            record = json.loads(manifest.read_text(encoding="utf-8"))
            if record["request"] != request or record["sha256"] != self._digest(
                destination
            ):
                raise ValueError("Cached sample request or digest mismatch")
        else:
            directory.mkdir(parents=True, exist_ok=True)
            self._download(request, directory, destination)
            # Parse before publishing a completion record; failed/empty downloads
            # are not recognized as completed cache entries on subsequent runs.
            if pd.read_csv(destination).empty:
                raise ValueError("No sample returned")
            record = {"request": request, "sha256": self._digest(destination)}
            manifest.write_text(
                json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
            )
        return pd.read_csv(destination)

    @staticmethod
    def _digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _download(self, request, directory, destination):
        try:
            available = importlib.util.find_spec("metocean_api") is not None
        except ModuleNotFoundError:
            available = False
        if not available:
            raise ImportError(
                "Install the optional metocean-api extra to fetch uncached samples"
            )
        result = subprocess.run(
            [sys.executable, "-c", _DOWNLOAD],
            input=json.dumps({"request": request, "destination": str(destination)}),
            cwd=directory,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if result.returncode:
            raise RuntimeError(
                f"metocean-api sample retrieval failed (exit {result.returncode})"
            )
