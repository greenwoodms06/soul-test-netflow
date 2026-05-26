"""Doppler-coupled neutronics<->thermal: power computed, negative feedback.

Validates the full multiphysics coupling on the unchanged core:
neutronics (eigenvalue via power iteration) + thermal + Doppler feedback.
"""

import numpy as np
import pytest

from netflow.coupling.neutronics_thermal import (
    solve_doppler_coupled, doppler_feedback_curve,
)


KW = dict(N=50, L=100.0, D=1.0, Sigma_a0=0.02, R_thermal=3e-4,
          alpha_doppler=0.02)


def test_cold_reactor_is_critical():
    """At zero power the reactor is cold-critical (k ~ 1)."""
    r = solve_doppler_coupled(power_W=0.0, **KW)
    assert r.converged
    assert abs(r.keff - 1.0) < 1e-3


def test_doppler_feedback_is_negative():
    """Raising power raises fuel T, raises Σa, lowers k. Stable reactor."""
    k_cold = solve_doppler_coupled(power_W=0.0, **KW).keff
    k_hot = solve_doppler_coupled(power_W=30e6, **KW).keff
    assert k_hot < k_cold


def test_power_raises_fuel_temperature():
    r_cold = solve_doppler_coupled(power_W=0.0, **KW)
    r_hot = solve_doppler_coupled(power_W=20e6, **KW)
    assert r_hot.fuel_T.max() > r_cold.fuel_T.max()


def test_feedback_curve_monotone_decreasing():
    """k-eff vs power must be monotonically decreasing (negative feedback)."""
    powers = [0.0, 10e6, 20e6, 30e6]
    ks = doppler_feedback_curve(powers, **KW)
    assert np.all(np.diff(ks) < 0)


def test_computed_power_closes_imposed_power_caveat():
    """The flux (hence power shape) is solved, not imposed — it should be
    a physical peaked mode, and the coupled state self-consistent."""
    r = solve_doppler_coupled(power_W=15e6, **KW)
    assert r.converged
    assert np.all(r.flux > 0)
    # Doppler flattens the flux slightly but it remains center-peaked
    assert r.flux.argmax() in range(KW["N"] // 2 - 5, KW["N"] // 2 + 5)
