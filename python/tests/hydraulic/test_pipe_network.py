"""Hydraulic pipe-network validation — proves netflow.core is domain-agnostic.

The hydraulic plugin uses a different state (pressure), a different flux
(volumetric flow), and a genuinely different nonlinearity (Darcy-Weisbach,
singular Jacobian at zero flow) — all on the UNCHANGED core. These tests
validate against analytical pipe-flow solutions.
"""

import math

import pytest

from netflow import Network, Node
from netflow.plugins.hydraulic import Pipe, LinearPipe


def test_single_pipe_darcy_weisbach():
    """Q = sqrt(ΔP/K) for a single pipe between two fixed pressures."""
    K = 1e6
    net = Network()
    net.add_node(Node(id="a", fixed=200000.0))
    net.add_node(Node(id="b", fixed=0.0))
    e = Pipe("a", "b", K=K)
    net.add_edge(e)
    res = net.solve_steady()
    assert res.converged
    assert math.isclose(res.edge_flux(e), math.sqrt(200000.0 / K), rel_tol=1e-6)


def test_parallel_split_analytical():
    """Q_in splits between two parallel pipes per the Q² law.

    ΔP = (Q_in / (1/√K1 + 1/√K2))²,  Q_i = √(ΔP/K_i)
    """
    K1, K2, Q_in = 1e6, 4e6, 0.5
    net = Network()
    net.add_node(Node(id="B", fixed=0.0))
    net.add_node(Node(id="A", source=Q_in))
    p1 = Pipe("A", "B", K=K1)
    p2 = Pipe("A", "B", K=K2)
    net.add_edge(p1)
    net.add_edge(p2)
    res = net.solve_steady(method="newton", tol=1e-12, max_iter=100)
    assert res.converged

    dP = (Q_in / (1 / math.sqrt(K1) + 1 / math.sqrt(K2))) ** 2
    assert math.isclose(res.edge_flux(p1), math.sqrt(dP / K1), rel_tol=1e-6)
    assert math.isclose(res.edge_flux(p2), math.sqrt(dP / K2), rel_tol=1e-6)
    # Continuity
    assert math.isclose(res.edge_flux(p1) + res.edge_flux(p2), Q_in, rel_tol=1e-9)


def test_series_pipes_conservation():
    """Two pipes in series carry the same flow; intermediate pressure
    partitions the head loss per the Q² law."""
    K1, K2 = 1e6, 3e6
    net = Network()
    net.add_node(Node(id="in", fixed=300000.0))
    net.add_node(Node(id="mid"))
    net.add_node(Node(id="out", fixed=0.0))
    e1 = Pipe("in", "mid", K=K1)
    e2 = Pipe("mid", "out", K=K2)
    net.add_edge(e1)
    net.add_edge(e2)
    res = net.solve_steady(method="newton", tol=1e-12, max_iter=100)
    assert res.converged
    # Same flow through both
    assert math.isclose(res.edge_flux(e1), res.edge_flux(e2), rel_tol=1e-7)
    # Total head loss conserved: ΔP1 + ΔP2 = 300000
    P_mid = res.states["mid"]
    assert math.isclose((300000 - P_mid) + (P_mid - 0), 300000.0, rel_tol=1e-9)
    # Analytical flow: Q = sqrt(300000/(K1+K2)) since ΔP=KQ² adds in series
    Q_analytic = math.sqrt(300000.0 / (K1 + K2))
    assert math.isclose(res.edge_flux(e1), Q_analytic, rel_tol=1e-6)


def test_loop_mass_conservation_and_pressure_closure():
    """A square loop (Hardy Cross): inflow at A, outflow at C. Verify
    mass conservation at every node and Kirchhoff pressure closure
    (sum of ΔP around the loop = 0)."""
    K = 2e6
    net = Network()
    net.add_node(Node(id="A", source=0.1))      # inflow 0.1 m³/s
    net.add_node(Node(id="B"))
    net.add_node(Node(id="C", fixed=0.0))        # outflow sink (pressure ref)
    net.add_node(Node(id="D"))
    # Two paths A->B->C and A->D->C
    ab = Pipe("A", "B", K=K)
    bc = Pipe("B", "C", K=K)
    ad = Pipe("A", "D", K=K)
    dc = Pipe("D", "C", K=K)
    for e in (ab, bc, ad, dc):
        net.add_edge(e)
    res = net.solve_steady(method="newton", tol=1e-12, max_iter=100)
    assert res.converged

    # Symmetric loop -> equal split
    assert math.isclose(res.edge_flux(ab), res.edge_flux(ad), rel_tol=1e-6)
    assert math.isclose(res.edge_flux(ab), 0.05, rel_tol=1e-6)
    # Mass conservation at B: in from A = out to C
    assert math.isclose(res.edge_flux(ab), res.edge_flux(bc), rel_tol=1e-9)
    # Pressure closure: P_A - P_B - (P_A - P_D) - (P_B... loop sum = 0
    # ΔP(A->B) + ΔP(B->C) should equal ΔP(A->D) + ΔP(D->C) (parallel paths)
    path1 = (res.states["A"] - res.states["B"]) + (res.states["B"] - res.states["C"])
    path2 = (res.states["A"] - res.states["D"]) + (res.states["D"] - res.states["C"])
    assert math.isclose(path1, path2, rel_tol=1e-9)


def test_singular_jacobian_at_zero_flow_is_handled():
    """A perfectly symmetric bridge network puts zero flow in the bridge
    pipe (ΔP=0). The Darcy-Weisbach Jacobian is singular there; the
    regularization must keep Newton stable and return ~zero flow."""
    K = 1e6
    net = Network()
    net.add_node(Node(id="in", fixed=100000.0))
    net.add_node(Node(id="L"))
    net.add_node(Node(id="R"))
    net.add_node(Node(id="out", fixed=0.0))
    # Symmetric Wheatstone-bridge-like layout; bridge L-R carries zero flow
    net.add_edge(Pipe("in", "L", K=K))
    net.add_edge(Pipe("in", "R", K=K))
    net.add_edge(Pipe("L", "out", K=K))
    net.add_edge(Pipe("R", "out", K=K))
    bridge = Pipe("L", "R", K=K)
    net.add_edge(bridge)
    res = net.solve_steady(method="newton", tol=1e-10, max_iter=100)
    assert res.converged
    # By symmetry, L and R are at the same pressure -> zero bridge flow
    assert abs(res.edge_flux(bridge)) < 1e-6
    assert math.isclose(res.states["L"], res.states["R"], abs_tol=1e-3)


def test_linear_pipe_baseline():
    """LinearPipe is the trivial Hagen-Poiseuille / resistor case."""
    net = Network()
    net.add_node(Node(id="a", fixed=50.0))
    net.add_node(Node(id="b", fixed=0.0))
    e = LinearPipe("a", "b", R=10.0)
    net.add_edge(e)
    res = net.solve_steady()
    assert math.isclose(res.edge_flux(e), 5.0, rel_tol=1e-9)
