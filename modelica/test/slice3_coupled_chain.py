"""Slice 3 — full fuel-channel → coolant chain.

PURPOSE (verification): two invariants checked to numerical noise --
  (a) ENERGY CLOSURE   mdot * (h_out - h_in) == ΣQ_i  (all pin power lands
                       in coolant via the stream-connector chain)
  (b) PER-PIN RADIAL   T_center_i = T_cool_i + Q_per_slice * R_tot

Constant properties. T-dependent closures are slice 4.
"""
from __future__ import annotations

import sys

import DyMat

from dymola_harness import new_dymola, simulate


def main() -> int:
    with new_dymola() as (dymola, work):
        mat_path = simulate(
            dymola, work,
            "NetflowModelica.Tests.CoupledChain",
            stop_time=1.0,
            n_intervals=10,
            result_stem="slice3",
        )
        m = DyMat.DyMatFile(mat_path)

    # scalar invariants
    Q_total = float(m.data("Q_total")[-1])
    Q_per_slice = float(m.data("Q_per_slice")[-1])
    R_tot_radial = float(m.data("R_tot_radial")[-1])
    mdot = float(m.data("mdot")[-1])
    h_in = float(m.data("h_in_K")[-1])
    h_out = float(m.data("h_out_K")[-1])

    # ---- (a) energy closure ----
    dh = h_out - h_in
    mdot_dh = mdot * dh
    res_energy = abs(mdot_dh - Q_total)
    print(f"(a) ENERGY CLOSURE")
    print(f"    mdot * Δh   = {mdot_dh:.6f} W")
    print(f"    Σ Q_i       = {Q_total:.6f} W")
    print(f"    |residual|  = {res_energy:.3e} W")

    # ---- (b) per-pin radial drop ----
    n = 10  # matches CoupledChain.n default
    max_err = 0.0
    print("\n(b) PER-PIN RADIAL DROP  T_center_i - T_cool_i  vs  Q*R_tot")
    print(f"    expected per pin: Q * R_tot = {Q_per_slice * R_tot_radial:.6f} K\n")
    print(f"    {'slice':>5s}  {'T_center [K]':>12s}  {'T_cool [K]':>11s}  {'measured ΔT':>13s}  {'|Δ vs expected|':>17s}")
    expected_dT = Q_per_slice * R_tot_radial
    for i in range(1, n + 1):
        Tcl = float(m.data(f"T_centerline[{i}]")[-1])
        Tcool = float(m.data(f"T_cool[{i}]")[-1])
        meas_dT = Tcl - Tcool
        err = abs(meas_dT - expected_dT)
        max_err = max(max_err, err)
        if i in (1, n // 2, n):
            print(f"    {i:>5d}  {Tcl:>12.4f}  {Tcool:>11.4f}  {meas_dT:>13.6f}  {err:>17.3e}")
    print(f"\n    max per-pin radial error = {max_err:.3e} K")

    # thresholds: energy closure to mW, radial drop to μK.
    ok = res_energy < 1e-3 and max_err < 1e-6
    print()
    if ok:
        print("VERIFY PASS (energy closes; every pin's radial drop exact)")
        return 0
    print("VERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
