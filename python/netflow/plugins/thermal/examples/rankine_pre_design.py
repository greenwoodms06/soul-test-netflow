"""Rankine pre-design example: PWR-ish fuel pin → coolant analysis.

A canonical sanity-check problem before building a full Modelica
plant model:

    UO2 pellet ─[pellet conduction]─ pellet surface
                                       │
                                       ├─ He gas conduction (gap)
                                       └─ gray-body radiation across gap
                                       │
                                       │   (parallel: gap_conduction || radiation)
                                       │
                              clad inner surface
                                       │
                                  [Zircaloy clad conduction]
                                       │
                              clad outer surface
                                       │
                                [forced convection to coolant]
                                       │
                                  bulk coolant (Dirichlet)

Run:

    python -m netflow.plugins.thermal.examples.rankine_pre_design
    python -m netflow.plugins.thermal.examples.rankine_pre_design --plots

The --plots flag writes PNGs to a ``results/`` directory beside the
project root (or wherever ``--out-dir`` points). matplotlib + networkx
required (``pip install 'netflow[viz]'``).
"""

from __future__ import annotations

import argparse
import math
import pathlib

from netflow import Network
from netflow.plugins.thermal import (
    CoolPropFluid,
    ForcedConvection,
    FuelRod,
    Helium_gap,
    UO2,
    Zircaloy4,
)


def build_pwr_fuel_pin_to_coolant(
    *,
    q_lin: float = 18_000.0,             # W/m
    T_coolant: float = 593.0,            # K (320 °C — PWR core inlet bulk)
    P_system: float = 15.5e6,            # Pa (PWR ~155 bar)
    mdot_subchannel: float = 0.30,       # kg/s per subchannel
) -> tuple[Network, dict]:
    """Build the fuel-pin → coolant network at a single axial location.

    Returns the Network plus a dict of named port IDs for inspection.
    """
    net = Network()

    # Fuel rod component
    rod = FuelRod(
        r_pellet=4.10e-3,
        gap_thickness=0.085e-3,
        r_clad_outer=4.75e-3,
        L=1.0,                            # 1-m axial slice
        fuel_material=UO2(),
        clad_material=Zircaloy4(),
        gap_material=Helium_gap,
        gap_emissivity=0.85,
        q_lin=q_lin,
    )
    ports = rod.build(net, prefix="rod_")

    # Coolant boundary
    coolant = CoolPropFluid("Water", default_P=P_system)
    net.add_node_from_name = None  # noqa: SLF001 — illustrative; no real use
    from netflow.core.node import Node
    net.add_node(Node(id="coolant", fixed=T_coolant))

    # Forced convection from clad outer surface to bulk coolant
    # Subchannel geometry: typical PWR square pitch p/D ~ 1.33
    # Hydraulic diameter for a typical subchannel:
    pitch = 12.6e-3        # m
    rod_OD = 2 * 4.75e-3
    A_xs = pitch ** 2 - math.pi * rod_OD ** 2 / 4
    P_wet = math.pi * rod_OD
    D_h = 4 * A_xs / P_wet
    A_ht = math.pi * rod_OD * 1.0    # 1-m slice

    conv = ForcedConvection(
        ports.clad_outer, "coolant",
        fluid=coolant,
        mdot=mdot_subchannel,
        D_h=D_h,
        A_ht=A_ht,
        A_xs=A_xs,
        correlation="dittus-boelter",
        wall_side="a",
    )
    net.add_edge(conv)

    return net, {
        "centerline": ports.centerline,
        "pellet_surface": ports.pellet_surface,
        "clad_inner": ports.clad_inner,
        "clad_outer": ports.clad_outer,
        "coolant": "coolant",
        "convection_edge": conv,
    }


def print_solution(res, named: dict, q_lin: float) -> None:
    print(f"\n  q_lin = {q_lin/1000:.1f} kW/m,  Q = {q_lin:.0f} W per meter")
    print(f"  converged: {res.converged} in {res.n_iter} iterations "
          f"({res.method}, {res.elapsed_s*1000:.1f} ms)")
    print(f"  ||F||_final = {res.residual_history[-1]:.3e}")
    print()
    print(f"  {'station':<20s} {'T (K)':>8s} {'T (°C)':>8s}")
    for label in ["centerline", "pellet_surface", "clad_inner", "clad_outer", "coolant"]:
        nid = named[label]
        T = res.states[nid]
        print(f"  {label:<20s} {T:8.1f} {T-273.15:8.1f}")
    print()
    Q = res.edge_flux(named["convection_edge"])
    print(f"  Heat removed by coolant: {Q:.0f} W (target {q_lin:.0f} W)")


