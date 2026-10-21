"""Cache-preservation contract from issue 1265; all records are synthetic.

Expected results are determined independently: an empty refresh contributes no
new records, so the prior cache bytes, metadata bytes and file modification times
must remain equal. No engineering conversions or empirical limits are used.
"""

import logging

import pytest

from worldenergydata.lng_terminals import config as config_module
from worldenergydata.lng_terminals.collectors.ferc_collector import FERCCollector
from worldenergydata.lng_terminals.constants import RefreshMode

FETCH_MODES = [RefreshMode.FULL, RefreshMode.INCREMENTAL, RefreshMode.CACHE_FIRST]
CSV = "Project Name,Status,Capacity (Bcf/d),Operator,Type,Date Operational\n"
ROW = "Synthetic Terminal,Operating,,Synthetic Operator,Import,\n"


@pytest.fixture
def collector(monkeypatch, tmp_path):
    """Use the real parser and temporary cache, without network requests."""
    config = config_module.get_config().model_copy(deep=True)
    config.cache.cache_dir = str(tmp_path)
    monkeypatch.setattr(config_module, "_config", config)
    with FERCCollector() as instance:
        monkeypatch.setattr(instance, "fetch_data", lambda: CSV + ROW)
        yield instance


def snapshot(collector):
    """Read both cache files and their timestamps independently of cache loading."""
    return [
        (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (collector._cache_path, collector._cache_meta_path)
    ]


@pytest.mark.parametrize("mode", FETCH_MODES)
@pytest.mark.parametrize("invalid_records", [False, True])
def test_empty_refresh_preserves_existing_cache(
    collector, monkeypatch, caplog, mode, invalid_records
):
    """Empty parsing or all-invalid validation must leave both files unchanged."""
    collector.collect(RefreshMode.FULL)
    # Force expiration via configuration, without introducing an age constant.
    # A negative TTL expires even the just-written cache in CACHE_FIRST mode.
    collector.config.sources["ferc"].cache_ttl = -1
    before = snapshot(collector)
    collected_at = collector.last_collected_at
    if invalid_records:
        monkeypatch.setattr(collector, "validate", lambda records: [])
    else:
        monkeypatch.setattr(collector, "fetch_data", lambda: CSV)

    with caplog.at_level(logging.WARNING):
        result = collector.collect(mode)

    assert result == []
    assert snapshot(collector) == before
    assert collector.last_collected_at == collected_at
    assert "No valid records" in caplog.text
    assert "ferc" in caplog.text


@pytest.mark.parametrize("mode", FETCH_MODES)
def test_empty_first_refresh_does_not_create_success_cache(
    collector, monkeypatch, caplog, mode
):
    """No prior success plus no new records must yield no successful cache files."""
    monkeypatch.setattr(collector, "fetch_data", lambda: CSV)
    with caplog.at_level(logging.WARNING):
        assert collector.collect(mode) == []
    assert not collector._cache_path.exists()
    assert not collector._cache_meta_path.exists()
    assert collector.last_collected_at is None
    assert "No valid records" in caplog.text


def test_empty_direct_write_preserves_cache(collector):
    """The persistence boundary must also reject an empty direct write."""
    collector.collect(RefreshMode.FULL)
    before = snapshot(collector)
    collector._write_cache([])
    assert snapshot(collector) == before


def test_nonempty_refresh_replaces_cache(collector, monkeypatch):
    """An independently named replacement must round-trip through FORCE_CACHE."""
    collector.collect(RefreshMode.FULL)
    replacement = ROW.replace("Synthetic Terminal", "Replacement Terminal")
    monkeypatch.setattr(collector, "fetch_data", lambda: CSV + replacement)
    fresh = collector.collect(RefreshMode.FULL)
    cached = collector.collect(RefreshMode.FORCE_CACHE)
    assert [terminal.terminal_name for terminal in fresh] == ["Replacement Terminal"]
    assert [terminal.terminal_name for terminal in cached] == ["Replacement Terminal"]
