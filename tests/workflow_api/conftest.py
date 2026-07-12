# ABOUTME: Shared session fixtures for the wed#927 BSEE HF pilot tests.
# ABOUTME: Runs the full dry-run pipeline ONCE (InMemoryHfPort) and caches it.
from __future__ import annotations

import logging

import pytest

# The wed engine is very chatty via loguru; silence it for the test session.
logging.disable(logging.CRITICAL)


@pytest.fixture(scope="session")
def pilot_config():
    from worldenergydata.workflow_api import bsee_pilot as P

    return P.load_config()


@pytest.fixture(scope="session")
def pilot_summary(pilot_config):
    """The full dry-run pipeline result (InMemoryHfPort, no HF network)."""
    from worldenergydata.workflow_api import bsee_pilot as P

    return P.run_pilot(config=pilot_config, write_report=False)
