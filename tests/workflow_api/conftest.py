# ABOUTME: Shared session fixtures for the wed#927 BSEE HF pilot tests.
# ABOUTME: Runs the full dry-run pipeline ONCE (InMemoryHfPort) and caches it.
from __future__ import annotations

import logging
from contextlib import contextmanager

import pytest


# The wed engine is very chatty via loguru; silence it while THESE tests run.
# A module-level logging.disable(CRITICAL) is process-global and leaks into every
# other test an xdist worker runs after importing this conftest — it blanked the
# captured output in tests/unit/common/test_logging.py on gw1 (#983 follow-up).
@contextmanager
def quiet_logging():
    """Suppress log records inside the block, restoring the prior disable level."""
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous)


@pytest.fixture(autouse=True)
def _quiet_engine_logging():
    with quiet_logging():
        yield


@pytest.fixture(scope="session")
def quiet_logging_cm():
    """Expose the suppressor to session fixtures defined in test modules."""
    return quiet_logging


@pytest.fixture(scope="session")
def pilot_config():
    from worldenergydata.workflow_api import bsee_pilot as P

    return P.load_config()


@pytest.fixture(scope="session")
def pilot_summary(pilot_config):
    """The full dry-run pipeline result (InMemoryHfPort, no HF network)."""
    from worldenergydata.workflow_api import bsee_pilot as P

    with quiet_logging():                      # chatty engine; session fixtures
        return P.run_pilot(config=pilot_config, write_report=False)
