# Reanalysis bias correction

This module implements additive delta change, empirical quantile mapping (EQM),
quantile delta mapping (QDM), and Hs-conditioned QDM for paired buoy/reanalysis
series. Related work: [#679](https://github.com/vamseeachanta/worldenergydata/issues/679),
[#1090](https://github.com/vamseeachanta/worldenergydata/issues/1090), and
[#1097](https://github.com/vamseeachanta/worldenergydata/issues/1097).

## Methods and API

```python
from worldenergydata.metocean.calibration import fit, time_block_split

# frame: sorted time, model/observed Tm02 (s), model/observed Hs (m).
cal, val = time_block_split(frame.time, ("2007", "2018"), ("2018", "2022"))
a, b = frame[cal], frame[val]
correction = fit(
    a.model_tm02, a.observed_tm02, "conditional_qdm",
    model_hs=a.model_hs, obs_hs=a.observed_hs, times=a.time,
)
corrected_tm02 = correction.apply(b.model_tm02, hs=b.model_hs)
provenance = correction.provenance
```

Use `delta_change`, `eqm`, or `qdm` for a single variable. Calibration requires
at least two finite pairs. Arrays pair positionally; Series indexes must agree.
Missing pairs are removed together; nonfinite application values become NaN.
No positivity clipping is applied. The returned array preserves input order.
Provide `times`, or a model Series with a DatetimeIndex, to record the effective
calibration window; otherwise the window is explicitly unknown (`None`).

Let M/O be calibration model/observation quantiles and A application model
quantiles. Delta change adds mean(observed) minus mean(model). EQM interpolates
O against M. Additive QDM returns `x + O(p) - M(p)`, with `p = F_A(x)` by default
(Cannon, Sobie and Murdock, 2015; additive adaptation). Apply the entire intended
validation/projection block together: its empirical CDF is batch dependent.
When A equals M, QDM equals EQM. A shifted-distribution test checks that QDM
preserves a known additive quantile change rather than behaving like EQM.

Set `qdm_reference="calibration"` in `fit` to use `p = F_M(x)`, matching the
stationary QDM formulation in the Oikonomou et al. (2026) Zenodo scripts.
In that mode EQM and QDM are algebraically equivalent, including this module's
tail treatment. The published benchmark explicitly uses this mode.

Defaults are 200 linearly spaced levels over P1–P99.9. Outside the supported
range, extend the nearest boundary **offset**, not the mapped value or slope.
Tied reference quantiles collapse to their mean correction; a deterministic
map cannot expand a point mass into a distribution. Ties are flagged in provenance.
Strict monotone stationary maps preserve ranks; ties or distribution-changing
QDM need separate dependence checks.

Conditional QDM fits paired Tm02 samples grouped by concurrent **model** Hs,
and applies each fitted map using concurrent uncorrected model Hs. Default
internal edges are observed calibration Hs P25/P50/P75/P95; `bin_edges` overrides
them. Bins are left-closed, with unbounded outer tails. Each bin requires two
finite pairs; sparse bins fail explicitly. Provenance records the method,
quantiles, effective window, pair counts, edges, and reference CDF.

`metrics(observed, model)` reports bias (model minus observation), RMSD, Pearson
r, population CV, P50 and P95; the last three describe model values.
`joint_diagnostics(obs_hs, obs_tm02, model_hs, model_tm02)` reports Spearman
correlations and L1 between probability masses in shared 0.25 m by 0.5 s cells.
Defaults cover all finite samples. Explicit edges normalize each histogram
inside that range and return retained counts so truncation is visible.
`time_block_split` requires ordered, disjoint, half-open time windows and sorted
timestamps, allowing equal timestamps across sites. It refuses random splits.

Corrected outputs are not qualified for extreme-value fitting: provenance sets
`extreme_value_fitting_allowed=False`. Design extremes require separate analysis.
The extrapolation facade still uses a synthetic baseline and spatial transfer;
its labels now describe spatial transfer rather than claiming buoy calibration.

## Published-data benchmark

Zenodo record 19239166 v1.0.0 declares CC BY 4.0 in both API metadata and README
(checked 2026-10-18). Its 9,283,272-byte archive and 9,714,406-byte MAT member
are below 100 MB. The manifest pins SHA-256 digests, settings and targets;
no dataset or upstream scripts are committed. The fetcher rechecks the licence,
limits downloads and refuses altered bytes or a destination inside this repo.

From the repository root, with the metocean package and pytest installed:

```bash
uv run python scripts/metocean/fetch_bias_correction_benchmark.py /tmp/metocean-bias-data
METOCEAN_BIAS_BENCHMARK_DIR=/tmp/metocean-bias-data uv run python -m pytest \
  --noconftest -o addopts='' tests/unit/metocean/calibration -q
```

Without the environment variable, only the 10 published-target tests skip.
An explicitly configured missing or corrupted dataset fails. Calibration is
2007–2017 and validation 2018–2021, with exact 3-hour stamps selected as in the
release, pooled across seven buoys (76,783 validation pairs). Older records are
excluded. MATLAB timestamp conversion retains the release's floating-point
stamp selection; no timestamp rounding or averaging is introduced.

| Validation metric | Published | Reproduced | Absolute tolerance |
| --- | ---: | ---: | ---: |
| Raw Tm02 RMSD (s) | 0.589 | 0.589008 | 0.01 |
| EQM/QDM Tm02 RMSD (s) | 0.460 | 0.459692 | 0.01 |
| Raw Hs P95 (m) | 2.506 | 2.506000 | 0.01 |
| EQM/QDM Hs P95 (m) | 2.639 | 2.638843 | 0.01 |
| Raw joint L1 | 0.568 | 0.568323 | 0.01 |
| EQM/QDM joint L1 | 0.272 | 0.272810 | 0.01 |
| Conditional QDM joint L1 | 0.217 | 0.207108 | 0.01 |

Joint benchmark cells cover Hs 0–3.5 m and Tm02 2–8 s. CQDM uses unrounded
observed calibration quantiles: 0.52, 0.82, 1.36, 2.676667 m. Its residual is
0.009892, close to the tolerance boundary; this is tolerance-level agreement,
not exact replication of published conditional binning. The released scripts
contain no CQDM implementation. The archive also uses P99 and EQM slope
extrapolation; this module uses the stated P99.9 and boundary-offset policy.
These differences are recorded rather than silently adopted or tuned away.

## References

- Oikonomou C.L.G., Rizaev I.G., Korres G., Denaxa D., Sheng W., Aggidis G.
  (2026). Bias correction of Copernicus Marine reanalysis for western Mediterranean
  wave energy applications. *Applied Ocean Research* 176, 105259.
  [doi:10.1016/j.apor.2026.105259](https://doi.org/10.1016/j.apor.2026.105259).
  [Code/data, Zenodo v1.0.0, CC BY 4.0](https://doi.org/10.5281/zenodo.19239166).
- Cannon A.J., Sobie S.R., Murdock T.Q. (2015). Bias correction of GCM precipitation
  by quantile mapping: How well do methods preserve changes in quantiles and
  extremes? *Journal of Climate* 28, 6938–6959.
  [doi:10.1175/JCLI-D-14-00754.1](https://doi.org/10.1175/JCLI-D-14-00754.1).
