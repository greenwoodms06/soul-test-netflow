"""Tests for FuelRod's empirical gap-conductance option.

Geometric He conduction under-predicts BOL gap conductance and over-
predicts fuel centerline T by ~200 K (tally §25/§26). The
``gap_conductance`` parameter lets users supply an empirical h_gap
[W/m²K] matching FRAPCON/BISON-style models.
"""

import math

import pytest

from netflow import Network
from netflow.plugins.thermal import (
    FuelRod, UO2, Zircaloy4, Helium_gap,
)


def _solve_rod(gap_conductance=None):
    net = Network()
    rod = FuelRod(
        r_pellet=4.096e-3, gap_thickness=0.084e-3, r_clad_outer=4.750e-3,
        L=1.0, fuel_material=UO2(), clad_material=Zircaloy4(),
        gap_material=Helium_gap, gap_emissivity=0.85,
        q_lin=20000.0, gap_conductance=gap_conductance,
    )
    ports = rod.build(net)
    net.fix_node(ports.clad_outer, 600.0)
    res = net.solve_steady(method="newton", tol=1e-7, max_iter=80)
    return res, ports


def test_empirical_gap_conductance_lowers_centerline_T():
    """Higher gap conductance => lower fuel centerline T (less gap ΔT)."""
    res_geom, p = _solve_rod(gap_conductance=None)       # geometric model
    res_emp, _ = _solve_rod(gap_conductance=7500.0)      # empirical h_gap

    assert res_geom.converged and res_emp.converged
    T_geom = res_geom.states[p.centerline]
    T_emp = res_emp.states[p.centerline]
    # The geometric model (~3000 W/m²K) should be hotter than the
    # higher empirical conductance (7500 W/m²K).
    assert T_geom > T_emp
    # And the difference should be of order 100+ K (the documented bias)
    assert (T_geom - T_emp) > 80.0


def test_gap_conductance_matches_hand_calc():
    """Gap ΔT = q' / (h_gap · A_gap) for the gap edge specifically."""
    h_gap = 7500.0
    res, p = _solve_rod(gap_conductance=h_gap)
    assert res.converged
    r_p = 4.096e-3
    L = 1.0
    A_gap = 2 * math.pi * r_p * L
    dT_gap_expected = 20000.0 / (h_gap * A_gap)
    dT_gap_actual = res.states[p.pellet_surface] - res.states[p.clad_inner]
    assert math.isclose(dT_gap_actual, dT_gap_expected, rel_tol=1e-6)


def test_geometric_gap_still_default():
    """Without gap_conductance, the geometric conduction+radiation model
    is used (backwards compatible)."""
    res, p = _solve_rod(gap_conductance=None)
    assert res.converged
    # Geometric gap is much more resistive → larger gap ΔT
    dT_gap = res.states[p.pellet_surface] - res.states[p.clad_inner]
    assert dT_gap > 150.0    # geometric He conduction gives a big drop
