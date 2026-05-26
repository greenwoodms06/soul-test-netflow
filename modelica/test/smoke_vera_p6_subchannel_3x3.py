"""Smoke test for AssemblyVeraP6Subchannel at 3x3x10.

Verifies: 4-port CoolantCellSub + cross-flow lattice compiles + simulates
on a tiny 3x3 grid. The 4-port mass balance and lateral connect() pattern
is the most likely failure mode for step 3c.

UNIFORM POWER + UNIFORM INLET: by symmetry, lateral m_flows should be zero
or very small (numerical noise). T_cool_exit_spread should be near zero.

If the model fails translation due to under-determination (no momentum, no
orifice loss), this smoke test catches it cheaply.
"""
from __future__ import annotations

import sys

import DyMat

from dymola_harness import new_dymola, simulate


def main() -> int:
    n_side = 3
    n_axial = 10
    L_total = 3.6576
    q_lin_avg = 17838.0
    Q_expected = q_lin_avg * L_total * n_side * n_side

    model = (
        f"NetflowModelica.Tests.AssemblyVeraP6Subchannel"
        f"(n_side={n_side}, n_axial={n_axial})"
    )

    try:
        with new_dymola() as (dymola, work):
            mat_path = simulate(
                dymola, work, model,
                stop_time=1.0, n_intervals=5,
                result_stem="vera_p6_subchannel_smoke",
            )
            m = DyMat.DyMatFile(mat_path)
    except Exception as e:  # noqa: BLE001
        print(f"SUBCHANNEL SMOKE TEST FAILED: {e!s}")
        print("  -> if this is 'system is structurally singular', subchannel")
        print("     model needs SimpleGenericOrifice elements between cells.")
        return 1

    Q = float(m.data("Q_total_assembly")[-1])
    spread = float(m.data("T_cool_exit_spread")[-1])
    T_hot = float(m.data("T_centerline_hot")[-1])

    print(f"  Q_total_assembly  = {Q:.4e} W  (expected {Q_expected:.4e} W)")
    print(f"  T_cool_exit_spread = {spread:.4e} K  (uniform -> expect ~0)")
    print(f"  T_centerline_hot  = {T_hot:.2f} K")

    assert abs(Q - Q_expected) / Q_expected < 1e-6, "Q_total mismatch"
    # Loose tolerance — numerical noise possible with the 6-port balance.
    assert abs(spread) < 1.0, f"spread too large for uniform: {spread}"
    assert 800.0 < T_hot < 1300.0, f"T_hot out of band: {T_hot}"

    print("\nSMOKE TEST PASSED (4-port CoolantCellSub + cross-flow lattice)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
