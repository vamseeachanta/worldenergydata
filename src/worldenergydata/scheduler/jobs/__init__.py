"""Job adapter implementations for the data collection scheduler."""

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult, write_refresh_metadata
from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob
from worldenergydata.scheduler.jobs.sodir_refresh import SodirRefreshJob
from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
from worldenergydata.scheduler.jobs.ukcs_refresh import UkcsRefreshJob
from worldenergydata.scheduler.jobs.metocean_refresh import MetoceanRefreshJob
from worldenergydata.scheduler.jobs.lng_terminals_refresh import LngTerminalsRefreshJob

__all__ = [
    "AbstractJob",
    "JobResult",
    "write_refresh_metadata",
    "BseeRefreshJob",
    "SodirRefreshJob",
    "EiaUsRefreshJob",
    "BrazilAnpRefreshJob",
    "UkcsRefreshJob",
    "MetoceanRefreshJob",
    "LngTerminalsRefreshJob",
]
