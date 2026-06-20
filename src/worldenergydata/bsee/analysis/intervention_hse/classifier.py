"""Classifier bridge for the intervention-HSE Phase-2 package.

Wraps the repo-canonical
``worldenergydata.safety_analysis.taxonomy.incident_classifier.IncidentClassifier``
so the intervention-HSE analysis can classify BSEE INCINV records without rewriting
the classification logic.

Import-light by design: the heavy root package ``__init__`` (pydantic/pandas) is
NOT required for classification. This module first attempts a normal import; if that
fails (because the heavy ``__init__`` blocks collection — the #407/#451 pattern),
it falls back to loading the three taxonomy files by file path with a tiny logging
stub, exactly mirroring the inline loader that the #416 / #426 exploration scripts
used. Behavior is preserved; this is a relocation, not a rewrite.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path
from typing import Any

# Layout: .../src/worldenergydata/bsee/analysis/intervention_hse/classifier.py
# parents[0]=intervention_hse [1]=analysis [2]=bsee [3]=worldenergydata [4]=src
_PKG_ROOT = Path(__file__).resolve().parents[3]  # src/worldenergydata
_TAXO = _PKG_ROOT / "safety_analysis" / "taxonomy"


def _load_classifier_by_path():
    """Load IncidentClassifier directly from the taxonomy files.

    Stubs ``worldenergydata.common.logging`` and defines the package shells so the
    relative imports inside the taxonomy files resolve, bypassing the heavy root
    ``__init__``. This is the same mechanism the #416 / #426 scripts used inline.
    """
    if "worldenergydata.common.logging" not in sys.modules:
        pkg = types.ModuleType("worldenergydata")
        pkg.__path__ = [str(_PKG_ROOT)]
        common = types.ModuleType("worldenergydata.common")
        common.__path__ = [str(_PKG_ROOT / "common")]
        logging_mod = types.ModuleType("worldenergydata.common.logging")

        def get_logger(name: Any = None):
            return logging.getLogger(name or "intervention_hse")

        logging_mod.get_logger = get_logger
        sys.modules.setdefault("worldenergydata", pkg)
        sys.modules.setdefault("worldenergydata.common", common)
        sys.modules["worldenergydata.common.logging"] = logging_mod

    base = "worldenergydata.safety_analysis.taxonomy"

    # A failed normal import (heavy __init__ pulling pydantic) can leave
    # half-initialized taxonomy modules in sys.modules. Purge those so the
    # by-path load below executes cleanly against the real files.
    for modname in (
        f"{base}.incident_classifier",
        f"{base}.activity_registry",
        f"{base}.activity_definitions",
        "worldenergydata.safety_analysis.taxonomy",
        "worldenergydata.safety_analysis",
    ):
        mod = sys.modules.get(modname)
        # Replace any module that didn't come from our shell stub / by-path load.
        if mod is not None and getattr(mod, "__spec__", None) is not None:
            sys.modules.pop(modname, None)

    for shell, path in (
        ("worldenergydata.safety_analysis", _TAXO.parent),
        ("worldenergydata.safety_analysis.taxonomy", _TAXO),
    ):
        if shell not in sys.modules:
            m = types.ModuleType(shell)
            m.__path__ = [str(path)]
            sys.modules[shell] = m

    def _load(modname: str, path: Path):
        # Only reuse a module we ourselves fully loaded from this exact file.
        existing = sys.modules.get(modname)
        if existing is not None and getattr(existing, "__file__", None) == str(path):
            return existing
        sys.modules.pop(modname, None)
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        return mod

    _load(f"{base}.activity_definitions", _TAXO / "activity_definitions.py")
    _load(f"{base}.activity_registry", _TAXO / "activity_registry.py")
    clf_mod = _load(f"{base}.incident_classifier", _TAXO / "incident_classifier.py")
    return clf_mod.IncidentClassifier


def get_incident_classifier():
    """Return an instantiated repo-canonical ``IncidentClassifier``.

    Tries the normal import path first; falls back to the by-path loader if the
    heavy root ``__init__`` blocks it. The returned object exposes
    ``classify(record, source="bsee")`` -> ClassificationResult with
    ``.activity``, ``.subactivity``, ``.confidence``, ``.match_method``.
    """
    try:  # pragma: no cover - depends on whether heavy __init__ is importable
        from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
            IncidentClassifier,
        )
    except Exception:
        IncidentClassifier = _load_classifier_by_path()
    return IncidentClassifier()
