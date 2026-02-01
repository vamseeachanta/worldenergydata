"""Tests for LNG terminal quality scorer."""

from datetime import datetime

from worldenergydata.modules.lng_terminals.collectors.seed_collector import (
    SeedCollector,
)
from worldenergydata.modules.lng_terminals.constants import (
    Region,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.modules.lng_terminals.models.data_quality import QualityScore
from worldenergydata.modules.lng_terminals.models.terminal import LNGTerminal
from worldenergydata.modules.lng_terminals.processors.quality_scorer import (
    QualityScorer,
)


def _make_terminal(**kwargs) -> LNGTerminal:
    defaults = {
        "terminal_name": "Test Terminal",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "last_updated": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return LNGTerminal(**defaults)


class TestQualityScorer:
    """Test quality scoring logic."""

    def test_minimal_terminal_has_low_score(self):
        """Terminal with only required fields should score low."""
        scorer = QualityScorer()
        terminal = _make_terminal()
        score = scorer.score_terminal(terminal)
        assert isinstance(score, QualityScore)
        # Required fields are all present, but optional and engineering are empty
        assert score.required_fields_score == 100.0
        assert score.engineering_score < 10.0
        assert score.total_score < 60.0

    def test_rich_terminal_has_higher_score(self):
        """Terminal with more fields should score higher."""
        scorer = QualityScorer()
        terminal = _make_terminal(
            capacity_mtpa=30.0,
            operator="Cheniere",
            year_commissioned=2016,
            region=Region.NORTH_AMERICA,
            latitude=29.76,
            longitude=-93.85,
        )
        score = scorer.score_terminal(terminal)
        assert score.total_score > 50.0
        assert score.required_fields_score == 100.0

    def test_score_terminals_updates_all(self):
        """score_terminals() should set data_quality_score on every terminal."""
        scorer = QualityScorer()
        terminals = [_make_terminal(), _make_terminal(terminal_name="Other")]
        scored = scorer.score_terminals(terminals)
        assert len(scored) == 2
        for t in scored:
            assert t.data_quality_score is not None
            assert t.data_quality_score.total_score >= 0

    def test_seed_data_quality(self):
        """Seed data should have avg quality > 40 per spec."""
        collector = SeedCollector()
        terminals = collector.collect()
        scorer = QualityScorer()
        scored = scorer.score_terminals(terminals)

        scores = [
            t.data_quality_score.total_score for t in scored if t.data_quality_score
        ]
        avg_score = sum(scores) / len(scores)
        assert avg_score > 40, f"Average quality score {avg_score:.1f} is below 40"

    def test_required_fields_all_present(self):
        """Required fields should score 100% when all present."""
        scorer = QualityScorer()
        terminal = _make_terminal()
        score = scorer.score_terminal(terminal)
        assert score.required_fields_score == 100.0

    def test_field_scores_dict(self):
        """field_scores should contain boolean presence values."""
        scorer = QualityScorer()
        terminal = _make_terminal(capacity_mtpa=10.0)
        score = scorer.score_terminal(terminal)
        assert "name" in score.field_scores
        assert score.field_scores["name"] is True
        assert "capacity_mtpa" in score.field_scores
        assert score.field_scores["capacity_mtpa"] is True
