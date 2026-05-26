"""Hydraulic pipe edges — incompressible flow as a function of pressure drop.

These import only from ``netflow.core`` (public API). No core changes are
needed to host a completely different physics — that is the point.
"""

from __future__ import annotations

import math

from netflow.core.edge import Edge


class Pipe(Edge):
    """Turbulent pipe flow (Darcy-Weisbach), state = pressure, flux = volumetric flow.

    The head-loss relation ΔP = K · Q · |Q| inverts to

        Q(P_a, P_b) = sign(ΔP) · √(|ΔP| / K),   ΔP = P_a − P_b

    where ``K`` [Pa·s²/m⁶] is the resistance coefficient
    K = f · L / D · ρ / (2 A²) (Darcy friction factor f, length L,
    diameter D, density ρ, area A) — or supplied directly.

    The Jacobian dQ/dΔP = 1 / (2 √(K |ΔP|)) is **singular at ΔP = 0**.
    This is a genuinely harder nonlinearity than thermal radiation. We
    regularize with a small laminar-like core of width ``dp_eps``: below
    that pressure drop the relation is linearized, keeping the flux and
    its derivative finite and continuous through zero. Standard practice
    in pipe-network solvers.
    """

    def __init__(self, a: str, b: str, *, K: float, dp_eps: float = 1.0):
        super().__init__(a, b)
        if K <= 0:
            raise ValueError("K must be positive")
        if dp_eps <= 0:
            raise ValueError("dp_eps must be positive")
        self.K = float(K)
        self.dp_eps = float(dp_eps)

    @classmethod
    def from_geometry(
        cls, a: str, b: str, *,
        L: float, D: float, friction_factor: float,
        rho: float = 998.0, dp_eps: float = 1.0,
    ) -> "Pipe":
        """Build K from pipe geometry: K = f·L/D · ρ/(2 A²)."""
        A = math.pi * D ** 2 / 4
        K = friction_factor * L / D * rho / (2 * A ** 2)
        return cls(a, b, K=K, dp_eps=dp_eps)

    def flux(self, P_a: float, P_b: float) -> float:
        dP = P_a - P_b
        if abs(dP) <= self.dp_eps:
            # Laminar-like linear core: match value & slope at ±dp_eps.
            # Q(dp_eps) = sqrt(dp_eps/K); linear slope = Q(dp_eps)/dp_eps.
            q_edge = math.sqrt(self.dp_eps / self.K)
            return q_edge * dP / self.dp_eps
        return math.copysign(math.sqrt(abs(dP) / self.K), dP)

    def jacobian(self, P_a: float, P_b: float) -> tuple[float, float]:
        dP = P_a - P_b
        if abs(dP) <= self.dp_eps:
            q_edge = math.sqrt(self.dp_eps / self.K)
            g = q_edge / self.dp_eps           # constant slope in the core
        else:
            g = 1.0 / (2.0 * math.sqrt(self.K * abs(dP)))
        return (g, -g)


class LinearPipe(Edge):
    """Laminar / linearized pipe: Q = (P_a − P_b) / R  (Hagen-Poiseuille form).

    The trivial linear case — same role as a resistor. Useful for
    creeping flow or as a sanity baseline.
    """

    def __init__(self, a: str, b: str, *, R: float):
        super().__init__(a, b)
        if R <= 0:
            raise ValueError("R must be positive")
        self.R = float(R)

    def flux(self, P_a: float, P_b: float) -> float:
        return (P_a - P_b) / self.R

    def jacobian(self, P_a: float, P_b: float) -> tuple[float, float]:
        g = 1.0 / self.R
        return (g, -g)
