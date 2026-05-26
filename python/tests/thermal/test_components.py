"""Component tests: multilayer wall, fuel rod, stack."""

import math

import pytest

from netflow import Network, Node
from netflow.plugins.thermal import (
    MultilayerCylindricalWall,
    InsulatedPipeSection,
    FuelRod,
    ResistanceStack,
    UO2,
    Zircaloy4,
    SS316L,
    Helium_gap,
    PlanarConduction,
    ContactResistance,
)


def test_multilayer_cylindrical_wall_two_layers():
    """Two-layer pipe wall. Series resistance is sum of cylindrical R's."""
    wall = MultilayerCylindricalWall(
        layers=[(0.005, 15.0), (0.020, 0.05)],   # steel, then insulation
        L=1.0, r_inner=0.025,
    )
    net = Network()
    ports = wall.build(net, prefix="w_")
    net.fix_node(ports.inner, 600.0)
    net.fix_node(ports.outer, 300.0)
    res = net.solve_steady()
    assert res.converged
    # Analytical R; interface temperature inferred from series-R partition
    R1 = math.log(0.030 / 0.025) / (2 * math.pi * 1.0 * 15.0)
    R2 = math.log(0.050 / 0.030) / (2 * math.pi * 1.0 * 0.05)
    R_total = R1 + R2
    Q_expected = (600 - 300) / R_total
    T_interface_expected = 600 - Q_expected * R1
    assert math.isclose(
        res.states[ports.interface(0)], T_interface_expected, rel_tol=1e-9,
    )


def test_insulated_pipe_section():
    """Sugar over MultilayerCylindricalWall; verify ports."""
    sec = InsulatedPipeSection(
        pipe_ID=0.050, pipe_OD=0.060,
        pipe_material=SS316L(),
        insulation_thickness=0.025,
        insulation_material=0.04,           # constant k
        L=2.0,
    )
    net = Network()
    ports = sec.build(net, prefix="p1_")
    assert ports.bore.endswith("0.025")     # r_inner = 0.025
    assert ports.pipe_outer.endswith("0.03")
    assert "0.055" in ports.ambient


def test_fuel_rod_centerline_temperature():
    """PWR-ish fuel rod: r_pellet=4.1mm, gap=0.085mm, r_clad_outer=4.75mm,
    L=1m, q_lin=18 kW/m. Fix clad outer at 600K.
    """
    net = Network()
    rod = FuelRod(
        r_pellet=4.1e-3, gap_thickness=0.085e-3, r_clad_outer=4.75e-3,
        L=1.0,
        fuel_material=UO2(),
        clad_material=Zircaloy4(),
        gap_material=Helium_gap,
        gap_emissivity=0.85,
        q_lin=18000.0,
    )
    ports = rod.build(net)
    # Apply the Dirichlet directly on the clad-outer node — no buffer needed
    net.fix_node(ports.clad_outer, 600.0)

    res = net.solve_steady(method="newton", max_iter=80, tol=1e-6)
    assert res.converged

    T_c = res.states[ports.centerline]
    T_s = res.states[ports.pellet_surface]
    T_ci = res.states[ports.clad_inner]
    T_co = res.states[ports.clad_outer]

    # Physical sanity: temperatures decrease outward
    assert T_c > T_s > T_ci > T_co
    # Centerline-surface ΔT roughly q_lin/(4π k_mean). k_UO2 evaluated
    # at T_mean(~1500K) is ~3 → ΔT ~ 477 K. Order-of-magnitude check.
    assert 300 < (T_c - T_s) < 800
    # Linear power balance: Q through clad must equal q_lin · L = 18000 W
    R_clad = (
        math.log(4.75e-3 / (4.1e-3 + 0.085e-3))
        / (2 * math.pi * 1.0 * Zircaloy4().k(0.5 * (T_ci + T_co)))
    )
    Q_clad = (T_ci - T_co) / R_clad
    assert math.isclose(Q_clad, 18000.0, rel_tol=5e-2)


def test_resistance_stack_three_resistors():
    """ResistanceStack chains three constant-R edges; R_eq = sum."""
    stack = ResistanceStack(
        ContactResistance("dummy_a", "dummy_b", R=2.0),
        ContactResistance("dummy_a", "dummy_b", R=3.0),
        ContactResistance("dummy_a", "dummy_b", R=5.0),
    )
    net = Network()
    ports = stack.build(net, prefix="s_")
    net.fix_node(ports.upstream, 10.0)
    net.fix_node(ports.downstream, 0.0)
    res = net.solve_steady()
    # With R_eq = 10, Q = 1. Interior node voltages = 10 - Q·R_partial
    assert math.isclose(res.states[ports.nodes[1]], 10.0 - 1.0 * 2.0, rel_tol=1e-9)
    assert math.isclose(res.states[ports.nodes[2]], 10.0 - 1.0 * 5.0, rel_tol=1e-9)
