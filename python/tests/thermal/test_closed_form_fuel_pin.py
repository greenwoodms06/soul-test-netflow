"""Verification against the textbook closed-form fuel-pin temperature
decomposition (Todreas & Kazimi, *Nuclear Systems I*; El-Wakil,
*Nuclear Heat Transport*; Incropera conduction forms).

This is a *verification* test (against the analytical solution the field
uses), not a *validation* test (against experiment). With constant
properties the network solver must reproduce each radial ΔT exactly.

Per unit length, linear power q' [W/m], built up from the coolant:
    ΔT_film = q' / (2π r_co h)
    ΔT_clad = q' ln(r_co/r_ci) / (2π k_clad)
    ΔT_gap  = q' ln(r_ci/r_p) / (2π k_gap)      (conduction-only gap)
    ΔT_fuel = q' / (4π k_fuel)                    (solid cylinder, uniform gen)
"""

import math

import pytest

from netflow import Network
from netflow.core.node import Node
from netflow.plugins.thermal import (
    Constant,
    ContactResistance,
    CylindricalConduction,
)
from netflow.plugins.thermal.components import _PelletConduction


def test_closed_form_radial_decomposition():
    qp = 18000.0          # W/m
    L = 1.0
    r_p, r_ci, r_co = 4.10e-3, 4.185e-3, 4.75e-3
    k_fuel, k_gap, k_clad = 3.0, 0.25, 17.0
    h = 30000.0
    T_cool = 580.0

    A_co = 2 * math.pi * r_co * L
    R_film = 1.0 / (h * A_co)

    dT_film = qp / (2 * math.pi * r_co * h)
    dT_clad = qp * math.log(r_co / r_ci) / (2 * math.pi * k_clad)
    dT_gap = qp * math.log(r_ci / r_p) / (2 * math.pi * k_gap)
    dT_fuel = qp / (4 * math.pi * k_fuel)
    T_center_analytic = T_cool + dT_film + dT_clad + dT_gap + dT_fuel

    net = Network()
    net.add_node(Node(id="center", source=qp * L))
    net.add_node(Node(id="psurf"))
    net.add_node(Node(id="cin"))
    net.add_node(Node(id="cout"))
    net.add_node(Node(id="cool", fixed=T_cool))
    net.add_edge(_PelletConduction("center", "psurf", L=L, k=Constant(k_fuel)))
    net.add_edge(CylindricalConduction("psurf", "cin",
                                       r_i=r_p, r_o=r_ci, L=L, k=Constant(k_gap)))
    net.add_edge(CylindricalConduction("cin", "cout",
                                       r_i=r_ci, r_o=r_co, L=L, k=Constant(k_clad)))
    net.add_edge(ContactResistance("cout", "cool", R=R_film))

    res = net.solve_steady(tol=1e-12, max_iter=50)
    T = res.states

    assert math.isclose(T["cout"] - T_cool, dT_film, rel_tol=1e-9)
    assert math.isclose(T["cin"] - T["cout"], dT_clad, rel_tol=1e-9)
    assert math.isclose(T["psurf"] - T["cin"], dT_gap, rel_tol=1e-9)
    assert math.isclose(T["center"] - T["psurf"], dT_fuel, rel_tol=1e-9)
    assert math.isclose(T["center"], T_center_analytic, rel_tol=1e-9)
