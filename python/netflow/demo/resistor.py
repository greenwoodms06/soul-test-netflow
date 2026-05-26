"""Linear-resistor demo plugin.

A scalar resistance edge: ``flux = (state_a - state_b) / R``.
Used by the core test suite and the scaling benchmark; no domain
context, no third-party deps beyond numpy.
"""

from __future__ import annotations

from netflow.core.edge import Edge
from netflow.core.network import Network
from netflow.core.node import Node


class LinearResistor(Edge):
    """flux_{a→b} = (state_a − state_b) / R."""

    def __init__(self, a: str, b: str, R: float):
        super().__init__(a, b)
        if R <= 0:
            raise ValueError(f"R must be positive; got {R}")
        self.R = float(R)

    def flux(self, state_a: float, state_b: float) -> float:
        return (state_a - state_b) / self.R

    def jacobian(self, state_a: float, state_b: float) -> tuple[float, float]:
        g = 1.0 / self.R
        return (g, -g)


def build_resistor_mesh(
    rows: int,
    cols: int,
    *,
    R: float = 1.0,
    left_state: float = 1.0,
    right_state: float = 0.0,
    name_prefix: str = "n",
) -> Network:
    """Build an ``rows × cols`` resistor mesh.

    Left column is Dirichlet at ``left_state``; right column is Dirichlet
    at ``right_state``. Interior nodes are unknowns; every grid edge is a
    ``LinearResistor(R)``.

    Useful for benchmarks and as a known-solution analytical test
    (e.g., 1×N reduces to a series chain with closed-form answer).
    """
    if rows < 1 or cols < 2:
        raise ValueError("need rows>=1 and cols>=2")
    net = Network()
    for i in range(rows):
        for j in range(cols):
            nid = f"{name_prefix}_{i}_{j}"
            if j == 0:
                net.add_node(Node(id=nid, fixed=left_state))
            elif j == cols - 1:
                net.add_node(Node(id=nid, fixed=right_state))
            else:
                net.add_node(Node(id=nid))
    for i in range(rows):
        for j in range(cols):
            if j < cols - 1:
                net.add_edge(LinearResistor(
                    f"{name_prefix}_{i}_{j}", f"{name_prefix}_{i}_{j+1}", R=R,
                ))
            if i < rows - 1:
                net.add_edge(LinearResistor(
                    f"{name_prefix}_{i}_{j}", f"{name_prefix}_{i+1}_{j}", R=R,
                ))
    return net
