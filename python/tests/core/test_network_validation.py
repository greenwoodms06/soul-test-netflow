"""Network validation and BC error handling."""

import pytest

from netflow import Network, Node
from netflow.core.exceptions import BadBC, DisconnectedGraph
from netflow.demo import LinearResistor


def test_duplicate_node_id_rejected():
    net = Network()
    net.add_node(Node(id="a"))
    with pytest.raises(ValueError, match="duplicate"):
        net.add_node(Node(id="a"))


def test_edge_endpoint_must_exist():
    net = Network()
    net.add_node(Node(id="a"))
    with pytest.raises(KeyError):
        net.add_edge(LinearResistor("a", "b", R=1.0))


def test_dirichlet_plus_source_rejected():
    with pytest.raises(BadBC, match="cannot both be set"):
        net = Network()
        net.add_node(Node(id="a", fixed=300.0, source=5.0))


def test_no_dirichlet_raises_on_solve():
    net = Network()
    net.add_node(Node(id="a"))
    net.add_node(Node(id="b"))
    net.add_edge(LinearResistor("a", "b", R=1.0))
    with pytest.raises(BadBC, match="no Dirichlet"):
        net.solve_steady()


def test_disconnected_interior_node():
    net = Network()
    net.add_node(Node(id="dh", fixed=10.0))
    net.add_node(Node(id="dc", fixed=0.0))
    net.add_node(Node(id="mid"))
    net.add_node(Node(id="orphan"))   # not connected to anything
    net.add_edge(LinearResistor("dh", "mid", R=1.0))
    net.add_edge(LinearResistor("mid", "dc", R=1.0))
    with pytest.raises(DisconnectedGraph) as exc:
        net.solve_steady()
    assert "orphan" in str(exc.value)
