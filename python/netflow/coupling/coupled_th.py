"""Picard-coupled hydraulic <-> thermal demonstration.

This proves the generic core supports *coupled* multi-physics (the true
payoff of Product B), and captures the mechanism behind the §28 VERA
coolant-spread gap: guide-tube bypass flow.

Coupling mirrors how MC21/CTF actually couple — Picard iteration between
two separate single-state solves on the unchanged core:

  1. HYDRAULIC solve (netflow.plugins.hydraulic): distribute a fixed
     total mass flow across parallel subchannels by their resistance K.
     Guide-tube channels have larger flow area -> lower K -> bypass flow.
  2. THERMAL update: each channel's coolant exit T = T_in + Q/(mdot*cp),
     using the per-channel mdot from step 1. Fuel channels heat; guide
     tubes (Q=0) stay near inlet.
  3. FEEDBACK: coolant T -> density -> updates each channel's K.
  4. Iterate to convergence.

This is a *demonstration of the mechanism*, NOT a CTF-fidelity claim:
no lateral cross-flow momentum, no grid form losses, no turbulent
mixing coefficients.

Run:
    python -m netflow.plugins.thermal.examples.coupled_th
"""

from __future__ import annotations

import math
import pathlib

from netflow import Network, Node
from netflow.plugins.hydraulic import Pipe


# Water density vs T at ~15.5 MPa (simple linear fit, kg/m3), 565-620 K
def water_density(T_K: float) -> float:
    # ~745 kg/m3 at 565 K down to ~660 kg/m3 at 620 K (PWR conditions)
    return 745.0 - 1.55 * (T_K - 565.0)


CP = 5500.0          # J/kg/K
T_INLET = 565.0      # K
TOTAL_MDOT = 100.0   # kg/s through the assembly row (arbitrary scale)


def build_channels(n_fuel: int, guide_positions: set[int], q_pin: float):
    """A row of channels: fuel channels carry power q_pin; guide-tube
    channels carry zero power and have ~2x flow area (lower K)."""
    channels = []
    idx = 0
    total = n_fuel + len(guide_positions)
    for pos in range(total):
        if pos in guide_positions:
            # Guide tube: larger flow area -> lower base resistance
            channels.append({"id": f"ch{pos}", "type": "guide",
                             "K_base": 0.5, "Q": 0.0})
        else:
            channels.append({"id": f"ch{pos}", "type": "fuel",
                             "K_base": 1.0, "Q": q_pin})
            idx += 1
    return channels


def solve_coupled(channels, *, coupled=True, max_picard=30, tol=1e-5):
    """Picard-couple hydraulic flow distribution with thermal heating.

    If ``coupled`` is False, flow is uniform (no hydraulic solve) — the
    baseline that ignores guide-tube bypass.
    Returns (mdot_per_channel, T_exit_per_channel, n_picard, converged).
    """
    ids = [c["id"] for c in channels]
    T_exit = {c["id"]: T_INLET for c in channels}
    mdot = {c["id"]: TOTAL_MDOT / len(channels) for c in channels}
    history = []

    for it in range(max_picard):
        if coupled:
            # --- HYDRAULIC SOLVE: distribute TOTAL_MDOT by resistance ---
            hyd = Network()
            hyd.add_node(Node(id="plenum_in", source=TOTAL_MDOT))
            hyd.add_node(Node(id="plenum_out", fixed=0.0))
            edges = {}
            for c in channels:
                T_mean = 0.5 * (T_INLET + T_exit[c["id"]])
                rho = water_density(T_mean)
                # Resistance rises as density drops (hot channels resist flow):
                K = c["K_base"] * (745.0 / rho)
                e = Pipe("plenum_in", "plenum_out", K=K)
                hyd.add_edge(e)
                edges[c["id"]] = e
            res = hyd.solve_steady(method="newton", tol=1e-12, max_iter=200)
            new_mdot = {cid: res.edge_flux(edges[cid]) for cid in ids}
        else:
            new_mdot = {c["id"]: TOTAL_MDOT / len(channels) for c in channels}

        # --- THERMAL UPDATE: per-channel coolant exit T ---
        new_T = {}
        for c in channels:
            m = max(new_mdot[c["id"]], 1e-9)
            new_T[c["id"]] = T_INLET + c["Q"] / (m * CP)

        # --- convergence on exit T ---
        delta = max(abs(new_T[cid] - T_exit[cid]) for cid in ids)
        T_exit = new_T
        mdot = new_mdot
        history.append(delta)
        if delta < tol:
            return mdot, T_exit, it + 1, True, history
    return mdot, T_exit, max_picard, False, history


