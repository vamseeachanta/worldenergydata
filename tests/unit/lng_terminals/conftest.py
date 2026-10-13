"""Keep collector tests' cache writes in their temporary directories."""

import pytest

from worldenergydata.lng_terminals import config as lng_config


@pytest.fixture(scope="module", autouse=True)
def temporary_collector_cache(tmp_path_factory):
    """Redirect default collector caches for every module in this directory."""
    config = lng_config.get_config().model_copy(deep=True)
    config.cache.cache_dir = str(tmp_path_factory.mktemp("collector-cache"))
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(lng_config, "_config", config)
        yield
