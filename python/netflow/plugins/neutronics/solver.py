"""Criticality (k-eff) via power iteration on the unchanged netflow core.

The generalized eigenvalue problem  M φ = (1/k) P φ  (M = migration +
absorption, P = fission production) is solved by power iteration:

    1. source S = (1/k_n) · P φ_n           (fission source from current flux)
    2. solve  M φ_{n+1} = S                  (a DRIVEN core solve — Newton)
    3. k_{n+1} = k_n · <P φ_{n+1}> / <P φ_n>  (fission-source ratio)
    4. normalize φ, repeat to convergence

Each step (2) is a standard driven network solve. The eigenvalue is a
property of the OUTER LOOP — the same meta-pattern as Picard multiphysics
coupling. No core change is needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from netflow import Network, Node
from netflow.plugins.neutronics.edges import Absorption, Diffusion


@dataclass
class SlabModel:
    """A 1-group bare-slab reactor discretized into N finite-volume cells."""
    network: Network
    cell_ids: list[str]
    fission_weight: np.ndarray   # νΣf · V per cell
    N: int
    L: float
    D: float
    Sigma_a: float
    nuSigma_f: float

    def analytic_keff(self) -> float:
        """Continuous bare-slab k-eff with zero-flux boundaries:
        k = νΣf / (Σa + D·B²),  B = π/L."""
        B2 = (math.pi / self.L) ** 2
        return self.nuSigma_f / (self.Sigma_a + self.D * B2)


def build_1group_slab(N: int, L: float, D: float,
                      Sigma_a: float, nuSigma_f: float,
                      area: float = 1.0) -> SlabModel:
    """Build a 1-D bare slab: N cells, width L, zero flux at x=0 and x=L."""
    dx = L / N
    V = area * dx
    net = Network()
    net.add_node(Node(id="ground", fixed=0.0))    # φ=0 sink for absorption
    net.add_node(Node(id="bnd_L", fixed=0.0))      # zero-flux boundaries
    net.add_node(Node(id="bnd_R", fixed=0.0))

    cell_ids = [f"cell_{i}" for i in range(N)]
    for cid in cell_ids:
        net.add_node(Node(id=cid, state0=1.0))

    coup = D * area / dx           # interior diffusion coupling
    coup_half = D * area / (dx / 2)  # cell-center to boundary (half cell)

    # interior diffusion
    for i in range(N - 1):
        net.add_edge(Diffusion(cell_ids[i], cell_ids[i + 1], coupling=coup))
    # boundary diffusion (vacuum: φ=0 at the faces)
    net.add_edge(Diffusion(cell_ids[0], "bnd_L", coupling=coup_half))
    net.add_edge(Diffusion(cell_ids[-1], "bnd_R", coupling=coup_half))
    # absorption (each cell -> ground)
    for cid in cell_ids:
        net.add_edge(Absorption(cid, "ground", removal=Sigma_a * V))

    fission_weight = np.full(N, nuSigma_f * V)
    return SlabModel(network=net, cell_ids=cell_ids,
                     fission_weight=fission_weight, N=N, L=L,
                     D=D, Sigma_a=Sigma_a, nuSigma_f=nuSigma_f)


@dataclass
class PowerIterationResult:
    keff: float
    flux: np.ndarray          # normalized fundamental-mode flux (max=1)
    n_iter: int
    converged: bool
    keff_history: list[float]


def power_iteration(model: SlabModel, *, max_iter: int = 200,
                    k_tol: float = 1e-7, flux_tol: float = 1e-7
                    ) -> PowerIterationResult:
    """Solve k-eff and the fundamental flux mode via power iteration.

    Implemented on the shared :func:`netflow.core.iterate.fixed_point`
    outer-loop driver — the same primitive used for Picard multiphysics
    coupling. Power iteration is "a fixed point whose step is one driven
    core solve plus an eigenvalue rescaling."
    """
    from netflow.core.iterate import fixed_point

    net = model.network
    cells = model.cell_ids
    w = model.fission_weight
    state = {"k": 1.0}            # eigenvalue rides along in the closure
    k_hist = [1.0]

    def step(phi: np.ndarray) -> np.ndarray:
        k = state["k"]
        # 1. fission source S_i = (1/k)·νΣf·V·φ_i (Neumann source per cell)
        for cid, s in zip(cells, w * phi / k):
            net.set_source(cid, float(s))
        # 2. driven core solve: M φ_new = S
        res = net.solve_steady(method="newton", tol=1e-12, max_iter=10)
        phi_new = np.array([res.states[cid] for cid in cells])
        # 3. eigenvalue update from the fission-source ratio
        state["k"] = k * float(np.sum(w * phi_new)) / float(np.sum(w * phi))
        k_hist.append(state["k"])
        # 4. normalize flux
        return phi_new / phi_new.max()

    fp = fixed_point(step, np.ones(model.N),
                     tol=min(k_tol, flux_tol), max_iter=max_iter)
    return PowerIterationResult(keff=state["k"], flux=fp.state,
                                n_iter=fp.n_iter, converged=fp.converged,
                                keff_history=k_hist)
