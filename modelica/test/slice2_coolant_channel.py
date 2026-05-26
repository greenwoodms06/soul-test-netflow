"""Slice 2 — coolant channel with stream FluidPort + IF97 medium.

PURPOSE: confirm Modelica's stream-connector semantics + IAPWS-IF97 medium
deliver the correct steady enthalpy balance:

    h_out = h_in + Q_total / mdot

with T_out recovered from the medium's (p, h) -> T inverse. No fuel pin yet
(slice 3); the cells exchange with FixedHeatFlow sources directly.

Verifies the equation Modelica's stream actually solves matches what we get
when we compute it independently in Python via CoolProp / scipy or via a
parallel call into Dymola's medium functions.
"""
from __future__ import annotations

import math
import sys

import DyMat
from CoolProp.CoolProp import PropsSI

from dymola_harness import new_dymola, simulate


N_CELLS = 5
MDOT = 0.30
P_NOM = 15.5e6
T_IN = 593.0
Q_TOTAL = 18_000.0


def analytic_outlet() -> tuple[float, float, float]:
    """Independently compute (h_in, h_out, T_out) via Python CoolProp (IAPWS-IF97).

    Using CoolProp rather than Dymola's own Medium means we are testing Dymola's
    answer against an INDEPENDENT IF97 implementation, not against itself.
    """
    # Explicitly ask CoolProp for IF97 (matches Dymola's StandardWater backend);
    # the default backend is HEOS (IAPWS-95), which differs from IF97 by mK in T.
    fluid = "IF97::Water"
    h_in = PropsSI("H", "T", T_IN, "P", P_NOM, fluid)
    h_out = h_in + Q_TOTAL / MDOT
    T_out = PropsSI("T", "P", P_NOM, "H", h_out, fluid)
    return float(h_in), float(h_out), float(T_out)


def read_modelica(mat_path: str) -> tuple[float, float]:
    m = DyMat.DyMatFile(mat_path)
    h_out = float(m.data("h_out_K")[-1])
    T_out = float(m.data("T_out_K")[-1])
    return h_out, T_out


def main() -> int:
    h_in, h_out_analytic, T_out_analytic = analytic_outlet()
    print(f"inlet h         = {h_in:.4f} J/kg  (T_in = {T_IN} K, p = {P_NOM/1e6:.1f} MPa)")
    print(f"expected h_out  = {h_out_analytic:.4f} J/kg  (= h_in + Q/mdot)")
    print(f"expected T_out  = {T_out_analytic:.6f} K\n")

    with new_dymola() as (dymola, work):
        mat = simulate(
            dymola, work,
            "NetflowModelica.Tests.CoolantChannelHeated",
            stop_time=1.0,
            n_intervals=10,
            result_stem="slice2",
        )
        h_out_mod, T_out_mod = read_modelica(mat)
    dh = abs(h_out_mod - h_out_analytic)
    dT = abs(T_out_mod - T_out_analytic)

    print(f"model h_out     = {h_out_mod:.4f} J/kg")
    print(f"model T_out     = {T_out_mod:.6f} K")
    print()
    print(f"|Δh|            = {dh:.3e} J/kg  ({dh/abs(h_out_analytic):.2e} rel)")
    print(f"|ΔT|            = {dT:.3e} K     ({dT/abs(T_out_analytic):.2e} rel)")

    # IF97 round-trip + connect()-emitted balance should hit float64 noise.
    # Set thresholds at 1 mJ/kg and 1 µK — well below any physics-meaningful scale.
    ok = dh < 1e-3 and dT < 1e-6
    if ok:
        print("\nVERIFY PASS (stream balance + IF97 round-trip at numerical noise)")
        return 0
    print("\nVERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
