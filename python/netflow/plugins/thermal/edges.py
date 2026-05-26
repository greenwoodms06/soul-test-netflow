"""Thermal-network edge primitives.

State variable: temperature (K). Flux: heat rate (W). Sign convention
inherited from ``netflow.core.Edge``: positive flux is transport a→b.

All edges are linear except ``Radiation`` and any conduction edge
constructed with a ``Material`` (T-dependent k). ``ForcedConvection``
is linear in (Ta − Tb) but its conductance ``hA`` depends on film
temperature; we expose an analytic jacobian using the *current* h
(frozen for one Newton step), which is the standard approach.
"""

from __future__ import annotations

import math
from typing import Union

from netflow.core.edge import Edge
from netflow.plugins.thermal.fluids import Fluid
from netflow.plugins.thermal.materials import Material


STEFAN_BOLTZMANN = 5.670374419e-8   # W/(m²·K⁴)

KType = Union[float, "Material"]


# ---------------------------------------------------------------------------
# Conduction
# ---------------------------------------------------------------------------

def _k_value_and_slope(k: KType, T: float) -> tuple[float, float]:
    """Return (k, dk/dT) at temperature T.

    If k is a float, slope is 0. If k is a Material, slope is computed
    by central difference at T (h = 0.5 K).
    """
    if isinstance(k, Material):
        h = 0.5
        kT = k.k(T)
        kp = (k.k(T + h) - k.k(T - h)) / (2 * h)
        return kT, kp
    return float(k), 0.0


class PlanarConduction(Edge):
    """1-D planar conduction through a slab of thickness L, area A.

    flux = k(T_mean) · A · (Ta − Tb) / L
    """

    def __init__(self, a: str, b: str, *, L: float, k: KType, A: float):
        super().__init__(a, b)
        if L <= 0 or A <= 0:
            raise ValueError("L and A must be positive")
        self.L = float(L)
        self.A = float(A)
        self.k = k

    @property
    def geom_factor(self) -> float:
        return self.A / self.L

    def flux(self, Ta: float, Tb: float) -> float:
        T_mean = 0.5 * (Ta + Tb)
        k_val, _ = _k_value_and_slope(self.k, T_mean)
        return k_val * self.geom_factor * (Ta - Tb)

    def jacobian(self, Ta, Tb) -> tuple[float, float]:
        T_mean = 0.5 * (Ta + Tb)
        k_val, dkdT = _k_value_and_slope(self.k, T_mean)
        g = self.geom_factor
        # flux = k(T_mean) * g * (Ta - Tb)
        # d/dTa = g * (Ta - Tb) * 0.5 * dk/dT + k(T_mean) * g
        # d/dTb = g * (Ta - Tb) * 0.5 * dk/dT - k(T_mean) * g
        sensitivity = 0.5 * dkdT * g * (Ta - Tb)
        return (sensitivity + k_val * g, sensitivity - k_val * g)


class CylindricalConduction(Edge):
    """Radial conduction through a cylinder, inner r_i to outer r_o, length L.

    flux = 2π · L · k(T_mean) · (Ta − Tb) / ln(r_o / r_i)
    """

    def __init__(self, a: str, b: str, *, r_i: float, r_o: float,
                 L: float, k: KType):
        super().__init__(a, b)
        if not (0 < r_i < r_o):
            raise ValueError("require 0 < r_i < r_o")
        if L <= 0:
            raise ValueError("L must be positive")
        self.r_i = float(r_i)
        self.r_o = float(r_o)
        self.L = float(L)
        self.k = k

    @property
    def geom_factor(self) -> float:
        return 2 * math.pi * self.L / math.log(self.r_o / self.r_i)

    def flux(self, Ta, Tb):
        T_mean = 0.5 * (Ta + Tb)
        k_val, _ = _k_value_and_slope(self.k, T_mean)
        return k_val * self.geom_factor * (Ta - Tb)

    def jacobian(self, Ta, Tb):
        T_mean = 0.5 * (Ta + Tb)
        k_val, dkdT = _k_value_and_slope(self.k, T_mean)
        g = self.geom_factor
        sensitivity = 0.5 * dkdT * g * (Ta - Tb)
        return (sensitivity + k_val * g, sensitivity - k_val * g)