def sweep_linear_power(
    q_lin_kW: list[float] | None = None,
) -> list[dict]:
    """Parametric sweep — q_lin from 10 to 40 kW/m by default.

    Returns a list of result records (one per q_lin) so callers can plot.
    """
    if q_lin_kW is None:
        q_lin_kW = [10.0, 12.5, 15.0, 17.5, 20.0, 22.5, 25.0, 27.5,
                    30.0, 32.5, 35.0, 37.5, 40.0, 42.5, 45.0]

    print()
    print("=" * 60)
    print("PWR fuel-pin → coolant — linear-power sweep")
    print("=" * 60)
    print(f"{'q_lin (kW/m)':>13s}  {'T_c (K)':>9s}  {'T_c (°C)':>9s}  {'iter':>5s}")
    print("-" * 50)

    records: list[dict] = []
    for q_kW in q_lin_kW:
        net, named = build_pwr_fuel_pin_to_coolant(q_lin=q_kW * 1000.0)
        res = net.solve_steady(method="newton", tol=1e-6, max_iter=80)
        rec = {
            "q_lin_kW": q_kW,
            "T_centerline": res.states[named["centerline"]],
            "T_pellet_surface": res.states[named["pellet_surface"]],
            "T_clad_inner": res.states[named["clad_inner"]],
            "T_clad_outer": res.states[named["clad_outer"]],
            "T_coolant": res.states[named["coolant"]],
            "n_iter": res.n_iter,
            "converged": res.converged,
        }
        records.append(rec)
        marker = "" if res.converged else "  !!"
        print(f"{q_kW:13.1f}  {rec['T_centerline']:9.1f}  "
              f"{rec['T_centerline']-273.15:9.1f}  {res.n_iter:5d}{marker}")
    return records


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _radii_for_profile() -> list[tuple[str, float]]:
    """Match the geometry used in build_pwr_fuel_pin_to_coolant.

    Returns labelled radial positions (m) for the radial profile plot.
    """
    return [
        ("centerline",     0.0),
        ("pellet_surface", 4.10e-3),
        ("clad_inner",     4.10e-3 + 0.085e-3),
        ("clad_outer",     4.75e-3),
        ("coolant",        4.75e-3 * 1.4),  # represent bulk a bit outboard
    ]


def plot_radial_profile(res, named: dict, q_lin: float, out_path: pathlib.Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    radii = _radii_for_profile()
    Ts = [res.states[named[label]] for label, _ in radii]
    Ts_C = [T - 273.15 for T in Ts]
    rs_mm = [r * 1000 for _, r in radii]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(rs_mm, Ts_C, marker="o", color="#cc3333", linewidth=2)
    for (label, _), x, y in zip(radii, rs_mm, Ts_C):
        ax.annotate(f"{label}\n{y:.0f}°C",
                    xy=(x, y), xytext=(6, 6), textcoords="offset points",
                    fontsize=8)
    ax.set_xlabel("radial position (mm)")
    ax.set_ylabel("temperature (°C)")
    ax.set_title(f"PWR fuel-pin radial profile  ·  q_lin = {q_lin/1000:.1f} kW/m")
    ax.grid(True, alpha=0.3)

    # Shade material regions
    ax.axvspan(0, 4.10, alpha=0.10, color="#666633", label="UO2 pellet")
    ax.axvspan(4.10, 4.185, alpha=0.20, color="#aaaaaa", label="He gap")
    ax.axvspan(4.185, 4.75, alpha=0.15, color="#3366aa", label="Zircaloy clad")
    ax.axvspan(4.75, rs_mm[-1] + 1, alpha=0.10, color="#3399ff", label="coolant")
    ax.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"  wrote {out_path}")


def plot_power_sweep(records: list[dict], out_path: pathlib.Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    qs = [r["q_lin_kW"] for r in records]
    Tc = [r["T_centerline"] - 273.15 for r in records]
    Tps = [r["T_pellet_surface"] - 273.15 for r in records]
    Tci = [r["T_clad_inner"] - 273.15 for r in records]
    Tco = [r["T_clad_outer"] - 273.15 for r in records]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(qs, Tc,  marker="o", linewidth=2, label="centerline", color="#cc3333")
    ax.plot(qs, Tps, marker="s", linewidth=1.5, label="pellet surface", color="#cc9933")
    ax.plot(qs, Tci, marker="^", linewidth=1.5, label="clad inner",   color="#3366aa")
    ax.plot(qs, Tco, marker="v", linewidth=1.5, label="clad outer",   color="#33aaaa")
    # UO2 melting point at ~2865°C — label on the right where there's space
    ax.axhline(2865, color="black", linestyle="--", linewidth=1, alpha=0.6)
    ax.text(qs[-1], 2865, "UO2 melt (2865 °C) ",
            fontsize=8, va="bottom", ha="right")
    ax.set_xlabel("linear power q_lin (kW/m)")
    ax.set_ylabel("temperature (°C)")
    ax.set_title("PWR fuel-pin temperatures vs linear power")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="center left", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"  wrote {out_path}")


def plot_network_topology(out_path: pathlib.Path):
    """Draw the Rankine network as a labelled graph."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from netflow.viz import draw_network

    net, named = build_pwr_fuel_pin_to_coolant(q_lin=18_000.0)
    res = net.solve_steady(method="newton", tol=1e-6, max_iter=80)

    fig, ax = plt.subplots(figsize=(10, 7))
    draw_network(
        net, result=res, ax=ax, layout="kamada_kawai",
        title="PWR fuel-pin → coolant network (T in K at solved state)",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(make_plots: bool = False,
         out_dir: pathlib.Path | None = None) -> None:
    print("=" * 60)
    print("Rankine pre-design: PWR fuel-pin → coolant (single axial slice)")
    print("=" * 60)
    net, named = build_pwr_fuel_pin_to_coolant(q_lin=18_000.0)
    res = net.solve_steady(method="newton", tol=1e-6, max_iter=80)
    print_solution(res, named, q_lin=18_000.0)

    records = sweep_linear_power()

    if make_plots:
        out_dir = out_dir or pathlib.Path("results")
        out_dir.mkdir(parents=True, exist_ok=True)
        print()
        print(f"writing plots to {out_dir.resolve()}/")
        plot_radial_profile(res, named, 18_000.0,
                            out_dir / "fuel_pin_radial_profile.png")
        plot_power_sweep(records,
                         out_dir / "fuel_pin_power_sweep.png")
        plot_network_topology(out_dir / "fuel_pin_network.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plots", action="store_true",
                        help="write PNG plots to --out-dir")
    parser.add_argument("--out-dir", type=pathlib.Path, default=None,
                        help="directory for plot output (default: ./results/)")
    args = parser.parse_args()
    main(make_plots=args.plots, out_dir=args.out_dir)
