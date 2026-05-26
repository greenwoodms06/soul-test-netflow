"""Steady-state nonlinear solvers: Newton with backtracking damping, and Picard.

Public entry points are ``solve_newton`` and ``solve_picard``. Both return
``(x, info)`` where ``info`` carries iteration history, convergence flag,
and the actual method used (Newton may downgrade to Picard if any edge
lacks an analytic Jacobian).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
from scipy.sparse.linalg import spsolve, MatrixRankWarning
import warnings

from netflow.core.assembly import (
    IndexedNetwork,
    assemble_jacobian,
    assemble_picard_linear_system,
    assemble_residual,
)
from netflow.core.exceptions import SingularJacobian

log = logging.getLogger("netflow.core.solver")


@dataclass
class SolveInfo:
    converged: bool = False
    n_iter: int = 0
    method: str = "newton"
    residual_history: list[float] = field(default_factory=list)
    damping_history: list[float] = field(default_factory=list)
    elapsed_s: float = 0.0
    downgraded_to_picard: bool = False
    edges_without_jacobian: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Newton with backtracking damping
# ---------------------------------------------------------------------------

def solve_newton(
    net: IndexedNetwork,
    x0: np.ndarray,
    *,
    tol: float = 1e-8,
    max_iter: int = 50,
    damping: float = 1.0,
    alpha_min: float = 1e-4,
) -> tuple[np.ndarray, SolveInfo]:
    """Newton with backtracking damping.

    Falls back to Picard if any edge lacks ``jacobian()``.
    """
    t0 = time.perf_counter()
    info = SolveInfo(method="newton")

    if net.n == 0:
        info.converged = True
        info.elapsed_s = time.perf_counter() - t0
        return x0.copy(), info

    x = x0.copy()
    F = assemble_residual(net, x)
    info.residual_history.append(float(np.linalg.norm(F, ord=np.inf)))

    for k in range(max_iter):
        if info.residual_history[-1] <= tol:
            info.converged = True
            break

        jac = assemble_jacobian(net, x)
        if jac.picard_required:
            log.info(
                "Newton downgraded to Picard: %d edge(s) lack jacobian()",
                len(jac.edges_without_jacobian),
            )
            info.downgraded_to_picard = True
            info.edges_without_jacobian = jac.edges_without_jacobian
            # Continue with Picard from current x
            x, picard_info = solve_picard(
                net, x, tol=tol, max_iter=max_iter - k,
            )
            info.method = "newton+picard"
            info.residual_history.extend(picard_info.residual_history[1:])
            info.n_iter = k + picard_info.n_iter
            info.converged = picard_info.converged
            info.elapsed_s = time.perf_counter() - t0
            return x, info

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", MatrixRankWarning)
                delta = spsolve(jac.J, -F)
        except (MatrixRankWarning, RuntimeError) as exc:
            raise SingularJacobian(
                f"Singular Jacobian at Newton iteration {k}: {exc}",
                iteration=k,
            ) from exc

        # Backtracking line search on ||F||_inf
        alpha = damping
        F_norm = info.residual_history[-1]
        while True:
            x_trial = x + alpha * delta
            F_trial = assemble_residual(net, x_trial)
            F_trial_norm = float(np.linalg.norm(F_trial, ord=np.inf))
            if F_trial_norm < F_norm or alpha <= alpha_min:
                break
            alpha *= 0.5
        x = x_trial
        F = F_trial
        info.residual_history.append(F_trial_norm)
        info.damping_history.append(alpha)
        info.n_iter = k + 1

    if info.residual_history[-1] <= tol:
        info.converged = True
    info.elapsed_s = time.perf_counter() - t0
    return x, info


# ---------------------------------------------------------------------------
# Picard
# ---------------------------------------------------------------------------

def solve_picard(
    net: IndexedNetwork,
    x0: np.ndarray,
    *,
    tol: float = 1e-8,
    max_iter: int = 200,
    relax: float = 1.0,
) -> tuple[np.ndarray, SolveInfo]:
    """Picard fixed-point on effective-conductance Laplacian.

    Slower than Newton on strong nonlinearity but always available.
    Optional under-relaxation: ``x_{k+1} = (1-relax) · x_k + relax · solve(...)``.
    """
    t0 = time.perf_counter()
    info = SolveInfo(method="picard")

    if net.n == 0:
        info.converged = True
        info.elapsed_s = time.perf_counter() - t0
        return x0.copy(), info

    x = x0.copy()
    F = assemble_residual(net, x)
    info.residual_history.append(float(np.linalg.norm(F, ord=np.inf)))

    for k in range(max_iter):
        if info.residual_history[-1] <= tol:
            info.converged = True
            break

        L, b = assemble_picard_linear_system(net, x)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", MatrixRankWarning)
                x_new = spsolve(L, b)
        except (MatrixRankWarning, RuntimeError) as exc:
            raise SingularJacobian(
                f"Singular Picard system at iteration {k}: {exc}",
                iteration=k,
            ) from exc

        if relax != 1.0:
            x_new = (1.0 - relax) * x + relax * x_new
        x = x_new
        F = assemble_residual(net, x)
        info.residual_history.append(float(np.linalg.norm(F, ord=np.inf)))
        info.n_iter = k + 1

    if info.residual_history[-1] <= tol:
        info.converged = True
    info.elapsed_s = time.perf_counter() - t0
    return x, info