# ---------------------------------------------------------------------------
# Simple scalar resistances
# ---------------------------------------------------------------------------

class ContactResistance(Edge):
    """Constant contact/interface resistance.

    flux = (Ta − Tb) / R   (R in K/W)
    """

    def __init__(self, a: str, b: str, *, R: float):
        super().__init__(a, b)
        if R <= 0:
            raise ValueError("R must be positive")
        self.R = float(R)

    def flux(self, Ta, Tb):
        return (Ta - Tb) / self.R

    def jacobian(self, Ta, Tb):
        g = 1.0 / self.R
        return (g, -g)


class Fouling(Edge):
    """Fouling resistance applied to a surface of area A.

    R = Rf / A   (Rf is the area-specific fouling factor, m²·K/W)
    flux = A · (Ta − Tb) / Rf
    """

    def __init__(self, a: str, b: str, *, Rf: float, A: float):
        super().__init__(a, b)
        if Rf <= 0 or A <= 0:
            raise ValueError("Rf and A must be positive")
        self.Rf = float(Rf)
        self.A = float(A)

    def flux(self, Ta, Tb):
        return self.A / self.Rf * (Ta - Tb)

    def jacobian(self, Ta, Tb):
        g = self.A / self.Rf
        return (g, -g)


class UAEdge(Edge):
    """Overall-conductance edge: flux = UA · (Ta − Tb)."""

    def __init__(self, a: str, b: str, *, UA: float):
        super().__init__(a, b)
        if UA <= 0:
            raise ValueError("UA must be positive")
        self.UA = float(UA)

    def flux(self, Ta, Tb):
        return self.UA * (Ta - Tb)

    def jacobian(self, Ta, Tb):
        return (self.UA, -self.UA)


# ---------------------------------------------------------------------------
# Radiation
# ---------------------------------------------------------------------------

class Radiation(Edge):
    """Gray-body radiation between two surfaces.

    flux = σ · ε_eff · F · A · (Ta⁴ − Tb⁴)

    ε_eff is the effective emissivity for the configuration (the user
    provides this — e.g., for two long concentric cylinders with
    emissivities ε_i and ε_o, ε_eff = 1/(1/ε_i + (r_i/r_o)(1/ε_o − 1))).
    For a single surface to a black enclosure, ε_eff = ε_surface.

    View factor F defaults to 1 (small-surface-to-large-enclosure or
    parallel-plate limit).
    """

    def __init__(self, a: str, b: str, *,
                 emissivity: float, area: float, view_factor: float = 1.0):
        super().__init__(a, b)
        if not (0 < emissivity <= 1):
            raise ValueError("emissivity must be in (0, 1]")
        if area <= 0:
            raise ValueError("area must be positive")
        if not (0 < view_factor <= 1):
            raise ValueError("view_factor must be in (0, 1]")
        self.emissivity = float(emissivity)
        self.area = float(area)
        self.view_factor = float(view_factor)

    @property
    def _const(self) -> float:
        return STEFAN_BOLTZMANN * self.emissivity * self.area * self.view_factor

    def flux(self, Ta, Tb):
        return self._const * (Ta**4 - Tb**4)

    def jacobian(self, Ta, Tb):
        c = self._const
        return (4 * c * Ta**3, -4 * c * Tb**3)


# ---------------------------------------------------------------------------
# Forced convection (single-phase, tube-side)
# ---------------------------------------------------------------------------

def _nu_dittus_boelter(Re: float, Pr: float, heating: bool) -> float:
    """Dittus-Boelter correlation.

    Nu = 0.023 · Re^0.8 · Pr^n,  n = 0.4 (heating) or 0.3 (cooling).
    Valid for: Re > 10^4, 0.7 ≤ Pr ≤ 160, fully developed turbulent
    flow in smooth circular tubes.
    """
    n = 0.4 if heating else 0.3
    return 0.023 * (Re ** 0.8) * (Pr ** n)


def _nu_gnielinski(Re: float, Pr: float) -> float:
    """Gnielinski correlation — better than DB in 3000 ≤ Re ≤ 5·10⁶.

    Uses the Petukhov friction factor f = (0.79·ln(Re) − 1.64)^(−2).
    """
    f = (0.79 * math.log(Re) - 1.64) ** (-2)
    num = (f / 8.0) * (Re - 1000.0) * Pr
    den = 1.0 + 12.7 * math.sqrt(f / 8.0) * (Pr ** (2 / 3) - 1.0)
    return num / den


