"""Code-to-code comparison against published VERA Problem 6/7 solutions.

IMPORTANT framing (Emissary digest, 2026-05-20): the VERA Core Physics
Benchmark specification (Godfrey, CASL-U-2012-0131-004) states verbatim for
BOTH Problem 6 and Problem 7: "No reference solution exists for this problem at
this time" (pp. 79, 81). P6/P7 define INPUTS ONLY. Every published P6/P7 result
is a code solution (Kelly/CTF, Aviles/COBRA-IE, VERA/MPACT), not a reference
truth. This script therefore performs a CODE-TO-CODE COMPARISON, not validation
against a benchmark standard.

Operating point (Problem 6, from the spec, Tables 1/2/18/P6-1):
    pellet OD 0.8192 cm, clad OD 0.95 cm, clad ID 0.836 cm (gap 84 um)
    rod pitch 1.26 cm, active length 365.76 cm
    264 fuel rods, 24 guide tubes, 1 instrument tube (17x17)
    inlet 565 K, 2250 psia (15.51 MPa), 1300 ppm boron, 3.10 wt% enrichment
    rated assembly power 17.67 MW; 97.4% in fuel; 9% core bypass
    assembly flow 0.6823 Mlbm/hr -> 85.98 kg/s; avg linear heat ~178 W/cm

Reference values compared against (Kelly et al., Nucl. Eng. Technol. 49 (2017)):
    P7 max VOLUME-AVERAGE fuel pin temp = 1065.8 C (Fig. 24)  [NOT centerline]
    P6 subchannel exit coolant spread (max-min) ~ 6.6 K (MC21/CTF & VERA, Fig. 11)
                                               ~ 8.7 K (MC21/COBRA-IE)
    P7 3D local pin-power peaking max = 1.92; radial pin peaking max = 1.37
"""

from __future__ import annotations

import math

import numpy as np

# --- corrected P6 operating point ------------------------------------------
ASSEMBLY_POWER_MW = 17.67
FRAC_IN_FUEL = 0.974
N_FUEL_RODS = 264
ACTIVE_L = 3.6576                     # m
ASSEMBLY_MDOT = 85.98                 # kg/s (0.6823 Mlbm/hr, 9% bypass removed)
T_INLET = 565.0                       # K
GAP_COND = 7500.0                     # W/m2K empirical
RADIAL_PEAK = 1.37                    # published P7 radial pin peaking
AXIAL_PEAK = 1.40                     # chopped-cosine; radial*axial ~ 1.92 (3D)

# average linear heat rate over fuel rods
Q_LIN_AVG = ASSEMBLY_POWER_MW * 1e6 * FRAC_IN_FUEL / (N_FUEL_RODS * ACTIVE_L)
print(f"derived average linear heat rate = {Q_LIN_AVG:.0f} W/m "
      f"({Q_LIN_AVG/100:.1f} W/cm)  [spec ~178 W/cm]", flush=True)


def hot_pin_volavg_fuel_temp() -> dict:
    """Single hot pin, conjugate fuel+coolant, return peak volume-average fuel
    temperature. Volume-average over the parabolic pellet profile is exactly
    (T_centerline + T_pellet_surface) / 2.
    """
    from netflow.bench.fuel_array import build_pin_assembly, cosine_axial_shape

    q_lin_hot = Q_LIN_AVG * RADIAL_PEAK          # this pin's axial-average power
    n_ax = 20
    net, meta = build_pin_assembly(
        n_x=1, n_y=1, n_axial=n_ax, L_total=ACTIVE_L,
        q_lin=q_lin_hot,
        axial_shape=cosine_axial_shape(AXIAL_PEAK),
        coolant_as_unknown=True,
        gap_conductance=GAP_COND,
    )
    res = net.solve_steady(method="newton", tol=1e-6, max_iter=80)

    volavg = []
    centerline = []
    for k in range(n_ax):
        tc = res.states[f"p0_0_z{k}_centerline"]
        ts = res.states[f"p0_0_z{k}_pellet_surface"]
        volavg.append(0.5 * (tc + ts))
        centerline.append(tc)
    peak_volavg = max(volavg)
    peak_centerline = max(centerline)
    return {
        "converged": res.converged,
        "q_lin_hot_avg_Wcm": q_lin_hot / 100,
        "q_lin_local_peak_Wcm": q_lin_hot * AXIAL_PEAK / 100,
        "local_3d_peaking": RADIAL_PEAK * AXIAL_PEAK,
        "peak_volavg_C": peak_volavg - 273.15,
        "peak_centerline_C": peak_centerline - 273.15,
    }


