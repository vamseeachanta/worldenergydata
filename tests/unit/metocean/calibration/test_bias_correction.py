"""Known-answer and failure tests for reanalysis calibration."""

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose
from scipy.stats import spearmanr

from worldenergydata.metocean.calibration import (
    fit,
    joint_diagnostics,
    metrics,
    time_block_split,
)


def test_delta_known_offset_and_variance():
    m = np.linspace(0.5, 8, 400)
    correction = fit(m, m + 0.7, "delta_change")
    out = correction.apply(m)
    assert_allclose(out, m + 0.7, atol=1e-12)
    assert_allclose(np.var(out), np.var(m), atol=1e-12)
    assert_allclose(np.mean(out) - np.mean(m), 0.7, atol=1e-12)


def test_eqm_all_200_quantile_knots_and_nonlinear_known_map():
    m = np.linspace(1, 4, 1001)
    o = m**2
    correction = fit(m, o, "eqm")
    q = np.linspace(0.01, 0.999, 200)
    assert_allclose(correction.apply(np.quantile(m, q)), np.quantile(o, q), atol=1e-9)


def test_qdm_stationary_identity_and_eqm_equivalence():
    m = np.linspace(1, 5, 1000)
    o = m**1.5
    assert_allclose(fit(m, m, "qdm").apply(m), m, atol=1e-12)
    assert_allclose(fit(m, o, "qdm").apply(m), fit(m, o, "eqm").apply(m), atol=1e-9)


@pytest.mark.parametrize("method", ["eqm", "qdm"])
def test_constant_boundary_delta_does_not_clip_or_extrapolate_slope(method):
    correction = fit(
        [1, 2, 3], [2, 4, 6], method, q_range=(0, 1), qdm_reference="calibration"
    )
    assert_allclose(correction.apply([-10, 0, 2, 4, 100]), [-9, 1, 4, 7, 103])


@pytest.mark.parametrize("method", ["delta_change", "eqm", "qdm"])
def test_univariate_mapping_preserves_joint_ranks(method):
    rng = np.random.default_rng(42)
    h = rng.uniform(0.1, 5, 2000)
    t = 2 + np.sqrt(h) + rng.uniform(0, 2, len(h))
    hc = fit(h, 1.2 * h + 0.1, method).apply(h)
    tc = fit(t, t**1.2, method).apply(t)
    assert_allclose(spearmanr(hc, tc).statistic, spearmanr(h, t).statistic, atol=1e-12)


def test_conditional_known_offsets_on_held_out_year():
    # Same deterministic sea-state population in disjoint years. Period offsets
    # depend on Hs; a single marginal map cannot reconstruct this joint structure.
    rng = np.random.default_rng(51)
    h = rng.uniform(0.05, 3.5, 6000)
    observed = rng.uniform(3, 7, len(h))
    edges = [0.51, 0.82, 1.37, 2.67]
    offsets = np.array([0.30, 0.25, 0.15, 0.08, 0.02])
    model = observed - offsets[np.searchsorted(edges, h, side="right")]
    times = pd.date_range("2016-01-01", periods=len(h), freq="h").append(
        pd.date_range("2018-01-01", periods=len(h), freq="h")
    )
    cal, val = time_block_split(times, ("2016", "2017"), ("2018", "2019"))
    hh, oo, mm = np.tile(h, 2), np.tile(observed, 2), np.tile(model, 2)
    conditional = fit(
        mm[cal],
        oo[cal],
        "conditional_qdm",
        model_hs=hh[cal],
        obs_hs=hh[cal],
        bin_edges=edges,
        times=times[cal],
    )
    corrected = conditional.apply(mm[val], hs=hh[val])
    marginal = fit(mm[cal], oo[cal], "qdm").apply(mm[val])
    assert_allclose(corrected, oo[val], atol=1e-12)

    def l1(t):
        return joint_diagnostics(hh[val], oo[val], hh[val], t)["l1"]

    assert l1(corrected) < l1(marginal) < l1(mm[val])
    assert conditional.provenance["n_pairs"] == len(h)
    assert conditional.provenance["calibration_window"][0].startswith("2016")
    assert conditional.provenance["extreme_value_fitting_allowed"] is False


