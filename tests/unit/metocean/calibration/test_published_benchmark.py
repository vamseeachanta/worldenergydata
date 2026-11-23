"""Opt-in reproduction of Oikonomou et al. (2026), DOI 10.1016/j.apor.2026.105259.

No downloads during pytest; use the licensed-data fetch script documented in README.
"""

import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.io import loadmat

from worldenergydata.metocean.calibration import (
    fit,
    joint_diagnostics,
    metrics,
    time_block_split,
)

MANIFEST = (
    Path(__file__).resolve().parents[3]
    / "fixtures/metocean/bias_correction/manifest.json"
)
SPEC = json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def published_results():
    directory = os.environ.get("METOCEAN_BIAS_BENCHMARK_DIR")
    if not directory:
        pytest.skip("Set METOCEAN_BIAS_BENCHMARK_DIR after fetching the CC BY 4.0 data")
    path = Path(directory) / SPEC["member"]["name"]
    # A configured but missing or changed dataset is a failure, never a skip.
    assert path.stat().st_size == SPEC["member"]["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SPEC["member"]["sha256"]
    data = loadmat(path, squeeze_me=True, struct_as_record=False)["data"]
    frames = []
    ids = (
        "61196|61197|61198|61280|61281|61417|61430|"
        "6100196|6100197|6100198|6100280|6100281|6100417|6100430"
    )
    for field in data._fieldnames:
        if not re.fullmatch(rf"IR_TS_MO_({ids})_\d{{4}}", field):
            continue
        a = np.asarray(getattr(data, field))
        if a.size == 0:
            continue
        # Schema from the archived data loader: MATLAB day, Hs/Tm02 obs/model.
        frames.append(
            pd.DataFrame(
                {
                    "time": pd.to_datetime(a[:, 0] - 719529, unit="D", errors="coerce"),
                    "oh": a[:, 11],
                    "ot": a[:, 13],
                    "mh": a[:, 17],
                    "mt": a[:, 18],
                }
            )
        )
    df = (
        pd.concat(frames, ignore_index=True).replace([np.inf, -np.inf], np.nan).dropna()
    )
    t = df.time.dt
    # Match the release's exact 3-hour stamp selection, without averaging or rounding.
    df = df[(t.minute == 0) & (t.second == 0) & (t.hour % 3 == 0)].sort_values("time")
    cal, val = time_block_split(df.time, SPEC["calibration"], SPEC["validation"])
    a, b = df[cal], df[val]
    assert len(b) == SPEC["validation_pairs"]
    settings = {
        "n_quantiles": SPEC["n_quantiles"],
        "q_range": SPEC["q_range"],
        "times": a.time,
        "qdm_reference": "calibration",
    }
    series = {"raw": (b.mh, b.mt)}
    for method in ("eqm", "qdm"):
        series[method] = (
            fit(a.mh, a.oh, method, **settings).apply(b.mh),
            fit(a.mt, a.ot, method, **settings).apply(b.mt),
        )
    cqdm = fit(a.mt, a.ot, "conditional_qdm", model_hs=a.mh, obs_hs=a.oh, **settings)
    series["conditional_qdm"] = (series["qdm"][0], cqdm.apply(b.mt, hs=b.mh))
    results = {}
    for method, (h, t) in series.items():
        results[f"{method}_hs_p95"] = metrics(b.oh, h)["p95"]
        results[f"{method}_tm02_rmsd"] = metrics(b.ot, t)["rmsd"]
        results[f"{method}_joint_l1"] = joint_diagnostics(
            b.oh,
            b.ot,
            h,
            t,
            hs_edges=np.arange(0, 3.51, 0.25),
            tm_edges=np.arange(2, 8.01, 0.5),
        )["l1"]
    print(json.dumps({"validation_pairs": len(b), "results": results}, indent=2))
    return results


@pytest.mark.parametrize("target,expected", SPEC["targets"].items())
def test_published_validation_value(published_results, target, expected):
    assert published_results[target] == pytest.approx(
        expected, abs=SPEC["absolute_tolerance"]
    )
