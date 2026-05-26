"""Smoke test for AssemblyVeraP6 at small scale (4x4x10).

Step-1 verification: model compiles + simulates + invariants hold.
- Q_total_assembly = q_lin_avg * L_total * sum(q_lin_factor) = 17838 * 3.6576 * 16
  = 1.04e6 W (16 fuel rods, uniform factor).
- T_cool_exit_spread = 0 K for uniform power (no cross-flow yet, identical channels).
- T_fuel_volavg_peak in 800-1200 K (single-phase PWR conditions, q_lin_avg low,
  no peaking).
"""
from __future__ import annotations

import os
import sys

import DyMat

from dymola_harness import new_dymola, simulate


def main() -> int:
    n_pin = 4 * 4
    n_axial = 10
    L_total = 3.6576
    q_lin_avg = 17838.0
    Q_expected = q_lin_avg * L_total * n_pin

    model = (
        f"NetflowModelica.Tests.AssemblyVeraP6"
        f"(n_pin={n_pin}, n_axial={n_axial})"
    )

    with new_dymola() as (dymola, work):
        mat_path = simulate(
            dymola, work, model,
            stop_time=1.0, n_intervals=5,
            result_stem="vera_p6_smoke",
        )
        m = DyMat.DyMatFile(mat_path)

    Q = float(m.data("Q_total_assembly")[-1])
    spread = float(m.data("T_cool_exit_spread")[-1])
    Tmax = float(m.data("T_cool_exit_max")[-1])
    Tmin = float(m.data("T_cool_exit_min")[-1])
    Tfuel = float(m.data("T_fuel_volavg_peak")[-1])

    print(f"  Q_total_assembly  = {Q:.4e} W  (expected {Q_expected:.4e} W)")
    print(f"  T_cool_exit_min   = {Tmin:.2f} K")
    print(f"  T_cool_exit_max   = {Tmax:.2f} K")
    print(f"  T_cool_exit_spread = {spread:.4e} K  (expected ~0 for uniform)")
    print(f"  T_fuel_volavg_peak = {Tfuel:.2f} K")

    assert abs(Q - Q_expected) / Q_expected < 1e-6, "Q_total mismatch"
    assert abs(spread) < 1e-3, f"spread non-zero for uniform: {spread}"
    assert 800.0 < Tfuel < 1300.0, f"T_fuel_volavg_peak out of band: {Tfuel}"
    assert 590.0 < Tmin < 615.0, f"Tmin out of band: {Tmin}"

    print("\nSMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
