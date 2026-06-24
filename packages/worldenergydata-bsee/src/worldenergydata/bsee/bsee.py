from worldenergydata.bsee.analysis.bsee_analysis import BSEEAnalysis
from worldenergydata.bsee.data.bsee_data import BSEEData

bsee_data = BSEEData()
bsee_analysis = BSEEAnalysis()


class bsee:

    def __init__(self):
        self._bsee_data = bsee_data
        self._bsee_analysis = bsee_analysis

    def router(self, cfg):
        basename = cfg["basename"]

        cfg[basename] = {}
        cfg[basename].update({"data": cfg.get("data", {}).copy()})
        cfg[basename].update({"analysis": cfg.get("analysis", {}).copy()})

        # The well-benchmark analytic self-loads its BSEE data (OGOR-A / WAR /
        # drilling) through the Lower-Tertiary orchestrator, so it bypasses the
        # generic per-group data router (which expects explicit well groups).
        analysis = cfg.get("analysis", {})
        if analysis.get("flag", False) and analysis.get("type") == "well_benchmark":
            return self._run_well_benchmark(cfg)

        cfg, data = bsee_data.router(cfg)
        cfg = bsee_analysis.router(cfg, data)

        return cfg

    def _run_well_benchmark(self, cfg):
        """Engine route for the saved LT well-benchmark analytic (#499)."""
        from worldenergydata.lower_tertiary.well_benchmark import (
            BenchmarkConfig,
            run_well_benchmark,
        )

        bench_cfg = BenchmarkConfig.from_mapping(cfg.get("benchmark", {}))
        df = run_well_benchmark(bench_cfg)
        cfg[cfg["basename"]]["well_benchmark"] = df
        return cfg
