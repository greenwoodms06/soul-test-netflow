"""Slice 6 — transient of the full coupled fuel-channel → coolant chain.

slice-3 topology + storage: HeatCapacitor at each pin centerline + fluid energy
storage M·dh/dt in each CoolantCellDyn. Cold → full-power startup at t=0.

VERIFICATION: at t_end (≈ 10 τ_pin), every centerline and every cell T must
match the slice-3 steady answer (which is the t→∞ limit of this transient).
The slice-3 steady is RUN INLINE in the same Dymola session — apples-to-apples
on the same machine, same medium, same closures.
"""
from __future__ import annotations

import math
import sys

import DyMat
import numpy as np

from dymola_harness import new_dymola, simulate


N = 10
T_END = 60.0


def read_array(m: DyMat.DyMatFile, name: str, n: int) -> np.ndarray:
    return np.array([float(m.data(f"{name}[{i}]")[-1]) for i in range(1, n + 1)])


def main() -> int:
    with new_dymola() as (dymola, work):
        # (1) slice 3 steady — the t→∞ target
        mat_ss = simulate(
            dymola, work,
            "NetflowModelica.Tests.CoupledChain",
            stop_time=1.0,
            n_intervals=5,
            result_stem="slice6_ref_ss",
        )
        m_ss = DyMat.DyMatFile(mat_ss)
        T_cool_ss = read_array(m_ss, "T_cool", N)
        T_cl_ss = read_array(m_ss, "T_centerline", N)
        R_tot = float(m_ss.data("R_tot_radial")[-1])
        Q_per = float(m_ss.data("Q_per_slice")[-1])
        print(f"slice-3 (steady) reference:")
        print(f"  T_cool[N] = {T_cool_ss[-1]:.4f} K, T_centerline[N] = {T_cl_ss[-1]:.4f} K")
        print(f"  per-pin ΔT = Q × R_tot = {Q_per * R_tot:.4f} K")

        # (2) slice 6 transient
        mat_tr = simulate(
            dymola, work,
            "NetflowModelica.Tests.TransientChain",
            stop_time=T_END,
            n_intervals=600,
            tolerance=1e-8,
            result_stem="slice6_transient",
        )
        m_tr = DyMat.DyMatFile(mat_tr)

    # final state
    T_cool_final = read_array(m_tr, "T_cool", N)
    T_cl_final = read_array(m_tr, "T_centerline", N)

    print(f"\ntransient final (t = {T_END:.1f} s):")
    print(f"  T_cool[N] = {T_cool_final[-1]:.4f} K, T_centerline[N] = {T_cl_final[-1]:.4f} K")

    # ---- (a) convergence to slice-3 steady ----
    err_cool = np.abs(T_cool_final - T_cool_ss)
    err_cl = np.abs(T_cl_final - T_cl_ss)
    max_err = float(max(err_cool.max(), err_cl.max()))
    print(f"\n max |T_final(slice6) - T_steady(slice3)| = {max_err:.4f} K")
    print(f"   T_cool:        max Δ = {err_cool.max():.4f} K")
    print(f"   T_centerline:  max Δ = {err_cl.max():.4f} K")

    # ---- (b) trajectory shape: first cell's centerline at a few times ----
    t = m_tr.abscissa("T_centerline[1]", valuesOnly=True)
    T_cl1 = m_tr.data("T_centerline[1]")
    print("\n cell-1 centerline trajectory:")
    for tt in (0.0, 5.0, 15.0, 30.0, T_END):
        idx = int(np.argmin(np.abs(t - tt)))
        print(f"   t={t[idx]:6.2f}  T_cl[1] = {T_cl1[idx]:.4f} K")

    # ---- pass criterion ----
    # The transient has a finite-time exponential tail; at t = 10 τ we still see
    # (T∞ - T_init) × e^{-10} ≈ 4.5e-5 of the rise. For ΔT ~ 730 K that's 30 mK.
    # Accept up to 100 mK at t_end.
    if max_err < 0.10:
        print(f"\nTRANSIENT-CHAIN VERIFY PASS"
              f" (t={T_END:.0f}s ≈ {T_END / (R_tot * Q_per / 660):.1f}τ;"
              f" t→∞ state matches slice-3 steady to {max_err*1000:.1f} mK)")
        return 0
    print("\nTRANSIENT-CHAIN VERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
