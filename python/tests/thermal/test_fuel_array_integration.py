"""Integration smoke tests for the fuel-array builder.

These tests guard against regressions in the high-level builder that
ties FuelRod, ForcedConvection, CoolantAdvection, CoolantMixing,
materials, and CoolPropFluid together. Small sizes (3×3 × 5 axial)
so the suite stays fast.
"""

import math

import pytest

CoolProp = pytest.importorskip("CoolProp")

from netflow.bench.fuel_array import (
    MDOT_CHANNEL,
    Q_LIN_NOMINAL,
    T_COOLANT_INLET,
    build_pin_assembly,
    cosine_axial_shape,
    cosine_radial_power,
)
from netflow.plugins.thermal import CoolPropFluid


def test_identical_pins_dirichlet_coolant_converges():
    net, _ = build_pin_assembly(n_x=3, n_y=3, n_axial=5,
                                q_lin=Q_LIN_NOMINAL)
    res = net.solve_steady(tol=1e-5, max_iter=40)
    assert res.converged


def test_identical_pins_solved_coolant_converges():
    net, _ = build_pin_assembly(n_x=3, n_y=3, n_axial=5,
                                q_lin=Q_LIN_NOMINAL,
                                coolant_as_unknown=True)
    res = net.solve_steady(tol=1e-5, max_iter=40)
    assert res.converged


def test_full_physics_stack_converges():
    """Non-identical radial + cosine axial + solved coolant + mixing."""
    net, _ = build_pin_assembly(
        n_x=3, n_y=3, n_axial=5,
        q_lin=cosine_radial_power(3, 3, peak_factor=1.4),
        axial_shape=cosine_axial_shape(1.5),
        coolant_as_unknown=True,
        cross_pin_mixing_fraction=0.05,
    )
    res = net.solve_steady(tol=1e-5, max_iter=40)
    assert res.converged


def test_mixing_requires_solved_coolant():
    """Cross-pin mixing only makes sense when coolant is a DOF."""
    with pytest.raises(ValueError, match="coolant_as_unknown=True"):
        build_pin_assembly(n_x=3, n_y=3, n_axial=5,
                           q_lin=Q_LIN_NOMINAL,
                           cross_pin_mixing_fraction=0.05)


def test_energy_balance_full_physics():
    """Global conservation: sum of Q_in must equal sum of mdot·cp·ΔT
    (per pin, with mixing). Mixing redistributes laterally but
    conserves globally."""
    fluid = CoolPropFluid("Water", default_P=15.5e6)
    n_x = n_y = 3
    n_axial = 8
    L = 1.5
    q_fn = cosine_radial_power(n_x, n_y, peak_factor=1.4)
    ax = cosine_axial_shape(1.5)

    net, _ = build_pin_assembly(
        n_x=n_x, n_y=n_y, n_axial=n_axial,
        q_lin=q_fn, axial_shape=ax,
        coolant_fluid=fluid,
        coolant_as_unknown=True,
        cross_pin_mixing_fraction=0.05,
    )
    res = net.solve_steady(tol=1e-5, max_iter=40)
    assert res.converged

    # Total power in (axial shape integrates to 1)
    total_Q_in = sum(q_fn(ix, iy) * L for ix in range(n_x) for iy in range(n_y))

    # Total power out (sum of per-pin outlet enthalpy rise)
    cp = 5500.0
    total_Q_out = sum(
        MDOT_CHANNEL * cp
        * (res.states[f"p{ix}_{iy}_cool_z{n_axial-1}"] - T_COOLANT_INLET)
        for ix in range(n_x) for iy in range(n_y)
    )
    rel_err = abs(total_Q_out - total_Q_in) / total_Q_in
    assert rel_err < 1e-3, (
        f"energy balance off by {rel_err*100:.3f}%: "
        f"Q_in={total_Q_in:.0f} W, Q_out={total_Q_out:.0f} W"
    )
