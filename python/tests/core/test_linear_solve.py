"""Analytical linear-solve tests: series, parallel, mesh."""

import math

import numpy as np
import pytest

from netflow import Network, Node
from netflow.demo import LinearResistor, build_resistor_mesh


def test_series_chain_three_resistors():
    """T_hot=12, three R=1 resistors in series to T_cold=0.
    Interior nodes at 8 and 4."""
    net = Network()
    net.add_node(Node(id="h", fixed=12.0))
    net.add_node(Node(id="m1"))
    net.add_node(Node(id="m2"))
    net.add_node(Node(id="c", fixed=0.0))
    net.add_edge(LinearResistor("h", "m1", R=1.0))
    net.add_edge(LinearResistor("m1", "m2", R=1.0))
    net.add_edge(LinearResistor("m2", "c", R=1.0))
    res = net.solve_steady()
    assert res.converged
    assert res.n_iter == 1                          # exact in one Newton step
    assert math.isclose(res.states["m1"], 8.0)
    assert math.isclose(res.states["m2"], 4.0)


def test_parallel_resistors_to_single_mid():
    """Two parallel R=2 resistors between T_hot=10 and a midpoint, then R=1 to T_cold=0.
    R_parallel = 1; total = 2; Q = 5; T_mid = 5."""
    net = Network()
    net.add_node(Node(id="h", fixed=10.0))
    net.add_node(Node(id="m"))
    net.add_node(Node(id="c", fixed=0.0))
    net.add_edge(LinearResistor("h", "m", R=2.0))
    net.add_edge(LinearResistor("h", "m", R=2.0))
    net.add_edge(LinearResistor("m", "c", R=1.0))
    res = net.solve_steady()
    assert res.converged
    assert math.isclose(res.states["m"], 5.0, abs_tol=1e-9)


def test_neumann_source_only():
    """Single interior node with Neumann source +Q feeding into a resistor to ground.
    F: Q - flux_out = 0 => flux = Q => (T - 0)/R = Q => T = Q*R."""
    net = Network()
    net.add_node(Node(id="g", fixed=0.0))
    net.add_node(Node(id="hot", source=5.0))
    net.add_edge(LinearResistor("hot", "g", R=2.0))
    res = net.solve_steady()
    assert res.converged
    assert math.isclose(res.states["hot"], 10.0)


def test_resistor_mesh_grid_symmetry():
    """A symmetric NxN mesh between left & right Dirichlet boundaries should
    show linear potential drop column-by-column."""
    N = 5
    net = build_resistor_mesh(rows=N, cols=N, R=1.0,
                              left_state=10.0, right_state=0.0)
    res = net.solve_steady()
    assert res.converged
    # All nodes in the same column have the same state (symmetry)
    cols_states = {j: [] for j in range(N)}
    for i in range(N):
        for j in range(N):
            cols_states[j].append(res.states[f"n_{i}_{j}"])
    for j, vals in cols_states.items():
        assert np.allclose(vals, vals[0], atol=1e-9), f"column {j} not symmetric: {vals}"
    # Column states are 10, 7.5, 5, 2.5, 0
    expected = np.linspace(10.0, 0.0, N)
    actual = np.array([cols_states[j][0] for j in range(N)])
    assert np.allclose(actual, expected, atol=1e-9)


def test_edge_flux_lookup():
    """Result.edge_flux returns the correct flux for the given edge object."""
    net = Network()
    net.add_node(Node(id="h", fixed=8.0))
    net.add_node(Node(id="c", fixed=0.0))
    e = LinearResistor("h", "c", R=4.0)
    net.add_edge(e)
    res = net.solve_steady()
    assert math.isclose(res.edge_flux(e), 2.0)      # 8/4