def subchannel_coolant_spread() -> dict:
    """17x17 subchannel coupled T-H at corrected flow; return exit coolant
    spread (max-min over fuel channels) and mean rise.
    """
    from netflow.coupling.subchannel import (
        solve_coupled_subchannel, GUIDE_17,
    )

    N = 17
    n_ax = 10
    q_map, mask = _p6_flat_qmap_and_mask(N)

    # Exit spread is a CALIBRATED quantity (cross-flow coefficients stand in
    # for turbulent momentum mixing the scalar model lacks). Sweep the mixing
    # fraction to show its sensitivity rather than report a single tuned value.
    sweep = {}
    for mix in (0.05, 0.10, 0.20, 0.40):
        result = solve_coupled_subchannel(
            N, n_ax, q_map, GUIDE_17, total_mdot=ASSEMBLY_MDOT,
            guide_K=0.5, K_lat=50.0, lateral_mix_frac=mix,
        )
        fuel_exit = result.coolant_exit[mask]
        sweep[mix] = {
            "converged": result.converged,
            "spread_K": float(fuel_exit.max() - fuel_exit.min()),
            "mean_rise_K": float(fuel_exit.mean() - T_INLET),
        }
    return sweep


def _p6_flat_qmap_and_mask(N: int):
    """Problem-6 power map: nearly FLAT radial power (single enrichment,
    published peaking ~1.05, Kelly Fig. 10), renormalized so the fuel-channel
    average equals Q_LIN_AVG. The P6 coolant spread is geometry-driven
    (guide-tube bypass), not power-driven, so the flat profile is faithful.
    """
    from netflow.coupling.subchannel import GUIDE_17
    mask = np.ones((N, N), dtype=bool)
    for (i, j) in GUIDE_17:
        mask[i, j] = False
    P6_RADIAL_PEAK = 1.05
    cx = cy = (N - 1) / 2
    r_max = math.hypot(cx, cy)
    q_map = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            r = math.hypot(i - cx, j - cy) / r_max
            shape = math.cos(min(r, 1.0) * math.pi / 2)
            q_map[i, j] = (P6_RADIAL_PEAK - 1.0) * shape + 1.0
    q_map *= Q_LIN_AVG / q_map[mask].mean()
    return q_map, mask


