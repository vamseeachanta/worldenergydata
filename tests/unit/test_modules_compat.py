"""Tests for worldenergydata.modules backward-compatibility shim."""

import importlib
import json
import re
import subprocess
import sys
import textwrap

import pytest


class TestModulesCompat:
    def test_dir_returns_moved_modules(self):
        from worldenergydata import modules
        from worldenergydata._compat import _MOVED_MODULES

        names = dir(modules)
        assert set(names) == _MOVED_MODULES

    def test_getattr_known_module(self, monkeypatch):
        from worldenergydata._compat import _MOVED_MODULES

        if not _MOVED_MODULES:
            pytest.skip("No moved modules configured")

        from worldenergydata import modules

        first_name = min(_MOVED_MODULES)
        canonical_name = f"worldenergydata.{first_name}"
        canonical = importlib.import_module(canonical_name)
        # Exercise first attribute access even if another test imported the alias.
        monkeypatch.delitem(modules.__dict__, first_name, raising=False)
        monkeypatch.setattr(modules, "_attr_warned", set())

        with pytest.warns(DeprecationWarning, match=re.escape(canonical_name)):
            mod = getattr(modules, first_name)
        assert mod is canonical

    def test_getattr_unknown_raises(self):
        from worldenergydata import modules

        with pytest.raises(AttributeError, match="no attribute"):
            _ = modules.nonexistent_module_xyz_12345


@pytest.mark.parametrize(
    "suffix", ["", ".analysis", ".analysis.incidents", ".importers", ".processors"]
)
@pytest.mark.parametrize("import_order", ["legacy_first", "canonical_first"])
def test_marine_safety_redirect_identity_and_warning(suffix, import_order, tmp_path):
    """Check real package aliases against independently spelled canonical paths.

    Basis: marine-safety compatibility pack (2026), sections 2 and 5, C5,
    at src/worldenergydata/modules/marine_safety/docs/agent-pack.md.
    Its suffix inventory defines the cases; the expected result is object
    identity plus a DeprecationWarning naming both paths, not a numeric value.
    Each subprocess starts with an empty import/warning cache so prior tests
    cannot satisfy identity or suppress the warning. Both import orders must
    work, and a cached repeat must retain identity without warning again.
    """
    script = textwrap.dedent(
        r"""
        import json
        import sys

        paths, suffix, import_order = sys.argv[1:]
        sys.path[:] = json.loads(paths)

        import importlib
        import re
        import warnings

        import pytest

        legacy_name = "worldenergydata.modules.marine_safety" + suffix
        canonical_name = "worldenergydata.marine_safety" + suffix
        canonical = None
        if import_order == "canonical_first":
            canonical = importlib.import_module(canonical_name)

        message = (
            rf"^{re.escape(legacy_name)} is deprecated\. "
            rf"Use {re.escape(canonical_name)} instead\.$"
        )
        with pytest.warns(DeprecationWarning, match=message):
            legacy = importlib.import_module(legacy_name)
        if canonical is None:
            canonical = importlib.import_module(canonical_name)
        assert legacy is canonical
        assert sys.modules[legacy_name] is canonical
        assert importlib.import_module(canonical_name) is canonical

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            assert importlib.import_module(legacy_name) is canonical
        assert not caught
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script, json.dumps(sys.path), suffix, import_order],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        pytest.fail(result.stdout + result.stderr)
