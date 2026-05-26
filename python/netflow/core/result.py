"""Result — the structured return value from ``Network.solve_steady``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from netflow.core.edge import Edge


@dataclass(frozen=True)
class Result:
    """Outcome of a ``solve_steady`` call.

    Immutable so that solving twice returns two distinct Results.
    """

    states: dict[str, float]
    edge_fluxes: list[float]
    edge_index: dict[int, int] = field(default_factory=dict)
    converged: bool = False
    n_iter: int = 0
    residual_history: np.ndarray = field(default_factory=lambda: np.array([]))
    method: str = "newton"
    elapsed_s: float = 0.0
    damping_history: tuple[float, ...] = ()

    def state_array(self, order: list[str] | None = None) -> np.ndarray:
        """Return states as a numpy array.

        Parameters
        ----------
        order :
            If given, return states in this order. Otherwise insertion
            order of ``self.states``.
        """
        if order is None:
            return np.array(list(self.states.values()))
        return np.array([self.states[k] for k in order])

    def edge_flux(self, edge: "Edge") -> float:
        """Return the converged flux through ``edge`` (by identity).

        Looks up the edge by Python ``id`` — the same object the caller
        passed to ``Network.add_edge``. Constructing a fresh Edge with
        the same endpoints will not match.
        """
        try:
            i = self.edge_index[id(edge)]
        except KeyError as exc:
            raise KeyError(
                "edge not found in this Result — was it part of the solved Network?"
            ) from exc
        return self.edge_fluxes[i]

    def __repr__(self) -> str:
        return (
            f"Result(converged={self.converged}, n_iter={self.n_iter}, "
            f"method={self.method!r}, n_states={len(self.states)}, "
            f"||F||_final={self.residual_history[-1] if len(self.residual_history) else float('nan'):.3e})"
        )
