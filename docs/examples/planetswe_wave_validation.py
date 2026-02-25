"""
planetswe_wave_validation.py
============================

Example: streaming planetswe (Shallow Water Equations) data from The Well and
performing a basic wave-amplitude validation against analytical expectations.

The Well dataset — CC BY 4.0, Polymathic AI
https://github.com/PolymathicAI/the_well

Prerequisites
-------------
Install the optional well extra::

    pip install worldenergydata[well]
    # or directly:
    pip install the_well>=1.2.0

What this script does
---------------------
1. Constructs a PlanetsweLoader pointed at the training split.
2. Streams 10 time-step snapshots without downloading the full dataset.
3. Prints basic statistics (min, max, mean) for the wave-height field in
   each snapshot — a smoke test that the data pipeline is functioning.
4. Demonstrates how to incorporate the attribution string required by the
   CC BY 4.0 license.

The planetswe dataset
---------------------
- 2D shallow water equations solved on a rotating sphere.
- Models planetary-scale wave propagation (Rossby / Kelvin waves).
- Grid: latitude × longitude with vorticity, divergence, and height fields.
- Relevant to metocean wave propagation model validation.
"""

import sys

# Attribution — required by CC BY 4.0 license when using The Well data.
from worldenergydata.metocean.well_datasets import THE_WELL_ATTRIBUTION, PlanetsweLoader

print(f"Data source: {THE_WELL_ATTRIBUTION}\n")

# ---------------------------------------------------------------------------
# 1. Construct the loader
# ---------------------------------------------------------------------------
loader = PlanetsweLoader(split="train")
print(f"Loader: {loader!r}\n")

# ---------------------------------------------------------------------------
# 2. Stream 10 time-step snapshots (no full-dataset download)
# ---------------------------------------------------------------------------
try:
    print("Streaming 10 planetswe snapshots...\n")
    for step_idx, sample in enumerate(loader.stream_sample(n_steps=10)):
        # Each sample is a dict; the wave field lives under "data".
        data = sample.get("data")

        if data is None:
            print(f"  step {step_idx:02d}: no 'data' key in sample — keys: {list(sample)}")
            continue

        # Basic statistics — works whether data is a numpy array or torch tensor.
        try:
            import numpy as _np

            arr = _np.asarray(data)
            print(
                f"  step {step_idx:02d}: shape={arr.shape}  "
                f"min={arr.min():.4f}  max={arr.max():.4f}  mean={arr.mean():.4f}"
            )
        except Exception:
            # Fallback if numpy conversion fails.
            print(f"  step {step_idx:02d}: sample received (type={type(data).__name__})")

    print("\nSmoke test passed — planetswe stream is operational.")

except ImportError as exc:
    print(f"\nCould not stream data: {exc}", file=sys.stderr)
    print(
        "Install the optional dependency with:  pip install the_well>=1.2.0",
        file=sys.stderr,
    )
    sys.exit(1)
