"""Smoke test for AssemblyVeraP6Neutronics at 4x4x10.

Verifies: 16 per-pin PointKinetics blocks + 16x10 dynamic-power pins
compile + simulate to a feedback equilibrium.

Equilibrium is NOT P_total = P_ref because the feedback signal is the
MID-AXIAL centerline T, not the peak. With uniform axial power and feedback
on mid-axial T, the equilibrium settles where T_fuel_mid = T_ref. For our
n_axial=10 case T_fuel_mid sits below T_ref → +Doppler → n>1 (about 10%
above ref). The smoke test confirms the topology resolves and the system
reaches a bounded steady state, not the specific value.
"""
from __future__ import annotations

import sys

import DyMat

from dymola_harness import new_dymola, simulate


def main() -> int:
    n_pin = 4 * 4
    n_axial = 10

    model = (
        f"NetflowModelica.Tests.AssemblyVeraP6Neutronics"
        f"(n_pin={n_pin}, n_axial={n_axial})"
    )

    with new_dymola() as (dymola, work):
        mat_path = simulate(
            dymola, work, model,
            stop_time=50.0, n_intervals=50,
            result_stem="vera_p6_neutronics_smoke",
        )
        m = DyMat.DyMatFile(mat_path)

    P_total = float(m.data("P_total")[-1])
    P_total_ref = float(m.data("P_total_ref")[-1])
    T_hot = float(m.data("T_centerline_hot")[-1])
    T_cool = float(m.data("T_cool_outlet_max")[-1])

    print(f"  P_total          = {P_total:.4e} W   (ref {P_total_ref:.4e})")
    print(f"  P_total / P_ref  = {P_total / P_total_ref:.4f}")
    print(f"  T_centerline_hot = {T_hot:.2f} K")
    print(f"  T_cool_outlet_max = {T_cool:.2f} K")

    # Equilibrium depends on feedback-signal choice. Just bound the result.
    assert 0.5 < P_total / P_total_ref < 2.0, \
        f"P_total / P_ref = {P_total / P_total_ref} out of reasonable band"
    assert 800.0 < T_hot < 1500.0, f"T_hot out of band: {T_hot}"
    assert 590.0 < T_cool < 615.0, f"T_cool out of band: {T_cool}"

    print("\nSMOKE TEST PASSED (per-pin PointKinetics × 16 + dynamic pins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
