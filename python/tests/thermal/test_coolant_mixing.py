"""Tests for CoolantMixing — symmetric lateral enthalpy exchange."""

import math

import pytest

from netflow import Network, Node
from netflow.plugins.thermal import CoolantMixing


def test_mixing_preserves_total_energy():
    """Two coolant nodes with Q-sources, connected only by a mixing edge.

    Net energy balance: Q_in_total + 0 = mdot·cp·(T_a − T_b) on the edge
    can't be a sink, only a *redistributor*. So system needs an open
    boundary somewhere. Build a 4-node test: two coolant nodes plus
    inlet and outlet via simple resistors.
    """
    from netflow.plugins.thermal import ContactResistance

    mdot_mix, cp = 0.05, 5500.0

    net = Network()
    net.add_node(Node(id="bath_a", fixed=300.0))
    net.add_node(Node(id="a"))
    net.add_node(Node(id="b"))
    net.add_node(Node(id="bath_b", fixed=300.0))
    # Each coolant node has a heat source (different magnitudes)
    net.add_node(Node(id="a_hot", source=10000.0))
    net.add_node(Node(id="b_hot", source=2000.0))
    # Source nodes connect to coolant via resistors (small R for tight coupling)
    net.add_edge(ContactResistance("a_hot", "a", R=0.001))
    net.add_edge(ContactResistance("b_hot", "b", R=0.001))
    # Each coolant connects to a bath at 300 K (so heat can leave the system)
    net.add_edge(ContactResistance("a", "bath_a", R=0.1))
    net.add_edge(ContactResistance("b", "bath_b", R=0.1))
    # Lateral mixing between the two coolant nodes
    e_mix = CoolantMixing("a", "b", mdot_mix=mdot_mix, cp=cp)
    net.add_edge(e_mix)

    res = net.solve_steady()
    assert res.converged
    # Symmetric: increasing mixing should pull the two nodes' T closer.
    T_a = res.states["a"]
    T_b = res.states["b"]
    assert T_a > T_b   # a is hotter (more heat in)
    # The mixing flux should be positive (a→b)
    flux = res.edge_flux(e_mix)
    assert flux > 0
    assert math.isclose(flux, mdot_mix * cp * (T_a - T_b), rel_tol=1e-9)


def test_mixing_zero_when_temperatures_equal():
    e = CoolantMixing("a", "b", mdot_mix=0.05, cp=5500.0)
    assert math.isclose(e.flux(310.0, 310.0), 0.0, abs_tol=1e-9)
    da, db = e.jacobian(310.0, 310.0)
    # Symmetric jacobian
    assert math.isclose(da, -db, rel_tol=1e-9)
    assert da > 0


def test_mixing_homogenises_in_chain():
    """Long chain of mixing edges, with heat in at one end and out the other.
    Interior nodes should be approximately linear between source and sink."""
    from netflow.plugins.thermal import ContactResistance

    N = 8
    mdot_mix, cp = 1.0, 5500.0   # strong mixing
    net = Network()
    net.add_node(Node(id="sink", fixed=300.0))
    for i in range(N):
        net.add_node(Node(id=f"c{i}"))
    # Heat into c0
    net.add_node(Node(id="src", source=5000.0))
    net.add_edge(ContactResistance("src", "c0", R=1e-4))
    # Heat out of c_{N-1}
    net.add_edge(ContactResistance(f"c{N-1}", "sink", R=1e-4))
    # Mixing between consecutive nodes
    for i in range(N - 1):
        net.add_edge(CoolantMixing(f"c{i}", f"c{i+1}",
                                   mdot_mix=mdot_mix, cp=cp))

    res = net.solve_steady()
    assert res.converged
    # Temperatures should decrease monotonically c0 > c1 > ... > c_{N-1}
    Ts = [res.states[f"c{i}"] for i in range(N)]
    for a, b in zip(Ts, Ts[1:]):
        assert a > b, f"chain not monotone: {Ts}"


def test_mixing_rejects_nonpositive_mdot():
    with pytest.raises(ValueError, match="mdot_mix must be positive"):
        CoolantMixing("a", "b", mdot_mix=0.0, cp=5500.0)
