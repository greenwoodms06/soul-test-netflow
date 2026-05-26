"""Thermal edge unit tests — analytical R_eq verification."""

import math

import pytest

from netflow import Network, Node
from netflow.plugins.thermal import (
    PlanarConduction,
    CylindricalConduction,
    ContactResistance,
    Fouling,
    UAEdge,
    Radiation,
    Constant,
    SS316L,
)


def test_planar_conduction_constant_k():
    """T_hot=500, slab L=0.01, k=20, A=2 -> R=L/(kA)=2.5e-4 K/W.
    With T_cold=400, Q = 100/2.5e-4 = 400000 W. Solve for verification."""
    net = Network()
    net.add_node(Node(id="h", fixed=500.0))
    net.add_node(Node(id="c", fixed=400.0))
    e = PlanarConduction("h", "c", L=0.01, k=20.0, A=2.0)
    net.add_edge(e)
    res = net.solve_steady()
    assert res.converged
    R = 0.01 / (20.0 * 2.0)
    expected_Q = (500 - 400) / R
    assert math.isclose(res.edge_flux(e), expected_Q, rel_tol=1e-9)


def test_planar_conduction_with_material():
    """k(T_mean) for SS316L at 450K = 13 + 0.015*(450-300) = 15.25.
    Same geometry; Q = ΔT / (L/(k·A)) = 100 / (0.01/(15.25*2)) = 30500 W."""
    net = Network()
    net.add_node(Node(id="h", fixed=500.0))
    net.add_node(Node(id="c", fixed=400.0))
    e = PlanarConduction("h", "c", L=0.01, k=SS316L(), A=2.0)
    net.add_edge(e)
    res = net.solve_steady()
    assert res.converged
    expected_Q = 100.0 / (0.01 / (15.25 * 2.0))
    assert math.isclose(res.edge_flux(e), expected_Q, rel_tol=1e-3)


def test_cylindrical_conduction():
    """R = ln(r_o/r_i)/(2πLk). r_i=0.05, r_o=0.06, L=1, k=15.
    R = ln(1.2)/(2π·1·15) = 0.001934 K/W."""
    net = Network()
    net.add_node(Node(id="h", fixed=400.0))
    net.add_node(Node(id="c", fixed=300.0))
    e = CylindricalConduction("h", "c",
                              r_i=0.05, r_o=0.06, L=1.0, k=15.0)
    net.add_edge(e)
    res = net.solve_steady()
    expected_R = math.log(0.06 / 0.05) / (2 * math.pi * 1.0 * 15.0)
    assert math.isclose(res.edge_flux(e), 100 / expected_R, rel_tol=1e-9)


def test_contact_resistance():
    R = 0.005
    net = Network()
    net.add_node(Node(id="h", fixed=350.0))
    net.add_node(Node(id="c", fixed=300.0))
    e = ContactResistance("h", "c", R=R)
    net.add_edge(e)
    res = net.solve_steady()
    assert math.isclose(res.edge_flux(e), 50 / R, rel_tol=1e-9)


def test_ua_edge():
    UA = 1234.5
    net = Network()
    net.add_node(Node(id="h", fixed=500.0))
    net.add_node(Node(id="c", fixed=300.0))
    e = UAEdge("h", "c", UA=UA)
    net.add_edge(e)
    res = net.solve_steady()
    assert math.isclose(res.edge_flux(e), UA * 200.0, rel_tol=1e-9)


def test_radiation_concentric_cylinders():
    """Black-body limit: q = σ A (Ta^4 - Tb^4). With ε=1, F=1.
    Hot 1000K -> cold 500K, A=1m^2:
        q = 5.67e-8 · (1000^4 - 500^4) = 5.67e-8 · 9.375e11 ≈ 53156 W"""
    net = Network()
    net.add_node(Node(id="h", fixed=1000.0))
    net.add_node(Node(id="c", fixed=500.0))
    e = Radiation("h", "c", emissivity=1.0, area=1.0, view_factor=1.0)
    net.add_edge(e)
    res = net.solve_steady()
    expected = 5.670374419e-8 * (1000.0**4 - 500.0**4)
    assert res.converged
    assert math.isclose(res.edge_flux(e), expected, rel_tol=1e-9)


def test_radiation_nonlinear_solve():
    """Single radiation between hot wall and ambient with conduction to ambient.
    Verify Newton converges with the analytic Jacobian."""
    net = Network()
    net.add_node(Node(id="hot", fixed=1500.0))
    net.add_node(Node(id="mid"))
    net.add_node(Node(id="cold", fixed=300.0))
    # Conduction hot -> mid (high R), Radiation mid -> cold
    net.add_edge(ContactResistance("hot", "mid", R=0.01))
    net.add_edge(Radiation("mid", "cold", emissivity=0.5, area=0.5))
    res = net.solve_steady()
    assert res.converged
    # Energy balance at "mid": flux_in == flux_out
    flux_in = (1500.0 - res.states["mid"]) / 0.01
    sigma = 5.670374419e-8
    flux_out = sigma * 0.5 * 0.5 * (res.states["mid"]**4 - 300.0**4)
    assert math.isclose(flux_in, flux_out, rel_tol=1e-8)


def test_jacobian_vs_finite_difference_planar():
    e = PlanarConduction("a", "b", L=0.002, k=SS316L(), A=0.1)
    Ta, Tb = 600.0, 500.0
    h = 0.5
    da_fd = (e.flux(Ta + h, Tb) - e.flux(Ta - h, Tb)) / (2 * h)
    db_fd = (e.flux(Ta, Tb + h) - e.flux(Ta, Tb - h)) / (2 * h)
    da, db = e.jacobian(Ta, Tb)
    assert math.isclose(da, da_fd, rel_tol=1e-4)
    assert math.isclose(db, db_fd, rel_tol=1e-4)


def test_jacobian_vs_finite_difference_radiation():
    e = Radiation("a", "b", emissivity=0.5, area=0.3, view_factor=1.0)
    Ta, Tb = 800.0, 400.0
    h = 0.5
    da_fd = (e.flux(Ta + h, Tb) - e.flux(Ta - h, Tb)) / (2 * h)
    db_fd = (e.flux(Ta, Tb + h) - e.flux(Ta, Tb - h)) / (2 * h)
    da, db = e.jacobian(Ta, Tb)
    # Central-difference relative error is O((h/T)^2) ~ 1.5e-6 at h=0.5, T=400
    assert math.isclose(da, da_fd, rel_tol=1e-5)
    assert math.isclose(db, db_fd, rel_tol=1e-5)
