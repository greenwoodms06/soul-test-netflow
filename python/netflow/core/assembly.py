"""Sparse residual and Jacobian assembly.

This module is pure: given an indexed network (interior-node map +
Dirichlet values), it builds the residual vector and the COO triplets
for the Jacobian. The solver consumes those.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy.sparse import csc_matrix, coo_matrix

if TYPE_CHECKING:
    from netflow.core.edge import Edge
    from netflow.core.node import Node


@dataclass
class IndexedNetwork:
    """Frozen view of a Network at the moment a solve begins.

    Built by Network._index() and consumed by assembly + solver.
    """

    interior_ids: list[str]              # ordered: x[i] is the state of interior_ids[i]
    interior_idx: dict[str, int]         # id -> position in x
    dirichlet: dict[str, float]          # fixed-state values for Dirichlet nodes
    sources: np.ndarray                  # length n_interior; Neumann source per interior node
    edges: list["Edge"]
    n: int                               # number of interior unknowns

    def state_at(self, node_id: str, x: np.ndarray) -> float:
        """Return the current value of ``node_id`` given unknown vector ``x``."""
        if node_id in self.dirichlet:
            return self.dirichlet[node_id]
        return x[self.interior_idx[node_id]]


def assemble_residual(net: IndexedNetwork, x: np.ndarray) -> np.ndarray:
    """Return F(x): F_i = source_i + Σ flux_in − Σ flux_out at interior nodes."""
    F = net.sources.copy()
    for e in net.edges:
        sa = net.state_at(e.a, x)
        sb = net.state_at(e.b, x)
        f = e.flux(sa, sb)
        ia = net.interior_idx.get(e.a)
        ib = net.interior_idx.get(e.b)
        if ia is not None:
            F[ia] -= f   # flux leaves a
        if ib is not None:
            F[ib] += f   # flux enters b
    return F


@dataclass
class JacobianAssembly:
    """Result of attempting Jacobian assembly.

    ``J`` is non-None on success. ``picard_required`` is True if any
    edge lacks ``jacobian()`` — the solver should fall back to Picard
    in that case.
    """

    J: csc_matrix | None
    picard_required: bool
    edges_without_jacobian: list[int]   # indices into net.edges


def assemble_jacobian(net: IndexedNetwork, x: np.ndarray) -> JacobianAssembly:
    """Build ∂F/∂x as a sparse CSC matrix.

    If any edge returns ``None`` from ``jacobian()``, signals Picard
    fallback rather than silently filling zeros.
    """
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    edges_without_jacobian: list[int] = []

    for k, e in enumerate(net.edges):
        sa = net.state_at(e.a, x)
        sb = net.state_at(e.b, x)
        j = e.jacobian(sa, sb)
        if j is None:
            edges_without_jacobian.append(k)
            continue
        da, db = j
        ia = net.interior_idx.get(e.a)
        ib = net.interior_idx.get(e.b)
        # F_a contribution: -flux  →  -da at (ia, ia), -db at (ia, ib)
        if ia is not None:
            rows.append(ia); cols.append(ia); vals.append(-da)
            if ib is not None:
                rows.append(ia); cols.append(ib); vals.append(-db)
        # F_b contribution: +flux  →  +da at (ib, ia), +db at (ib, ib)
        if ib is not None:
            if ia is not None:
                rows.append(ib); cols.append(ia); vals.append(da)
            rows.append(ib); cols.append(ib); vals.append(db)

    if edges_without_jacobian:
        return JacobianAssembly(
            J=None, picard_required=True,
            edges_without_jacobian=edges_without_jacobian,
        )

    if net.n == 0:
        # no interior unknowns; trivial case
        return JacobianAssembly(
            J=csc_matrix((0, 0)), picard_required=False,
            edges_without_jacobian=[],
        )

    J_coo = coo_matrix((vals, (rows, cols)), shape=(net.n, net.n))
    return JacobianAssembly(
        J=J_coo.tocsc(), picard_required=False, edges_without_jacobian=[],
    )


# --- Picard helpers --------------------------------------------------------

def assemble_picard_linear_system(
    net: IndexedNetwork, x: np.ndarray, *, eps: float = 1e-12
) -> tuple[csc_matrix, np.ndarray]:
    """Build (L, b) such that L · x_{k+1} = b is the Picard fixed-point step.

    Each edge contributes an effective conductance
        g_e = f_e(x_k) / (s_a − s_b)
    (degenerate-difference falls back to the linearised jacobian, then
    to zero if even that is unavailable). The result is a symmetric
    weighted Laplacian augmented with Dirichlet contributions to the
    right-hand side.
    """
    n = net.n
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    b = net.sources.copy()

    for e in net.edges:
        sa = net.state_at(e.a, x)
        sb = net.state_at(e.b, x)
        df = sa - sb
        if abs(df) > eps:
            g = e.flux(sa, sb) / df
        else:
            # Use jacobian if available — at zero ΔT the conductance is the slope.
            j = e.jacobian(sa, sb)
            g = j[0] if j is not None else 0.0
        ia = net.interior_idx.get(e.a)
        ib = net.interior_idx.get(e.b)
        if ia is not None and ib is not None:
            rows += [ia, ia, ib, ib]
            cols += [ia, ib, ia, ib]
            vals += [g, -g, -g, g]
        elif ia is not None:
            rows.append(ia); cols.append(ia); vals.append(g)
            b[ia] += g * sb
        elif ib is not None:
            rows.append(ib); cols.append(ib); vals.append(g)
            b[ib] += g * sa
        # else: both Dirichlet, edge does not enter the system

    if n == 0:
        return csc_matrix((0, 0)), np.zeros(0)

    L = coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsc()
    return L, b