class CoolantAdvection(Edge):
    """1-D advection (upwind) of enthalpy between adjacent coolant slices.

    Models steady energy transport by mass flow from upstream node ``a``
    to downstream node ``b``:

        flux_{a→b} = mdot · cp(T_a) · T_a       [W]

    The flux depends only on the upstream temperature — this is the
    canonical upwind scheme. The jacobian is therefore one-sided:
    ``(mdot · cp, 0)`` (plus a small correction if cp is T-dependent).

    Why one-sided? Combining upwind advection edges into the netflow
    KCL gives, at interior coolant slice k with wall flux Q_w,k:

        F_k = Q_w,k + flux_in_from_k-1 − flux_out_to_k+1
            = Q_w,k + mdot·cp·T_{k-1} − mdot·cp·T_k
            = Q_w,k + mdot·cp·(T_{k-1} − T_k) = 0

        ⇒ T_k = T_{k-1} + Q_w,k / (mdot · cp)

    which is the correct 1-D energy balance.

    Boundary handling
    -----------------
    - Inlet: connect a Dirichlet node at ``T_inlet`` upstream of the
      first interior coolant slice.
    - Outlet: connect a Dirichlet "sink" node downstream of the last
      interior coolant slice. Its T value is irrelevant — the edge's
      flux depends only on the upstream T, so the sink absorbs the
      correct outflow regardless of its own state. Setting it to any
      reasonable value (e.g. T_inlet) is fine.

    Parameters
    ----------
    mdot : float
        Mass flow rate from a → b (kg/s). Must be positive.
    cp : float | Callable[[float], float]
        Specific heat. Either a constant or a callable cp(T). Evaluated
        at the upstream T.
    """

    def __init__(self, a: str, b: str, *, mdot: float, cp):
        super().__init__(a, b)
        if mdot <= 0:
            raise ValueError("mdot must be positive (upwind direction is a → b)")
        self.mdot = float(mdot)
        self.cp = cp

    def _cp(self, T: float) -> float:
        return self.cp(T) if callable(self.cp) else float(self.cp)

    def flux(self, T_a: float, T_b: float) -> float:
        return self.mdot * self._cp(T_a) * T_a

    def jacobian(self, T_a: float, T_b: float) -> tuple[float, float]:
        # df/dT_a = mdot · (cp + T_a · dcp/dT).  Approximate dcp/dT by
        # central difference if cp is callable; otherwise it's zero.
        cp_val = self._cp(T_a)
        if callable(self.cp):
            h = 0.5
            dcp_dT = (self._cp(T_a + h) - self._cp(T_a - h)) / (2 * h)
        else:
            dcp_dT = 0.0
        return (self.mdot * (cp_val + T_a * dcp_dT), 0.0)


class CoolantMixing(Edge):
    """Symmetric lateral enthalpy exchange between two coolant nodes
    at the same axial level — the "turbulent diffusive mixing"
    approximation used in pre-design subchannel models (e.g. simplified
    COBRA-style analysis without lateral mass flux).

        flux(T_a, T_b) = mdot_mix · cp · (T_a − T_b)

    Unlike :class:`CoolantAdvection` (asymmetric upwind), this edge is
    *symmetric*: energy leaves the hotter node and enters the cooler
    node at the same rate. No net lateral mass transfer; only
    enthalpy diffusion driven by turbulent eddies.

    Conservation. The flux is purely a function of (T_a − T_b);
    integrating around any closed lateral loop returns zero. Energy
    leaving a is exactly the energy entering b.

    Parameters
    ----------
    mdot_mix : float
        Effective mass-flow equivalent of the turbulent mixing
        (kg/s). Typical pre-design values are 1–10% of the axial
        mass-flow rate.
    cp : float | Callable[[float], float]
        Specific heat. Evaluated at the mean of the two endpoint
        temperatures.
    """

    def __init__(self, a: str, b: str, *, mdot_mix: float, cp):
        super().__init__(a, b)
        if mdot_mix <= 0:
            raise ValueError("mdot_mix must be positive")
        self.mdot_mix = float(mdot_mix)
        self.cp = cp

    def _cp(self, T: float) -> float:
        return self.cp(T) if callable(self.cp) else float(self.cp)

    def flux(self, T_a: float, T_b: float) -> float:
        T_mean = 0.5 * (T_a + T_b)
        return self.mdot_mix * self._cp(T_mean) * (T_a - T_b)

    def jacobian(self, T_a: float, T_b: float) -> tuple[float, float]:
        T_mean = 0.5 * (T_a + T_b)
        cp_val = self._cp(T_mean)
        # Ignore the dcp/dT contribution (small at PWR conditions).
        g = self.mdot_mix * cp_val
        return (g, -g)


