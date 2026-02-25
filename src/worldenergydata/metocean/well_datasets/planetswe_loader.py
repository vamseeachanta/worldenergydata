# ABOUTME: PlanetsweLoader — streams planetswe (Shallow Water Equations) dataset from The Well.
# ABOUTME: Optional integration; gracefully degrades when the_well package is not installed.

"""
PlanetsweLoader: HuggingFace-streaming loader for The Well's planetswe dataset.

The Well dataset — CC BY 4.0, Polymathic AI
https://github.com/PolymathicAI/the_well

planetswe: 2D shallow water equations on a rotating sphere (planetary-scale waves).
Suitable for validating metocean wave propagation models without downloading full dataset.

Usage::

    from worldenergydata.metocean.well_datasets import PlanetsweLoader

    loader = PlanetsweLoader()
    for sample in loader.stream_sample(n_steps=10):
        print(sample["data"].shape)
"""

from __future__ import annotations

from itertools import islice
from typing import Any, Dict, Generator

# Optional dependency guard — the_well is not required for core worldenergydata operation.
try:
    from the_well.data import WellDataset  # type: ignore[import]

    WELL_AVAILABLE: bool = True
except ImportError:
    WELL_AVAILABLE = False
    WellDataset = None  # type: ignore[assignment,misc]

#: Attribution string required by CC BY 4.0 license for The Well dataset.
THE_WELL_ATTRIBUTION: str = (
    "The Well dataset — CC BY 4.0, Polymathic AI"
    " (https://github.com/PolymathicAI/the_well)"
)

_INSTALL_HINT: str = (
    "The 'the_well' package is required to stream planetswe data. "
    "Install it with:  pip install the_well>=1.2.0"
)


class PlanetsweLoader:
    """Stream shallow-water-equation snapshots from The Well's planetswe dataset.

    Attributes
    ----------
    dataset_name : str
        Always ``"planetswe"``.
    split : str
        Which dataset split to stream (``"train"``, ``"valid"``, or ``"test"``).
    attribution : str
        CC BY 4.0 attribution string for The Well dataset.

    Notes
    -----
    The Well dataset — CC BY 4.0, Polymathic AI
    Uses Hugging Face streaming so no 15 TB download is required.
    """

    #: Fixed dataset identifier within The Well.
    dataset_name: str = "planetswe"

    def __init__(self, split: str = "train") -> None:
        """Construct a PlanetsweLoader.

        Parameters
        ----------
        split:
            Dataset split to stream. One of ``"train"``, ``"valid"``, ``"test"``.
            Defaults to ``"train"``.
        """
        self.split = split
        self.attribution: str = THE_WELL_ATTRIBUTION

    def __repr__(self) -> str:
        return (
            f"PlanetsweLoader(dataset_name={self.dataset_name!r}, split={self.split!r})"
        )

    def stream_sample(
        self, n_steps: int = 10
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield up to *n_steps* snapshots from the planetswe dataset via HF streaming.

        Parameters
        ----------
        n_steps:
            Maximum number of time-step samples to yield. Defaults to 10.

        Yields
        ------
        dict
            Each yielded item is a dict with at minimum a ``"data"`` key containing
            the wave-field tensor for that time step.

        Raises
        ------
        ImportError
            If ``the_well`` package is not installed. Raised immediately on call,
            not deferred to iteration, so the error is visible without consuming
            the generator.

        Notes
        -----
        The Well dataset — CC BY 4.0, Polymathic AI
        Streaming is used so no full-dataset download occurs.
        """
        # Guard is placed in a private helper to ensure ImportError is raised
        # eagerly (before any iteration), not lazily inside the generator frame.
        if not WELL_AVAILABLE:
            raise ImportError(_INSTALL_HINT)
        return self._generate(n_steps)

    def _generate(
        self, n_steps: int
    ) -> Generator[Dict[str, Any], None, None]:
        """Internal generator — only called after WELL_AVAILABLE is confirmed."""
        dataset = WellDataset(self.dataset_name, split=self.split)
        yield from islice(dataset, n_steps)