def test_conditional_edges_missing_values_and_sparse_bin_rejection():
    h = np.arange(1.0, 101)
    correction = fit(h, h + 1, "conditional_qdm", model_hs=h, obs_hs=h)
    assert_allclose(
        correction.provenance["bin_edges"], np.quantile(h, [0.25, 0.5, 0.75, 0.95])
    )
    assert_allclose(
        correction.apply([10, 30, 50, 80, 99], hs=[10, 30, 50, 80, 99]),
        [11, 31, 51, 81, 100],
    )
    assert np.isnan(correction.apply([10, np.nan], hs=[np.nan, 10])).all()
    with pytest.raises(ValueError, match="bin"):
        fit(h, h, "conditional_qdm", model_hs=h, obs_hs=h, bin_edges=[500])
    with pytest.raises(ValueError, match="hs"):
        correction.apply([1, 2])


def test_pairwise_missing_and_nonmutating_input():
    m = np.array([1, np.nan, 3, np.inf, 5.0])
    o = np.array([2, 100, 4, 200, np.nan])
    correction = fit(m, o, "delta_change")
    assert correction.provenance["n_pairs"] == 2
    assert_allclose(correction.apply([2, 4]), [3, 5])
    assert np.isnan(correction.apply([np.nan, np.inf])).all()
    assert np.isinf(m[3])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"method": "unknown"},
        {"method": "eqm", "n_quantiles": 1},
        {"method": "eqm", "q_range": (0.9, 0.1)},
        {"method": "eqm", "q_range": (-0.1, 1)},
    ],
)
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        fit([1, 2, 3], [2, 3, 4], **kwargs)


def test_invalid_pairs_and_misaligned_series():
    for m, o in [
        ([1], [2]),
        ([1, 2], [3]),
        ([[1, 2]], [[2, 3]]),
        ([np.nan, 2], [3, np.nan]),
    ]:
        with pytest.raises(ValueError):
            fit(m, o, "qdm")
    with pytest.raises(ValueError, match="index"):
        fit(pd.Series([1, 2], index=[1, 2]), pd.Series([2, 3], index=[2, 3]), "eqm")


def test_tied_quantiles_are_deterministic():
    correction = fit(
        np.ones(100), np.linspace(2, 4, 100), "qdm", qdm_reference="calibration"
    )
    # A point mass cannot be deterministically expanded into a distribution.
    assert_allclose(correction.apply([0, 1, 2]), [2.009, 3.009, 4.009], atol=1e-12)
    assert_allclose(correction.apply([1, 1]), correction.apply([1, 1])[::-1])
    assert correction.provenance["tied_quantiles"] is True


def test_metrics_known_values_and_joint_normalization():
    result = metrics([1, 3], [2, 4])
    assert result["bias"] == 1
    assert result["rmsd"] == 1
    assert result["pearson_r"] == pytest.approx(1)
    assert result["cv"] == pytest.approx(1 / 3)
    assert result["p50"] == 3
    assert result["p95"] == pytest.approx(3.9)
    result = joint_diagnostics(
        [0.1, 0.9], [1, 3], [0.1, 0.9], [3, 1], hs_edges=[0, 0.5, 1], tm_edges=[0, 2, 4]
    )
    assert result["l1"] == 2
    assert result["spearman_observed"] == pytest.approx(1)
    assert result["spearman_model"] == pytest.approx(-1)
    assert result["observed_in_range"] == 2


def test_joint_range_counts_and_empty_histogram_rejection():
    result = joint_diagnostics(
        [0.1, 9], [1, 3], [0.2, 8], [1, 3], hs_edges=[0, 1], tm_edges=[0, 4]
    )
    assert result["l1"] == 0
    assert result["n_pairs"] == 2
    assert result["observed_in_range"] == result["model_in_range"] == 1
    with pytest.raises(ValueError, match="range"):
        joint_diagnostics([9, 10], [1, 3], [8, 9], [1, 3], hs_edges=[0, 1])


