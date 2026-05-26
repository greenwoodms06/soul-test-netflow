"""netflow.neutronics — one-group neutron diffusion via power iteration.

The third domain plugin, and the deepest test of the core: neutron
diffusion is an *eigenvalue* problem (criticality k), not a driven
boundary-value problem. It is nonetheless solved on the UNCHANGED core
by **power iteration** — an outer loop in which each iteration is a
driven diffusion solve (which the core does natively), with the fission
source updated from the previous flux. The eigenvalue k emerges from the
outer-loop normalization.

This mirrors the "outer loop of core solves" pattern already used for
Picard multiphysics coupling — establishing it as the meta-abstraction
that lets a driven-BVP solver also handle eigenvalue and coupled
problems.

State variable per node: scalar neutron flux φ (arbitrary normalization).
Edges:
  * ``Diffusion`` — leakage between adjacent cells (Fick's law),
    structurally identical to thermal conduction.
  * ``Absorption`` — removal proportional to local flux, modeled as an
    edge to a φ=0 "ground" node (conductance Σa·V).
Fission source is a Neumann source updated each power iteration.
"""

from netflow.plugins.neutronics.edges import Diffusion, Absorption
from netflow.plugins.neutronics.solver import (
    power_iteration, PowerIterationResult, build_1group_slab,
)

__all__ = [
    "Diffusion", "Absorption",
    "power_iteration", "PowerIterationResult", "build_1group_slab",
]
