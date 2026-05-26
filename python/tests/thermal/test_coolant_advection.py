"""Tests for CoolantAdvection — 1-D upwind energy transport.

The contract: for an interior coolant slice k with wall flux Q_w and
upstream/downstream advection edges, the steady-state balance must give

    T_k = T_{k-1} + Q_w / (mdot · cp)

regardless of the downstream temperature (upwind scheme).
"""

import math

import pytest

from netflow import Network, Node
from netflow.plugins.thermal import CoolantAdvection, ContactResistance


def test_single_advection_balance():
    """One interior coolant slice with a fixed wall flux source.

    coolant_in (Dirichlet=300) → adv → coolant_1 (interior, +Q_w source)
                                   → adv → coolant_out (sink Dirichlet)

    Expect: T_1 = T_in + Q_w / (mdot · cp).
    """
    mdot = 0.3
    cp = 5500.0
    Q_w = 18000.0   # W (the heat going into slice 1)
    T_in = 300.0

    net = Network()
    net.add_node(Node(id="in", fixed=T_in))
    net.add_node(Node(id="c1", source=Q_w))   # Neumann source = wall flux
    net.add_node(Node(id="out", fixed=T_in))  # sink Dirichlet
    net.add_edge(CoolantAdvection("in",  "c1",  mdot=mdot, cp=cp))
    net.add_edge(CoolantAdvection("c1",  "out", mdot=mdot, cp=cp))

    res = net.solve_steady()
    assert res.converged
    expected = T_in + Q_w / (mdot * cp)
    assert math.isclose(res.states["c1"], expected, rel_tol=1e-9)


def test_advection_chain_three_slices_with_per_slice_source():
    """Three interior coolant slices, each receives its own wall flux.

    Expect: T_k = T_in + Σ_{j<=k} Q_j / (mdot · cp)
    """
    mdot = 0.3
    cp = 5500.0
    Q = [10000.0, 12000.0, 14000.0]
    T_in = 300.0

    net = Network()
    net.add_node(Node(id="in", fixed=T_in))
    net.add_node(Node(id="out", fixed=T_in))
    prev = "in"
    for k, Qk in enumerate(Q):
        nid = f"c{k}"
        net.add_node(Node(id=nid, source=Qk))
        net.add_edge(CoolantAdvection(prev, nid, mdot=mdot, cp=cp))
        prev = nid
    net.add_edge(CoolantAdvection(prev, "out", mdot=mdot, cp=cp))

    res = net.solve_steady()
    assert res.converged

    cumulative = 0.0
    for k, Qk in enumerate(Q):
        cumulative += Qk
        expected = T_in + cumulative / (mdot * cp)
        assert math.isclose(res.states[f"c{k}"], expected, rel_tol=1e-9), \
            f"slice {k}: got {res.states[f'c{k}']}, expected {expected}"


def test_downstream_temperature_does_not_affect_upstream():
    """Upwind property: changing the outlet sink Dirichlet must not
    change interior coolant temperatures."""
    mdot, cp, Q_w, T_in = 0.3, 5500.0, 18000.0, 300.0

    def solve_with_sink_T(T_sink: float) -> float:
        net = Network()
        net.add_node(Node(id="in",  fixed=T_in))
        net.add_node(Node(id="c1",  source=Q_w))
        net.add_node(Node(id="out", fixed=T_sink))
        net.add_edge(CoolantAdvection("in",  "c1",  mdot=mdot, cp=cp))
        net.add_edge(CoolantAdvection("c1",  "out", mdot=mdot, cp=cp))
        return net.solve_steady().states["c1"]

    T_low  = solve_with_sink_T(50.0)
    T_high = solve_with_sink_T(900.0)
    assert math.isclose(T_low, T_high, rel_tol=1e-9), (
        "outlet sink should not influence interior coolant T (upwind)"
    )


def test_advection_with_callable_cp():
    """cp can be a function of T. The upwind scheme evaluates cp at the
    upstream T on each edge, so the steady balance becomes

        cp(T_1) · T_1 = cp(T_in) · T_in + Q_w / mdot

    (because the flux out of c1 carries cp(T_1)·T_1 and the flux in
    from inlet carries cp(T_in)·T_in)."""
    def cp_fn(T):
        return 5000.0 + 2.0 * (T - 300.0)   # mild T-dependence

    mdot, Q_w, T_in = 0.3, 18000.0, 300.0
    net = Network()
    net.add_node(Node(id="in", fixed=T_in))
    net.add_node(Node(id="c1", source=Q_w))
    net.add_node(Node(id="out", fixed=T_in))
    net.add_edge(CoolantAdvection("in",  "c1",  mdot=mdot, cp=cp_fn))
    net.add_edge(CoolantAdvection("c1",  "out", mdot=mdot, cp=cp_fn))

    res = net.solve_steady()
    assert res.converged
    T1 = res.states["c1"]

    # Solve the upwind-cp balance by fixed-point iteration: it converges
    # quickly for a smooth cp(T).
    rhs = cp_fn(T_in) * T_in + Q_w / mdot
    T_expected = T_in
    for _ in range(50):
        T_expected = rhs / cp_fn(T_expected)
    assert math.isclose(T1, T_expected, rel_tol=1e-6)


def test_advection_rejects_zero_or_negative_mdot():
    with pytest.raises(ValueError, match="mdot must be positive"):
        CoolantAdvection("a", "b", mdot=0.0, cp=5500.0)
    with pytest.raises(ValueError, match="mdot must be positive"):
        CoolantAdvection("a", "b", mdot=-1.0, cp=5500.0)
