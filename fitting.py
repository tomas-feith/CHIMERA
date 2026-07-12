"""Orthogonal-distance-regression curve fitting for CHIMERA.

Separated from the Tkinter UI (``main.py``) so the fitting maths can be exercised
without a display. Input validation and error reporting stay in the UI layer;
this module assumes it is handed a validated expression and clean numeric data.
"""

import warnings
from typing import Any

import numpy as np

# TODO: scipy.odr is deprecated (SciPy 1.17) and slated for removal in 1.19;
# migrate to the odrpack package. scipy is pinned <1.19 meanwhile (see
# pyproject.toml) and the deprecation notice is silenced on import.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from scipy import odr

from expr_eval import safe_eval


def _evaluate(expr: str, B: Any, x: Any) -> Any:
    return safe_eval(expr, {"np": np, "B": B, "_x": x})


def _format_output(fit: Any) -> str:
    lines = [
        "Beta:" + str(fit.beta),
        "Beta Std Error:" + str(fit.sd_beta),
        "Beta Covariance:" + str(fit.cov_beta),
        "Residual Variance:" + str(fit.res_var),
        "Inverse Condition #:" + str(fit.inv_condnum),
        "Reason(s) for Halting:",
    ]
    lines.extend(str(r) for r in fit.stopreason)
    return "\n".join(lines) + "\n"


def run_odr_fit(
    expr: str,
    x_points: list,
    y_points: list,
    x_err: list,
    y_err: list,
    init_params: list,
    max_iter: int,
) -> tuple:
    """Fit ``expr`` to the given data with orthogonal distance regression.

    ``x_err`` may be empty when the data has no x uncertainty. Returns
    ``(beta, sd_beta, res_var, r2, full_output_text)``.
    """
    model = odr.Model(lambda B, x: _evaluate(expr, B, x))
    if x_err:
        fit_data = odr.RealData(x_points, y_points, sx=x_err, sy=y_err, fix=[0] * len(x_points))
    else:
        fit_data = odr.RealData(x_points, y_points, sy=y_err, fix=[0] * len(x_points))

    fit = odr.ODR(fit_data, model, beta0=init_params, maxit=max_iter).run()
    full_output = _format_output(fit)

    # coeficiente de determinação R^2
    ss_tot = sum((y - np.average(y_points)) ** 2 for y in y_points)
    ss_res = sum(
        (y_points[i] - _evaluate(expr, fit.beta, x_points[i])) ** 2 for i in range(len(y_points))
    )
    r2 = 1 - ss_res / ss_tot

    return fit.beta, fit.sd_beta, fit.res_var, r2, full_output
