"""Nonlinear solve tests using a synthetic cubic edge."""

import math

import numpy as np
import pytest

from netflow import Edge, Network, Node


class CubicEdge(Edge):
    """flux = k * (sa^3 - sb^3). Analytic jacobian. Strongly nonlinear."""

    def __init__(self, a, b, k=1.0):
        super().__init__(a, b)
        self.k = k

    def flux(self, sa, sb):
        return self.k * (sa**3 - sb**3)

    def jacobian(self, sa, sb):
        return (3 * self.k * sa**2, -3 * self.k * sb**2)


class CubicEdgeNoJac(Edge):
    """Same as CubicEdge but no jacobian — exercises Picard fallback."""

    def __init__(self, a, b, k=1.0):
        super().__init__(a, b)
        self.k = k

    def flux(self, sa, sb):
        return self.k * (sa**3 - sb**3)


def test_cubic_series_newton():
    """T_hot=2, R cubic R cubic, T_cold=0.
    For series with f = k(sa^3 - sb^3) = constant Q:
        Q = k(2^3 - x^3) = k(x^3 - 0^3)  =>  x^3 = 4  =>  x = 4^(1/3)."""
    net = Network()
    net.add_node(Node(id="h", fixed=2.0))
    net.add_node(Node(id="m", state0=1.0))
    net.add_node(Node(id="c", fixed=0.0))
    net.add_edge(CubicEdge("h", "m", k=1.0))
    net.add_edge(CubicEdge("m", "c", k=1.0))
    res = net.solve_steady()
    assert res.converged
    assert math.isclose(res.states["m"], 4.0 ** (1 / 3), rel_tol=1e-8)
    assert res.method == "newton"


def test_cubic_series_picard_fallback():
    """Same problem with edges that lack jacobian → Newton must downgrade."""
    net = Network()
    net.add_node(Node(id="h", fixed=2.0))
    net.add_node(Node(id="m", state0=1.0))
    net.add_node(Node(id="c", fixed=0.0))
    net.add_edge(CubicEdgeNoJac("h", "m", k=1.0))
    net.add_edge(CubicEdgeNoJac("m", "c", k=1.0))
    res = net.solve_steady()
    assert res.converged
    assert math.isclose(res.states["m"], 4.0 ** (1 / 3), rel_tol=1e-6)
    assert "picard" in res.method  # newton+picard or picard


def test_explicit_picard_method():
    net = Network()
    net.add_node(Node(id="h", fixed=2.0))
    net.add_node(Node(id="m", state0=1.0))
    net.add_node(Node(id="c", fixed=0.0))
    net.add_edge(CubicEdge("h", "m", k=1.0))
    net.add_edge(CubicEdge("m", "c", k=1.0))
    res = net.solve_steady(method="picard")
    assert res.converged
    assert math.isclose(res.states["m"], 4.0 ** (1 / 3), rel_tol=1e-6)
    assert res.method == "picard"


def test_nonconvergence_returns_result_by_default():
    """Force divergence by setting max_iter absurdly low and bad initial guess."""
    net = Network()
    net.add_node(Node(id="h", fixed=10.0))
    net.add_node(Node(id="m", state0=-100.0))
    net.add_node(Node(id="c", fixed=0.0))
    net.add_edge(CubicEdge("h", "m", k=1.0))
    net.add_edge(CubicEdge("m", "c", k=1.0))
    res = net.solve_steady(max_iter=1, tol=1e-12)
    # 1 iter from initial guess of -100 is not enough — expect non-convergence
    assert res.converged is False
    assert len(res.residual_history) >= 1


def test_finite_difference_jacobian_agrees():
    """Analytic jacobian agrees with central-difference."""
    e = CubicEdge("a", "b", k=2.5)
    sa, sb = 1.7, 0.4
    h = 1e-6
    da_fd = (e.flux(sa + h, sb) - e.flux(sa - h, sb)) / (2 * h)
    db_fd = (e.flux(sa, sb + h) - e.flux(sa, sb - h)) / (2 * h)
    da, db = e.jacobian(sa, sb)
    assert math.isclose(da, da_fd, rel_tol=1e-6)
    assert math.isclose(db, db_fd, rel_tol=1e-6)