def main():
    # A row of 9 channels: guide tubes at positions 2 and 6
    guide = {2, 6}
    q_pin = 60000.0     # W per fuel channel (lumped)
    channels = build_channels(n_fuel=7, guide_positions=guide, q_pin=q_pin)

    print("=" * 64)
    print("Picard-coupled hydraulic <-> thermal demonstration")
    print("=" * 64)
    print(f"9-channel row, guide tubes at positions {sorted(guide)} "
          f"(zero power, 2x flow area)\n")

    # Baseline: uniform flow (ignores bypass)
    mdot_u, T_u, _, _, _ = solve_coupled(channels, coupled=False)
    spread_u = max(T_u.values()) - min(T_u.values())

    # Coupled: hydraulic distributes flow
    mdot_c, T_c, n_pic, conv, hist = solve_coupled(channels, coupled=True)
    spread_c = max(T_c.values()) - min(T_c.values())

    print(f"{'channel':>10s} {'type':>6s} {'mdot uniform':>13s} "
          f"{'mdot coupled':>13s} {'Texit uniform':>14s} {'Texit coupled':>14s}")
    print("-" * 76)
    for c in channels:
        cid = c["id"]
        print(f"{cid:>10s} {c['type']:>6s} {mdot_u[cid]:>13.2f} "
              f"{mdot_c[cid]:>13.2f} {T_u[cid]-273.15:>13.1f}C {T_c[cid]-273.15:>13.1f}C")

    print()
    print(f"Picard converged: {conv} in {n_pic} iterations")
    print(f"Coolant exit SPREAD (max-min):")
    print(f"  uniform-flow baseline : {spread_u:.2f} K")
    print(f"  coupled (with bypass) : {spread_c:.2f} K")
    print(f"  -> coupling increases the spread by "
          f"{(spread_c/spread_u - 1)*100:.0f}% by routing bypass flow")
    print()
    total_guide_flow = sum(mdot_c[c['id']] for c in channels if c['type']=='guide')
    print(f"Guide tubes carry {total_guide_flow:.1f} kg/s "
          f"({total_guide_flow/TOTAL_MDOT*100:.0f}% of total) as cool bypass flow")

    # Plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        x = np.arange(len(channels))
        types = [c["type"] for c in channels]
        colors = ["#3366aa" if t == "guide" else "#cc6633" for t in types]

        ax1.bar(x - 0.2, [mdot_u[c["id"]] for c in channels], width=0.4,
                label="uniform (no hydraulics)", color="#bbbbbb")
        ax1.bar(x + 0.2, [mdot_c[c["id"]] for c in channels], width=0.4,
                label="coupled (flow by ΔP)", color=colors)
        ax1.set_xlabel("channel index"); ax1.set_ylabel("mass flow (kg/s)")
        ax1.set_title("Flow distribution — guide tubes bypass")
        ax1.legend(); ax1.grid(True, alpha=0.3)
        for gp in guide:
            ax1.annotate("guide\ntube", xy=(gp, mdot_c[f"ch{gp}"]),
                         xytext=(0, 6), textcoords="offset points",
                         ha="center", fontsize=7, color="#3366aa")

        ax2.plot(x, [T_u[c["id"]]-273.15 for c in channels], "o-",
                 label=f"uniform (spread {spread_u:.1f} K)", color="#999999")
        ax2.plot(x, [T_c[c["id"]]-273.15 for c in channels], "s-",
                 label=f"coupled (spread {spread_c:.1f} K)", color="#cc3333")
        ax2.set_xlabel("channel index"); ax2.set_ylabel("coolant exit T (°C)")
        ax2.set_title("Coolant exit temperature spread")
        ax2.legend(); ax2.grid(True, alpha=0.3)

        fig.suptitle("Picard-coupled hydraulic↔thermal: guide-tube bypass "
                     "widens the coolant spread (the §28 mechanism)", fontsize=11)
        fig.tight_layout()
        out = pathlib.Path("results/coupled_th_demo.png")
        out.parent.mkdir(exist_ok=True)
        fig.savefig(out, dpi=130, bbox_inches="tight")
        print(f"\nwrote {out}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
