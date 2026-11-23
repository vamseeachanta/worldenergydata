# ABOUTME: NLP classification model performance report with confusion matrix and metrics.
"""
Classification Model Performance Report

Generates interactive HTML reports for evaluating NLP classification
models, including confusion matrices, per-class precision/recall/F1
charts, and multi-model comparison views.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import plotly.graph_objects as go

from worldenergydata.common import get_logger
from worldenergydata.safety_analysis.reports.base_report import BaseReport

logger = get_logger(__name__)


class ClassificationReport(BaseReport):
    """Generates classification model evaluation reports."""

    def __init__(
        self,
        title: str = "Safety Classification Model Report",
    ) -> None:
        super().__init__(
            title=title,
            subtitle="NLP Classification Performance Evaluation",
        )

    @classmethod
    def from_evaluation(
        cls,
        eval_results: Dict[str, Any],
        models: Optional[List[Dict[str, Any]]] = None,
    ) -> "ClassificationReport":
        """Build a classification report from evaluation results.

        Args:
            eval_results: Dictionary containing at minimum:
                - ``accuracy`` (float)
                - ``confusion_matrix`` (2-D list of ints)
                - ``class_labels`` (list of str)
                - ``classification_report`` (dict with per-class metrics)
            models: Optional list of model summary dicts for comparison,
                each with ``name``, ``accuracy``, ``f1_weighted``.

        Returns:
            Populated ClassificationReport ready for HTML generation.
        """
        report = cls()

        accuracy = eval_results.get("accuracy", 0.0)
        report.add_summary_stat("Accuracy", f"{accuracy:.1%}")

        class_report = eval_results.get("classification_report", {})
        weighted = class_report.get("weighted avg", {})
        if weighted:
            report.add_summary_stat(
                "Weighted F1",
                f"{weighted.get('f1-score', 0.0):.3f}",
            )
            report.add_summary_stat(
                "Weighted Precision",
                f"{weighted.get('precision', 0.0):.3f}",
            )
            report.add_summary_stat(
                "Weighted Recall",
                f"{weighted.get('recall', 0.0):.3f}",
            )

        cm = eval_results.get("confusion_matrix")
        labels = eval_results.get("class_labels", [])
        if cm is not None:
            report.add_section(
                title="Confusion Matrix",
                figure=cls._confusion_matrix_chart(cm, labels),
                description="Predicted vs actual class labels.",
            )

        if class_report:
            report.add_section(
                title="Per-Class Metrics",
                figure=cls._class_metrics_chart(class_report, labels),
                description="Precision, recall, and F1 score per class.",
            )

        if models and len(models) > 1:
            report.add_section(
                title="Model Comparison",
                figure=cls._model_comparison_chart(models),
                description="Side-by-side comparison of model performance.",
            )

        return report

    # ------------------------------------------------------------------
    # Chart builders
    # ------------------------------------------------------------------

    @staticmethod
    def _confusion_matrix_chart(
        cm: List[List[int]],
        labels: List[str],
    ) -> go.Figure:
        """Plotly annotated heatmap for the confusion matrix."""
        z = np.array(cm)
        text = [[str(val) for val in row] for row in z]

        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=labels or None,
                y=labels or None,
                colorscale="Blues",
                text=text,
                texttemplate="%{text}",
                hovertemplate=(
                    "Predicted: %{x}<br>"
                    "Actual: %{y}<br>"
                    "Count: %{z}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Predicted",
            yaxis_title="Actual",
            height=500,
        )
        return fig

    @staticmethod
    def _class_metrics_chart(
        class_report: Dict[str, Any],
        labels: List[str],
    ) -> go.Figure:
        """Plotly grouped bar chart of precision, recall, F1 per class."""
        class_names = []
        precisions = []
        recalls = []
        f1s = []

        target_labels = labels if labels else sorted(class_report.keys())
        for label in target_labels:
            metrics = class_report.get(label)
            if not isinstance(metrics, dict):
                continue
            class_names.append(label)
            precisions.append(metrics.get("precision", 0.0))
            recalls.append(metrics.get("recall", 0.0))
            f1s.append(metrics.get("f1-score", 0.0))

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Precision",
                    x=class_names,
                    y=precisions,
                    marker_color="#667eea",
                ),
                go.Bar(name="Recall", x=class_names, y=recalls, marker_color="#764ba2"),
                go.Bar(name="F1 Score", x=class_names, y=f1s, marker_color="#48bb78"),
            ]
        )
        fig.update_layout(
            barmode="group",
            template="plotly_white",
            xaxis_title="Class",
            yaxis_title="Score",
            height=450,
        )
        return fig

    @staticmethod
    def _model_comparison_chart(
        models: List[Dict[str, Any]],
    ) -> go.Figure:
        """Bar chart comparing multiple model metrics."""
        names = [m.get("name", f"Model {i}") for i, m in enumerate(models)]
        accuracies = [m.get("accuracy", 0.0) for m in models]
        f1_scores = [m.get("f1_weighted", 0.0) for m in models]

        fig = go.Figure(
            data=[
                go.Bar(name="Accuracy", x=names, y=accuracies, marker_color="#667eea"),
                go.Bar(
                    name="F1 (weighted)", x=names, y=f1_scores, marker_color="#ed8936"
                ),
            ]
        )
        fig.update_layout(
            barmode="group",
            template="plotly_white",
            xaxis_title="Model",
            yaxis_title="Score",
            height=400,
        )
        return fig
