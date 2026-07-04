"""Adapter package for unified production query interface."""

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.adapters.brazil_anp_adapter import (
    BrazilAnpAdapter,
)
from worldenergydata.production.unified.adapters.bsee_adapter import BseeAdapter
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter
from worldenergydata.production.unified.adapters.eia_us_adapter import EiaUsAdapter
from worldenergydata.production.unified.adapters.mexico_cnh_adapter import (
    MexicoCnhAdapter,
)
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.production.unified.adapters.texas_rrc_adapter import (
    TexasRrcAdapter,
)
from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter

__all__ = [
    "AbstractProductionAdapter",
    "SodirAdapter",
    "BseeAdapter",
    "BrazilAnpAdapter",
    "UkcsAdapter",
    "SpainCoresAdapter",
    "EiaUsAdapter",
    "MexicoCnhAdapter",
    "TexasRrcAdapter",
    "CanadaAdapter",
]
