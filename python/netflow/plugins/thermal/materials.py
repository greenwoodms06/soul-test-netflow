"""Solid-material thermal conductivity catalog.

Each Material exposes ``k(T) -> W/(m·K)`` and a validity range. Calls
outside the range emit a ``RangeWarning`` but still return a value so the
solver does not crash mid-iteration.

Correlations are simple polynomial / piecewise fits suitable for
pre-design work. Production-grade fidelity is the user's responsibility
(supply your own ``Material`` subclass or use ``Constant``).

References (validity ranges and coefficients):
  - SS316L: Touloukian Vol. 1, Mills "Heat Transfer" App.
  - Zircaloy-4: MATPRO / IAEA TECDOC-1496
  - UO2: Fink "Thermophysical properties of uranium dioxide" (2000)
  - Helium: Petersen DTU-289 (1970), low-T fits
  - Air: Mills App., 250–1000 K
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass


class RangeWarning(UserWarning):
    """Raised when a Material is evaluated outside its validity range."""


class Material(ABC):
    """Solid material with temperature-dependent thermal conductivity."""

    name: str = "<unset>"
    t_min: float = 0.0
    t_max: float = float("inf")

    @abstractmethod
    def k(self, T: float) -> float:
        """Return k(T) in W/(m·K)."""

    def _check_range(self, T: float) -> None:
        if T < self.t_min or T > self.t_max:
            warnings.warn(
                f"Material {self.name}: T={T:.1f} K outside validity range "
                f"[{self.t_min:.1f}, {self.t_max:.1f}] K",
                RangeWarning,
                stacklevel=3,
            )


@dataclass
class Constant(Material):
    """k(T) = constant. The escape hatch."""

    k_value: float
    name: str = "Constant"

    def k(self, T: float) -> float:
        return self.k_value


class SS316L(Material):
    """Linearised fit to 316L stainless data, 300–1000 K.

    k(T) ≈ 13.0 + 0.0150 * (T − 300)  W/(m·K).
    """

    name = "SS316L"
    t_min = 250.0
    t_max = 1100.0

    def k(self, T: float) -> float:
        self._check_range(T)
        return 13.0 + 0.0150 * (T - 300.0)


class Zircaloy4(Material):
    """Linearised fit, 300–1300 K.

    k(T) ≈ 12.6 + 0.0048 * (T − 300)  W/(m·K).
    """

    name = "Zircaloy-4"
    t_min = 250.0
    t_max = 1400.0

    def k(self, T: float) -> float:
        self._check_range(T)
        return 12.6 + 0.0048 * (T - 300.0)


class UO2(Material):
    """UO2 fuel — Fink fit (simplified), 300–3000 K.

    k(T) = 1 / (0.0375 + 2.165e-4 · T) + 4.715e9 / T² · exp(-16361/T)

    The first term dominates below ~2000 K; the second is the
    electronic (radiation) contribution at high T.
    """

    name = "UO2"
    t_min = 300.0
    t_max = 3000.0

    def k(self, T: float) -> float:
        import math
        self._check_range(T)
        phonon = 1.0 / (0.0375 + 2.165e-4 * T)
        electronic = 4.715e9 / (T * T) * math.exp(-16361.0 / T)
        return phonon + electronic


class _Helium(Material):
    """Helium gas-gap conductivity, atmospheric pressure.

    Sutherland-like fit, 200–1500 K:  k(T) ≈ 2.682e-3 · T^0.71  W/(m·K).
    Note: this is *gas* conductivity used for fuel-clad gap modeling;
    convection in the gap is neglected in lumped resistance form.
    """

    name = "Helium (gap)"
    t_min = 200.0
    t_max = 1500.0

    def k(self, T: float) -> float:
        self._check_range(T)
        return 2.682e-3 * (T ** 0.71)


Helium_gap = _Helium()


class _Air(Material):
    """Air thermal conductivity, 250–1000 K.

    Linearised: k(T) ≈ 0.0241 + 7.7e-5 · (T − 300)  W/(m·K).
    """

    name = "Air"
    t_min = 250.0
    t_max = 1000.0

    def k(self, T: float) -> float:
        self._check_range(T)
        return 0.0241 + 7.7e-5 * (T - 300.0)


Air = _Air()
