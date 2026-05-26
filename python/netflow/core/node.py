"""Node — a vertex in the network."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """A vertex in a Network.

    Parameters
    ----------
    id :
        Unique identifier within a Network. Strings (not ints) so the value
        survives renaming, serialisation, and subgraph merging.
    fixed :
        Dirichlet boundary value. If set, this node's state is pinned and
        it is removed from the unknown vector.
    source :
        Neumann boundary source — external flux *into* the node
        (sign convention: positive = into).
    capacity :
        Lumped capacitance for transient solves. Stored only; ignored at
        steady state. Reserved as the transient-extension hook so adding
        ``solve_transient`` later does not require a data-model change.
    state0 :
        Initial guess for the unknown. Only used for interior nodes.
    meta :
        Plugin scratchpad. The core never reads this. Plugins may stash
        per-node metadata here (e.g. ``{"units": "K"}`` for the thermal
        plugin).
    """

    id: str
    fixed: float | None = None
    source: float = 0.0
    capacity: float | None = None
    state0: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def is_dirichlet(self) -> bool:
        return self.fixed is not None
