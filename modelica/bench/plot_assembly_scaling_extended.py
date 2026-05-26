"""Extended assembly scaling plot — through the 25×25 ladder.

Combines existing 17×17 ladder + new 25×25 ladder data into one
log-log scaling curve. Shows where the 1.38 high-end exponent lands and
whether it holds, slides, or breaks at 18×18 / 20×20 / 22×22 / 25×25.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "results")


def _load(name):
    path = os.path.join(OUT_DIR, name)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return json.load(f)


def main() -> int:
    # Original 17×17 ladder from the prior CLOSEOUT (digitised here)
    prior = [
        (16, 10, 8.1),
        (64, 10, 22.7),
        (64, 20, 41.3),
        (289, 10, 105.9),
        (289, 20, 227.2),
        (289, 30, 397.1),
    ]

    # New 25×25 ladder
    ladder = _load("stress_assembly_25x25.json")
    new_points = [(r["n_pin"], r["n_axial"], r["wall_s"])
                  for r in ladder if r.get("ok")]

    if not new_points:
        print("[no step-4 data yet]")
        # Still draw the prior ladder for completeness.
        new_points = []

    fig, ax = plt.subplots(figsize=(8.5, 6))

    # Prior ladder
    px = [p * a for p, _, _ in [(p, a, w) for p, a, w in prior] for a in [_]] if False else None
    px = [p * a for (p, a, _) in prior]
    py = [w for (_, _, w) in prior]
    ax.plot(px, py, "o-", color="#1f77b4", label="prior 17×17 ladder (Assembly17x17)")
    for (p, a, w) in prior:
        ax.annotate(f"{int(np.sqrt(p))}×{int(np.sqrt(p))}×{a}\n{w:.0f}s",
                    xy=(p * a, w), xytext=(5, -10), textcoords="offset points",
                    fontsize=7)

    if new_points:
        nx = [p * a for (p, a, _) in new_points]
        ny = [w for (_, _, w) in new_points]
        ax.plot(nx, ny, "s-", color="#d62728",
                label="2026-05-26 unfreeze 25×25 ladder")
        for (p, a, w) in new_points:
            side = int(np.sqrt(p))
            ax.annotate(f"{side}×{side}×{a}\n{w:.0f}s",
                        xy=(p * a, w), xytext=(5, 10),
                        textcoords="offset points", fontsize=7,
                        color="#d62728")

    # Reference lines for exponent estimates
    # Anchor at 17×17×30 = 8670 nodes, 397 s (vanilla, original measurement).
    anchor_x, anchor_y = 8670, 397.0
    xs = np.array([1000, 30000])
    for exponent, color in [(1.0, "#cccccc"), (1.38, "#aaaaaa"), (1.6, "#888888")]:
        ys = anchor_y * (xs / anchor_x) ** exponent
        ax.plot(xs, ys, "--", color=color, lw=0.8,
                label=f"slope = {exponent} (anchor 17×17×30)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Pin nodes (n_pin × n_axial)")
    ax.set_ylabel("Wall time (s)")
    ax.set_title("PWR assembly wall-time vs problem size — Assembly17x17 + 25×25 extension")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(linestyle=":", alpha=0.4)

    out_path = os.path.join(OUT_DIR, "assembly_scaling_extended.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
