"""Slice 6 visual witness: render axial-profile + time-series figures from the
transient-chain trajectory. F030/F031 — capture the visual artifact and inspect
it; do not defer to 'the human will look'.

Run after slice6_transient_chain.py has passed.
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


N = 10
T_END = 60.0
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "results",
)


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    with new_dymola() as (dymola, work):
        mat = simulate(
            dymola, work,
            "NetflowModelica.Tests.TransientChain",
            stop_time=T_END,
            n_intervals=600,
            tolerance=1e-8,
            result_stem="slice6_plot",
        )
        m = DyMat.DyMatFile(mat)

    t = m.abscissa("T_centerline[1]", valuesOnly=True)
    T_cl = np.array([m.data(f"T_centerline[{i}]") for i in range(1, N + 1)])
    T_co = np.array([m.data(f"T_cool[{i}]") for i in range(1, N + 1)])

    # final-time axial profile
    fig, ax = plt.subplots(figsize=(7, 5))
    cells = np.arange(1, N + 1)
    ax.plot(cells, T_cl[:, -1], marker="o", label="fuel centerline")
    ax.plot(cells, T_co[:, -1], marker="s", label="coolant bulk")
    ax.set_xlabel("axial cell index")
    ax.set_ylabel("T [K]")
    ax.set_title(f"Axial profile at t = {T_END:.0f} s (slice 6 final state)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    p1 = os.path.join(OUT_DIR, "slice6_axial_profile.png")
    fig.tight_layout()
    fig.savefig(p1, dpi=120)
    plt.close(fig)

    # time series at three axial positions
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, lbl in ((1, "centerline cell 1 (inlet)"),
                   (N // 2, f"centerline cell {N // 2} (middle)"),
                   (N, f"centerline cell {N} (outlet)")):
        ax.plot(t, T_cl[i - 1, :], label=lbl)
    ax.plot(t, T_co[N - 1, :], ls="--", color="black", label="outlet coolant bulk")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("T [K]")
    ax.set_title("Startup transient: step power at t=0, cold→full power")
    ax.grid(True, alpha=0.3)
    ax.legend()
    p2 = os.path.join(OUT_DIR, "slice6_timeseries.png")
    fig.tight_layout()
    fig.savefig(p2, dpi=120)
    plt.close(fig)

    print(f"wrote {p1}")
    print(f"wrote {p2}")
    print()
    print("INSPECT EXPECTATIONS:")
    print(" (axial)  monotone-rising T_cool from inlet to outlet (~565 → ~603 K)")
    print("          monotone-rising T_centerline ~660 K above each cell's T_cool")
    print(" (time)   smooth exponential rise, no overshoot (first-order pin)")
    print("          outlet coolant rises slower than inlet centerline (mass transport delay)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
