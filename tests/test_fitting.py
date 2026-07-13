"""Tests for the ODR fitting layer, exercised without any GUI."""

import numpy as np

from fitting import run_odr_fit


def test_linear_fit_recovers_parameters():
    # y = 2x + 1
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [1.0, 3.0, 5.0, 7.0, 9.0]
    y_err = [0.1] * len(x)

    beta, sd_beta, res_var, r2, output = run_odr_fit(
        "B[0]*_x+B[1]", x, y, [], y_err, [1.0, 0.0], 2000
    )

    assert np.allclose(beta, [2.0, 1.0], atol=1e-6)
    assert r2 > 0.999
    assert len(sd_beta) == 2


def test_full_output_contains_expected_sections():
    x = [0.0, 1.0, 2.0]
    y = [1.0, 2.0, 3.0]
    _, _, _, _, output = run_odr_fit("B[0]*_x+B[1]", x, y, [], [0.1] * 3, [1.0, 1.0], 2000)

    assert output.startswith("Beta:")
    for section in ("Beta Std Error:", "Residual Variance:", "Reason(s) for Halting:"):
        assert section in output
    assert output.endswith("\n")


def test_fit_with_x_uncertainty_runs():
    x = [0.0, 1.0, 2.0, 3.0]
    y = [1.0, 3.0, 5.0, 7.0]
    x_err = [0.05] * len(x)
    y_err = [0.1] * len(x)

    beta, _, _, r2, _ = run_odr_fit("B[0]*_x+B[1]", x, y, x_err, y_err, [1.0, 0.0], 2000)

    assert np.allclose(beta, [2.0, 1.0], atol=1e-2)
    assert r2 > 0.99


def test_nonlinear_fit_through_numpy_path():
    # y = A*exp(k*x); exercises the safe_eval np.<func> code path.
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [2.0 * np.exp(0.5 * xi) for xi in x]
    y_err = [0.01] * len(x)

    beta, _, _, r2, _ = run_odr_fit("B[0]*np.exp(B[1]*_x)", x, y, [], y_err, [1.0, 1.0], 5000)

    assert np.allclose(beta, [2.0, 0.5], atol=1e-3)
    assert r2 > 0.999


def test_x_error_is_ignored():
    # CHIMERA holds x fixed (OLS), so x_err must not change the result at all.
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [1.0, 3.1, 4.9, 7.2, 8.8]
    y_err = [0.1] * len(x)

    without = run_odr_fit("B[0]*_x+B[1]", x, y, [], y_err, [1.0, 0.0], 2000)
    with_xerr = run_odr_fit("B[0]*_x+B[1]", x, y, [5.0] * len(x), y_err, [1.0, 0.0], 2000)

    assert np.array_equal(without[0], with_xerr[0])  # identical beta


def test_y_error_weighting_changes_result():
    # Constant model B[0] fit to three zeros and one outlier at 10. Down-weighting
    # the outlier pulls the estimate toward 0; up-weighting it pulls it up.
    x = [0.0, 1.0, 2.0, 3.0]
    y = [0.0, 0.0, 0.0, 10.0]

    outlier_trusted = run_odr_fit("B[0]+0*_x", x, y, [], [1.0, 1.0, 1.0, 0.1], [0.0], 2000)[0][0]
    outlier_doubted = run_odr_fit("B[0]+0*_x", x, y, [], [1.0, 1.0, 1.0, 100.0], [0.0], 2000)[0][0]

    assert outlier_trusted > outlier_doubted


def test_r2_is_nan_when_y_has_no_spread():
    # All y equal -> ss_tot == 0; R^2 is undefined and must not divide by zero.
    x = [0.0, 1.0, 2.0, 3.0]
    y = [5.0, 5.0, 5.0, 5.0]

    _, _, _, r2, _ = run_odr_fit("B[0]+0*_x", x, y, [], [0.1] * 4, [5.0], 2000)

    assert np.isnan(r2)
