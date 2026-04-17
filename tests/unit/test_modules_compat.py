"""Tests for worldenergydata.modules backward-compatibility shim."""

import warnings

import pytest


class TestModulesCompat:
    def test_dir_returns_moved_modules(self):
        from worldenergydata import modules

        names = dir(modules)
        assert isinstance(names, list)
        assert names == sorted(names)

    def test_getattr_known_module(self):
        from worldenergydata._compat import _MOVED_MODULES

        if not _MOVED_MODULES:
            pytest.skip("No moved modules configured")

        from worldenergydata import modules

        first_name = sorted(_MOVED_MODULES)[0]

        # First access should emit DeprecationWarning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mod = getattr(modules, first_name)
            assert mod is not None

    def test_getattr_unknown_raises(self):
        from worldenergydata import modules

        with pytest.raises(AttributeError, match="no attribute"):
            getattr(modules, "nonexistent_module_xyz_12345")
