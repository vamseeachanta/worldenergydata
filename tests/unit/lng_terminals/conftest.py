"""Keep collector tests' cache writes in their temporary directories."""

import pytest

from worldenergydata.lng_terminals import config as lng_config


@pytest.fixture(scope="module", autouse=True)
def temporary_collector_cache(request, tmp_path_factory):
    """Redirect only the collector and CLI modules that use default caches."""
    if request.node.path.name not in {
        "test_analysis.py",
        "test_cli.py",
        "test_ferc_collector.py",
        "test_quality_dashboard.py",
        "test_quality_scorer.py",
        "test_seed_collector.py",
        "test_web_collector.py",
    }:
        yield
        return
    config = lng_config.get_config().model_copy(deep=True)
    config.cache.cache_dir = str(tmp_path_factory.mktemp("collector-cache"))
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(lng_config, "_config", config)
        yield
