"""Optional visualization helpers — requires ``networkx`` and ``matplotlib``.

Kept out of the core because the core has zero domain or viz imports.
Importing this module is allowed because it is *peer* to the core: it
reads ``netflow.core`` public API only, and is gated behind the
``[viz]`` extra in ``pyproject.toml``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import networkx as nx
    import matplotlib.pyplot as plt
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "netflow.viz requires networkx and matplotlib. "
        "Install with: pip install 'netflow[viz]'"
    ) from exc

if TYPE_CHECKING:
    from netflow.core.network import Network
    from netflow.core.result import Result


def to_networkx(network: "Network") -> "nx.MultiDiGraph":
    """Convert a Network to a ``networkx.MultiDiGraph`` for inspection / drawing.

    Node attributes: ``fixed``, ``source``, ``capacity``, ``state0``.
    Edge attributes: ``edge_type`` (class name), ``edge_obj`` (the Edge instance).
    Multi-edges are preserved (parallel edges between the same pair of nodes).
    """
    g: "nx.MultiDiGraph" = nx.MultiDiGraph()
    for nid, node in network.nodes.items():
        g.add_node(
            nid,
            fixed=node.fixed,
            source=node.source,
            capacity=node.capacity,
            state0=node.state0,
        )
    for e in network.edges:
        g.add_edge(
            e.a, e.b,
            edge_type=type(e).__name__,
            edge_obj=e,
        )
    return g


def draw_network(
    network: "Network",
    result: "Result | None" = None,
    *,
    ax=None,
    layout: str = "spring",
    node_label_fmt: str = "{nid}\n{state:.1f}",
    figsize: tuple[float, float] = (8.0, 6.0),
    title: str | None = None,
):
    """Draw the network as a labeled graph.

    Parameters
    ----------
    network :
        The Network to draw.
    result :
        Optional ``Result`` — if supplied, node labels include the
        solved state and Dirichlet nodes are highlighted.
    layout :
        ``"spring"`` (default), ``"kamada_kawai"``, ``"circular"``,
        or ``"shell"``.
    """
    g = to_networkx(network)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    layouts = {
        "spring": nx.spring_layout,
        "kamada_kawai": nx.kamada_kawai_layout,
        "circular": nx.circular_layout,
        "shell": nx.shell_layout,
    }
    if layout not in layouts:
        raise ValueError(f"unknown layout {layout!r}; pick from {list(layouts)}")
    pos = layouts[layout](g)

    # Color nodes: Dirichlet = orange, Neumann (source != 0) = green, interior = lightblue
    node_colors = []
    for nid in g.nodes:
        attrs = g.nodes[nid]
        if attrs["fixed"] is not None:
            node_colors.append("#ff9966")    # Dirichlet
        elif attrs["source"] != 0.0:
            node_colors.append("#66cc66")    # Neumann source
        else:
            node_colors.append("#99ccff")    # Interior

    nx.draw_networkx_nodes(g, pos, ax=ax, node_color=node_colors,
                           node_size=900, edgecolors="black", linewidths=0.5)
    nx.draw_networkx_edges(g, pos, ax=ax, arrows=True,
                           arrowstyle="-|>", arrowsize=15,
                           width=1.2, edge_color="#555555",
                           connectionstyle="arc3,rad=0.08")

    # Labels
    if result is not None:
        labels = {
            nid: node_label_fmt.format(nid=nid, state=result.states[nid])
            for nid in g.nodes
        }
    else:
        labels = {nid: nid for nid in g.nodes}
    nx.draw_networkx_labels(g, pos, labels=labels, ax=ax, font_size=8)

    # Edge type labels (only show if not too crowded). Multi-edges are
    # joined with " / " so parallel paths (e.g. conduction || radiation)
    # both appear. Leading underscores on internal class names are
    # stripped for display.
    if len(g.edges) <= 25:
        collapsed: dict[tuple[str, str], str] = {}
        for u, v, _k, d in g.edges(keys=True, data=True):
            display = d["edge_type"].lstrip("_")
            key = (u, v)
            collapsed[key] = (
                collapsed[key] + " / " + display if key in collapsed else display
            )
        nx.draw_networkx_edge_labels(
            g, pos, edge_labels=collapsed,
            ax=ax, font_size=6, font_color="#444444",
        )

    if title:
        ax.set_title(title)
    ax.set_axis_off()

    # Legend
    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor="#ff9966", edgecolor="black", label="Dirichlet (fixed)"),
        Patch(facecolor="#66cc66", edgecolor="black", label="Neumann (source)"),
        Patch(facecolor="#99ccff", edgecolor="black", label="Interior (unknown)"),
    ]
    ax.legend(handles=legend_elems, loc="lower right", fontsize=8, framealpha=0.9)
    return ax


__all__ = ["to_networkx", "draw_network"]
