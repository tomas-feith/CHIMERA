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
