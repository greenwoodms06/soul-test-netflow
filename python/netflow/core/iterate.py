"""Fixed-point outer-loop driver — the meta-abstraction of this project.

The core solves *driven* boundary-value problems (F(x)=0). Three larger
problem classes are all expressible as an OUTER LOOP that repeatedly
calls a driven solve and updates parameters between calls:

  * eigenvalue (criticality)  — power iteration: update the source from
    the previous solution, rescale the eigenvalue.
  * coupled multiphysics      — Picard: solve each physics, pass updated
    fields to the others.
  * (transient uses a different driver — implicit time stepping — but
    each BDF step is itself a driven Newton solve.)

``fixed_point`` captures the shared structure: iterate a state through a
``step`` function until the change drops below tolerance. ``step`` does
whatever inner driven solve(s) the problem requires.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeVar

import numpy as np

S = TypeVar("S")


@dataclass
class FixedPointResult:
    state: object
    n_iter: int
    converged: bool
    history: list[float] = field(default_factory=list)


def _default_norm(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float(np.max(np.abs(a - b)))


def fixed_point(
    step: Callable[[S], S],
    x0: S,
    *,
    tol: float = 1e-7,
    max_iter: int = 200,
    norm: Callable[[S, S], float] = _default_norm,
    relax: float | None = None,
) -> FixedPointResult:
    """Iterate ``x_{n+1} = step(x_n)`` until ``norm(x_{n+1}, x_n) < tol``.

    Parameters
    ----------
    step :
        One outer-loop step. Typically performs a driven core solve and
        returns the updated state.
    x0 :
        Initial state (array-like by default; supply ``norm`` for other
        types).
    relax :
        Optional under-relaxation in [0,1]: ``x ← (1-relax)·x_old +
        relax·step(x_old)``. Only valid when the state supports the
        arithmetic (e.g. numpy arrays). Helps stiff couplings converge.
    """
    x = x0
    history: list[float] = []
    for it in range(max_iter):
        x_new = step(x)
        if relax is not None:
            x_new = (1.0 - relax) * np.asarray(x) + relax * np.asarray(x_new)
        delta = norm(x_new, x)
        history.append(delta)
        x = x_new
        if delta < tol:
            return FixedPointResult(state=x, n_iter=it + 1,
                                    converged=True, history=history)
    return FixedPointResult(state=x, n_iter=max_iter,
                            converged=False, history=history)
