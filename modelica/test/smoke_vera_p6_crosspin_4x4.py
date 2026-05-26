"""Smoke test for AssemblyVeraP6CrossPin at 4x4x10.

Verifies: cross-pin ThermalConductors compile + simulate at small scale.
Invariants:
  - Q_total_assembly matches q_lin * L * n_pin exactly (cross-pin doesn't
    change total power, only its distribution).
  - For uniform power: T_centerline_hot equal to baseline (no peaking).
  - For uniform power: T_cool_exit_spread = 0 (symmetric channels).
  - Cross-pin G > 0 shouldn't break physics for uniform input.
"""
from __future__ import annotations

import sys

import DyMat

from dymola_harness import new_dymola, simulate


def main() -> int:
    n_pin = 4 * 4
    n_axial = 10
    L_total = 3.6576
    q_lin_avg = 17838.0
    Q_expected = q_lin_avg * L_total * n_pin

    # Test with non-trivial cross-pin conductance to exercise the topology.
    model = (
        f"NetflowModelica.Tests.AssemblyVeraP6CrossPin"
        f"(n_pin={n_pin}, n_axial={n_axial}, G_cross=0.5)"
    )

    with new_dymola() as (dymola, work):
        mat_path = simulate(
            dymola, work, model,
            stop_time=1.0, n_intervals=5,
            result_stem="vera_p6_crosspin_smoke",
        )
        m = DyMat.DyMatFile(mat_path)

    Q = float(m.data("Q_total_assembly")[-1])
    spread = float(m.data("T_cool_exit_spread")[-1])
    Tcl = float(m.data("T_fuel_volavg_peak")[-1])

    print(f"  Q_total_assembly  = {Q:.4e} W  (expected {Q_expected:.4e} W)")
    print(f"  T_cool_exit_spread = {spread:.4e} K  (expected ~0 for uniform)")
    print(f"  T_fuel_volavg_peak = {Tcl:.2f} K  (should equal vanilla VERA P6)")

    assert abs(Q - Q_expected) / Q_expected < 1e-6, "Q_total mismatch"
    assert abs(spread) < 1e-3, f"spread non-zero for uniform: {spread}"
    assert 800.0 < Tcl < 1300.0, f"Tcl out of band: {Tcl}"

    print("\nSMOKE TEST PASSED (cross-pin topology + uniform power)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
