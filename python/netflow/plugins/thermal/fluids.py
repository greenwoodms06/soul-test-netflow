"""Fluid thermophysical property providers.

Fluid ABC exposes (rho, mu, k, cp, Pr) as functions of (T, P).
Two concrete implementations:

* ``CoolPropFluid`` — wraps ``CoolProp.CoolProp.PropsSI``. Default for
  water/steam and all CoolProp-supported fluids. CoolProp is imported
  lazily so this module stays importable without the dependency.
* ``CallableFluid`` — user supplies plain callables; useful for custom
  fluids or fast simplified correlations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class Fluid(ABC):
    """Single-phase fluid with temperature/pressure dependent properties.

    All methods return SI: kg/m³ for density, Pa·s for viscosity,
    W/(m·K) for conductivity, J/(kg·K) for specific heat. Prandtl is
    dimensionless and defaults to ``μ·cp / k`` if not overridden.
    """

    @abstractmethod
    def rho(self, T: float, P: float) -> float: ...
    @abstractmethod
    def mu(self, T: float, P: float) -> float: ...
    @abstractmethod
    def k(self, T: float, P: float) -> float: ...
    @abstractmethod
    def cp(self, T: float, P: float) -> float: ...

    def Pr(self, T: float, P: float) -> float:
        return self.mu(T, P) * self.cp(T, P) / self.k(T, P)


class CoolPropFluid(Fluid):
    """Wraps ``CoolProp.PropsSI`` for an arbitrary fluid name.

    Includes an internal quantized (T, P) cache so repeated calls at
    nearby states reuse the same PropsSI lookup. The cache bucket size
    is set by ``cache_T_resolution`` (default 0.05 K) — well below the
    accuracy of single-phase correlations themselves. Set the
    resolution to 0 to disable caching.

    Parameters
    ----------
    name :
        CoolProp fluid identifier (``"Water"``, ``"R134a"``, …).
    default_P :
        Optional default pressure (Pa). If set, callers may pass
        ``P=None`` and the default is used.
    cache_T_resolution :
        Temperature bucket size (K) for the property cache. Two calls
        whose temperatures round to the same bucket return the same
        cached property tuple. ``0.0`` disables caching.
    """

    def __init__(
        self,
        name: str = "Water",
        default_P: float | None = None,
        cache_T_resolution: float = 0.05,
    ):
        self.name = name
        self.default_P = default_P
        self._cache_T_res = float(cache_T_resolution)
        # key = (T_bucket, P) → dict of all five properties
        self._cache: dict[tuple[float, float], dict[str, float]] = {}
        # Import lazily so the thermal package stays importable without CoolProp.
        try:
            from CoolProp.CoolProp import PropsSI  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "CoolPropFluid requires the CoolProp package. "
                "Install with: pip install CoolProp"
            ) from exc

    def _P(self, P: float | None) -> float:
        if P is None:
            if self.default_P is None:
                raise ValueError(
                    f"CoolPropFluid({self.name!r}) called without P and no default_P set"
                )
            return self.default_P
        return P

    _PROP_KEYS = ("D", "V", "L", "C", "PRANDTL")

    def _lookup_bucket(self, T_q: float, P_val: float) -> dict[str, float]:
        """Return properties at the *exact* bucket point (T_q, P_val), cached."""
        key = (T_q, P_val)
        if key not in self._cache:
            from CoolProp.CoolProp import PropsSI
            self._cache[key] = {
                k: float(PropsSI(k, "T", T_q, "P", P_val, self.name))
                for k in self._PROP_KEYS
            }
        return self._cache[key]

    def _props_all(self, T: float, P: float | None) -> dict[str, float]:
        """Return {D, V, L, C, PRANDTL} for (T, P).

        With cache enabled (``cache_T_resolution > 0``), look up the two
        adjacent buckets bracketing T and *linearly interpolate*. This
        makes the property function piecewise-linear in T — smooth and
        differentiable enough for Newton, while still amortising
        PropsSI calls across nearby states. Nearest-bucket (no interp)
        was tried and broke Newton convergence for non-identical
        workloads: bucket transitions create step discontinuities in
        h(T_film), and Newton oscillated between buckets without
        converging. Recorded in tally §17.
        """
        P_val = self._P(P)
        if self._cache_T_res > 0:
            import math
            T_lo = math.floor(T / self._cache_T_res) * self._cache_T_res
            T_hi = T_lo + self._cache_T_res
            alpha = (T - T_lo) / self._cache_T_res
            lo = self._lookup_bucket(T_lo, P_val)
            hi = self._lookup_bucket(T_hi, P_val)
            return {k: (1 - alpha) * lo[k] + alpha * hi[k] for k in self._PROP_KEYS}
        return self._lookup_bucket(T, P_val)

    def cache_stats(self) -> dict[str, int]:
        """Return cache size and a hint for tuning resolution."""
        return {"entries": len(self._cache), "T_resolution_K": self._cache_T_res}

    def clear_cache(self) -> None:
        self._cache.clear()

    def rho(self, T, P=None): return self._props_all(T, P)["D"]
    def mu(self, T, P=None): return self._props_all(T, P)["V"]
    def k(self, T, P=None): return self._props_all(T, P)["L"]
    def cp(self, T, P=None): return self._props_all(T, P)["C"]
    def Pr(self, T, P=None): return self._props_all(T, P)["PRANDTL"]


class CallableFluid(Fluid):
    """User supplies callables for each property.

    Each callable takes ``(T, P)`` and returns a float. Useful for
    custom fluids or simplified correlations.
    """

    def __init__(
        self,
        rho: Callable[[float, float], float],
        mu: Callable[[float, float], float],
        k: Callable[[float, float], float],
        cp: Callable[[float, float], float],
        Pr: Callable[[float, float], float] | None = None,
    ):
        self._rho = rho
        self._mu = mu
        self._k = k
        self._cp = cp
        self._Pr = Pr

    def rho(self, T, P): return self._rho(T, P)
    def mu(self, T, P): return self._mu(T, P)
    def k(self, T, P): return self._k(T, P)
    def cp(self, T, P): return self._cp(T, P)

    def Pr(self, T, P):
        if self._Pr is not None:
            return self._Pr(T, P)
        return super().Pr(T, P)
