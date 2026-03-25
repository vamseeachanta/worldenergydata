# ABOUTME: Backward compatibility layer for worldenergydata import migrations.
# ABOUTME: Redirects worldenergydata.modules.X -> worldenergydata.X with DeprecationWarning.

"""Backward compatibility layer for worldenergydata import migrations.

Handles redirect: worldenergydata.modules.X -> worldenergydata.X

After the module flatten (WRK-096), all modules previously at
``worldenergydata.modules.<name>`` now live at ``worldenergydata.<name>``.
This finder ensures old import paths continue to work while emitting a
DeprecationWarning so callers can migrate at their own pace.

Usage:
    from worldenergydata._compat import install_redirect
    install_redirect()  # called once in worldenergydata/__init__.py
"""

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import warnings

# All modules that were moved from worldenergydata.modules.X to worldenergydata.X
_MOVED_MODULES: set[str] = {
    "bsee",
    "canada",
    "fdas",
    "hse",
    "landman",
    "lng_terminals",
    "marine_safety",
    "metocean",
    "mexico_cnh",
    "pipeline_safety",
    "reporting",
    "safety_analysis",
    "sodir",
    "texas_rrc",
    "vessel_hull_models",
    "well_production_dashboard",
    "lower_tertiary",
}

_warned: set[str] = set()
_finding: set[str] = set()  # Re-entrancy guard


class _RedirectLoader(importlib.abc.Loader):
    """Loader that redirects an old module path to its new location."""

    def __init__(self, new_name: str, old_name: str):
        self.new_name = new_name
        self.old_name = old_name

    def create_module(self, spec):
        return None  # Use default semantics

    def exec_module(self, module):
        if self.old_name not in _warned:
            _warned.add(self.old_name)
            warnings.warn(
                f"{self.old_name} is deprecated. "
                f"Use {self.new_name} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        real_mod = importlib.import_module(self.new_name)
        module.__dict__.update(real_mod.__dict__)
        module.__path__ = getattr(real_mod, "__path__", [])
        module.__loader__ = self
        # Ensure both old and new names resolve to the same module object
        sys.modules[self.old_name] = real_mod


class _ModulesRedirectFinder(importlib.abc.MetaPathFinder):
    """Redirect worldenergydata.modules.X imports to worldenergydata.X.

    Intercepts any import of ``worldenergydata.modules.<name>`` (or deeper
    sub-imports like ``worldenergydata.modules.<name>.sub.mod``) and
    rewrites it to ``worldenergydata.<name>`` (or
    ``worldenergydata.<name>.sub.mod``).
    """

    _PREFIX = "worldenergydata.modules."

    def find_spec(self, fullname, path, target=None):
        # Re-entrancy guard
        if fullname in _finding:
            return None

        if not fullname.startswith(self._PREFIX):
            return None

        # Extract the part after "worldenergydata.modules."
        suffix = fullname[len(self._PREFIX):]
        parts = suffix.split(".")
        top_module = parts[0]

        if top_module not in _MOVED_MODULES:
            return None

        # Build new import path: worldenergydata.<suffix>
        new_fullname = f"worldenergydata.{suffix}"

        # Check that the new path actually exists
        _finding.add(fullname)
        try:
            spec = importlib.util.find_spec(new_fullname)
        except (ModuleNotFoundError, ValueError):
            spec = None
        finally:
            _finding.discard(fullname)

        if spec is None:
            return None

        loader = _RedirectLoader(new_fullname, fullname)
        return importlib.machinery.ModuleSpec(
            fullname,
            loader,
            is_package=spec.submodule_search_locations is not None,
        )


def install_redirect() -> None:
    """Install the _ModulesRedirectFinder on sys.meta_path.

    Safe to call multiple times; only installs once.
    """
    if not any(isinstance(f, _ModulesRedirectFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _ModulesRedirectFinder())


def is_moved(name: str) -> bool:
    """Check if a module name has been registered as moved."""
    return name in _MOVED_MODULES


def get_moved_modules() -> frozenset[str]:
    """Return the set of all moved module names."""
    return frozenset(_MOVED_MODULES)
