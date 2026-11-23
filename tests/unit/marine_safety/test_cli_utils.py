"""Tests for marine safety CLI utility functions."""

import pytest

from worldenergydata.marine_safety.cli_utils import (
    create_progress_spinner,
    get_source_enum,
)
from worldenergydata.marine_safety.constants import DataSource


class TestGetSourceEnum:
    def test_uscg(self):
        assert get_source_enum("uscg") == DataSource.USCG

    def test_ntsb(self):
        assert get_source_enum("ntsb") == DataSource.NTSB

    def test_bsee(self):
        assert get_source_enum("bsee") == DataSource.BSEE

    def test_atsb(self):
        assert get_source_enum("atsb") == DataSource.ATSB

    def test_maib(self):
        assert get_source_enum("maib") == DataSource.MAIB

    def test_tsb(self):
        assert get_source_enum("tsb") == DataSource.TSB

    def test_imo(self):
        assert get_source_enum("imo") == DataSource.IMO

    def test_case_insensitive(self):
        assert get_source_enum("USCG") == DataSource.USCG
        assert get_source_enum("Ntsb") == DataSource.NTSB

    def test_unknown_returns_none(self):
        assert get_source_enum("unknown") is None

    def test_uscg_misle(self):
        assert get_source_enum("uscg_misle") == DataSource.USCG_MISLE

    def test_uscg_bard(self):
        assert get_source_enum("uscg_bard") == DataSource.USCG_BARD


class TestCreateProgressSpinner:
    def test_returns_progress(self):
        spinner = create_progress_spinner("Loading data...")
        assert spinner is not None
