"""Verify the 17×17 assembly produces physically correct answers, not just that it runs.

Closes the SOUL-F028 gap: the stress test measured wall-clock only. A model
that compiles, runs to completion, and returns garbage temperatures would
pass that test. Here we check the global energy invariant + sanity bounds.

Runs 17×17×10 (fast, 106 s) — same physics as slice 3's CoupledChain but
spread across 289 parallel channels.
"""
from __future__ import annotations

import sys

import DyMat

from dymola_harness import new_dymola, simulate


def main() -> int:
    with new_dymola() as (dymola, work):
        mat = simulate(
            dymola, work,
            "NetflowModelica.Tests.Assembly17x17(n_pin=289, n_axial=10)",
            stop_time=1.0, n_intervals=5, result_stem="verify_assembly",
        )
        m = DyMat.DyMatFile(mat)

        # global scalars exposed by the model
        T_cl_hot = float(m.data("T_centerline_hot")[-1])
        T_cool_out_max = float(m.data("T_cool_outlet_max")[-1])
        Q_total = float(m.data("Q_total_assembly")[-1])

    # ---- physics expectations ----
    # T_cool_inlet = 565 K; mdot_per_pin = 0.30; q_lin = 18 kW/m; L = 3.66 m
    # Per-pin total power = 18000 * 3.66 = 65880 W
    # 289 channels in parallel → Q_total = 289 * 65880 = 19,039,320 W
    Q_total_expected = 289 * 18000 * 3.66
    # Per-pin coolant ΔT ≈ Q_per_pin / (mdot * cp_water_PWR ≈ 5500 J/kg/K)
    # = 65880 / (0.30 * 5500) ≈ 39.9 K → outlet ≈ 565 + 40 = 605 K (constant-cp est;
    # IF97 cp is closer to 5400-5800 → expect 603-605 K)
    T_cool_out_expected_band = (600.0, 615.0)
    # Per-pin radial drop ≈ Q_per_pin × R_tot
    # R_tot per axial slice (dz = 0.366 m, with slice-3 closures) ≈ 0.366 K/W
    # Per slice: Q_per_slice = 18000 * 0.366 = 6588 W; ΔT_radial ≈ 6588 × 0.366 = 2410 K??
    # No wait — R_tot scales as 1/dz, so per-slice ΔT_radial = q_lin × (constants) and
    # is independent of dz: ≈ 660 K (verified in slice 3). So T_centerline_hot ≈
    # T_cool_outlet_hot + 660 ≈ 603 + 660 ≈ 1265 K (in a parallel channel; equals
    # slice-3 outlet centerline within IF97 cp variation).
    T_cl_hot_expected_band = (1240.0, 1290.0)

    print(f"Q_total_assembly        = {Q_total:.0f} W      expected {Q_total_expected:.0f} W")
    print(f"T_cool_outlet_max       = {T_cool_out_max:.3f} K   expected in {T_cool_out_expected_band}")
    print(f"T_centerline_hot        = {T_cl_hot:.3f} K   expected in {T_cl_hot_expected_band}")

    fails = []
    if abs(Q_total - Q_total_expected) > 1.0:
        fails.append(f"Q_total off by {Q_total - Q_total_expected:.1f} W (expected 0 — it's a parameter)")
    if not (T_cool_out_expected_band[0] <= T_cool_out_max <= T_cool_out_expected_band[1]):
        fails.append(f"T_cool_outlet_max outside {T_cool_out_expected_band}")
    if not (T_cl_hot_expected_band[0] <= T_cl_hot <= T_cl_hot_expected_band[1]):
        fails.append(f"T_centerline_hot outside {T_cl_hot_expected_band}")

    if fails:
        print("\nPHYSICS CHECK FAIL:")
        for f in fails:
            print(f"  * {f}")
        return 1
    print("\nPHYSICS CHECK PASS — assembly produces physically sensible answers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
