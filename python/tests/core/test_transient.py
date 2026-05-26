"""Tests for Network.solve_transient — the time-dependent ODE solver."""

import math

import numpy as np
import pytest

from netflow import Network, Node
from netflow.demo import LinearResistor


def test_solve_transient_requires_capacity_on_every_interior_node():
    """A network with no capacities must refuse to run a transient."""
    net = Network()
    net.add_node(Node(id="hot", fixed=10.0))
    net.add_node(Node(id="mid"))   # no capacity
    net.add_node(Node(id="cold", fixed=0.0))
    net.add_edge(LinearResistor("hot", "mid", R=1.0))
    net.add_edge(LinearResistor("mid", "cold", R=1.0))
    with pytest.raises(ValueError, match="capacity"):
        net.solve_transient((0.0, 1.0))


def test_single_capacitor_relaxation():
    """One node with capacity C connected via R to a Dirichlet bath.

    Analytical: T(t) = T_bath + (T_0 − T_bath) · exp(−t/τ),  τ = RC.
    """
    R = 2.0       # K/W
    C = 5.0       # J/K
    tau = R * C   # = 10 s
    T_bath = 0.0
    T_0 = 100.0
    t_end = 30.0   # 3 time constants

    net = Network()
    net.add_node(Node(id="bath", fixed=T_bath))
    net.add_node(Node(id="x", capacity=C, state0=T_0))
    net.add_edge(LinearResistor("x", "bath", R=R))

    t_eval = np.linspace(0.0, t_end, 31)
    tr = net.solve_transient((0.0, t_end), y0={"x": T_0}, t_eval=t_eval,
                             rtol=1e-7, atol=1e-5)
    assert tr.converged

    T_x = tr.states["x"]
    expected = T_bath + (T_0 - T_bath) * np.exp(-tr.t / tau)
    # Relaxation to a Dirichlet bath — accurate to ~1e-4 with tight tols
    max_abs_err = float(np.max(np.abs(T_x - expected)))
    assert max_abs_err < 0.01, f"max error {max_abs_err}"


def test_two_capacitor_chain():
    """Bath─R1─[C1]─R2─[C2]─R3─bath. Should equilibrate to linear T profile
    between the two bath temperatures at long time."""
    R = 1.0
    C = 2.0
    T_left, T_right = 0.0, 100.0

    net = Network()
    net.add_node(Node(id="left", fixed=T_left))
    net.add_node(Node(id="x1", capacity=C, state0=50.0))
    net.add_node(Node(id="x2", capacity=C, state0=50.0))
    net.add_node(Node(id="right", fixed=T_right))
    net.add_edge(LinearResistor("left",  "x1", R=R))
    net.add_edge(LinearResistor("x1",    "x2", R=R))
    net.add_edge(LinearResistor("x2", "right", R=R))

    # Long enough to reach steady; 10 time constants for slowest mode
    tr = net.solve_transient((0.0, 100.0), t_eval=np.array([0.0, 100.0]),
                             rtol=1e-7, atol=1e-5)
    assert tr.converged
    # At steady state, T_x1 = T_left + (1/3)·(T_right − T_left) = 33.33
    # T_x2 = T_left + (2/3)·(T_right − T_left) = 66.66
    assert math.isclose(tr.states["x1"][-1], 100.0 / 3, abs_tol=0.01)
    assert math.isclose(tr.states["x2"][-1], 200.0 / 3, abs_tol=0.01)


def test_transient_reaches_steady_state():
    """Long transient should converge to the same answer as solve_steady."""
    R = 0.5
    C = 4.0
    T_bath = 25.0

    net = Network()
    net.add_node(Node(id="bath", fixed=T_bath))
    net.add_node(Node(id="hot", source=10.0, capacity=C, state0=0.0))
    net.add_edge(LinearResistor("hot", "bath", R=R))

    ss = net.solve_steady()
    T_ss = ss.states["hot"]

    tr = net.solve_transient((0.0, 50.0), t_eval=np.array([50.0]),
                             rtol=1e-7, atol=1e-6)
    assert tr.converged
    assert math.isclose(tr.states["hot"][-1], T_ss, abs_tol=0.001)


def test_time_varying_source_fn_invoked():
    """source_fn must be called with t and network; updates take effect."""
    net = Network()
    net.add_node(Node(id="bath", fixed=0.0))
    net.add_node(Node(id="x", source=0.0, capacity=1.0, state0=0.0))
    net.add_edge(LinearResistor("x", "bath", R=1e6))   # near-adiabatic

    invocations: list[float] = []

    def source_fn(t, network):
        invocations.append(t)
        # Step source: 1 W for t < 5, 0 otherwise
        network._nodes["x"].source = 1.0 if t < 5.0 else 0.0

    tr = net.solve_transient(
        (0.0, 10.0),
        source_fn=source_fn,
        t_eval=np.array([0.0, 2.5, 5.0, 7.5, 10.0]),
        rtol=1e-6, atol=1e-5,
    )
    assert tr.converged
    assert len(invocations) > 0
    # Adiabatic capacitor with 1 W for 5 s → ΔT = 5 K
    # After t=5 source vanishes, T holds (near-adiabatic) until t=10
    assert tr.states["x"][-1] > 4.9   # heated up
    assert tr.states["x"][-1] < 5.1   # but not significantly more after step
