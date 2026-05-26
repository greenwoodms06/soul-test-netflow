"""Slice 1 — single steady fuel pin, Modelica acausal network vs textbook closed form.

PURPOSE (verification, not validation): confirm Modelica's connect() assembles
and solves the across/through thermal network correctly, by checking the four
node temperatures against the independently-computed analytic series-resistance
result to machine precision. Constant properties on purpose — this isolates the
SOLVER MACHINERY from the closures. Matching netflow's T-dependent number is
slice 4. See docs/adr/0001.

Standing limits (greppable, per Soul completion gate):
DEBT: constant properties (k_fuel, k_clad, h_gap) — verification only.
      T-dependent UO2/He/Zr closures + Dittus-Boelter convection come in slice 4.
"""
from __future__ import annotations

import math
import sys

import DyMat

from dymola_harness import new_dymola, simulate


# Geometry / operating point (must match Components.FuelPinConst defaults)
R_PELLET = 4.10e-3
GAP_THICK = 0.085e-3
R_CO = 4.75e-3
L = 1.0
Q_LIN = 18_000.0
K_FUEL = 3.0
K_CLAD = 16.0
H_GAP = 5_000.0
T_COOL = 593.0


def analytic_node_temperatures() -> dict[str, float]:
    """Independently re-derived from the same geometry & properties.

    Series resistances [K/W], pellet uses the solid-cylinder uniform-generation
    closed form R = 1 / (4 pi k L).
    """
    r_ci = R_PELLET + GAP_THICK
    Q_total = Q_LIN * L

    R_fuel = 1.0 / (4.0 * math.pi * K_FUEL * L)
    R_gap = 1.0 / (2.0 * math.pi * R_PELLET * H_GAP * L)
    R_clad = math.log(R_CO / r_ci) / (2.0 * math.pi * K_CLAD * L)

    T_co = T_COOL  # pinned by FixedTemperature; no convection resistance in slice 1
    T_ci = T_co + Q_total * R_clad
    T_ps = T_ci + Q_total * R_gap
    T_cl = T_ps + Q_total * R_fuel
    return {
        "centerline": T_cl,
        "pellet_surface": T_ps,
        "clad_inner": T_ci,
        "clad_outer": T_co,
    }


def read_modelica_steady(mat_path: str) -> dict[str, float]:
    m = DyMat.DyMatFile(mat_path)
    # Trajectories are constant (no states); take the final point.
    return {
        "centerline": float(m.data("pin.T_centerline_K")[-1]),
        "pellet_surface": float(m.data("pin.T_pellet_surface_K")[-1]),
        "clad_inner": float(m.data("pin.T_clad_inner_K")[-1]),
        "clad_outer": float(m.data("pin.T_clad_outer_K")[-1]),
    }


def main() -> int:
    anal = analytic_node_temperatures()
    print("analytic (independently re-derived):")
    for k, v in anal.items():
        print(f"  {k:<16s} = {v:.6f} K")

    with new_dymola() as (dymola, work):
        mat = simulate(
            dymola, work,
            "NetflowModelica.Tests.FuelPinSteady",
            stop_time=1.0,
            n_intervals=10,
            result_stem="slice1",
        )
        mod = read_modelica_steady(mat)

    print("\nmodel:")
    for k, v in mod.items():
        print(f"  {k:<16s} = {v:.6f} K")

    print("\n node              model [K]    analytic [K]   |Δ| [K]")
    max_d = 0.0
    for k in anal:
        d = abs(mod[k] - anal[k])
        max_d = max(max_d, d)
        print(f"  {k:<16s} {mod[k]:11.4f}  {anal[k]:13.4f}   {d:.2e}")

    print(f"\n max node Δ = {max_d:.2e} K")
    # Machine-precision target — Julia's slice 1 hit ~0 (linear system; one Newton step).
    # Loosened slightly to account for Dymola's translate-time numerical evaluation
    # of the resistance parameters in single-precision-promoted intermediates.
    threshold = 1e-9
    if max_d < threshold:
        print(f"VERIFY PASS (machine-precision agreement, Δ < {threshold:g} K)")
        return 0
    else:
        print(f"VERIFY FAIL (Δ >= {threshold:g} K)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
