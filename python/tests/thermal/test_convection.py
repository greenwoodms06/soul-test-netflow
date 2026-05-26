"""ForcedConvection tests with CoolProp water."""

import math

import pytest

CoolProp = pytest.importorskip("CoolProp")

from netflow import Network, Node
from netflow.plugins.thermal import (
    CoolPropFluid,
    CallableFluid,
    ForcedConvection,
    ContactResistance,
)


def test_dittus_boelter_against_hand_calc():
    """Water at ~300K, mdot=0.5 kg/s, D=0.02 m, A_ht = π·D·L with L=1.
    From CoolProp at 300K, 1atm:
      μ ≈ 8.54e-4 Pa·s, k ≈ 0.610 W/m/K, Pr ≈ 5.86, ρ ≈ 997 kg/m³.
    A_xs = π(0.02)²/4 = 3.14e-4 m².
    Re = mdot · D / (μ · A_xs) = 0.5·0.02/(8.54e-4·3.14e-4) ≈ 37300.
    Nu = 0.023·Re^0.8·Pr^0.4  (heating, since wall_T > fluid_T)
       ≈ 0.023·5400·2.04 ≈ 253
    h = Nu·k/D ≈ 253·0.610/0.02 ≈ 7720 W/(m²·K)
    """
    water = CoolPropFluid("Water", default_P=101325.0)
    net = Network()
    net.add_node(Node(id="wall", fixed=320.0))
    net.add_node(Node(id="bulk", fixed=300.0))
    e = ForcedConvection(
        "wall", "bulk", fluid=water,
        mdot=0.5, D_h=0.02, A_ht=math.pi * 0.02 * 1.0,
        correlation="dittus-boelter", wall_side="a",
    )
    net.add_edge(e)
    res = net.solve_steady()
    assert res.converged
    Q = res.edge_flux(e)
    # Hand-calc range: h ∈ [6000, 9000], A_ht ≈ 0.0628 m², ΔT=20 K
    # Q ≈ h·A·ΔT ≈ 7500·0.0628·20 ≈ 9420 W (rough)
    # Loose bound: 7000 < Q < 12000
    assert 7000 < Q < 13000


def test_gnielinski_vs_dittus_boelter():
    """Both should be within ~20% in the DB-valid range Re > 10^4."""
    water = CoolPropFluid("Water", default_P=101325.0)
    common = dict(
        fluid=water, mdot=0.5, D_h=0.02, A_ht=math.pi * 0.02,
        wall_side="a",
    )

    net1 = Network()
    net1.add_node(Node(id="wall", fixed=320.0))
    net1.add_node(Node(id="bulk", fixed=300.0))
    e1 = ForcedConvection("wall", "bulk", correlation="dittus-boelter", **common)
    net1.add_edge(e1)
    Q_db = net1.solve_steady().edge_flux(e1)

    net2 = Network()
    net2.add_node(Node(id="wall", fixed=320.0))
    net2.add_node(Node(id="bulk", fixed=300.0))
    e2 = ForcedConvection("wall", "bulk", correlation="gnielinski", **common)
    net2.add_edge(e2)
    Q_gn = net2.solve_steady().edge_flux(e2)

    rel_err = abs(Q_db - Q_gn) / Q_db
    assert rel_err < 0.30, f"DB and Gnielinski disagree by {rel_err*100:.1f}%"


def test_callable_fluid_no_coolprop():
    """CallableFluid lets users build a network without CoolProp."""
    fluid = CallableFluid(
        rho=lambda T, P: 1000.0,
        mu=lambda T, P: 1e-3,
        k=lambda T, P: 0.6,
        cp=lambda T, P: 4180.0,
    )
    assert math.isclose(fluid.Pr(300, 1e5), 1e-3 * 4180.0 / 0.6, rel_tol=1e-9)


def test_convection_with_conduction_series():
    """T_hot=400 -> Rwall (constant R=0.001) -> wall_inner -> Forced conv to bulk=300.
    Verify both temperatures and heat flow balance."""
    water = CoolPropFluid("Water", default_P=2e6)   # 2 MPa
    net = Network()
    net.add_node(Node(id="hot", fixed=400.0))
    net.add_node(Node(id="wall"))
    net.add_node(Node(id="bulk", fixed=300.0))
    net.add_edge(ContactResistance("hot", "wall", R=0.001))
    e_conv = ForcedConvection(
        "wall", "bulk", fluid=water,
        mdot=1.0, D_h=0.025, A_ht=math.pi * 0.025 * 2.0,
        correlation="dittus-boelter", wall_side="a",
    )
    net.add_edge(e_conv)
    res = net.solve_steady()
    assert res.converged
    # Energy balance through both resistances
    Q1 = (400 - res.states["wall"]) / 0.001
    Q2 = res.edge_flux(e_conv)
    assert math.isclose(Q1, Q2, rel_tol=1e-6)
