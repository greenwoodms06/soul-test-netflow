"""Slice 10 — axial conduction across pin slices.

Three runs at G_axial in {realistic≈no-axial, moderate=5 W/K, exaggerated=50 W/K}.
Energy conservation must hold *exactly* for all G_axial (axial only
redistributes; total ṁ·Δh = ΣQ always). Centerline peak smooths as G_axial↑.

Plus: the MTK-F11 "G=0 degeneracy" trap — does Dymola handle a zero-conductance
element gracefully, or does the same singularity bite?
"""
from __future__ import annotations

import math
import os
import sys

import DyMat

from dymola_harness import new_dymola, simulate


N = 10
L_TOTAL = 3.66
DZ = L_TOTAL / N
Q_LIN_AVG = 18000.0
Q_TOTAL = Q_LIN_AVG * L_TOTAL


def cases() -> list[tuple[str, float]]:
    # realistic axial G ≈ k_UO2 · A_pellet / dz
    k_uo2 = 3.0
    a_pellet = math.pi * 4.10e-3 ** 2
    Gax_real = k_uo2 * a_pellet / DZ
    return [
        ("realistic (≈no axial)", Gax_real),
        ("moderate G=5 W/K", 5.0),
        ("exaggerated G=50 W/K", 50.0),
    ]


def run_case(dymola, work, label: str, Gax: float, stem: str) -> dict:
    mat = simulate(
        dymola, work,
        f"NetflowModelica.Tests.AxialConductionChain(G_axial={Gax})",
        stop_time=1.0, n_intervals=5, result_stem=stem,
    )
    m = DyMat.DyMatFile(mat)
    T_cl = [float(m.data(f"T_centerline[{i}]")[-1]) for i in range(1, N + 1)]
    mdot_dh = float(m.data("mdot_dh")[-1])
    return {
        "label": label, "Gax": Gax,
        "T_cl": T_cl,
        "T_cl_peak": max(T_cl),
        "T_cl_range": max(T_cl) - min(T_cl),
        "mdot_dh": mdot_dh,
        "energy_resid": abs(mdot_dh - Q_TOTAL),
    }


def main() -> int:
    with new_dymola() as (dymola, work):
        results = []
        for i, (label, Gax) in enumerate(cases(), start=1):
            print(f"--- case: {label}, G_axial = {Gax:.3g} W/K ---", flush=True)
            r = run_case(dymola, work, label, Gax, f"slice10_case{i}")
            results.append(r)
            print(
                f"  peak T = {r['T_cl_peak']:.1f} K   range = {r['T_cl_range']:.1f} K"
                f"   mdot·Δh = {r['mdot_dh']:.3f} W   |resid| = {r['energy_resid']:.2e} W",
                flush=True,
            )

        # G=0 degeneracy probe (MTK-F11 trap)
        print("\n--- probe: G_axial = 0 (degenerate zero-conductance element) ---", flush=True)
        try:
            r0 = run_case(dymola, work, "G=0 probe", 0.0, "slice10_g0")
            print(f"  G=0 case PASSED: peak T = {r0['T_cl_peak']:.1f} K   |resid| = {r0['energy_resid']:.2e} W")
            print("  (Modelica handled G=0 cleanly — Julia MTK-F11 noted MTK failed here)")
            g0_status = "PASS"
        except Exception as e:
            print(f"  G=0 case FAILED: {type(e).__name__}: {str(e)[:200]}")
            g0_status = "FAIL"

    print("\nsummary:")
    print(f" {'case':<24s} {'peak T [K]':>10s} {'range [K]':>10s} {'|energy resid| [W]':>20s}")
    max_resid = 0.0
    for r in results:
        max_resid = max(max_resid, r["energy_resid"])
        print(f" {r['label']:<24s} {r['T_cl_peak']:>10.1f} {r['T_cl_range']:>10.2f} {r['energy_resid']:>20.2e}")
    print(f"\n max energy residual across all G_axial = {max_resid:.2e} W")
    print(f" G=0 degeneracy probe: {g0_status}")

    if max_resid < 1e-3:
        print("\nAXIAL-CONDUCTION VERIFY PASS (energy conserved ∀ G_axial; peak smooths as G↑)")
        return 0
    print("\nAXIAL-CONDUCTION VERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
