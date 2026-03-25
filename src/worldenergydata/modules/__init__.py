# ABOUTME: Backward-compatibility shim for worldenergydata.modules namespace.
# ABOUTME: Attribute access redirects to worldenergydata.<name> with deprecation warning.

"""Backward-compatibility shim for the old ``worldenergydata.modules`` namespace.

All modules have been moved to ``worldenergydata.<name>``.
Accessing ``worldenergydata.modules.<name>`` still works but emits a
DeprecationWarning.  The MetaPathFinder in ``_compat.py`` handles
``import worldenergydata.modules.X``; this ``__getattr__`` handles
``from worldenergydata.modules import X``.
"""

import importlib
import warnings

from worldenergydata._compat import _MOVED_MODULES

_attr_warned: set[str] = set()


def __getattr__(name: str):
    if name in _MOVED_MODULES:
        new_path = f"worldenergydata.{name}"
        if name not in _attr_warned:
            _attr_warned.add(name)
            warnings.warn(
                f"worldenergydata.modules.{name} is deprecated. "
                f"Use {new_path} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return importlib.import_module(new_path)
    raise AttributeError(f"module 'worldenergydata.modules' has no attribute {name!r}")


def __dir__():
    return sorted(_MOVED_MODULES)