def make_subchannel_figure(out_path="results/subchannel_pinresolved.png",
                           mix=0.10):
    """Pin-resolved subchannel figure, generated from the SAME solve as the
    code-comparison table (one source of truth -- ADR-0001). Carries the sourced
    reference labels (6.6 K CTF/VERA, 8.7 K COBRA-IE), never the withdrawn 8.3 K.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from netflow.coupling.subchannel import solve_coupled_subchannel, GUIDE_17

    N, n_ax = 17, 10
    q_map, mask = _p6_flat_qmap_and_mask(N)
    res = solve_coupled_subchannel(
        N, n_ax, q_map, GUIDE_17, total_mdot=ASSEMBLY_MDOT,
        guide_K=0.5, K_lat=50.0, lateral_mix_frac=mix,
    )
    exit_C = res.coolant_exit - 273.15
    fuel_C = res.fuel_centerline - 273.15
    spread = float(res.coolant_exit[mask].max() - res.coolant_exit[mask].min())
    gi = [g[0] for g in GUIDE_17]
    gj = [g[1] for g in GUIDE_17]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    im0 = axes[0].imshow(exit_C.T, origin="lower", cmap="coolwarm")
    axes[0].scatter(gi, gj, s=55, facecolors="none", edgecolors="cyan", linewidths=1.4)
    axes[0].set_title(f"Coolant exit T  (spread {spread:.1f} K)\n"
                      "CTF/VERA 6.6 K · COBRA-IE 8.7 K", fontsize=10)
    fig.colorbar(im0, ax=axes[0], label="°C")

    im1 = axes[1].imshow(fuel_C.T, origin="lower", cmap="inferno")
    axes[1].scatter(gi, gj, s=55, facecolors="none", edgecolors="cyan", linewidths=1.4)
    axes[1].set_title(f"Fuel centerline T (LUMPED est., max {np.nanmax(fuel_C):.0f} °C)\n"
                      "headline = hot-pin volume-avg (table)", fontsize=10)
    fig.colorbar(im1, ax=axes[1], label="°C")

    im2 = axes[2].imshow(res.channel_flow.T, origin="lower", cmap="viridis")
    axes[2].set_title("Channel mass flow (guide-tube bypass)")
    fig.colorbar(im2, ax=axes[2], label="kg/s")
    for ax in axes:
        ax.set_xlabel("pin ix")
        ax.set_ylabel("pin iy")

    fig.suptitle("Subchannel-resolved coupled T-H — generic core at VERA P6 scale "
                 f"(calibrated cross-flow; mix={mix:.2f})", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}  (spread {spread:.1f} K)", flush=True)
    return spread


def make_comparison_figure(out_path="results/vera_comparison.png"):
    """netflow-vs-published comparison (code-to-code) — the 'how well does it
    match' visual. Built from the same solves as the table (one source of truth).
    Panel A: agreement ratio for predicted scalars. Panel B: the calibrated
    coolant spread bracketing the two published code solutions.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fp = hot_pin_volavg_fuel_temp()
    sweep = subchannel_coolant_spread()
    mixes = sorted(sweep)

    # predicted scalars: (label, netflow, published, source)
    nf_fuelT = fp["peak_volavg_C"]
    nf_rise = sweep[0.10]["mean_rise_K"]
    rows = [
        ("peak volume-avg\nfuel T (°C)", nf_fuelT, 1066.0),   # Kelly P7
        ("coolant mean\nrise (K)", nf_rise, 35.5),                 # ~34-37 midpoint
    ]
    ratios = [n / p for _, n, p in rows]
    nf_spreads = [sweep[m]["spread_K"] for m in mixes]

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.3))

    y = list(range(len(rows)))
    axA.axvspan(0.9, 1.1, color="green", alpha=0.08, label="±10%")
    axA.axvline(1.0, color="gray", ls="--", lw=1)
    axA.barh(y, ratios, color="#2c6fbb", height=0.45)
    for i, (lab, n, p) in enumerate(rows):
        axA.text(ratios[i] + 0.012, i,
                 f"netflow {n:.4g} vs {p:.4g}  ({(ratios[i]-1)*100:+.0f}%)",
                 va="center", fontsize=9)
    axA.set_yticks(y)
    axA.set_yticklabels([r[0] for r in rows])
    axA.set_xlim(0.7, 1.35)
    axA.set_xlabel("netflow / published")
    axA.set_title("Predicted scalars vs MC21/CTF [Kelly]\n(shaded = ±10%)")

    axB.plot(mixes, nf_spreads, "o-", color="#c0392b", label="netflow (calibrated)")
    axB.axhline(6.6, color="#2c6fbb", ls="--", label="CTF/VERA 6.6 K")
    axB.axhline(8.7, color="#8e44ad", ls=":", label="COBRA-IE 8.7 K")
    axB.set_xlabel("lateral mixing fraction")
    axB.set_ylabel("coolant exit spread (K)")
    axB.set_ylim(0, 10)
    axB.set_title("Coolant spread is calibration-controlled\n(brackets the published codes)")
    axB.legend(fontsize=8, loc="lower left")

    fig.suptitle("netflow vs published VERA P6/P7 code solutions "
                 "(code-to-code; P6/P7 have no reference solution)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}", flush=True)


if __name__ == "__main__":
    print("\n=== Hot-pin volume-average fuel temperature (vs Kelly P7 1065.8 C) ===",
          flush=True)
    fp = hot_pin_volavg_fuel_temp()
    for k, v in fp.items():
        print(f"  {k:24s} = {v}", flush=True)

    print("\n=== Subchannel exit coolant spread vs mixing coeff "
          "(vs Kelly P6 ~6.6 K CTF/VERA, ~8.7 K COBRA-IE) ===", flush=True)
    sc = subchannel_coolant_spread()
    print(f"  {'mix_frac':>10s} | {'spread_K':>9s} | {'mean_rise_K':>11s} | conv",
          flush=True)
    for mix, v in sc.items():
        print(f"  {mix:>10.2f} | {v['spread_K']:>9.2f} | "
              f"{v['mean_rise_K']:>11.2f} | {v['converged']}", flush=True)
    print("  [expected mean rise ~36 K = 17.21 MW / (85.98 kg/s x 5500 J/kgK)]",
          flush=True)

    print("\n=== regenerating subchannel figure (one source of truth) ===",
          flush=True)
    make_subchannel_figure()
