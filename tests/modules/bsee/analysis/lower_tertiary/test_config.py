"""Tests for LTConfig — YAML config loader for Lower Tertiary analysis.

Run with:
    PYTHONPATH=src /usr/bin/python3 -m pytest \
        tests/modules/bsee/analysis/lower_tertiary/ -v \
        --override-ini="addopts=-v --tb=short" \
        -W "default::pytest.PytestRemovedIn9Warning"
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Resolve project root from test file location."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent


@pytest.fixture
def config(project_root: Path):
    """Load LTConfig from the canonical YAML file."""
    from worldenergydata.bsee.analysis.lower_tertiary.config import LTConfig

    yaml_path = project_root / "config" / "input" / "world_oil_lower_tertiary.yaml"
    return LTConfig(yaml_path)


# ── Basic loading ────────────────────────────────────────────────────


def test_load_config_from_yaml(config) -> None:
    """Config loads successfully and exposes expected top-level sections."""
    assert config.metadata is not None
    assert config.all_fields is not None
    assert config.article_metrics is not None
    assert config.architecture is not None
    assert config.data_paths is not None
    assert config.output_config is not None


# ── Field counts ─────────────────────────────────────────────────────


def test_subsea_fields_count(config) -> None:
    """YAML defines 9 subsea fields."""
    assert len(config.subsea_fields) == 9


def test_dry_tree_fields_count(config) -> None:
    """YAML defines 4 dry-tree fields."""
    assert len(config.dry_tree_fields) == 4


def test_all_fields_merge(config) -> None:
    """all_fields merges subsea + dry_tree into 13 entries."""
    assert len(config.all_fields) == 13


# ── field_blocks() ───────────────────────────────────────────────────


def test_field_blocks_known(config) -> None:
    """Tiber is in KC block 102."""
    area, blocks = config.field_blocks("Tiber")
    assert area == "KC"
    assert blocks == [102]


def test_field_blocks_jack(config) -> None:
    """Jack spans four WR blocks."""
    area, blocks = config.field_blocks("Jack")
    assert area == "WR"
    assert blocks == [718, 719, 758, 759]


def test_field_blocks_unknown_raises(config) -> None:
    """Non-existent field raises KeyError."""
    with pytest.raises(KeyError, match="Unknown field"):
        config.field_blocks("NonExistent")


# ── Article metrics ──────────────────────────────────────────────────


def test_article_metrics_accessible(config) -> None:
    """Aggregate total investment is $50B per the article."""
    assert config.article_metrics["aggregate"]["total_investment_billion"] == 50


# ── Architecture ─────────────────────────────────────────────────────


def test_architecture_systems(config) -> None:
    """Five architecture systems defined."""
    assert len(config.architecture["systems"]) == 5


def test_architecture_ratings_dimensions(config) -> None:
    """Each system has exactly 6 rating dimensions."""
    ratings = config.architecture["ratings"]
    for system, scores in ratings.items():
        assert len(scores) == 6, f"{system} has {len(scores)} ratings, expected 6"


# ── Legacy CSV paths ─────────────────────────────────────────────────


def test_legacy_csv_paths(config) -> None:
    """Julia legacy config resolves 4 CSV Path entries."""
    base = Path("/base")
    paths = config.legacy_csv_paths("julia", base)
    assert len(paths) == 4
    for key, value in paths.items():
        assert isinstance(value, Path)
        assert str(value).startswith("/base/")


def test_legacy_csv_paths_unknown(config) -> None:
    """Unknown legacy field raises KeyError."""
    with pytest.raises(KeyError, match="No legacy data for field"):
        config.legacy_csv_paths("unknown_field", Path("/base"))


# ── Output config ────────────────────────────────────────────────────


def test_output_config(config) -> None:
    """Output config has reports with part1, part2, executive."""
    reports = config.output_config["reports"]
    assert "part1" in reports
    assert "part2" in reports
    assert "executive" in reports


# ── Data paths ───────────────────────────────────────────────────────


def test_data_paths(config) -> None:
    """Data config includes war_zip path."""
    assert "war_zip" in config.data_paths
