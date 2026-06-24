"""Pipeline orchestrator for BSEE field analysis.

Coordinates production analysis, activity analysis, and casing schematics
into a consolidated :class:`FieldReport`.  Each stage is wrapped in
try/except so that partial failures produce warnings, not crashes.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.bsee.pipeline.field_query import FieldContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FieldReport:
    """Consolidated analysis results for a BSEE field.

    Not frozen -- allows incremental population by the pipeline runner.
    """

    context: FieldContext
    generated_at: str  # ISO-8601 timestamp

    # Production summary (from AllFieldsRunner)
    production_summary: pd.DataFrame

    # Activity analysis (from ComprehensiveActivityAnalyzer)
    activity_analysis: dict

    # Casing data
    casing_strings: dict[str, list]  # api12 -> list of CasingString
    casing_matrices: dict[str, pd.DataFrame]  # api12 -> matrix DataFrame
    casing_svgs: dict[str, str]  # api12 -> SVG string

    # Wellbore summary
    wellbore_count: int
    lease_count: int

    # Errors/warnings during execution
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


class PipelineRunner:
    """Orchestrates all BSEE field analysis stages.

    Accepts optional analyzer overrides via constructor injection so that
    tests can provide lightweight stubs without importing real analyzers.
    """

    def __init__(
        self,
        field_resolver: Any,
        era_classifier: Any,
        data_dir: Path,
        tubulars_path: Path | None = None,
        all_fields_runner: Any | None = None,
        activity_analyzer_cls: type | None = None,
    ) -> None:
        self._field_resolver = field_resolver
        self._era_classifier = era_classifier
        self._data_dir = Path(data_dir)
        self._tubulars_path = tubulars_path
        self._all_fields_runner = all_fields_runner
        self._activity_analyzer_cls = activity_analyzer_cls

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        context: FieldContext,
        export_formats: list[str] | None = None,
        export_dir: str | None = None,
    ) -> FieldReport:
        """Execute the full analysis pipeline for a resolved field.

        Parameters
        ----------
        context:
            Resolved field context (from :func:`resolve_field`).
        export_formats:
            Optional list of formats to export after the pipeline completes.
            Supported values: ``"xlsx"``, ``"parquet"``, ``"csv"``,
            ``"json"``, ``"pdf"``.  When *None* (default) no export is run.

            Integration pattern::

                from worldenergydata.reporting import export_report

                class _FieldReportAdapter:
                    def __init__(self, report: FieldReport) -> None:
                        self.data = report.production_summary
                        self.summary = report.activity_analysis

                adapter = _FieldReportAdapter(field_report)
                manifest = export_report(
                    adapter,
                    formats=export_formats,
                    output_dir=export_dir,
                    filename_prefix=context.field_name.lower().replace(" ", "_"),
                )
        export_dir:
            Directory for exported files.  Passed through to
            :func:`~worldenergydata.reporting.export_report`.
        """
        warnings: list[str] = []

        # 1. Load production data and filter to resolved field
        raw_production_df = self._load_production_data(warnings)
        production_df = self._filter_to_field(raw_production_df, context, warnings)

        # 2. Run AllFieldsRunner for production summary
        production_summary = self._run_production_analysis(production_df, warnings)

        # 3. Compute wellbore count from field-scoped production data
        wellbore_count = self._compute_wellbore_count(production_df, context)

        # 4. Load activity data and run intervention analysis
        activity_analysis = self._run_activity_analysis(warnings)

        # 5. Load casing data for wells
        casing_strings, casing_matrices, casing_svgs = self._run_casing_analysis(
            context, production_df, warnings
        )

        # 6. Build consolidated FieldReport
        report = FieldReport(
            context=context,
            generated_at=datetime.now(timezone.utc).isoformat(),
            production_summary=production_summary,
            activity_analysis=activity_analysis,
            casing_strings=casing_strings,
            casing_matrices=casing_matrices,
            casing_svgs=casing_svgs,
            wellbore_count=wellbore_count,
            lease_count=len(context.leases),
            warnings=warnings,
        )

        # 7. Optional multi-format export stage
        if export_formats:
            self._export_report(report, export_formats, export_dir, context)

        return report

    def _export_report(
        self,
        report: FieldReport,
        export_formats: list[str],
        export_dir: str | None,
        context: FieldContext,
    ) -> None:
        """Run the multi-format export stage as the pipeline's final step."""
        try:
            from worldenergydata.reporting import export_report

            class _Adapter:
                """Adapt FieldReport to the export_report interface."""

                def __init__(self, r: FieldReport) -> None:
                    self.data = r.production_summary
                    self.summary = r.activity_analysis

            prefix = context.field_name.lower().replace(" ", "_")
            manifest = export_report(
                _Adapter(report),
                formats=export_formats,
                output_dir=export_dir,
                filename_prefix=prefix,
            )
            logger.info(
                "Export complete — %d formats succeeded, dir=%s",
                len(manifest.formats_succeeded),
                manifest.output_dir,
            )
            if manifest.formats_failed:
                logger.warning("Export failures: %s", manifest.formats_failed)
        except Exception as exc:
            logger.warning("Export stage failed: %s", exc)

    # ------------------------------------------------------------------
    # Stage 1: Production data loading
    # ------------------------------------------------------------------

    def _load_production_data(self, warnings: list[str]) -> pd.DataFrame:
        """Load production summary data from binary files."""
        candidates = [
            self._data_dir / "production_raw" / "mv_productionsum.bin",
            self._data_dir / "production" / "mv_productionsum.bin",
        ]

        for path in candidates:
            df = _load_pickle_safe(path)
            if not df.empty:
                logger.info("Loaded production data from %s (%d rows)", path, len(df))
                return df

        warnings.append("No production data found — production summary will be empty")
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Stage 2: AllFieldsRunner
    # ------------------------------------------------------------------

    def _run_production_analysis(
        self,
        production_df: pd.DataFrame,
        warnings: list[str],
    ) -> pd.DataFrame:
        """Run AllFieldsRunner on the production data."""
        if production_df.empty:
            return pd.DataFrame()

        runner = self._get_all_fields_runner()
        if runner is None:
            warnings.append("AllFieldsRunner unavailable — production summary skipped")
            return pd.DataFrame()

        try:
            return runner.run(production_df)
        except Exception as exc:
            warnings.append(f"AllFieldsRunner failed: {exc} — production summary empty")
            logger.warning("AllFieldsRunner error: %s", exc)
            return pd.DataFrame()

    def _get_all_fields_runner(self) -> Any | None:
        """Return the AllFieldsRunner instance (injected or lazy-imported)."""
        if self._all_fields_runner is not None:
            return self._all_fields_runner

        try:
            from worldenergydata.bsee.analysis.all_fields_runner import (
                AllFieldsRunner,
            )

            return AllFieldsRunner(self._field_resolver, self._era_classifier)
        except Exception as exc:
            logger.warning("Cannot import AllFieldsRunner: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Stage 3: Activity analysis
    # ------------------------------------------------------------------

    def _run_activity_analysis(self, warnings: list[str]) -> dict:
        """Load activity data and run intervention analysis."""
        activity_df = self._load_activity_data(warnings)
        if activity_df.empty:
            return {}

        cls = self._get_activity_analyzer_cls()
        if cls is None:
            warnings.append("Activity analyzer unavailable — activity analysis skipped")
            return {}

        try:
            analyzer = cls(activity_df)
            return analyzer.analyze()
        except Exception as exc:
            warnings.append(f"Activity analysis failed: {exc}")
            logger.warning("Activity analyzer error: %s", exc)
            return {}

    def _load_activity_data(self, warnings: list[str]) -> pd.DataFrame:
        """Load WAR activity data for intervention analysis."""
        candidates = [
            self._data_dir / "eWellAPD" / "mv_ewellapd.bin",
            self._data_dir / "WAR" / "mv_war.bin",
            self._data_dir / "war" / "mv_war.bin",
        ]

        for path in candidates:
            df = _load_pickle_safe(path)
            if not df.empty:
                logger.info("Loaded activity data from %s (%d rows)", path, len(df))
                return df

        warnings.append("No activity data found — activity analysis will be empty")
        return pd.DataFrame()

    def _get_activity_analyzer_cls(self) -> type | None:
        """Return the activity analyzer class (injected or lazy-imported)."""
        if self._activity_analyzer_cls is not None:
            return self._activity_analyzer_cls

        try:
            from worldenergydata.bsee.analysis.intervention.comprehensive_analyzer import (
                ComprehensiveActivityAnalyzer,
            )

            return ComprehensiveActivityAnalyzer
        except Exception as exc:
            logger.warning("Cannot import ComprehensiveActivityAnalyzer: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Stage 4: Casing analysis
    # ------------------------------------------------------------------

    def _run_casing_analysis(
        self,
        context: FieldContext,
        production_df: pd.DataFrame,
        warnings: list[str],
    ) -> tuple[dict[str, list], dict[str, pd.DataFrame], dict[str, str]]:
        """Load casing data for each well and build schematics."""
        strings_map: dict[str, list] = {}
        matrices_map: dict[str, pd.DataFrame] = {}
        svgs_map: dict[str, str] = {}

        if self._tubulars_path is None:
            warnings.append("No tubulars path configured — casing analysis skipped")
            return strings_map, matrices_map, svgs_map

        # Gather unique API12s from production data
        api12s = self._collect_api12s(context, production_df)

        if not api12s:
            warnings.append("No well APIs found — casing analysis skipped")
            return strings_map, matrices_map, svgs_map

        try:
            from worldenergydata.bsee.pipeline.casing_schematic import (
                casing_matrix,
                load_well_casing,
                render_casing_svg,
            )
        except Exception as exc:
            warnings.append(f"Cannot import casing modules: {exc}")
            return strings_map, matrices_map, svgs_map

        for api12 in api12s:
            try:
                strings = load_well_casing(api12, self._tubulars_path)
                strings_map[api12] = strings
                if strings:
                    matrices_map[api12] = casing_matrix(strings)
                    svgs_map[api12] = render_casing_svg(strings, well_name=api12)
            except Exception as exc:
                warnings.append(f"Casing analysis failed for {api12}: {exc}")
                logger.warning("Casing error for %s: %s", api12, exc)

        return strings_map, matrices_map, svgs_map

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_to_field(
        df: pd.DataFrame,
        context: FieldContext,
        warnings: list[str],
    ) -> pd.DataFrame:
        """Filter production DataFrame to rows belonging to the resolved field.

        Tries field code column first, then lease number.  Returns the
        unfiltered DataFrame if no matching column is found (with a warning).
        """
        if df.empty:
            return df

        # Try field code columns
        field_col_candidates = [
            "FIELD_NAME_CODE",
            "BOTM_FLD_NAME_CD",
            "FIELD_CODE",
        ]
        for col in field_col_candidates:
            if col in df.columns:
                filtered = df[df[col].astype(str) == context.field_code]
                if not filtered.empty:
                    return filtered

        # Fallback: filter by leases
        if context.leases and "LEASE_NUMBER" in df.columns:
            filtered = df[df["LEASE_NUMBER"].isin(context.leases)]
            if not filtered.empty:
                return filtered

        warnings.append(
            "Could not filter production data to field — using full dataset"
        )
        return df

    @staticmethod
    def _collect_api12s(
        context: FieldContext,
        production_df: pd.DataFrame,
    ) -> list[str]:
        """Gather unique well API12 numbers from field-scoped production data."""
        if not production_df.empty and "API_WELL_NUMBER" in production_df.columns:
            return production_df["API_WELL_NUMBER"].astype(str).unique().tolist()
        return []

    @staticmethod
    def _compute_wellbore_count(
        production_df: pd.DataFrame,
        context: FieldContext,
    ) -> int:
        """Count unique wellbores from field-scoped production data or context."""
        if not production_df.empty and "API_WELL_NUMBER" in production_df.columns:
            return int(production_df["API_WELL_NUMBER"].nunique())
        return context.well_count


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _load_pickle_safe(file_path: Path) -> pd.DataFrame:
    """Load a pickle file, returning empty DataFrame for LFS stubs or errors."""
    if not file_path.exists():
        logger.debug("File not found: %s", file_path)
        return pd.DataFrame()

    try:
        with open(file_path, "rb") as f:
            header = f.read(40)
        if b"version https://git-lfs" in header:
            logger.warning("LFS stub detected (not materialized): %s", file_path)
            return pd.DataFrame()

        with open(file_path, "rb") as f:
            obj = pickle.load(f)  # nosec B301

        if isinstance(obj, pd.DataFrame):
            return obj

        logger.warning("File does not contain a DataFrame: %s", file_path)
        return pd.DataFrame()

    except Exception as exc:
        logger.error("Error loading %s: %s", file_path, exc)
        return pd.DataFrame()
