"""Configured production/EUR uncertainty with monthly, time-zero-capex NPV."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from worldenergydata.production.forecast.decline import ArpsDeclineCurve
from worldenergydata.production.forecast.uq import (
    PriorSpec,
    percentiles,
    rank_sensitivity,
    sample_priors,
    shared_engine,
)

PARAMETERS = {
    "qi",
    "Di",
    "b",
    "economic_limit",
    "oil_price",
    "opex",
    "capex",
    "discount_rate",
}


@dataclass
class ProbabilisticResult:
    """Auditable samples, month-end rate bands and scalar result summary."""

    run_matrix: pd.DataFrame
    fan: pd.DataFrame
    summary: dict
    config_echo: dict
    sampler_used: str


class ProbabilisticForecast:
    """Evaluate independent input priors; no fitted or hardcoded field priors."""

    def run(self, config: dict) -> ProbabilisticResult:
        cfg = json.loads(json.dumps(config, allow_nan=False))
        base = cfg["base"]
        if set(base) != PARAMETERS:
            raise ValueError(f"base must define exactly {sorted(PARAMETERS)}")
        if (
            not isinstance(cfg.get("field"), str)
            or not cfg["field"].strip()
            or cfg.get("data_basis") not in {"synthetic", "public", "assumed"}
        ):
            raise ValueError(
                "field and data_basis (synthetic/public/assumed) are required"
            )
        priors = [PriorSpec(**p) for p in cfg["priors"]]
        if any(p.config["name"] not in PARAMETERS for p in priors):
            raise ValueError("unknown forecast prior name")
        samples, sampler = sample_priors(
            priors, cfg["n_samples"], cfg["seed"], cfg.get("engine", "auto")
        )
        backend = shared_engine(
            "digitalmodel" if sampler == "digitalmodel.lhs" else "builtin"
        )
        rows, profiles = [], []
        for index, sample in enumerate(samples.to_dict("records")):
            params = {**base, **sample}
            try:
                row, profile = self._evaluate(
                    params, cfg["forecast_months"], cfg.get("price_multipliers")
                )
            except (ValueError, ArithmeticError) as exc:
                raise ValueError(f"sample {index}: {exc}") from exc
            rows.append({**params, **row})
            profiles.append(profile)
        matrix = pd.DataFrame(rows)
        if not np.isfinite(matrix.to_numpy()).all():
            raise ValueError("non-finite forecast outputs")
        fan = pd.DataFrame(
            [
                {"month": month, **percentiles(values, backend)}
                for month, values in enumerate(np.asarray(profiles).T, start=1)
            ]
        )
        summary = self._summary(cfg, matrix, priors, sampler, backend)
        return ProbabilisticResult(matrix, fan, summary, cfg, sampler)

    @staticmethod
    def _evaluate(params, months, price_multipliers):
        from worldenergydata.fdas.api import EconomicsQuery

        if not all(
            isinstance(v, (float, int)) and not isinstance(v, bool) and np.isfinite(v)
            for v in params.values()
        ):
            raise ValueError("all model inputs must be finite numbers")
        if any(params[k] < 0 for k in ("oil_price", "opex", "capex")):
            raise ValueError("price and costs must be nonnegative")
        # FDAS calculate_npv supports annual rates in [-1,1]; -1 is singular.
        if not -1 < params["discount_rate"] <= 1:
            raise ValueError("discount_rate must lie in (-1, 1]")
        result = ArpsDeclineCurve().simulate(
            **{key: params[key] for key in ("qi", "Di", "b", "economic_limit")},
            months=months,
        )
        multipliers = (
            np.ones(months)
            if price_multipliers is None
            else np.asarray(price_multipliers, dtype=float)
        )
        if (
            multipliers.shape != (months,)
            or not np.isfinite(multipliers).all()
            or (multipliers < 0).any()
        ):
            raise ValueError(
                "price_multipliers needs one finite nonnegative value per month"
            )
        # numpy-financial npv (2026 documentation): sum CF[t]/(1+r)**t.
        # FDAS period='monthly' converts annual discount using 12 months/year.
        # CAPEX occurs at t=0; exact integrated barrel volumes earn cash at
        # each month end. OPEX is USD/bbl; price multipliers form the deck.
        net = (
            params["oil_price"] * multipliers - params["opex"]
        ) * result.forecast_df.volume_bbl
        cashflows = np.r_[-params["capex"], net.to_numpy()]
        npv = EconomicsQuery.npv(cashflows, params["discount_rate"], period="monthly")
        return {
            "eur_bbl": result.eur_bbl,
            "npv_usd": npv,
        }, result.forecast_df.rate_bbl.to_numpy()

    @staticmethod
    def _summary(cfg, matrix, priors, sampler, backend):
        summary = {
            "field": cfg["field"],
            "data_basis": cfg["data_basis"],
            "n_samples": cfg["n_samples"],
            "seed": cfg["seed"],
            "sampler": sampler,
            "forecast_months": cfg["forecast_months"],
            "percentile_convention": "non-exceedance; p10=10th, p50=50th, p90=90th",
            "eur_basis": "future recovery to rate limit, not booked reserves",
            "npv_basis": "forecast horizon only; no terminal value, tax or royalties",
            "eur_bbl": percentiles(matrix.eur_bbl, backend),
            "npv_usd": percentiles(matrix.npv_usd, backend),
            "spearman": rank_sensitivity(
                matrix, [p.config["name"] for p in priors], backend
            ),
            "screening_status": "NOT_EVALUATED",
            "screening_rule": "No minimum NPV criterion was supplied",
            "input_sha256": hashlib.sha256(
                json.dumps(cfg, sort_keys=True).encode()
            ).hexdigest(),
        }
        if "minimum_p10_npv_usd" in cfg:
            threshold = cfg["minimum_p10_npv_usd"]
            if (
                not isinstance(threshold, (int, float))
                or isinstance(threshold, bool)
                or not np.isfinite(threshold)
            ):
                raise ValueError("minimum_p10_npv_usd must be finite")
            summary["screening_status"] = (
                "pass" if summary["npv_usd"]["p10"] >= threshold else "fail"
            )
            summary["screening_rule"] = f"non-exceedance NPV p10 >= {threshold} USD"
        return summary
