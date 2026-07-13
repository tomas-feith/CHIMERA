"""Orthogonal-distance-regression curve fitting for CHIMERA.

Separated from the Tkinter UI (``main.py``) so the fitting maths can be exercised
without a display. Input validation and error reporting stay in the UI layer;
this module assumes it is handed a validated expression and clean numeric data.

Uses the maintained ``odrpack`` package (the successor to the removed
``scipy.odr``).
"""

from typing import Any

import numpy as np
from odrpack import odr_fit

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
        str(fit.stopreason),
    ]
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
    """Fit ``expr`` to the given data and return the results.

    CHIMERA has always held the x values fixed (they are never adjusted), i.e.
    this is a weighted least-squares fit in y. ``x_err`` is accepted for API
    compatibility but does not affect the result, matching the long-standing
    behaviour (``task='OLS'`` reproduces the previous ``scipy.odr`` results with
    ``fix=[0]*n`` exactly). Returns
    ``(beta, sd_beta, res_var, r2, full_output_text)``.
    """
    x = np.asarray(x_points, dtype=float)
    y = np.asarray(y_points, dtype=float)
    # scipy.odr took standard deviations (sy); odrpack takes weights = 1/sy**2.
    weight_y = 1.0 / np.asarray(y_err, dtype=float) ** 2

    fit = odr_fit(
        lambda xd, beta: _evaluate(expr, beta, xd),
        x,
        y,
        init_params,
        weight_y=weight_y,
        task="OLS",
        maxit=max_iter,
    )
    full_output = _format_output(fit)

    # coefficient of determination R^2. Undefined when the data has no spread in
    # y (all points equal): ss_tot == 0 would divide by zero, so report nan.
    ss_tot = sum((yi - np.average(y)) ** 2 for yi in y)
    ss_res = sum((y[i] - _evaluate(expr, fit.beta, x[i])) ** 2 for i in range(len(y)))
    r2 = float("nan") if ss_tot == 0 else 1 - ss_res / ss_tot

    return fit.beta, fit.sd_beta, fit.res_var, r2, full_output