@pytest.mark.parametrize(
    "cal,val",
    [
        (("2016", "2019"), ("2018", "2020")),
        (("2018", "2019"), ("2016", "2017")),
        (("2018", "2018"), ("2019", "2020")),
    ],
)
def test_split_rejects_overlap_reversed_and_empty_windows(cal, val):
    with pytest.raises(ValueError):
        time_block_split(pd.date_range("2016", "2021", freq="D"), cal, val)


def test_split_refuses_random_and_unsorted_times_and_uses_half_open_blocks():
    times = pd.to_datetime(["2017-12-31", "2018-01-01", "2021-12-31", "2022-01-01"])
    cal, val = time_block_split(times, ("2007", "2018"), ("2018", "2022"))
    assert_allclose(cal, [True, False, False, False])
    assert_allclose(val, [False, True, True, False])
    with pytest.raises(ValueError, match="random"):
        time_block_split(times, ("2007", "2018"), ("2018", "2022"), random=True)
    with pytest.raises(ValueError, match="sorted"):
        time_block_split(times[::-1], ("2007", "2018"), ("2018", "2022"))


def test_qdm_preserves_known_quantile_change_in_application_distribution():
    m = np.linspace(1, 5, 1001)
    o = 2 * m
    # Additive QDM preserves the +10 change at every interior quantile.
    correction = fit(m, o, "qdm")
    q = np.linspace(0.01, 0.999, 200)
    future = m + 10
    assert_allclose(
        np.quantile(correction.apply(future), q), np.quantile(o, q) + 10, atol=1e-9
    )
    assert np.max(np.abs(correction.apply(future) - fit(m, o, "eqm").apply(future))) > 1
    assert correction.provenance["qdm_reference"] == "application_cdf"
    paper = fit(m, o, "qdm", qdm_reference="calibration")
    assert_allclose(paper.apply(future), fit(m, o, "eqm").apply(future), atol=1e-9)


def test_qdm_refuses_unknown_reference():
    with pytest.raises(ValueError, match="reference"):
        fit([1, 2], [2, 3], "qdm", qdm_reference="unknown")


def test_conditional_internal_edge_belongs_to_upper_bin():
    correction = fit(
        [3, 4, 3, 4],
        [4, 5, 6, 7],
        "conditional_qdm",
        model_hs=[0.1, 0.2, 0.5, 1],
        obs_hs=[0.1, 0.2, 0.5, 1],
        bin_edges=[0.5],
        qdm_reference="calibration",
    )
    assert_allclose(correction.apply([3, 3, 3], hs=[0.49, 0.5, 20]), [4, 6, 6])


def test_datetime_index_provenance_is_effective_pairs_and_detached():
    dates = pd.date_range("2010", periods=4, freq="D")
    m = pd.Series([np.nan, 1, 2, 3], index=dates)
    correction = fit(m, m + 1, "eqm")
    metadata = correction.provenance
    assert metadata["calibration_window"] == [
        dates[1].isoformat(),
        dates[3].isoformat(),
    ]
    metadata["quantile_levels"].clear()
    assert len(correction.provenance["quantile_levels"]) == 200
    assert len(correction.apply([])) == 0
    with pytest.raises(ValueError, match="times"):
        fit([1, 2], [2, 3], "qdm", times=dates)


def test_undefined_metrics_are_nan_and_joint_edges_are_checked():
    result = metrics([1, 1], [0, 0])
    assert np.isnan(result["pearson_r"])
    assert np.isnan(result["cv"])
    with pytest.raises(ValueError, match="edges"):
        joint_diagnostics([1, 2], [1, 2], [1, 2], [1, 2], hs_edges=[1, 0])
    with pytest.raises(ValueError, match="finite"):
        metrics([1, np.nan], [np.nan, 1])