class ForcedConvection(Edge):
    """Single-phase forced convection in a duct.

    flux = h(T_film) · A_ht · (Ta − Tb)

    The "wall" side (whose temperature drives the heating/cooling
    direction in the DB correlation) is selected by ``wall_side``;
    defaults to "a". T_film = (Ta + Tb)/2.

    Parameters
    ----------
    fluid :
        ``Fluid`` providing rho, mu, k, cp, Pr.
    mdot :
        Mass flow rate (kg/s).
    D_h :
        Hydraulic diameter (m).
    A_ht :
        Heat-transfer area (m²) — usually π·D·L for a circular pipe.
    A_xs :
        Cross-section area (m²) — defaults to π·D_h²/4.
    P :
        Pressure (Pa). If None, uses fluid's default_P if set.
    correlation :
        ``"dittus-boelter"`` (default) or ``"gnielinski"``.
    wall_side :
        ``"a"`` or ``"b"`` — which endpoint is the wall (affects only
        the heating/cooling exponent in Dittus-Boelter).
    """

    def __init__(
        self,
        a: str,
        b: str,
        *,
        fluid: Fluid,
        mdot: float,
        D_h: float,
        A_ht: float,
        A_xs: float | None = None,
        P: float | None = None,
        correlation: str = "dittus-boelter",
        wall_side: str = "a",
    ):
        super().__init__(a, b)
        if mdot <= 0 or D_h <= 0 or A_ht <= 0:
            raise ValueError("mdot, D_h, A_ht must be positive")
        if correlation not in ("dittus-boelter", "gnielinski"):
            raise ValueError(
                f"unknown correlation {correlation!r} — "
                "use 'dittus-boelter' or 'gnielinski'"
            )
        if wall_side not in ("a", "b"):
            raise ValueError("wall_side must be 'a' or 'b'")
        self.fluid = fluid
        self.mdot = float(mdot)
        self.D_h = float(D_h)
        self.A_ht = float(A_ht)
        self.A_xs = float(A_xs) if A_xs is not None else math.pi * (D_h ** 2) / 4
        self.P = P
        self.correlation = correlation
        self.wall_side = wall_side

    def _h(self, Ta: float, Tb: float) -> float:
        T_film = 0.5 * (Ta + Tb)
        f = self.fluid
        rho = f.rho(T_film, self.P)
        mu = f.mu(T_film, self.P)
        k = f.k(T_film, self.P)
        Pr = f.Pr(T_film, self.P)
        # Re = ρ·v·D_h/μ = (mdot/A_xs)·D_h/μ
        Re = self.mdot * self.D_h / (mu * self.A_xs)
        if self.correlation == "dittus-boelter":
            # heating means wall is hotter than bulk -> wall_T > fluid_T
            wall_T = Ta if self.wall_side == "a" else Tb
            fluid_T = Tb if self.wall_side == "a" else Ta
            heating = wall_T > fluid_T
            Nu = _nu_dittus_boelter(Re, Pr, heating)
        else:
            Nu = _nu_gnielinski(Re, Pr)
        return Nu * k / self.D_h

    def flux(self, Ta, Tb):
        h = self._h(Ta, Tb)
        return h * self.A_ht * (Ta - Tb)

    def jacobian(self, Ta, Tb):
        """Frozen-h jacobian: treat h(T_film) as constant for the Newton step.

        Newton recomputes h next iteration. Film-T variation per step is
        small in typical Rankine work; this gets Newton converging
        without falling back to Picard for every convection edge.
        """
        h = self._h(Ta, Tb)
        g = h * self.A_ht
        return (g, -g)
