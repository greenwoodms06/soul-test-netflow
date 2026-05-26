"""netflow.hydraulic — incompressible pipe-network plugin.

The second domain plugin, built to test the project's founding claim:
that ``netflow.core`` is genuinely domain-agnostic. It uses ONLY the
public core API — no core changes — and demonstrates a third distinct
physics on the same solver.

State variable per node: pressure (Pa).
Flux: volumetric flow rate (m³/s), positive a → b.
Conservation: net flow into each interior node = 0 (mass continuity).

Boundary conditions:
- Dirichlet ``fixed`` = imposed pressure (e.g., a reservoir / tank).
- Neumann ``source`` = imposed volumetric flow injection (m³/s).

The headline edge is :class:`Pipe`, whose flux law is the turbulent
Darcy-Weisbach relation Q = sign(ΔP)·√(|ΔP|/K). Its Jacobian is
*singular at zero flow* — a genuinely harder nonlinearity than thermal
radiation, regularized with a small laminar-like core so Newton stays
stable.
"""

from netflow.plugins.hydraulic.edges import Pipe, LinearPipe

__all__ = ["Pipe", "LinearPipe"]
