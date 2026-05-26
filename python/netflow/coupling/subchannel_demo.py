"""Pin-resolved subchannel coupled-T-H visuals, calibrated to VERA Problem 6.

Runs the subchannel-resolved coupled hydraulic<->thermal solve at full
17x17 assembly scale with the lateral mixing coefficient calibrated to
reproduce VERA's published coolant spread (8.3 K). Produces pin-resolved
2D heatmaps (coolant, fuel, flow) and a side-by-side vs the VERA range.

Honest framing: the *mechanism* (guide-tube perturbation + lateral
cross-flow) is from the generic-core physics; the lateral mixing
*coefficient* (~0.22) is calibrated to the benchmark, exactly as real
subchannel codes calibrate their turbulent-mixing factor.

Run:  python -m netflow.coupling.subchannel_demo
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from netflow.coupling.subchannel import solve_coupled_subchannel, GUIDE_17

VERA_MIN, VERA_MAX = 321.1, 329.4   # VERA P6 coolant exit (C)
MIX_CALIBRATED = 0.22                # tuned to VERA spread


def main():
    N = 17
    guide = GUIDE_17
    n_fuel = N * N - len(guide)
    # Mild radial tilt (VERA P6 is nearly flat, peak/avg ~1.05)
    cx = cy = (N - 1) / 2
    rmax = np.hypot(cx, cy)
    q_map = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            r = np.hypot(i - cx, j - cy) / rmax
            q_map[i, j] = 18000.0 * (1.0 + 0.05 * np.cos(r * np.pi / 2) - 0.025)
    total_mdot = 0.358 * n_fuel

    print(f"Solving 17x17 subchannel coupled T-H (mix={MIX_CALIBRATED})...")
    res = solve_coupled_subchannel(
        N, n_ax=12, q_map=q_map, guide=guide, total_mdot=total_mdot,
        guide_K=0.85, lateral_mix_frac=MIX_CALIBRATED, max_picard=10,
    )
    print(f"  picard={res.n_picard} converged={res.converged}")
    print(f"  coolant exit: {res.coolant_exit.min()-273.15:.1f}-"
          f"{res.coolant_exit.max()-273.15:.1f} C, spread {res.spread_K:.2f} K")
    print(f"  VERA: {VERA_MIN}-{VERA_MAX} C, spread {VERA_MAX-VERA_MIN:.1f} K")

    # Mask guide tubes for cleaner fuel plot
    cool = res.coolant_exit - 273.15
    fuel = res.fuel_centerline - 273.15
    flow = res.channel_flow.copy()
    guide_mask = np.zeros((N, N), dtype=bool)
    for (i, j) in guide:
        guide_mask[i, j] = True

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))

    # Coolant exit (pin-resolved)
    im0 = axes[0].imshow(cool.T, origin="lower", cmap="coolwarm",
                         extent=[-0.5, N-0.5, -0.5, N-0.5])
    axes[0].set_title(f"Coolant exit T  (spread {res.spread_K:.1f} K; "
                      f"VERA {VERA_MAX-VERA_MIN:.1f} K)")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, label="°C")

    # Fuel centerline (pin-resolved), guide tubes masked
    fuel_masked = np.ma.array(fuel, mask=guide_mask)
    im1 = axes[1].imshow(fuel_masked.T, origin="lower", cmap="hot",
                         extent=[-0.5, N-0.5, -0.5, N-0.5])
    axes[1].set_title(f"Fuel centerline T  (max {np.nanmax(fuel):.0f} °C)")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, label="°C")

    # Flow distribution (guide-tube bypass)
    im2 = axes[2].imshow(flow.T, origin="lower", cmap="viridis",
                         extent=[-0.5, N-0.5, -0.5, N-0.5])
    axes[2].set_title("Channel mass flow (guide-tube bypass)")
    plt.colorbar(im2, ax=axes[2], fraction=0.046, label="kg/s")

    for ax in axes:
        ax.set_xlabel("pin ix"); ax.set_ylabel("pin iy")
        for (i, j) in guide:
            ax.plot(i, j, "o", mfc="none", mec="cyan", ms=6, mew=1.0)

    fig.suptitle(
        "Subchannel-resolved coupled T-H — generic core pushed to "
        f"VERA-scale complexity (mixing coeff calibrated to VERA spread)",
        fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = pathlib.Path("results/subchannel_pinresolved.png")
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
