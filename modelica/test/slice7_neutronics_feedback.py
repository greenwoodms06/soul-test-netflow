"""Slice 7 — neutronics + Doppler feedback coupled to thermal (multiphysics).

Same scenario as soultest-julia slice 7: +100 pcm external reactivity inserted
at t=0; power rises; fuel heats; negative Doppler returns ρ → 0 at a new
equilibrium. Verifies Modelica's signal/acausal composition.

Analytic equilibrium:
  T_eq = T_ref − ρ_ext / α
  P_eq = (T_eq − T_cool) / R_th
  n_eq = P_eq / P0
"""
from __future__ import annotations

import os
import sys

import DyMat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dymola_harness import new_dymola, simulate


RHO_EXT = 1e-3
ALPHA = -2.5e-5
T_NOM = 593.0 + 18000.0 * 0.036666
T_COOL = 593.0
R_TH = 0.036666
P0 = 18000.0


def main() -> int:
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"
    )
    os.makedirs(out_dir, exist_ok=True)

    with new_dymola() as (dymola, work):
        mat = simulate(
            dymola, work,
            "NetflowModelica.Tests.NeutronicsDopplerFeedback",
            stop_time=300.0,
            n_intervals=600,
            tolerance=1e-9,
            result_stem="slice7",
        )
        m = DyMat.DyMatFile(mat)

    T_eq = T_NOM - RHO_EXT / ALPHA
    P_eq = (T_eq - T_COOL) / R_TH
    n_eq = P_eq / P0
    print(f"analytic equilibrium:  T_eq = {T_eq:.3f} K   P_eq = {P_eq:.1f} W   n_eq = {n_eq:.5f}")

    t = m.abscissa("fuel.T", valuesOnly=True)
    T = m.data("fuel.T")
    n = m.data("kin.n")
    rho = m.data("kin.rho")

    T_f = float(T[-1])
    n_f = float(n[-1])
    rho_f = float(rho[-1])
    P_f = P0 * n_f
    print()
    print(f"               model final     analytic")
    print(f"T_fuel [K]   {T_f:11.3f}     {T_eq:.3f}")
    print(f"power  [W]   {P_f:11.1f}     {P_eq:.1f}")
    print(f"n (rel)      {n_f:11.5f}     {n_eq:.5f}")
    print(f"ρ (pcm)      {rho_f*1e5:11.3f}        0.0")

    # plot
    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    mask = t <= 60
    axes[0].plot(t[mask], n[mask], color="tab:blue")
    axes[0].set_ylabel("n (rel)")
    axes[0].set_title("Neutronics ↔ thermal: +100 pcm step, Doppler settling")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(t[mask], T[mask], color="tab:orange")
    axes[1].axhline(T_eq, ls="--", color="black", alpha=0.5, label=f"T_eq = {T_eq:.2f}")
    axes[1].set_ylabel("fuel T [K]"); axes[1].legend(); axes[1].grid(True, alpha=0.3)
    axes[2].plot(t[mask], rho[mask] * 1e5, color="tab:green")
    axes[2].axhline(0, ls="--", color="black", alpha=0.5)
    axes[2].set_ylabel("ρ [pcm]"); axes[2].set_xlabel("t [s]")
    axes[2].grid(True, alpha=0.3)
    fig.tight_layout()
    plot_path = os.path.join(out_dir, "slice7_neutronics_feedback.png")
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)
    print(f"\nwrote {plot_path}")

    ok = abs(T_f - T_eq) < 0.05 and abs(rho_f) < 5e-6
    if ok:
        print("\nMULTIPHYSICS VERIFY PASS (Doppler equilibrium ρ→0; T matches analytic)")
        return 0
    print("\nMULTIPHYSICS VERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
