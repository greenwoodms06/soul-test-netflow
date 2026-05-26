"""Network — container for Nodes and Edges, plus solve entry points."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Literal

import numpy as np

from netflow.core.assembly import IndexedNetwork
from netflow.core.edge import Edge
from netflow.core.exceptions import (
    BadBC,
    DisconnectedGraph,
    NonConvergence,
)
from netflow.core.node import Node
from netflow.core.result import Result
from netflow.core.solver import solve_newton, solve_picard

log = logging.getLogger("netflow.core.network")


@dataclass
class ValidationReport:
    ok: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Network:
    """A graph of Nodes and Edges with steady-state solve.

    Nodes are added by ``add_node`` and looked up by string ID.
    Edges are added by ``add_edge`` and reference endpoints by ID.
    Calling ``solve_steady`` freezes the network into an
    :class:`IndexedNetwork`, assembles, and runs the chosen solver.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []

    # ------------------------------------------------------------------ adds
    def add_node(self, node: Node) -> Node:
        if node.id in self._nodes:
            raise ValueError(f"duplicate node id: {node.id!r}")
        if node.is_dirichlet and node.source != 0.0:
            raise BadBC(
                f"node {node.id!r}: Dirichlet (fixed={node.fixed}) and "
                f"Neumann (source={node.source}) cannot both be set; "
                "a fixed-state node absorbs whatever flux is required."
            )
        self._nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> Edge:
        if edge.a not in self._nodes:
            raise KeyError(f"edge endpoint {edge.a!r} not in network")
        if edge.b not in self._nodes:
            raise KeyError(f"edge endpoint {edge.b!r} not in network")
        self._edges.append(edge)
        return edge

    def fix_node(self, node_id: str, value: float) -> None:
        """Mark an existing node as Dirichlet at ``value``.

        Useful after a component has emitted nodes via ``build()`` — the
        caller can pin one of the component's ports without reaching
        into the Node's private state.
        """
        if node_id not in self._nodes:
            raise KeyError(f"node {node_id!r} not in network")
        n = self._nodes[node_id]
        if n.source != 0.0:
            raise BadBC(
                f"node {node_id!r}: cannot fix (Dirichlet) a node with "
                f"a non-zero Neumann source ({n.source}); clear source first"
            )
        n.fixed = float(value)

    def set_source(self, node_id: str, value: float) -> None:
        """Set the Neumann source on an existing node.

        Adds (or replaces) the external flux into ``node_id`` (W or
        whatever the domain's flux units are). Cannot be combined with a
        Dirichlet BC on the same node.
        """
        if node_id not in self._nodes:
            raise KeyError(f"node {node_id!r} not in network")
        n = self._nodes[node_id]
        if n.is_dirichlet:
            raise BadBC(
                f"node {node_id!r}: cannot set source on a Dirichlet node; "
                "clear fixed first"
            )
        n.source = float(value)

    def merge_subgraph(
        self,
        nodes: Iterable[Node],
        edges: Iterable[Edge],
        prefix: str = "",
    ) -> dict[str, str]:
        """Add a batch of Nodes/Edges, optionally name-prefixed.

        Returns a map ``local_id -> global_id``. Edges' endpoint
        references are rewritten in place to use the prefixed IDs.
        """
        id_map: dict[str, str] = {}
        nodes = list(nodes)
        edges = list(edges)
        for n in nodes:
            new_id = f"{prefix}{n.id}" if prefix else n.id
            id_map[n.id] = new_id
            n.id = new_id
            self.add_node(n)
        for e in edges:
            if e.a in id_map:
                e.a = id_map[e.a]
            if e.b in id_map:
                e.b = id_map[e.b]
            self.add_edge(e)
        return id_map

    # -------------------------------------------------------------- inspection
    @property
    def nodes(self) -> dict[str, Node]:
        """Read-only access; mutate via add_node only."""
        return dict(self._nodes)

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    # --------------------------------------------------------------- validate
    def validate(self) -> ValidationReport:
        """Check structural invariants before solving."""
        warnings_: list[str] = []
        errors: list[str] = []

        # Every edge endpoint exists (re-check defensively)
        for e in self._edges:
            if e.a not in self._nodes:
                errors.append(f"edge {e!r}: endpoint a={e.a!r} not in network")
            if e.b not in self._nodes:
                errors.append(f"edge {e!r}: endpoint b={e.b!r} not in network")

        # At least one Dirichlet anywhere
        if not any(n.is_dirichlet for n in self._nodes.values()):
            errors.append(
                "no Dirichlet node in the network — the steady-state "
                "problem is undefined without at least one fixed state"
            )

        # Connectivity: every interior node must reach a Dirichlet via edges.
        # Build adjacency over nodes; do BFS from the union of Dirichlets.
        adj: dict[str, set[str]] = {nid: set() for nid in self._nodes}
        for e in self._edges:
            adj[e.a].add(e.b)
            adj[e.b].add(e.a)
        dirichlet_ids = {nid for nid, n in self._nodes.items() if n.is_dirichlet}
        seen = set(dirichlet_ids)
        frontier = list(dirichlet_ids)
        while frontier:
            cur = frontier.pop()
            for nbr in adj[cur]:
                if nbr not in seen:
                    seen.add(nbr)
                    frontier.append(nbr)
        unreachable = [
            nid for nid, n in self._nodes.items()
            if not n.is_dirichlet and nid not in seen
        ]
        if unreachable:
            errors.append(
                f"interior nodes with no path to any Dirichlet: {unreachable!r}"
            )

        return ValidationReport(
            ok=not errors, warnings=warnings_, errors=errors,
        )

    # ------------------------------------------------------------ index/solve
    def _index(self) -> IndexedNetwork:
        report = self.validate()
        if not report.ok:
            joined = "; ".join(report.errors)
            # "No Dirichlet at all" is the more fundamental error: the
            # disconnect check follows as a consequence. Prefer BadBC.
            if any("no Dirichlet" in e for e in report.errors):
                raise BadBC(joined)
            if any("path to any Dirichlet" in e for e in report.errors):
                unreachable: list[str] = []
                for err in report.errors:
                    if "path to any Dirichlet" in err:
                        start = err.find("[")
                        if start != -1:
                            try:
                                unreachable = list(eval(err[start:]))  # noqa: S307
                            except Exception:
                                pass
                raise DisconnectedGraph(joined, node_ids=unreachable)
            raise BadBC(joined)

        interior_ids = [nid for nid, n in self._nodes.items() if not n.is_dirichlet]
        interior_idx = {nid: i for i, nid in enumerate(interior_ids)}
        dirichlet = {
            nid: n.fixed for nid, n in self._nodes.items() if n.is_dirichlet
        }
        sources = np.array(
            [self._nodes[nid].source for nid in interior_ids], dtype=float
        )
        return IndexedNetwork(
            interior_ids=interior_ids,
            interior_idx=interior_idx,
            dirichlet=dirichlet,
            sources=sources,
            edges=list(self._edges),
            n=len(interior_ids),
        )

    def _initial_guess(self, idx: IndexedNetwork) -> np.ndarray:
        """Use per-node ``state0`` if given, else the mean of Dirichlet values."""
        if idx.n == 0:
            return np.zeros(0)
        if idx.dirichlet:
            default = float(np.mean(list(idx.dirichlet.values())))
        else:
            default = 0.0
        x0 = np.empty(idx.n, dtype=float)
        for nid, i in idx.interior_idx.items():
            n = self._nodes[nid]
            x0[i] = n.state0 if n.state0 != 0.0 else default
        return x0

    def solve_transient(
        self, t_span, *, y0=None, source_fn=None, t_eval=None,
        method: str = "BDF", rtol: float = 1e-4, atol: float = 1e-2,
        max_step=None,
    ):
        """Integrate the transient ODE C·dT/dt = F(T, t).

        Requires every interior node to have ``capacity > 0``.
        See :func:`netflow.core.transient.solve_transient` for details.
        """
        from netflow.core.transient import solve_transient as _solve
        return _solve(
            self, t_span, y0=y0, source_fn=source_fn, t_eval=t_eval,
            method=method, rtol=rtol, atol=atol, max_step=max_step,
        )

    def solve_steady(
        self,
        *,
        method: Literal["newton", "picard"] = "newton",
        tol: float = 1e-8,
        max_iter: int = 50,
        damping: float = 1.0,
        x0: dict[str, float] | None = None,
        raise_on_nonconverge: bool = False,
    ) -> Result:
        """Solve F(x) = 0 at steady state."""
        idx = self._index()

        guess = self._initial_guess(idx)
        if x0:
            for nid, v in x0.items():
                if nid in idx.interior_idx:
                    guess[idx.interior_idx[nid]] = v

        if method == "newton":
            x, info = solve_newton(
                idx, guess, tol=tol, max_iter=max_iter, damping=damping,
            )
        elif method == "picard":
            x, info = solve_picard(idx, guess, tol=tol, max_iter=max_iter)
        else:
            raise ValueError(f"unknown solve method: {method!r}")

        if not info.converged and raise_on_nonconverge:
            raise NonConvergence(
                f"{method} did not converge to tol={tol} in {info.n_iter} iterations "
                f"(||F||_final = {info.residual_history[-1]:.3e})",
                residual_history=np.array(info.residual_history),
                n_iter=info.n_iter,
            )

        # Build state dict (interior + Dirichlet)
        states: dict[str, float] = {}
        for nid, n in self._nodes.items():
            if n.is_dirichlet:
                states[nid] = float(n.fixed)
            else:
                states[nid] = float(x[idx.interior_idx[nid]])

        # Edge fluxes evaluated at converged state
        edge_fluxes: list[float] = []
        edge_index: dict[int, int] = {}
        for k, e in enumerate(self._edges):
            edge_index[id(e)] = k
            sa = states[e.a]
            sb = states[e.b]
            edge_fluxes.append(float(e.flux(sa, sb)))

        return Result(
            states=states,
            edge_fluxes=edge_fluxes,
            edge_index=edge_index,
            converged=info.converged,
            n_iter=info.n_iter,
            residual_history=np.array(info.residual_history),
            method=info.method,
            elapsed_s=info.elapsed_s,
            damping_history=tuple(info.damping_history),
        )
