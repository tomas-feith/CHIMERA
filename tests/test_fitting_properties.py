"""Property-based tests for the ODR fit.

`tests/test_fitting.py` checks specific fits against known answers. These check
invariants that must hold for *every* dataset -- the kind of thing that breaks
quietly when the weighting or the R^2 formula is touched, because any single
example still looks plausible.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from fitting import run_odr_fit

LINEAR = "B[0]*_x+B[1]"

# Well-conditioned inputs: the properties are about the estimator, not about
# odrpack's behaviour on degenerate data.
reals = st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False)
slopes = st.floats(min_value=-20, max_value=20, allow_nan=False, allow_infinity=False)
sigmas = st.floats(min_value=0.01, max_value=10, allow_nan=False, allow_infinity=False)


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(slopes, reals)
def test_an_exact_line_is_recovered_exactly(slope: float, intercept: float) -> None:
    """Noise-free data on a line must return that line, whatever the line."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    y = [slope * xi + intercept for xi in x]
    beta, _, _, r2, _ = run_odr_fit(LINEAR, x, y, [], [0.5] * len(x), [1.0, 0.0], 5000)

    # Tolerance is odrpack's convergence criterion, not ours: it stops around
    # 1e-6 absolute. Loose enough not to flag the optimiser, tight enough that a
    # genuinely wrong slope or intercept -- which would be off by orders of
    # magnitude, not parts per million -- still fails.
    assert beta[0] == pytest.approx(slope, abs=1e-4)
    assert beta[1] == pytest.approx(intercept, abs=1e-4)
    # A perfect fit: ss_res is 0, so R^2 is 1 -- unless y barely varies, where
    # ss_tot collapses and R^2 is undefined (reported as nan) or numerically wild.
    if abs(slope) > 1e-3:
        assert r2 == pytest.approx(1.0, abs=1e-6)


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(reals, min_size=4, max_size=10, unique=True), slopes, reals)
def test_r2_never_exceeds_one(xs: list[float], slope: float, intercept: float) -> None:
    """R^2 = 1 - ss_res/ss_tot is bounded above by 1 for any data at all."""
    xs = sorted(xs)
    rng = np.random.default_rng(len(xs))
    y = [slope * x + intercept + rng.normal(0, 1) for x in xs]
    assume(len(set(np.round(y, 9))) > 1)  # ss_tot > 0, else R^2 is nan by design

    _, _, _, r2, _ = run_odr_fit(LINEAR, xs, y, [], [1.0] * len(xs), [1.0, 0.0], 5000)
    assert np.isnan(r2) or r2 <= 1.0 + 1e-9


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(sigmas)
def test_scaling_every_uncertainty_leaves_the_parameters_alone(k: float) -> None:
    """Weights are 1/sigma^2, so a uniform rescale cancels in the normal equations.

    If it ever stops holding, the weighting has picked up an absolute term --
    exactly the sort of change that leaves individual fits looking fine.
    """
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [1.0, 3.1, 4.9, 7.2, 8.8]
    base = run_odr_fit(LINEAR, x, y, [], [0.4] * len(x), [1.0, 0.0], 5000)
    scaled = run_odr_fit(LINEAR, x, y, [], [0.4 * k] * len(x), [1.0, 0.0], 5000)

    assert scaled[0][0] == pytest.approx(base[0][0], rel=1e-6)
    assert scaled[0][1] == pytest.approx(base[0][1], rel=1e-6)
    assert scaled[3] == pytest.approx(base[3], rel=1e-6)  # and R^2 with them


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.permutations([0, 1, 2, 3, 4, 5]))
def test_the_fit_does_not_depend_on_point_order(order: list[int]) -> None:
    """Least squares is a sum; the order it is accumulated in cannot matter."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    y = [1.0, 3.1, 4.9, 7.2, 8.8, 11.3]
    err = [0.1, 0.2, 0.15, 0.3, 0.2, 0.25]

    straight = run_odr_fit(LINEAR, x, y, [], err, [1.0, 0.0], 5000)
    shuffled = run_odr_fit(
        LINEAR,
        [x[i] for i in order],
        [y[i] for i in order],
        [],
        [err[i] for i in order],
        [1.0, 0.0],
        5000,
    )

    assert shuffled[0][0] == pytest.approx(straight[0][0], rel=1e-6)
    assert shuffled[0][1] == pytest.approx(straight[0][1], rel=1e-6)
    assert shuffled[3] == pytest.approx(straight[3], rel=1e-6)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.floats(min_value=-1e-12, max_value=1e-12))
def test_any_zero_uncertainty_is_rejected(near_zero: float) -> None:
    """1/sigma**2 is infinite at zero; it must be refused rather than produce nan."""
    x = [0.0, 1.0, 2.0, 3.0]
    y = [1.0, 3.0, 5.0, 7.0]
    err = [0.1, 0.0, 0.1, 0.1]
    with pytest.raises(ValueError, match="non-zero"):
        run_odr_fit(LINEAR, x, y, [], err, [1.0, 0.0], 2000)
