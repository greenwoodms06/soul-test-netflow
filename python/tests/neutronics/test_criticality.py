"""Neutron-diffusion criticality validation — proves the core handles
EIGENVALUE problems (not just driven BVPs) via power iteration.

Validated against the analytical bare-slab k-eff: k = νΣf/(Σa + D·B²),
B = π/L, with the flux fundamental mode a cosine.
"""

import math

import numpy as np
import pytest

from netflow.plugins.neutronics import build_1group_slab, power_iteration


def test_keff_matches_analytic_bare_slab():
    D, Sa, L = 1.0, 0.02, 100.0
    nuSf = Sa + D * (math.pi / L) ** 2     # tuned for analytic k=1
    model = build_1group_slab(N=200, L=L, D=D, Sigma_a=Sa, nuSigma_f=nuSf)
    res = power_iteration(model)
    assert res.converged
    # Within 1 pcm at N=200
    assert abs(res.keff - 1.0) < 1e-5


def test_keff_converges_with_mesh_refinement():
    """Finite-volume error should drop ~O(Δ²) as N increases."""
    D, Sa, L = 1.0, 0.02, 100.0
    nuSf = Sa + D * (math.pi / L) ** 2
    errs = []
    for N in (25, 50, 100):
        model = build_1group_slab(N=N, L=L, D=D, Sigma_a=Sa, nuSigma_f=nuSf)
        res = power_iteration(model)
        errs.append(abs(res.keff - model.analytic_keff()))
    # Each refinement should reduce error by roughly 4x (2nd order)
    assert errs[1] < errs[0] / 3
    assert errs[2] < errs[1] / 3


def test_fundamental_mode_is_cosine():
    D, Sa, L = 1.0, 0.02, 100.0
    nuSf = Sa + D * (math.pi / L) ** 2
    N = 200
    model = build_1group_slab(N=N, L=L, D=D, Sigma_a=Sa, nuSigma_f=nuSf)
    res = power_iteration(model)
    x = (np.arange(N) + 0.5) * L / N
    cosine = np.cos(math.pi * (x - L / 2) / L)
    assert np.max(np.abs(res.flux - cosine)) < 1e-3


def test_supercritical_and_subcritical():
    """More fission -> k>1 (supercritical); less -> k<1 (subcritical)."""
    D, Sa, L = 1.0, 0.02, 100.0
    nuSf_crit = Sa + D * (math.pi / L) ** 2
    k_super = power_iteration(
        build_1group_slab(100, L, D, Sa, nuSf_crit * 1.10)).keff
    k_sub = power_iteration(
        build_1group_slab(100, L, D, Sa, nuSf_crit * 0.90)).keff
    assert k_super > 1.0
    assert k_sub < 1.0


def test_flux_positive_everywhere():
    D, Sa, L = 1.0, 0.02, 100.0
    nuSf = Sa + D * (math.pi / L) ** 2
    res = power_iteration(build_1group_slab(80, L, D, Sa, nuSf))
    assert np.all(res.flux > 0)
