"""Neutron-diffusion edges — built on netflow.core public API only.

Both edges are linear in flux (the nonlinearity of criticality lives in
the power-iteration outer loop, not in any edge), so the core's Newton
solver converges each driven solve in one step.
"""

from __future__ import annotations

from netflow.core.edge import Edge


class Diffusion(Edge):
    """Fick's-law neutron leakage between two cells.

        flux_{a→b} = (D · A / Δ) · (φ_a − φ_b)

    Structurally identical to thermal conduction — D is the diffusion
    coefficient (cm), A the interface area (cm²), Δ the cell-center
    spacing (cm). The combined ``coupling = D·A/Δ`` may be passed
    directly.
    """

    def __init__(self, a: str, b: str, *, coupling: float):
        super().__init__(a, b)
        if coupling <= 0:
            raise ValueError("coupling (D·A/Δ) must be positive")
        self.coupling = float(coupling)

    def flux(self, phi_a: float, phi_b: float) -> float:
        return self.coupling * (phi_a - phi_b)

    def jacobian(self, phi_a: float, phi_b: float) -> tuple[float, float]:
        return (self.coupling, -self.coupling)


class Absorption(Edge):
    """Neutron removal proportional to local flux, as an edge to a φ=0
    ground node.

        flux_{cell→ground} = (Σa · V) · (φ_cell − 0) = Σa·V·φ_cell

    The ``ground`` node must be a Dirichlet node fixed at 0. This is the
    network idiom for a "loss proportional to state" (the same trick a
    thermal model would use for a volumetric heat sink).
    """

    def __init__(self, cell: str, ground: str, *, removal: float):
        super().__init__(cell, ground)
        if removal <= 0:
            raise ValueError("removal (Σa·V) must be positive")
        self.removal = float(removal)

    def flux(self, phi_cell: float, phi_ground: float) -> float:
        return self.removal * (phi_cell - phi_ground)

    def jacobian(self, phi_cell: float, phi_ground: float) -> tuple[float, float]:
        return (self.removal, -self.removal)
