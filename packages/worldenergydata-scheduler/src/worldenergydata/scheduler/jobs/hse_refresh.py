"""HSE (offshore safety) data refresh job.

Automates what ``scripts/refresh_bsee_hse.sh`` did by hand: downloads the BSEE
incident-investigation and INC raw archives (via :class:`BSEEAcquirer`) into
``<output_dir>/raw/bsee`` and writes refresh metadata. This is the mechanism the
source-refresh contract (#489) points its ``hse_refresh`` scheduler job at — it
keeps the incident corpus that the grounded-analysis stream (#486) reads fresh,
instead of relying on a manual run.

Scope: acquire + verify the raw corpus and emit a freshness signal. DB import
(``scripts/import_bsee_hse_to_db.py``) remains a separate concern.

The acquirer is created via :meth:`_acquirer` so tests inject a fake (no network).
"""

import logging
from datetime import datetime
from pathlib import Path

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("hse")


class HseRefreshJob(AbstractJob):
    """Refresh BSEE offshore HSE incident raw data."""

    name = "hse_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def _acquirer(self):
        """Build the BSEE HSE acquirer (overridden in tests to avoid network)."""
        from worldenergydata.hse.acquirers.bsee_acquirer import BSEEAcquirer

        return BSEEAcquirer()

    @staticmethod
    def _count_rows(verification: dict) -> int:
        return sum(
            int(f.get("rows", 0))
            for result in verification.values()
            for f in result.get("files", [])
        )

    def run(self, config: dict) -> JobResult:
        start = datetime.now()
        if "output_dir" not in config:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="HSE live refresh requires an explicit output_dir",
            )

        output_dir = Path(config["output_dir"])
        raw_dir = output_dir / "raw" / "bsee"
        raw_dir.mkdir(parents=True, exist_ok=True)
        acquirer = self._acquirer()

        try:
            acquirer.download_all(str(raw_dir), force=True)
        except Exception as exc:  # network / IO — retry-worthy
            error_msg = f"HSE download failed: {exc}"
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
                retryable=True,
            )

        total = self._count_rows(acquirer.verify_data(str(raw_dir)))
        if total <= 0:
            error_msg = "HSE refresh produced 0 rows (download incomplete)"
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
                retryable=True,
            )

        write_refresh_metadata("hse", output_dir, total)
        logger.info("HSE refresh wrote %d incident rows to %s", total, raw_dir)
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="success",
            records_updated=total,
            error_msg=None,
        )
