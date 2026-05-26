"""Edge — the protocol every plugin's flux primitives implement."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Edge(ABC):
    """Relate two endpoints' states to a scalar conserved flux a -> b.

    Sign convention: ``flux > 0`` means transport from ``a`` to ``b``.
    Energy/charge/etc. conservation at an interior node ``i`` is

        source_i + Σ flux_in − Σ flux_out = 0

    where an edge ``(a, b)`` contributes ``+flux`` to its ``b`` endpoint
    and ``−flux`` to its ``a`` endpoint.

    Subclasses must implement ``flux``. They *should* implement
    ``jacobian`` to enable Newton iteration; if omitted, the solver
    falls back to Picard fixed-point iteration on that edge.
    """

    def __init__(self, a: str, b: str):
        if a == b:
            raise ValueError(f"Edge endpoints must differ; got {a!r} twice")
        self.a = a
        self.b = b

    @abstractmethod
    def flux(self, state_a: float, state_b: float) -> float:
        """Return the flux a -> b for the given endpoint states."""

    def jacobian(
        self, state_a: float, state_b: float
    ) -> tuple[float, float] | None:
        """Return (∂flux/∂state_a, ∂flux/∂state_b).

        Default ``None`` signals the solver to fall back to Picard
        iteration. Subclasses override this when an analytic Jacobian
        is available.
        """
        return None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.a!r} -> {self.b!r})"
