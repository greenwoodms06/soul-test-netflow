"""Unit tests for Node and Edge basics."""

import pytest

from netflow import Node, Edge


def test_node_defaults():
    n = Node(id="a")
    assert n.id == "a"
    assert n.fixed is None
    assert n.source == 0.0
    assert n.capacity is None
    assert n.state0 == 0.0
    assert n.meta == {}
    assert n.is_dirichlet is False


def test_node_dirichlet_flag():
    n = Node(id="b", fixed=300.0)
    assert n.is_dirichlet is True


def test_edge_rejects_self_loop():
    class _E(Edge):
        def flux(self, a, b):
            return 0.0

    with pytest.raises(ValueError, match="must differ"):
        _E("x", "x")


def test_edge_default_jacobian_is_none():
    class _E(Edge):
        def flux(self, a, b):
            return a - b

    e = _E("x", "y")
    assert e.jacobian(1.0, 0.0) is None
