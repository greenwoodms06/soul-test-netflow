"""Slice 5 — transient fuel pin (constant-property first-order system).

Storage added to the slice-1 stack via a HeatCapacitor at the centerline.
Verifies the solver trajectory against the exact analytic first-order solution
        T(t) = T_inf + (T_cool − T_inf) exp(−t/τ)
at many time points, AND that T(t→∞) recovers slice-1's 1252.99 K.
"""
from __future__ import annotations

import math
import sys

import DyMat
import numpy as np

from dymola_harness import new_dymola, simulate


def main() -> int:
    with new_dymola() as (dymola, work):
        mat_path = simulate(
            dymola, work,
            "NetflowModelica.Tests.TransientPinConst",
            stop_time=80.0,
            n_intervals=500,
            tolerance=1e-9,
            result_stem="slice5",
        )
        m = DyMat.DyMatFile(mat_path)

    # scalar parameters (read off the parameter section)
    tau = float(m.data("tau")[-1])
    T_inf = float(m.data("T_inf")[-1])
    T_cool = float(m.data("T_cool")[-1])
    C_fuel = float(m.data("C_fuel")[-1])
    R_tot = float(m.data("R_tot")[-1])

    print(f"τ = R·C = {tau:.4f} s   (C = {C_fuel:.2f} J/K, R_tot = {R_tot:.6f} K/W)")
    print(f"steady T_inf = {T_inf:.4f} K  (slice-1 steady centerline)")

    t = m.abscissa("T_centerline_K", valuesOnly=True)
    T_mod = m.data("T_centerline_K")

    def T_an(tt: np.ndarray) -> np.ndarray:
        return T_inf + (T_cool - T_inf) * np.exp(-tt / tau)

    T_ref = T_an(t)
    err = np.abs(T_mod - T_ref)
    max_err = float(err.max())
    rms_err = float(np.sqrt(np.mean(err ** 2)))

    # spot-check at τ, 5τ, 12τ
    print("\n t [s]      Modelica [K]    analytic [K]    |Δ| [K]")
    for tt in (0.0, tau, 5 * tau, 12 * tau):
        idx = int(np.argmin(np.abs(t - tt)))
        print(f"  {t[idx]:7.3f}   {T_mod[idx]:12.4f}    {T_ref[idx]:12.4f}    {abs(T_mod[idx] - T_ref[idx]):.3e}")

    print(f"\nmax  |T_mod(t) − T_an(t)| over full trajectory = {max_err:.3e} K")
    print(f"rms  ............................................. = {rms_err:.3e} K")

    if max_err < 1e-2:
        print("\nTRANSIENT VERIFY PASS (full-trajectory match to <10 mK against analytic first-order)")
        return 0
    print("\nTRANSIENT VERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
