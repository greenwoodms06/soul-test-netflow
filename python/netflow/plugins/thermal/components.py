"""Composable thermal components.

A component is anything with a ``build(network, prefix="")`` method that:
* adds the appropriate Nodes and Edges to the given Network, and
* returns a small dataclass of *ports* — named string node IDs that the
  caller wires into the rest of the model.

Components import only from ``netflow.core`` and the thermal plugin's
own public API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from netflow.core.edge import Edge
from netflow.core.network import Network
from netflow.core.node import Node
from netflow.plugins.thermal.edges import (
    ContactResistance,
    CylindricalConduction,
    Radiation,
    _k_value_and_slope,
)
from netflow.plugins.thermal.materials import Material


# ---------------------------------------------------------------------------
# Multilayer cylindrical wall
# ---------------------------------------------------------------------------

@dataclass
class CylindricalWallPorts:
    inner: str
    outer: str
    interfaces: list[str]    # interfaces[i] = node ID between layers i and i+1

    def interface(self, i: int) -> str:
        return self.interfaces[i]


class MultilayerCylindricalWall:
    """Multi-layer cylindrical wall (pipe, cladding stack, …).

    Parameters
    ----------
    layers :
        Sequence of ``(thickness_m, material_or_k)`` pairs from inner to outer.
        ``material_or_k`` is either a float (constant k) or a ``Material``.
    L :
        Axial length (m).
    r_inner :
        Inner radius (m).
    """

    def __init__(
        self,
        layers: Sequence[tuple[float, float | Material]],
        *,
        L: float,
        r_inner: float,
    ):
        if not layers:
            raise ValueError("MultilayerCylindricalWall: layers must be non-empty")
        if L <= 0 or r_inner <= 0:
            raise ValueError("L and r_inner must be positive")
        for thickness, _ in layers:
            if thickness <= 0:
                raise ValueError("layer thickness must be positive")
        self.layers = list(layers)
        self.L = float(L)
        self.r_inner = float(r_inner)

    def build(self, network: Network, prefix: str = "") -> CylindricalWallPorts:
        r = self.r_inner
        ids: list[str] = [f"{prefix}wall_r{r:.4g}"]
        network.add_node(Node(id=ids[0]))
        for i, (thickness, k) in enumerate(self.layers):
            r_next = r + thickness
            nid = f"{prefix}wall_r{r_next:.4g}"
            ids.append(nid)
            network.add_node(Node(id=nid))
            network.add_edge(CylindricalConduction(
                ids[i], ids[i + 1],
                r_i=r, r_o=r_next, L=self.L, k=k,
            ))
            r = r_next
        return CylindricalWallPorts(
            inner=ids[0],
            outer=ids[-1],
            interfaces=ids[1:-1],
        )


# ---------------------------------------------------------------------------
# Insulated pipe section
# ---------------------------------------------------------------------------

@dataclass
class InsulatedPipePorts:
    bore: str
    ambient: str
    pipe_outer: str


class InsulatedPipeSection:
    """Pipe wall + insulation. Sugar over MultilayerCylindricalWall.

    Parameters
    ----------
    pipe_ID :
        Inner diameter of the pipe (m).
    pipe_OD :
        Outer diameter of the pipe (m) (= inner diameter of insulation).
    pipe_material :
        Pipe material (float k or ``Material``).
    insulation_thickness :
        Radial thickness of insulation (m).
    insulation_material :
        Insulation material (float k or ``Material``).
    L :
        Axial length (m).
    """

    def __init__(
        self,
        *,
        pipe_ID: float,
        pipe_OD: float,
        pipe_material: float | Material,
        insulation_thickness: float,
        insulation_material: float | Material,
        L: float,
    ):
        if pipe_OD <= pipe_ID:
            raise ValueError("pipe_OD must exceed pipe_ID")
        self.pipe_ID = pipe_ID
        self.pipe_OD = pipe_OD
        self.pipe_material = pipe_material
        self.insulation_thickness = insulation_thickness
        self.insulation_material = insulation_material
        self.L = L

    def build(self, network: Network, prefix: str = "") -> InsulatedPipePorts:
        r_inner = self.pipe_ID / 2
        wall_thickness = (self.pipe_OD - self.pipe_ID) / 2
        wall = MultilayerCylindricalWall(
            layers=[
                (wall_thickness, self.pipe_material),
                (self.insulation_thickness, self.insulation_material),
            ],
            L=self.L,
            r_inner=r_inner,
        )
        ports = wall.build(network, prefix=prefix + "pipe_")
        return InsulatedPipePorts(
            bore=ports.inner,
            ambient=ports.outer,
            pipe_outer=ports.interface(0),
        )


# ---------------------------------------------------------------------------
# Fuel rod
# ---------------------------------------------------------------------------

class _PelletConduction(Edge):
    """Centerline-to-surface resistance for a solid cylinder with uniform
    volumetric heat generation.

    Analytical result for a solid cylinder of radius r with uniform q''':
        ΔT(centerline → surface) = q''' · r² / (4 · k)
    With q_lin = π · r² · q''' [W/m] this gives R_pellet = 1 / (4π · k · L).
    Thus the equivalent edge flux is:
        flux(T_c, T_s) = 4π · k(T_mean) · L · (T_c − T_s).
    """

    def __init__(self, a: str, b: str, *, L: float, k):
        super().__init__(a, b)
        if L <= 0:
            raise ValueError("L must be positive")
        self.L = float(L)
        self.k = k

    @property
    def geom_factor(self) -> float:
        return 4 * math.pi * self.L

    def flux(self, Ta, Tb):
        Tmean = 0.5 * (Ta + Tb)
        k_val, _ = _k_value_and_slope(self.k, Tmean)
        return k_val * self.geom_factor * (Ta - Tb)

    def jacobian(self, Ta, Tb):
        Tmean = 0.5 * (Ta + Tb)
        k_val, dkdT = _k_value_and_slope(self.k, Tmean)
        g = self.geom_factor
        sens = 0.5 * dkdT * g * (Ta - Tb)
        return (sens + k_val * g, sens - k_val * g)


@dataclass
class FuelRodPorts:
    centerline: str
    pellet_surface: str
    clad_inner: str
    clad_outer: str


class FuelRod:
    """Cylindrical fuel rod: pellet + parallel gas/radiation gap + clad.

    Parameters
    ----------
    r_pellet :
        Pellet outer radius (m).
    gap_thickness :
        Radial gap between pellet and clad inner surface (m).
    r_clad_outer :
        Clad outer radius (m). Must exceed r_pellet + gap_thickness.
    L :
        Active length (m).
    fuel_material :
        Material of the fuel (``UO2`` by default elsewhere; here required).
    clad_material :
        Material of the clad (``Zircaloy4`` typically).
    gap_material :
        Material in the gap for gas conduction (``Helium_gap`` typically).
    gap_emissivity :
        Effective emissivity for radiation across the gap (0 disables rad).
    q_lin :
        Linear power (W/m). Applied as Neumann source at the centerline.
    """

    def __init__(
        self,
        *,
        r_pellet: float,
        gap_thickness: float,
        r_clad_outer: float,
        L: float,
        fuel_material: Material,
        clad_material: float | Material,
        gap_material: float | Material,
        gap_emissivity: float = 0.85,
        q_lin: float = 0.0,
        gap_conductance: float | None = None,
    ):
        r_clad_inner = r_pellet + gap_thickness
        if r_clad_outer <= r_clad_inner:
            raise ValueError("r_clad_outer must exceed r_pellet + gap_thickness")
        if gap_thickness <= 0:
            raise ValueError("gap_thickness must be positive")
        self.r_pellet = float(r_pellet)
        self.gap_thickness = float(gap_thickness)
        self.r_clad_inner = r_clad_inner
        self.r_clad_outer = float(r_clad_outer)
        self.L = float(L)
        self.fuel_material = fuel_material
        self.clad_material = clad_material
        self.gap_material = gap_material
        self.gap_emissivity = float(gap_emissivity)
        self.q_lin = float(q_lin)
        # If set, model the gap with an *empirical* gap conductance
        # h_gap [W/m²K] (Ross-Stoute style, includes contact + jump-distance)
        # instead of pure geometric He conduction. Geometric conduction
        # under-predicts BOL gap conductance and over-predicts fuel
        # centerline T by ~200 K (see tally §25/§26). Validated tools
        # (FRAPCON/BISON) use this empirical form; supply it for
        # realistic absolute fuel temperatures.
        self.gap_conductance = (
            float(gap_conductance) if gap_conductance is not None else None
        )

    def build(self, network: Network, prefix: str = "") -> FuelRodPorts:
        cl = f"{prefix}centerline"
        ps = f"{prefix}pellet_surface"
        ci = f"{prefix}clad_inner"
        co = f"{prefix}clad_outer"

        Q_source = self.q_lin * self.L     # total power deposited

        # Capacities for transient solves. Lumped per-slice mass × cp,
        # split across nodes representing each material region.
        m_pellet = math.pi * self.r_pellet ** 2 * self.L * 10900.0  # ρ_UO2
        cp_pellet = 300.0
        C_pellet = m_pellet * cp_pellet     # all pellet mass at centerline
                                            # (lumped, since pellet_surface is
                                            # a thin interface)
        m_clad = math.pi * (self.r_clad_outer**2 - self.r_clad_inner**2) \
                 * self.L * 6500.0           # ρ_Zr
        cp_clad = 285.0
        C_clad = m_clad * cp_clad           # split half/half across clad nodes

        # Small surface capacities to avoid DAE; ~1% of bulk to keep them
        # algebraic-fast without breaking the ODE integrator.
        C_surface = max(C_pellet, C_clad) * 1e-3

        network.add_node(Node(id=cl, source=Q_source, capacity=C_pellet))
        network.add_node(Node(id=ps, capacity=C_surface))
        network.add_node(Node(id=ci, capacity=0.5 * C_clad))
        network.add_node(Node(id=co, capacity=0.5 * C_clad))

        # Pellet: centerline -> pellet_surface (analytic solid-cylinder Q gen)
        network.add_edge(_PelletConduction(
            cl, ps, L=self.L, k=self.fuel_material,
        ))

        # Gap: either an empirical gap conductance (preferred for realistic
        # absolute fuel T) or geometric He conduction + radiation.
        gap_area = 2 * math.pi * self.r_pellet * self.L
        if self.gap_conductance is not None:
            # Empirical h_gap: R = 1 / (h_gap · A_gap). This already folds
            # in gas conduction, solid contact, and radiation, so we do
            # NOT add a separate radiation edge here.
            network.add_edge(ContactResistance(
                ps, ci, R=1.0 / (self.gap_conductance * gap_area),
            ))
        else:
            # Geometric model: parallel gas conduction + gray radiation.
            network.add_edge(CylindricalConduction(
                ps, ci,
                r_i=self.r_pellet, r_o=self.r_clad_inner,
                L=self.L, k=self.gap_material,
            ))
            if self.gap_emissivity > 0:
                network.add_edge(Radiation(
                    ps, ci,
                    emissivity=self.gap_emissivity,
                    area=gap_area,
                    view_factor=1.0,
                ))

        # Clad: clad_inner -> clad_outer
        network.add_edge(CylindricalConduction(
            ci, co,
            r_i=self.r_clad_inner, r_o=self.r_clad_outer,
            L=self.L, k=self.clad_material,
        ))

        return FuelRodPorts(
            centerline=cl, pellet_surface=ps, clad_inner=ci, clad_outer=co,
        )


# ---------------------------------------------------------------------------
# Generic series builder
# ---------------------------------------------------------------------------

@dataclass
class ResistanceStackPorts:
    upstream: str
    downstream: str
    nodes: list[str]


class ResistanceStack:
    """Build a series chain of pre-instantiated edges between auto-named nodes.

    Each edge is *re-targeted* — its ``a``/``b`` strings are overwritten
    so the edges form n_0 → n_1 → … → n_N. Useful for stacking arbitrary
    edge types (conduction + contact + fouling + …) without hand-naming
    intermediate nodes.

    Example
    -------
    >>> stack = ResistanceStack(
    ...     PlanarConduction("", "", L=0.005, k=k_SS, A=1.0),
    ...     ContactResistance("", "", R=1e-4),
    ...     PlanarConduction("", "", L=0.02, k=k_insul, A=1.0),
    ... )
    >>> ports = stack.build(net, prefix="wall_")
    >>> # ports.upstream and ports.downstream are the chain ends
    """

    def __init__(self, *edges: Edge):
        if not edges:
            raise ValueError("ResistanceStack needs at least one edge")
        self._edges = list(edges)

    def build(self, network: Network, prefix: str = "") -> ResistanceStackPorts:
        n_nodes = len(self._edges) + 1
        node_ids = [f"{prefix}stack_{i}" for i in range(n_nodes)]
        for nid in node_ids:
            network.add_node(Node(id=nid))
        for i, edge in enumerate(self._edges):
            edge.a = node_ids[i]
            edge.b = node_ids[i + 1]
            network.add_edge(edge)
        return ResistanceStackPorts(
            upstream=node_ids[0],
            downstream=node_ids[-1],
            nodes=node_ids,
        )
