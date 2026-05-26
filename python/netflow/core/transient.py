"""Transient (time-dependent) solver.

For an interior node ``i`` with capacity ``C_i > 0``, the energy
balance becomes

    C_i · dT_i/dt = F_i(T, t)

where ``F_i`` is the same residual computed for steady-state: source
plus net flux from all incident edges. The system is a coupled ODE
solved by ``scipy.integrate.solve_ivp`` (default method ``BDF``
because thermal problems are stiff — pellet timescale ~1 s, clad
timescale ~10 ms, coolant flow timescale ~10 ms).

Dirichlet nodes hold their fixed values for the duration of the
simulation (they could in principle be time-varying — supported via
``source_fn`` updating ``node.fixed``, but the common case is
constant boundaries with time-varying sources, e.g. a power ramp).

Time-varying Neumann sources are handled by an optional ``source_fn``
callback that mutates ``network._nodes[*].source`` (or ``.fixed``)
based on current time ``t`` before each F evaluation.
"""

from __future__ import annotations

import time as _time_clock
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import numpy as np
from scipy.integrate import solve_ivp

from scipy.sparse import diags

from netflow.core.assembly import assemble_jacobian, assemble_residual

if TYPE_CHECKING:
    from netflow.core.network import Network


@dataclass(frozen=True)
class TransientResult:
    """Result of a ``solve_transient`` call."""
    t: np.ndarray                       # shape (nt,)
    states: dict[str, np.ndarray]       # node_id → shape (nt,)
    dirichlet: dict[str, float]         # static (Dirichlet) boundaries
    converged: bool
    n_rhs_evals: int
    elapsed_s: float
    message: str
    n_jac_evals: int = 0

    def state_array(self, node_id: str) -> np.ndarray:
        """Trajectory for one node. Dirichlet nodes return a constant array."""
        if node_id in self.states:
            return self.states[node_id]
        if node_id in self.dirichlet:
            return np.full_like(self.t, self.dirichlet[node_id])
        raise KeyError(node_id)

    def at(self, t_query: float) -> dict[str, float]:
        """Return all node states (interior + Dirichlet) at the requested
        time, by linear interpolation between stored time points."""
        out: dict[str, float] = dict(self.dirichlet)
        for nid, arr in self.states.items():
            out[nid] = float(np.interp(t_query, self.t, arr))
        return out


def solve_transient(
    network: "Network",
    t_span: tuple[float, float],
    *,
    y0: dict[str, float] | None = None,
    source_fn: Callable[[float, "Network"], None] | None = None,
    t_eval: np.ndarray | None = None,
    method: str = "BDF",
    rtol: float = 1e-4,
    atol: float = 1e-2,
    max_step: float | None = None,
) -> TransientResult:
    """Integrate the network from ``t_span[0]`` to ``t_span[1]``.

    Parameters
    ----------
    network :
        A Network where *every interior node has* ``capacity > 0``.
    t_span :
        ``(t_start, t_end)`` in seconds.
    y0 :
        Initial state per node id. Missing nodes use ``Node.state0``
        if non-zero, else the mean of Dirichlet temperatures.
    source_fn :
        Optional callback ``f(t, network)`` invoked before each
        F evaluation. Use it to update ``node.source`` (or
        ``node.fixed``) for time-varying boundary conditions.
    t_eval :
        Specific times at which to record the trajectory. If None, the
        integrator chooses adaptive output and we use whatever it
        returns.
    method :
        scipy.integrate.solve_ivp method (default ``"BDF"`` — stiff).
    rtol, atol :
        Integrator tolerances. atol in Kelvin (default 1e-2).
    """
    # Build the IndexedNetwork (uses the same validation as solve_steady)
    idx = network._index()      # noqa: SLF001 — internal API by design

    # Validate capacities
    missing: list[str] = []
    C = np.empty(idx.n, dtype=float)
    for nid, i in idx.interior_idx.items():
        c = network._nodes[nid].capacity
        if c is None or c <= 0:
            missing.append(nid)
        else:
            C[i] = float(c)
    if missing:
        raise ValueError(
            f"solve_transient requires capacity > 0 for every interior node; "
            f"{len(missing)} node(s) missing capacity, e.g. {missing[:5]}"
        )

    # Initial guess vector
    x0 = network._initial_guess(idx)
    if y0:
        for nid, v in y0.items():
            if nid in idx.interior_idx:
                x0[idx.interior_idx[nid]] = v

    n_rhs = 0
    n_jac = 0
    inv_C = diags(1.0 / C)
    picard_warned = [False]

    def _sync_sources_and_dirichlet(t: float) -> None:
        """Pull current Node.source / Node.fixed back into the IndexedNetwork.

        Called whenever ``source_fn`` may have mutated them.
        """
        if source_fn is None:
            return
        source_fn(t, network)
        for nid, i in idx.interior_idx.items():
            idx.sources[i] = network._nodes[nid].source
        for nid in idx.dirichlet:
            idx.dirichlet[nid] = network._nodes[nid].fixed

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        nonlocal n_rhs
        n_rhs += 1
        _sync_sources_and_dirichlet(t)
        F = assemble_residual(idx, y)
        return F / C

    def jac(t: float, y: np.ndarray):
        nonlocal n_jac
        n_jac += 1
        _sync_sources_and_dirichlet(t)
        ja = assemble_jacobian(idx, y)
        if ja.picard_required:
            if not picard_warned[0]:
                picard_warned[0] = True
            # Returning None tells scipy to fall back to FD — slow, but
            # correct. Avoid this by giving every edge a jacobian().
            return None
        # ∂(F/C)/∂T = (1/C) · ∂F/∂T — sparse-friendly row scaling
        return inv_C @ ja.J

    t0_wall = _time_clock.perf_counter()
    sol = solve_ivp(
        rhs, t_span, x0,
        method=method,
        jac=jac,                              # <-- analytic sparse Jacobian
        t_eval=t_eval,
        rtol=rtol, atol=atol,
        max_step=max_step if max_step is not None else np.inf,
    )
    elapsed = _time_clock.perf_counter() - t0_wall

    # Assemble per-node trajectories
    states: dict[str, np.ndarray] = {}
    for nid, i in idx.interior_idx.items():
        states[nid] = sol.y[i, :]

    dirichlet = {nid: float(v) for nid, v in idx.dirichlet.items()}

    return TransientResult(
        t=sol.t,
        states=states,
        dirichlet=dirichlet,
        converged=bool(sol.success),
        n_rhs_evals=n_rhs,
        elapsed_s=elapsed,
        message=sol.message,
        n_jac_evals=n_jac,
    )
