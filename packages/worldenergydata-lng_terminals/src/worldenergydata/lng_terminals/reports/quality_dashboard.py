"""Data quality dashboard for LNG terminal dataset."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..config import REPORTS_DIR
from ..models.terminal import LNGTerminal
from ..processors.quality_scorer import QualityScorer

logger = logging.getLogger(__name__)


class QualityDashboard:
    """Generate data quality/completeness reports."""

    def __init__(self, terminals: list[LNGTerminal]) -> None:
        self.terminals = terminals

    def generate_report(self) -> dict[str, Any]:
        """Generate a quality report dict."""
        # Ensure all terminals are scored
        scorer = QualityScorer()
        scorer.score_terminals(self.terminals)

        scores = [
            t.data_quality_score
            for t in self.terminals
            if t.data_quality_score is not None
        ]

        if not scores:
            return {"error": "No scored terminals"}

        total_scores = [s.total_score for s in scores]
        required_scores = [s.required_fields_score for s in scores]
        optional_scores = [s.optional_fields_score for s in scores]
        engineering_scores = [s.engineering_score for s in scores]

        return {
            "total_terminals": len(self.terminals),
            "scored_terminals": len(scores),
            "overall": {
                "average": round(sum(total_scores) / len(total_scores), 2),
                "min": round(min(total_scores), 2),
                "max": round(max(total_scores), 2),
                "median": round(sorted(total_scores)[len(total_scores) // 2], 2),
            },
            "required_fields": {
                "average": round(sum(required_scores) / len(required_scores), 2),
                "all_complete": sum(1 for s in required_scores if s == 100.0),
            },
            "optional_fields": {
                "average": round(sum(optional_scores) / len(optional_scores), 2),
            },
            "engineering_fields": {
                "average": round(sum(engineering_scores) / len(engineering_scores), 2),
            },
            "source_coverage": {
                "average_sources": round(
                    sum(s.source_count for s in scores) / len(scores), 2
                ),
                "multi_source": sum(1 for s in scores if s.source_count > 1),
            },
            "distribution": self._score_distribution(total_scores),
        }

    def _score_distribution(self, scores: list[float]) -> dict[str, int]:
        """Categorize scores into buckets."""
        buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        for s in scores:
            if s < 20:
                buckets["0-20"] += 1
            elif s < 40:
                buckets["20-40"] += 1
            elif s < 60:
                buckets["40-60"] += 1
            elif s < 80:
                buckets["60-80"] += 1
            else:
                buckets["80-100"] += 1
        return buckets

    def export_json(self, output_path: Path | None = None) -> Path:
        """Export quality report as JSON."""
        if output_path is None:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = REPORTS_DIR / "quality_report.json"

        report = self.generate_report()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Quality report exported: {output_path}")
        return output_path
