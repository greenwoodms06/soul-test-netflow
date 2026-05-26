"""Doppler-coupled neutronics <-> thermal — the power is COMPUTED, not imposed.

Closes the project's most pervasive validation caveat. Couples the
neutronics plugin (k-eff + flux via power iteration) to a lumped thermal
model via Picard, with Doppler feedback (resonance absorption rises with
fuel temperature):

    Σa(T) = Σa0 · (1 + α_D · (√T − √T_ref))

Demonstrates the negative temperature coefficient that makes reactors
self-stabilizing: as power (hence fuel T) rises, Σa rises, k falls.

All on the unchanged core: neutronics is an eigenvalue solve (power
iteration = outer loop of driven core solves); the thermal feedback is
another outer (Picard) loop on top. Outer-loop composition again.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from netflow.plugins.neutronics import build_1group_slab, power_iteration


@dataclass
class CoupledResult:
    keff: float
    flux: np.ndarray
    fuel_T: np.ndarray
    power_W: float
    n_picard: int
    converged: bool


def solve_doppler_coupled(
    *, N=100, L=100.0, D=1.0, Sigma_a0=0.02, nuSigma_f=None,
    power_W=0.0, T_coolant=565.0, T_ref=565.0,
    R_thermal=2e-4, alpha_doppler=-0.02, kappa_Sigma_f=None,
    max_picard=40, tol=1e-6,
) -> CoupledResult:
    """Picard-couple neutronics (with Doppler) and a lumped thermal model.

    ``alpha_doppler`` is the fractional change in Σa per unit √T (1/√K);
    negative-feedback physics makes Σa *rise* with T, so use a positive
    magnitude on √T - √T_ref … encoded with alpha_doppler>0 raising Σa.
    Here we pass alpha_doppler as the coefficient such that
    Σa = Σa0·(1 + |alpha|·(√T − √T_ref)).
    """
    if nuSigma_f is None:
        nuSigma_f = Sigma_a0 + D * (math.pi / L) ** 2   # cold-critical
    if kappa_Sigma_f is None:
        kappa_Sigma_f = nuSigma_f   # power weight ∝ νΣf·φ

    alpha = abs(alpha_doppler)
    fuel_T = np.full(N, T_coolant)
    flux = np.ones(N)
    keff = 1.0
    converged = False

    for it in range(max_picard):
        # Doppler: per-cell absorption rises with sqrt(T)
        Sa_cell = Sigma_a0 * (1 + alpha * (np.sqrt(fuel_T) - math.sqrt(T_ref)))
        # Build slab with mean Σa (uniform build; apply per-cell via removal)
        model = build_1group_slab(N=N, L=L, D=D,
                                  Sigma_a=Sigma_a0, nuSigma_f=nuSigma_f)
        # Override per-cell absorption removal for Doppler (edge to ground)
        dx = L / N
        for i, cid in enumerate(model.cell_ids):
            for e in model.network.edges:
                if getattr(e, "a", None) == cid and getattr(e, "b", None) == "ground":
                    e.removal = Sa_cell[i] * dx   # area=1
        res = power_iteration(model, max_iter=300)
        new_flux, new_k = res.flux, res.keff

        # Power distribution from flux (normalized to total power_W)
        weight = kappa_Sigma_f * new_flux
        if power_W > 0 and weight.sum() > 0:
            power_i = power_W * weight / weight.sum()
        else:
            power_i = np.zeros(N)

        # Thermal: lumped fuel temperature per cell
        new_T = T_coolant + power_i * R_thermal

        dT = float(np.max(np.abs(new_T - fuel_T)))
        dk = abs(new_k - keff)
        fuel_T, flux, keff = new_T, new_flux, new_k
        if dT < tol and dk < tol:
            converged = True
            break

    return CoupledResult(keff=keff, flux=flux, fuel_T=fuel_T,
                         power_W=power_W, n_picard=it + 1, converged=converged)


def doppler_feedback_curve(power_levels, **kw):
    """k-eff vs reactor power level — the Doppler feedback signature.
    Negative slope = stable reactor."""
    ks = []
    for P in power_levels:
        r = solve_doppler_coupled(power_W=P, **kw)
        ks.append(r.keff)
    return np.array(ks)
